"""MCP server for Cordra digital object repository."""

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from .client import CordraClient, CordraClientError, CordraNotFoundError
from .config import CordraConfig

# Initialize the MCP server
mcp = FastMCP("mcp-cordra")

# Initialize Cordra client at startup
config = CordraConfig()
cordra_client = CordraClient(config)


@mcp.resource("cordra://objects/{prefix}/{suffix}", name="cordra-object", description="Retrieve a Cordra digital object by ID")
async def get_cordra_object(prefix: str, suffix: str) -> str:
    """Retrieve a Cordra digital object by its ID.
    
    Args:
        prefix: The prefix part of the object ID (e.g., 'wildlive')
        suffix: The suffix part of the object ID (e.g., '7a4b7b65f8bb155ad36d')
        
    Returns:
        JSON representation of the digital object
        
    Raises:
        RuntimeError: If the object is not found or there's an API error
    """
    object_id = f"{prefix}/{suffix}"
    try:
        digital_object = await cordra_client.get_object(object_id)
        object_dict = digital_object.model_dump()
        return json.dumps(object_dict, indent=2)

    except CordraNotFoundError as e:
        raise RuntimeError(f"Object not found: {object_id}") from e
    except CordraClientError as e:
        raise RuntimeError(f"Failed to retrieve object {object_id}: {e}") from e


@mcp.resource("cordra://schemas", name="cordra-schemas-list", description="List available Cordra type schemas")
async def list_cordra_schemas() -> str:
    """List available Cordra type schemas.
    
    Returns:
        JSON array of available schema names
        
    Raises:
        RuntimeError: If there's an API error
    """
    try:
        # Use the client's find method to get all schema objects
        schemas = await cordra_client.find("type:Schema")
        
        # Extract the names from the schema objects
        schema_names = []
        for schema in schemas:
            if isinstance(schema, dict) and 'name' in schema:
                schema_names.append(schema['name'])
        
        result = {
            "schemas": schema_names,
            "count": len(schema_names)
        }
        return json.dumps(result, indent=2)
        
    except Exception as e:
        raise RuntimeError(f"Failed to list schemas: {e}") from e


@mcp.tool()
async def ping() -> str:
    """Simple ping tool to test server connectivity."""
    return "pong"


def main() -> None:
    """Main entry point for the MCP server."""
    asyncio.run(mcp.run())  # type: ignore


if __name__ == "__main__":
    main()
