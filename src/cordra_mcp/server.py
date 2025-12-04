"""MCP server for Cordra digital object repository."""

import json
import logging

from mcp.server.fastmcp import FastMCP

from . import __version__
from .client import (
    CordraAuthenticationError,
    CordraClient,
    CordraClientError,
    CordraNotFoundError,
)
from .config import CordraConfig

# Initialize the MCP server
config = CordraConfig()
mcp = FastMCP("cordra-mcp", host=config.host, port=8000)

# Initialize Cordra client at startup
cordra_client = CordraClient(config)

logger = logging.getLogger(__name__)
logger.setLevel(config.log_level)


@mcp.tool(
    name="search_objects",
    title="Search Cordra Objects",
    description="""Search for digital objects using Lucene/Solr query syntax.

CRITICAL SYNTAX RULES:
1. Properties MUST start with '/' - Example: /title:report
2. Nested properties: /parent/child:value
3. Use 'type' parameter - NEVER 'type:' in query
4. Operators: * ? AND OR NOT "phrases"

✅ CORRECT:
- /title:*report* /author/name:Daniel
- /status:active AND /priority:high
- query="/title:report", type="Document"

❌ WRONG:
- name:John (missing /)
- author/name:Daniel (missing /)
- type:Person (use type parameter)

Returns: {results: [ids], total_count, page_num, page_size}
Pagination: limit (default 25), page_num (0-based)""",
)
async def search_objects(
    query: str,
    type: str | None = None,
    limit: int = 25,
    page_num: int = 0,
) -> str:
    """Search for digital objects in the Cordra repository with pagination support.

    Args:
        query: Search query (Lucene/Solr). Properties MUST start with '/'.
               ✅ CORRECT: /title:*report*, /author/name:Daniel
               ❌ WRONG: name:John, author/name:Daniel, type:Person
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
- type:Person - Find all Persons. Note that "type" is special and uses no slash "/"
- /author/name:Daniel - Find objects with author Daniel as nested property.
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
        query: Search query (Lucene/Solr). Properties MUST start with '/'.
               ✅ CORRECT: /title:*report*, /author/name:Daniel
               ❌ WRONG: name:John, author/name:Daniel, type:Person
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


@mcp.tool(
    name="get_object",
    title="Get Cordra Object by ID",
    description="""Retrieve a digital object by its complete ID/handle.

Returns: Full object with metadata as JSON
Example: get_object("test/abc123")""",
)
async def get_object(object_id: str) -> str:
    """Retrieve a Cordra digital object by its complete ID.

    Args:
        object_id: The complete object ID/handle (e.g., "test/abc123" or "wildlive/7a4b7b65f8bb155ad36d")

    Returns:
        JSON string containing the complete digital object with all metadata

    Raises:
        RuntimeError: If the object is not found or there's an API error
    """
    try:
        digital_object = await cordra_client.get_object(object_id)
        object_dict = digital_object.model_dump()
        return json.dumps(object_dict, indent=2)

    except ValueError as e:
        raise RuntimeError(f"Invalid object ID: {e}") from e
    except CordraNotFoundError as e:
        raise RuntimeError(f"Object not found: {object_id}") from e
    except CordraAuthenticationError as e:
        raise RuntimeError(f"Authentication failed: {e}") from e
    except CordraClientError as e:
        raise RuntimeError(f"Failed to retrieve object {object_id}: {e}") from e


@mcp.tool(
    name="get_design_object",
    title="Get Cordra Design Object",
    description="""
    The design object is the central location where Cordra stores its configuration,
    including type definitions, workflow configurations, and system settings.
    Administrative privileges are typically required to access this object.

    Returns: The design object as JSON
""",
)
async def get_cordra_design_object() -> str:
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


@mcp.tool(
    name="list_types",
    title="List Available Types",
    description="""List all available object types in the Cordra repository.

Returns a list of type names that are defined in the repository as json array.""",
)
async def list_types() -> str:
    """List all available types in the Cordra repository.

    Returns:
        JSON string containing a list of type names

    Raises:
        RuntimeError: If there's an API error or authentication failure
    """
    try:
        # Get all available types using pagination
        all_types = []
        page_num = 0
        page_size = 20

        while True:
            search_result = await cordra_client.find(
                "type:Schema", page_size=page_size, page_num=page_num
            )
            schemas = search_result["results"]

            for schema in schemas:
                type_name = schema.get("content", {}).get("name")
                if type_name:
                    all_types.append(type_name)

            # Check if we've retrieved all schemas
            if len(schemas) < page_size:
                break

            page_num += 1

        all_types.sort()
        return json.dumps(all_types, indent=2)

    except CordraAuthenticationError as e:
        raise RuntimeError(f"Authentication failed: {e}") from e
    except CordraClientError as e:
        raise RuntimeError(f"Failed to list types: {e}") from e


@mcp.tool(
    name="get_type_schema",
    title="Get Type Schema",
    description="""Retrieve the JSON schema definition for a specific type.

Args:
    type_name: The name of the type (e.g., "Person", "Document", "Project")

Returns: The full schema definition as JSON""",
)
async def get_type_schema(type_name: str) -> str:
    """Retrieve the JSON schema definition for a specific object type.

    Args:
        type_name: The name of the type to retrieve the schema for

    Returns:
        JSON string containing the schema definition

    Raises:
        RuntimeError: If the type is not found, authentication fails, or there's an API error
    """
    try:
        schema_object = await cordra_client.get_schema(type_name)
        schema_dict = schema_object.model_dump()
        return json.dumps(schema_dict, indent=2)
    except CordraNotFoundError as e:
        raise RuntimeError(f"Type '{type_name}' not found") from e
    except CordraAuthenticationError as e:
        raise RuntimeError(f"Authentication failed: {e}") from e
    except CordraClientError as e:
        raise RuntimeError(
            f"Failed to retrieve schema for type '{type_name}': {e}"
        ) from e


def main() -> None:
    """Main entry point for the MCP server."""
    logger.info(f"Starting Cordra MCP server v{__version__}...")
    if config.run_mode == "stdio":
        mcp.run()
    else:
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
