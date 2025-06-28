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

## Operations

The MCP server provides eight essential operations:

### 1. `get_object`
Retrieve a specific digital object by its ID or handle, including all metadata and content.

**Parameters:**
- `id` (string): Object identifier or handle

**Returns:** Complete object JSON with metadata

### 2. `search_objects`
Search for objects using queries, filters, and sorting options with pagination support.

**Parameters:**
- `query` (string, optional): Search query
- `type` (string, optional): Filter by object type
- `pageNum` (number, optional): Page number for pagination
- `pageSize` (number, optional): Number of results per page
- `sortFields` (string, optional): Fields to sort by

**Returns:** Search results with object summaries and pagination info

### 3. `list_schemas`
List all available schemas/types in the repository.

**Returns:** Array of schema names and basic information

### 4. `get_schema`
Retrieve detailed schema definition for a specific object type.

**Parameters:**
- `type` (string): Schema/type name

**Returns:** Complete JSON schema with Cordra-specific extensions

### 5. `list_payloads`
List binary payloads attached to a specific object.

**Parameters:**
- `id` (string): Object identifier or handle

**Returns:** Array of payload metadata (names, sizes, content types)

### 6. `get_object_acl`
Retrieve access control list for a specific object.

**Parameters:**
- `id` (string): Object identifier or handle

**Returns:** Object permissions including readers and writers

### 7. `get_server_info`
Get server version, capabilities, and technical information.

**Returns:** Server metadata and configuration details

### 8. `get_design_object`
Retrieve the repository's design object containing behavioral configuration.

**Returns:** Repository configuration including authorization settings, handle minting rules, and UI behavior

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