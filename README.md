# Cordra MCP Server

## About Cordra

Cordra is a configurable digital object repository system that stores digital objects as JSON documents with associated metadata and optional binary payloads. Each object follows a defined JSON schema and is assigned a unique handle identifier using the `prefix/suffix` format. Cordra provides a robust HTTP REST API for data access and supports fine-grained access control, versioning, and flexible schema definitions.

Key Cordra features:
- JSON-based digital objects with schema validation
- Handle-based identifier system for object resolution
- Binary payload attachment support
- Configurable authorization and access control
- RESTful HTTP API for programmatic access
- Flexible schema system with Cordra-specific extensions

## About the MCP Server

This Model Context Protocol (MCP) server provides AI assistants with read-only access to explore and understand Cordra repositories. It enables AI systems to discover data structures, examine object schemas, browse repository contents, and understand repository configuration without making any modifications.

## Purpose

The primary purpose of this MCP server is to assist developers in building applications that integrate with Cordra repositories. By providing AI assistants with repository exploration capabilities, developers can:

- Quickly understand the data model and schema structure
- Explore existing objects and their relationships
- Learn about the repository's configuration and behavior
- Understand access control patterns and permissions
- Discover available binary payloads and their metadata

This exploration capability accelerates the development process by allowing developers to understand repository structure through natural language queries to AI assistants.

## Core Features

### Read-Only Access
All operations are strictly read-only, ensuring safe exploration without risk of data modification or corruption.

### Schema Discovery
Complete access to repository schemas and type definitions, including Cordra-specific schema extensions for UI behavior, auto-generated fields, and object relationships.

### Object Exploration
Search and retrieve digital objects with full metadata, enabling understanding of real data structures and content patterns.

### Configuration Understanding
Access to repository design object and server information to understand behavioral rules, authorization settings, and system capabilities.

### Binary Payload Awareness
Discovery of attached binary files with metadata (names, sizes, types) without downloading the actual content.

## MCP Architecture

### Resources
- `cordra://schemas/` - List all available schema types
- `cordra://schemas/{type_name}` - Schema definition for a specific type
- `cordra://objects/` - Browse repository objects
- `cordra://objects/{object_id}` - Object metadata and content
- `cordra://design_object/` - Repository design configuration

### Tools
#### `search_objects`
Search for objects using queries, filters, and sorting options with pagination support.

**Parameters:**
- `query` (string, optional): Search query
- `type` (string, optional): Filter by object type
- `pageNum` (number, optional): Page number for pagination
- `pageSize` (number, optional): Number of results per page
- `sortFields` (string, optional): Fields to sort by

**Returns:** Search results with object summaries and pagination info

## Configuration

The MCP server requires connection details for the target Cordra instance:

```json
{
  "cordra_url": "https://localhost:8443",
  "username": "your_username",
  "password": "your_password",
  "max_search_results": 1000
}
```

## Security

- All operations are read-only by design
- Authentication credentials are required for repository access
- Respects existing Cordra access control and permissions
- No data modification capabilities to ensure repository safety