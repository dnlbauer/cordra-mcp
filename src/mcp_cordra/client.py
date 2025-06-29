"""Cordra client wrapper using CordraPy."""

from typing import Any

import cordra
from pydantic import BaseModel, Field

from .config import CordraConfig


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


class CordraClient:
    """Client for interacting with Cordra repository."""

    def __init__(self, config: CordraConfig) -> None:
        """Initialize the Cordra client.
        
        Args:
            config: Configuration settings for the Cordra connection
        """
        self.config = config

    async def get_object(self, object_id: str) -> DigitalObject:
        """Retrieve a digital object by its ID.
        
        Args:
            object_id: The unique identifier of the object to retrieve
            
        Returns:
            The full digital object
            
        Raises:
            CordraNotFoundError: If the object is not found
            CordraClientError: For other API errors
        """
        try:
            cordra_obj: dict[str, Any] = cordra.CordraObject.read(
                host=self.config.cordra_url,  #type: ignore
                obj_id=object_id,
                username=self.config.username,
                password=self.config.password,
                verify=self.config.verify_ssl,
                full=True  # Get full object details including metadata, paylods, etc.
            )

            return DigitalObject(
                id=object_id,
                type=cordra_obj['type'],
                content=cordra_obj['content'],
                metadata=cordra_obj.get('metadata'),
                acl=cordra_obj.get('acl'),
                payloads=cordra_obj.get('payloads'),
            )

        except Exception as e:
            error_msg = str(e).lower()
            if 'not found' in error_msg or '404' in error_msg:
                raise CordraNotFoundError(f"Object not found: {object_id}") from e
            raise CordraClientError(f"Failed to retrieve object {object_id}: {e}") from e

    async def find(self, query: str) -> list[dict[str, Any]]:
        """Find objects using a Cordra query.
        
        Args:
            query: The query string to search for objects
            
        Returns:
            List of objects matching the query as dictionaries
            
        Raises:
            CordraClientError: If there's an API error
        """
        try:
            # Use CordraPy to find objects
            # TODO - need to handle pagination, but the CordraPy API does not support it.
            response: dict[str, Any] = cordra.CordraObject.find(
                self.config.cordra_url,  # type: ignore
                query
            )
            
            # Extract the results array from the response
            if isinstance(response, dict) and 'results' in response:
                return response['results']
            else:
                return []
        
        except Exception as e:
            raise CordraClientError(f"Failed to search with query '{query}': {e}") from e

