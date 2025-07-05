"""Cordra client wrapper using HTTP requests."""

import logging
from typing import Any

import requests
from pydantic import BaseModel, Field

from .config import CordraConfig

logger = logging.getLogger(__name__)


class DigitalObject(BaseModel):
    """Model for a Cordra digital object."""

    id: str = Field(description="Object identifier")
    type: str = Field(description="Object type")
    content: dict[str, Any] = Field(description="Object content as JSON")
    metadata: dict[str, Any] | None = Field(default=None, description="Object metadata")
    acl: dict[str, Any] | None = Field(default=None, description="Access control list")
    payloads: list[dict[str, Any]] | None = Field(
        default=None, description="List of payloads"
    )


class CordraClientError(Exception):
    """Base exception for Cordra client errors."""

    pass


class CordraNotFoundError(CordraClientError):
    """Exception raised when an object is not found."""

    pass


class CordraAuthenticationError(CordraClientError):
    """Exception raised for authentication/authorization failures."""

    pass


class CordraClient:
    """Client for interacting with Cordra repository using HTTP requests."""

    def __init__(self, config: CordraConfig) -> None:
        """Initialize the Cordra client.

        Args:
            config: Configuration settings for the Cordra connection
        """
        self.config = config
        self.session = requests.Session()
        self.session.verify = config.verify_ssl

        # Set up authentication
        if config.username and config.password:
            self.session.auth = (config.username, config.password)
        elif config.username or config.password:
            logger.warning(
                "Only username or password provided, not both. Authentication may fail."
            )

    def _handle_http_error(self, response: requests.Response, context: str) -> None:
        """Handle HTTP errors and raise appropriate exceptions.

        Args:
            response: The HTTP response object
            context: Context description for the error message

        Raises:
            CordraNotFoundError: For 404 errors
            CordraAuthenticationError: For 401/403 errors
            CordraClientError: For other HTTP errors
        """
        status_code = response.status_code
        if status_code == 404:
            raise CordraNotFoundError(f"{context}: Resource not found")
        elif status_code in (401, 403):
            raise CordraAuthenticationError(
                f"{context}: Authentication failed (HTTP {status_code})"
            )
        elif status_code >= 500:
            raise CordraClientError(f"{context}: Server error (HTTP {status_code})")
        else:
            raise CordraClientError(f"{context}: HTTP error {status_code}")

    async def get_object(self, object_id: str) -> DigitalObject:
        """Retrieve a digital object by its ID.

        Args:
            object_id: The unique identifier of the object to retrieve

        Returns:
            The full digital object

        Raises:
            ValueError: If object_id is empty
            CordraNotFoundError: If the object is not found
            CordraAuthenticationError: If authentication fails
            CordraClientError: For other API errors
        """
        url = f"{self.config.base_url}/objects/{object_id}"
        params = {"full": "true"}

        try:
            response = self.session.get(url, params=params, timeout=self.config.timeout)

            if not response.ok:
                self._handle_http_error(
                    response, f"Failed to retrieve object {object_id}"
                )

            cordra_obj = response.json()

            return DigitalObject(
                id=object_id,
                type=cordra_obj.get("type", ""),
                content=cordra_obj.get("content", cordra_obj),
                metadata=cordra_obj.get("metadata"),
                acl=cordra_obj.get("acl"),
                payloads=cordra_obj.get("payloads"),
            )

        except requests.RequestException as e:
            raise CordraClientError(
                f"Failed to retrieve object {object_id}: {e}"
            ) from e

    async def find(self, query: str, object_type: str | None = None, page_size: int = 20, page_num: int = 0) -> dict[str, Any]:
        """Find objects using a Cordra query with pagination support.

        Args:
            query: The query string to search for objects
            object_type: Optional filter by object type
            page_size: Number of results per page (if None, no limit)
            page_num: Page number to retrieve (0-based, default: 0)

        Returns:
            Dict containing:
            - results: List of objects matching the query as dictionaries
            - total_size: Total number of results available
            - page_num: Current page number
            - page_size: Number of results per page

        Raises:
            ValueError: If query is empty
            CordraAuthenticationError: If authentication fails
            CordraClientError: For other API errors
        """
        # Construct the final query with type filter if specified
        final_query = query
        if object_type:
            final_query = f"type:{object_type} AND ({query})"

        url = f"{self.config.base_url}/search"
        params = {
            "query": final_query,
            "pageSize": str(page_size),
            "pageNum": str(page_num),
        }

        try:
            response = self.session.get(url, params=params, timeout=self.config.timeout)

            if not response.ok:
                self._handle_http_error(
                    response, f"Failed to search with query '{final_query}'"
                )

            search_result = response.json()

            return {
                "results": search_result["results"],
                "total_size": search_result["size"],
                "page_num": search_result["pageNum"],
                "page_size": search_result["pageSize"]
            }

        except requests.RequestException as e:
            raise CordraClientError(
                f"Failed to search with query '{final_query}': {e}"
            ) from e

    async def get_schema(self, schema_name: str) -> DigitalObject:
        """Retrieve a schema definition by its name.

        Args:
            schema_name: The name of the schema to retrieve

        Returns:
            The schema object containing the type definition

        Raises:
            CordraNotFoundError: If the schema is not found
            CordraAuthenticationError: If authentication fails
            CordraClientError: For other API errors
        """
        # Search for the specific schema by name using correct query format
        query = f"type:Schema AND /name:{schema_name}"

        try:
            search_result = await self.find(query)
            schemas = search_result["results"]

            if not schemas:
                raise CordraNotFoundError(f"Schema '{schema_name}' not found")

            # Get the first matching schema (should be unique by name)
            schema_data = schemas[0]

            # Get the full schema object using its ID
            return await self.get_object(schema_data["id"])

        except (CordraNotFoundError, CordraAuthenticationError):
            raise
        except Exception as e:
            raise CordraClientError(
                f"Failed to retrieve schema '{schema_name}': {e}"
            ) from e

    async def get_design(self) -> DigitalObject:
        """Retrieve the Cordra design object containing repository configuration.

        The design object contains the central configuration for the Cordra repository
        including type definitions, workflow configurations, and system settings.
        Administrative privileges are typically required to access this object.

        Returns:
            The design object as a DigitalObject

        Raises:
            CordraNotFoundError: If the design object is not found
            CordraAuthenticationError: If authentication fails or insufficient privileges
            CordraClientError: For other API errors
        """
        url = f"{self.config.base_url}/api/objects/design"

        try:
            response = self.session.get(url, timeout=self.config.timeout)

            if not response.ok:
                self._handle_http_error(
                    response, "Failed to retrieve design object"
                )

            design_obj = response.json()

            return DigitalObject(
                id="design",
                type=design_obj.get("type", "CordraDesign"),
                content=design_obj.get("content", design_obj),
                metadata=design_obj.get("metadata"),
                acl=design_obj.get("acl"),
                payloads=design_obj.get("payloads"),
            )

        except requests.RequestException as e:
            raise CordraClientError(
                f"Failed to retrieve design object: {e}"
            ) from e
