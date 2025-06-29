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
    payloads: list[dict[str, Any]] | None = Field(default=None, description="List of payloads")


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
            logger.warning("Only username or password provided, not both. Authentication may fail.")

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
            raise CordraAuthenticationError(f"{context}: Authentication failed (HTTP {status_code})")
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
        url = f"{self.config.cordra_url}/objects/{object_id}"
        params = {"full": "true"}
        
        try:
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            
            if not response.ok:
                self._handle_http_error(response, f"Failed to retrieve object {object_id}")
            
            cordra_obj = response.json()
            
            return DigitalObject(
                id=object_id,
                type=cordra_obj.get('type', ''),
                content=cordra_obj.get('content', cordra_obj),
                metadata=cordra_obj.get('metadata'),
                acl=cordra_obj.get('acl'),
                payloads=cordra_obj.get('payloads'),
            )
            
        except requests.RequestException as e:
            raise CordraClientError(f"Failed to retrieve object {object_id}: {e}") from e

    async def find(self, query: str) -> list[dict[str, Any]]:
        """Find objects using a Cordra query.
        
        Args:
            query: The query string to search for objects
            
        Returns:
            List of objects matching the query as dictionaries
            
        Raises:
            ValueError: If query is empty
            CordraAuthenticationError: If authentication fails
            CordraClientError: For other API errors
        """
        url = f"{self.config.cordra_url}/search"
        params = {"query": query}
        
        try:
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            
            if not response.ok:
                self._handle_http_error(response, f"Failed to search with query '{query}'")
            
            search_result = response.json()
            
            # Extract the results array from the response
            if isinstance(search_result, dict) and 'results' in search_result:
                return search_result['results']
            else:
                return []
        
        except requests.RequestException as e:
            raise CordraClientError(f"Failed to search with query '{query}': {e}") from e