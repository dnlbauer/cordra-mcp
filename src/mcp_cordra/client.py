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
            # Build URL: cordra_base_url/objects/prefix/postfix
            url = f"{self.config.cordra_url}/objects/{object_id}"
            
            # Add full=true parameter to get complete object details
            params = {"full": "true"}
            
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            
            if response.status_code == 404:
                raise CordraNotFoundError(f"Object not found: {object_id}")
            
            response.raise_for_status()
            cordra_obj = response.json()

            return DigitalObject(
                id=object_id,
                type=cordra_obj.get('type', ''),
                content=cordra_obj.get('content', cordra_obj),
                metadata=cordra_obj.get('metadata'),
                acl=cordra_obj.get('acl'),
                payloads=cordra_obj.get('payloads'),
            )

        except CordraNotFoundError:
            raise
        except requests.RequestException as e:
            raise CordraClientError(f"Failed to retrieve object {object_id}: {e}") from e
        except Exception as e:
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
            # Use HTTP GET request to search endpoint
            url = f"{self.config.cordra_url}/search"
            params = {"query": query}
            
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            
            search_result = response.json()
            
            # Extract the results array from the response
            if isinstance(search_result, dict) and 'results' in search_result:
                return search_result['results']
            else:
                return []
        
        except requests.RequestException as e:
            raise CordraClientError(f"Failed to search with query '{query}': {e}") from e
        except Exception as e:
            raise CordraClientError(f"Failed to search with query '{query}': {e}") from e