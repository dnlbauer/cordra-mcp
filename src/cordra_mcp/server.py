"""MCP server for Cordra digital object repository."""

import asyncio
import json
import logging

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.resources import FunctionResource

from .client import (
    CordraAuthenticationError,
    CordraClient,
    CordraClientError,
    CordraNotFoundError,
)
from .config import CordraConfig

# Initialize the MCP server
mcp = FastMCP("cordra-mcp")

# Initialize Cordra client at startup
config = CordraConfig()
cordra_client = CordraClient(config)

logger = logging.getLogger(__name__)


@mcp.resource(
    "cordra://objects/{prefix}/{suffix}",
    name="cordra-object",
    description="Retrieve a Cordra digital object by ID",
)
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
    except CordraNotFoundError as e:
        raise RuntimeError(f"Object not found: {object_id}") from e
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
    except CordraNotFoundError as e:
        raise RuntimeError(f"Schema not found: {schema_name}") from e
    except CordraAuthenticationError as e:
        raise RuntimeError(f"Authentication failed: {e}") from e
    except CordraClientError as e:
        raise RuntimeError(f"Failed to retrieve schema {schema_name}: {e}") from e


async def register_schema_resources() -> None:
    """Register individual schema resources dynamically."""
    try:
        # Get all available schemas
        schemas = await cordra_client.find("type:Schema")

        for schema in schemas:
            schema_name = schema.get("content", {}).get("name")
            if not schema_name:
                logger.warning("Schema without a name found, skipping.")
                continue

            logger.info(f"Registering schema resource for cordra type {schema_name}")

            async def schema_fn(name: str = schema_name) -> str:
                return await create_schema_resource(name)

            mcp.add_resource(
                FunctionResource.from_function(
                    uri=f"cordra://schemas/{schema_name}",
                    fn=schema_fn,
                    name=f"cordra-type-schema-{schema_name}",
                    description=f"JSON schema for Cordra type {schema_name}",
                )
            )

        logger.info(f"Registered {len(schemas)} schema resources")

    except Exception as e:
        logger.warning(f"Failed to register schema resources: {e}")


@mcp.tool()
async def ping() -> str:
    """Simple ping tool to test server connectivity."""
    return "pong"


async def initialize_server() -> None:
    """Initialize server resources before starting."""
    logger.info("Initializing Cordra MCP server...")
    await register_schema_resources()
    logger.info("Server initialization complete")


def main() -> None:
    """Main entry point for the MCP server."""
    asyncio.run(initialize_server())
    mcp.run()


if __name__ == "__main__":
    main()
