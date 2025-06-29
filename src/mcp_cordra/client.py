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
            # Use CordraPy to read the object
            cordra_obj = cordra.CordraObject.read(
                host=self.config.cordra_url,  # type: ignore
                obj_id=object_id,
                username=self.config.username,
                password=self.config.password,
                verify=self.config.verify_ssl,
                full=True  # Get full object details including metadata, paylods, etc.
            )

            return DigitalObject(
                id=object_id,
                type=getattr(cordra_obj, 'type', ''),
                content=getattr(cordra_obj, 'content', {}),
                metadata=getattr(cordra_obj, 'metadata', None),
                acl=getattr(cordra_obj, 'acl', None),
                payloads=getattr(cordra_obj, 'payloads', None),
            )

        except Exception as e:
            error_msg = str(e).lower()
            if 'not found' in error_msg or '404' in error_msg:
                raise CordraNotFoundError(f"Object not found: {object_id}") from e
            raise CordraClientError(f"Failed to retrieve object {object_id}: {e}") from e

