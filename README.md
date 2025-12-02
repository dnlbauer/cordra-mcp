# Cordra MCP Server

Cordra is a configurable digital object repository system that stores digital objects as JSON documents
with associated metadata and optional binary payloads.
This Model Context Protocol (MCP) server provides AI assistants with read-only
access to explore and understand Cordra repositories.
This allows AI systems to quickly understand the data model and schema structure
of a Cordra repository and to explore digital objects and their relationships.

![Example](example.gif)

## Features

- **Read-Only Access**: All operations are strictly read-only,
ensuring safe exploration without risk of data modification or corruption.
- **Schema Discovery**: Discover and retrieve schema definitions for each type in the repository.
- **Individual Object Retrieval**: Retrieve specific digital objects by their handle identifier with complete metadata.

## MCP Architecture

### Resources

- `cordra://objects/{prefix}/{suffix}` - Retrieve a specific object by its handle identifier
- `cordra://schemas/{schema_name}` - Schema definition for a specific type.
- `cordra://design` - Design document containing the overall structure and configuration of the Cordra repository.

### Tools

- `get_object` - Retrieve a digital object by its complete ID/handle.
  - `object_id` - Complete object ID (e.g., "test/abc123")
- `search_objects` - Search for digital objects using a query string with pagination support.
  - `query` - Lucene/Solr compatible search query
  - `type` - Optional filter by object type
  - `limit` - Number of results per page (default: 25)
  - `page_num` - Page number to retrieve, 0-based (default: 0)
- `count_objects` - Count the total number of objects matching a query.
  - `query` - Lucene/Solr compatible search query
  - `type` - Optional filter by object type

#### Query Syntax

**CRITICAL**: JSON properties MUST be prefixed with `/`

✅ **Correct Examples:**
- `/title:*report*` - Wildcard search in title field
- `/author/name:Daniel` - Nested property access
- `/status:active AND /priority:high` - Boolean operators
- Use `type` parameter instead of including `type:` in query

❌ **Wrong (will fail):**
- `name:John` - Missing `/` prefix
- `author/name:Daniel` - Missing leading `/`
- `type:Person` - Use the `type` parameter instead

**Operators:** `*` (wildcard), `?` (single char), `AND`, `OR`, `NOT`, `"phrases"`  

## Configuration

The MCP server can be configured using environment variables:

- `CORDRA_BASE_URL` - Cordra server URL (default: `https://localhost:8443`)
- `CORDRA_USERNAME` - Username for authentication (optional)
- `CORDRA_PASSWORD` - Password for authentication (optional)
- `CORDRA_VERIFY_SSL` - SSL certificate verification (default: `true`)
- `CORDRA_TIMEOUT` - Request timeout in seconds (default: `30`)
- `LOGLEVEL` - Logging level (default: `INFO`, options: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)

## Usage

Run the MCP server:

```bash
uv run mcp-cordra
```

### Claude Code

You can add this MCP to Claude Code by registering it in the settings
of your project or creating a `.mcp.json` file in your workdir:

Example using the docker build:

```json
{
  "mcpServers": {
    "cordra": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "CORDRA_BASE_URL",
        "ghcr.io/dnlbauer/cordra-mcp:latest"
      ],
      "env": {
        "CORDRA_BASE_URL": "https://cordra.example.de"
      }
    }
  }
}
```

Example using the python package with `uvx`:

```json
{
  "mcpServers": {
    "cordra": {
      "command": "uvx",
      "args": [
        "cordra-mcp"
      ],
      "env": {
        "CORDRA_BASE_URL": "https://cordra.example.de"
      }
    }
  }
}
```
