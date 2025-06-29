"""MCP server for Cordra digital object repository."""

import asyncio
import json
import logging

from mcp.server.fastmcp import FastMCP

from .client import (
    CordraClient,
    CordraClientError,
    CordraNotFoundError,
    CordraAuthenticationError,
)
from .config import CordraConfig

# Initialize the MCP server
mcp = FastMCP("mcp-cordra")

# Initialize Cordra client at startup
config = CordraConfig()
cordra_client = CordraClient(config)

logger = logging.getLogger(__name__)


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

    except ValueError as e:
        raise RuntimeError(f"Invalid parameters: {e}") from e
    except CordraNotFoundError:
        raise RuntimeError(f"Object not found: {object_id}")
    except CordraAuthenticationError as e:
        raise RuntimeError(f"Authentication failed: {e}") from e
    except CordraClientError as e:
        raise RuntimeError(f"Failed to retrieve object {object_id}: {e}") from e


async def create_schema_resource(schema_name: str) -> str:
    """Create content for a specific schema resource."""
    try:
        schema_object = await cordra_client.get_schema(schema_name)
        schema_dict = schema_object.model_dump()
        return json.dumps(schema_dict, indent=2)
    except CordraNotFoundError:
        raise RuntimeError(f"Schema not found: {schema_name}")
    except CordraAuthenticationError as e:
        raise RuntimeError(f"Authentication failed: {e}") from e
    except CordraClientError as e:
        raise RuntimeError(f"Failed to retrieve schema {schema_name}: {e}") from e


async def register_schema_resources():
    """Register individual schema resources dynamically."""
    try:
        # Get all available schemas
        schemas = await cordra_client.find("type:Schema")
        
        # Add individual schema resources
        for schema in schemas:
            if isinstance(schema, dict) and 'content' in schema and 'name' in schema['content']:
                schema_name = schema['content']['name']
                
                # Create an async resource handler for this specific schema
                # Use a closure to capture the schema_name properly
                def make_schema_handler(captured_name):
                    async def schema_handler():
                        return await create_schema_resource(captured_name)
                    return schema_handler
                
                # Register using the decorator approach
                mcp.resource(
                    f"cordra://schemas/{schema_name}",
                    name=f"cordra-schema-{schema_name}",
                    description=f"Cordra schema definition for {schema_name}"
                )(make_schema_handler(schema_name))
                
        logger.info(f"Registered {len(schemas)} schema resources")
        
    except Exception as e:
        logger.warning(f"Failed to register schema resources: {e}")


@mcp.tool()
async def ping() -> str:
    """Simple ping tool to test server connectivity."""
    return "pong"


def main() -> None:
    """Main entry point for the MCP server."""
    async def startup():
        await register_schema_resources()
    
    # Run startup tasks, then start the server
    asyncio.run(startup())
    mcp.run()


if __name__ == "__main__":
    main()
