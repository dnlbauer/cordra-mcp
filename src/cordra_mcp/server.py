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
logger.setLevel(config.log_level)


@mcp.tool(
    name="search_objects",
    title="Search Cordra Objects",
    description="""Search for digital objects in the Cordra repository using Lucene/Solr query syntax.

Examples:
- /title:report - Find objects with 'report' in title
- /author:smith - Find objects by author Smith
- /name:John AND type:Person - Complex queries

Pagination:
- Results are paginated with 0-based page numbering
- Use 'limit' to control page size (default: 25)
- Use 'page_num' to specify which page to retrieve (default: 0)

Returns a JSON object containing:
- object_ids: List of object IDs that match the search
- total_count: Total number of objects matching the query
- page_num: Current page number
- page_size: Number of results per page

Use the cordra://objects/{prefix}/{suffix} resources to retrieve full object details.""",
)
async def search_objects(
    query: str,
    type: str | None = None,
    limit: int = 25,
    page_num: int = 0,
) -> str:
    """Search for digital objects in the Cordra repository with pagination support.

    Args:
        query: The search query string (Lucene/Solr compatible). Examples:
               - "/title:report" - Find objects with "report" in title
               - "/author:smith" - Find objects by author Smith
               - "/name:John AND type:Person" - Complex queries
        type: Optional filter by object type (e.g., "Person", "Document", "Project")
        limit: Page size - number of results per page (default: 25)
        page_num: Page number to retrieve, 0-based (default: 0 for first page)

    Returns:
        JSON string containing object IDs and pagination info
    """
    try:
        search_result = await cordra_client.find(
            query, object_type=type, page_size=limit, page_num=page_num
        )

        # Extract only the IDs from the results
        search_result["results"] = [obj["id"] for obj in search_result["results"]]
        # Rename for consistency with documentation
        search_result["total_count"] = search_result.pop("total_size")
        return json.dumps(search_result, indent=2)

    except ValueError as e:
        raise RuntimeError(f"Invalid search parameters: {e}") from e
    except CordraAuthenticationError as e:
        raise RuntimeError(f"Authentication failed: {e}") from e
    except CordraClientError as e:
        raise RuntimeError(f"Search failed: {e}") from e


@mcp.tool(
    name="count_objects",
    title="Count Cordra Objects matching a query",
    description="""Count the total number of digital objects matching a search query.

Examples:
- /title:report - Count objects with 'report' in title
- /author:smith - Count objects by author Smith
- /name:John AND type:Person - Complex queries

Returns the count of objects as integer.
""",
)
async def count_objects(
    query: str,
    type: str | None = None,
) -> str:
    """Count digital objects in the Cordra repository matching a search query.

    Args:
        query: The search query string (Lucene/Solr compatible). Examples:
               - "/title:report" - Count objects with "report" in title
               - "/author:smith" - Count objects by author Smith
               - "/name:John AND type:Person" - Complex queries
        type: Optional filter by object type (e.g., "Person", "Document", "Project")

    Returns:
        integer with the number of objects matching the criteria.
    """
    try:
        # Use page_size=1 to get minimal data, we only need the total count
        search_result = await cordra_client.find(
            query, object_type=type, page_size=1, page_num=0
        )

        total_size: int = search_result["total_size"]
        return str(total_size)
    except ValueError as e:
        raise RuntimeError(f"Invalid search parameters: {e}") from e
    except CordraAuthenticationError as e:
        raise RuntimeError(f"Authentication failed: {e}") from e
    except CordraClientError as e:
        raise RuntimeError(f"Count failed: {e}") from e


@mcp.resource(
    "cordra://objects/{prefix}/{suffix}",
    name="cordra-object",
    title="Retrieve Cordra Digital Object",
    description="Retrieve a Digital Object and Metadata from Cordra by its ID/handle.",
    mime_type="application/json",
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


@mcp.resource(
    "cordra://design",
    name="cordra-design",
    title="Retrieve Cordra Design Object",
    description="Retrieve the Cordra design object containing repository configuration. Administrative privileges are typically required to access this object.",
    mime_type="application/json",
)
async def get_cordra_design() -> str:
    """Retrieve the Cordra design object containing repository configuration.

    The design object is the central location where Cordra stores its configuration,
    including type definitions, workflow configurations, and system settings.
    Administrative privileges are typically required to access this object.

    Returns:
        JSON representation of the design object

    Raises:
        RuntimeError: If the design object is not found, authentication fails, or there's an API error
    """
    try:
        design_object = await cordra_client.get_design()
        object_dict = design_object.model_dump()
        return json.dumps(object_dict, indent=2)

    except CordraNotFoundError as e:
        raise RuntimeError("Design object not found") from e
    except CordraAuthenticationError as e:
        raise RuntimeError(f"Authentication failed: {e}") from e
    except CordraClientError as e:
        raise RuntimeError(f"Failed to retrieve design object: {e}") from e


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
        # Get all available schemas using pagination
        all_schemas = []
        page_num = 0
        page_size = 20

        while True:
            search_result = await cordra_client.find(
                "type:Schema", page_size=page_size, page_num=page_num
            )
            schemas = search_result["results"]
            all_schemas.extend(schemas)

            # Check if we've retrieved all schemas
            if len(schemas) < page_size:
                break

            page_num += 1

        for schema in all_schemas:
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
                    title=f"Cordra Type Schema: {schema_name}",
                    description=f"Retrieve the JSON schema for the Cordra Type {schema_name}",
                    mime_type="application/json",
                )
            )

        logger.info(f"Registered {len(all_schemas)} schema resources")

    except Exception as e:
        logger.warning(f"Failed to register schema resources: {e}")


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
