# Cordra MCP Server

Cordra is a configurable digital object repository system that stores digital objects as JSON documents
with associated metadata and optional binary payloads.
This Model Context Protocol (MCP) server provides AI assistants with read-only
access to explore and understand Cordra repositories.
This allows AI systems to quickly understand the data model and schema structure
of a Cordra repository and to explore digital objects and their relationships.

## Features

- **Read-Only Access**: All operations are strictly read-only,
ensuring safe exploration without risk of data modification or corruption.
- **Schema Discovery**: Discover and retrieve schema definitions for each type in the repository.
- **Individual Object Retrieval**: Retrieve specific digital objects by their handle identifier with complete metadata.

## MCP Architecture

### Resources

- `cordra://objects/{prefix}/{suffix}` - Retrieve a specific object by its handle identifier
- `cordra://schemas/{schema_name}` - Schema definition for a specific type.

### Tools

Currently, none.

## Configuration

The MCP server can be configured using environment variables with the `MCP_CORDRA_` prefix or a `.env` file:

- `MCP_CORDRA_BASE_URL` - Cordra server URL (default: `https://localhost:8443`)
- `MCP_CORDRA_USERNAME` - Username for authentication (optional)
- `MCP_CORDRA_PASSWORD` - Password for authentication (optional)
- `MCP_CORDRA_VERIFY_SSL` - SSL certificate verification (default: `true`)
- `MCP_CORDRA_TIMEOUT` - Request timeout in seconds (default: `30`)
- `MCP_CORDRA_MAX_SEARCH_RESULTS` - Maximum search results (default: `1000`)

## Usage

Run the MCP server:

```bash
uv run mcp-cordra
```
