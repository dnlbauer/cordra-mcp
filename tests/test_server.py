"""Unit tests for the MCP server."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from mcp_cordra.client import CordraClientError, CordraNotFoundError, DigitalObject
from mcp_cordra.server import get_cordra_object


@pytest.fixture
def sample_digital_object():
    """Create a sample DigitalObject for testing."""
    return DigitalObject(
        id="people/john-doe-123",
        type="Person",
        content={
            "name": "John Doe",
            "birthday": "1990-05-15",
            "email": "john.doe@example.com",
        },
        metadata={"created": "2023-01-01", "modified": "2023-06-15"},
        acl={"read": ["public"], "write": ["admin"]},
        payloads=[
            {
                "name": "profile_photo",
                "filename": "john_doe_profile.jpg",
                "size": 125440,
                "mediaType": "image/jpeg"
            }
        ]
    )


class TestGetCordraObject:
    """Test the get_cordra_object resource handler."""

    @patch('mcp_cordra.server.cordra_client')
    async def test_get_object_success(self, mock_client, sample_digital_object):
        """Test successful object retrieval."""
        mock_client.get_object = AsyncMock(return_value=sample_digital_object)

        result = await get_cordra_object("people", "john-doe-123")

        # Verify the result is valid JSON
        parsed_result = json.loads(result)
        assert parsed_result["id"] == "people/john-doe-123"
        assert parsed_result["type"] == "Person"
        assert parsed_result["content"]["name"] == "John Doe"
        assert parsed_result["content"]["birthday"] == "1990-05-15"
        assert parsed_result["metadata"]["created"] == "2023-01-01"
        assert len(parsed_result["payloads"]) == 1
        assert parsed_result["payloads"][0]["name"] == "profile_photo"

        # Verify the client was called with the correct object ID
        mock_client.get_object.assert_called_once_with("people/john-doe-123")

    @patch('mcp_cordra.server.cordra_client')
    async def test_get_object_not_found(self, mock_client):
        """Test object not found exception."""
        mock_client.get_object = AsyncMock(
            side_effect=CordraNotFoundError("Object not found: people/nonexistent")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await get_cordra_object("people", "nonexistent")

        assert "Object not found: people/nonexistent" in str(exc_info.value)
        mock_client.get_object.assert_called_once_with("people/nonexistent")

    @patch('mcp_cordra.server.cordra_client')
    async def test_get_object_client_error(self, mock_client):
        """Test general client error handling."""
        mock_client.get_object = AsyncMock(
            side_effect=CordraClientError("Connection failed")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await get_cordra_object("people", "john-doe-123")

        assert "Failed to retrieve object people/john-doe-123" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)
        mock_client.get_object.assert_called_once_with("people/john-doe-123")

    @patch('mcp_cordra.server.cordra_client')
    async def test_object_id_construction(self, mock_client, sample_digital_object):
        """Test that object ID is correctly constructed from prefix and suffix."""
        mock_client.get_object = AsyncMock(return_value=sample_digital_object)

        # Test various prefix/suffix combinations
        test_cases = [
            ("people", "john-doe-123", "people/john-doe-123"),
            ("documents", "report-2023", "documents/report-2023"),
            ("items", "item_with_underscores", "items/item_with_underscores"),
        ]

        for prefix, suffix, expected_id in test_cases:
            await get_cordra_object(prefix, suffix)
            mock_client.get_object.assert_called_with(expected_id)

    @patch('mcp_cordra.server.cordra_client')
    async def test_json_formatting(self, mock_client, sample_digital_object):
        """Test that the returned JSON is properly formatted."""
        mock_client.get_object = AsyncMock(return_value=sample_digital_object)

        result = await get_cordra_object("people", "john-doe-123")

        # Verify it's valid JSON with proper indentation
        parsed_result = json.loads(result)
        assert isinstance(parsed_result, dict)

        # Check that the result contains indentation (pretty-printed)
        assert "  " in result  # Should have 2-space indentation

        # Verify all expected fields are present
        assert "id" in parsed_result
        assert "type" in parsed_result
        assert "content" in parsed_result
        assert "metadata" in parsed_result
        assert "acl" in parsed_result
        assert "payloads" in parsed_result

    @patch('mcp_cordra.server.cordra_client')
    async def test_minimal_object(self, mock_client):
        """Test handling of object with minimal data."""
        minimal_object = DigitalObject(
            id="test/minimal",
            type="",
            content={"id": "test/minimal"},
            metadata=None,
            acl=None,
            payloads=None
        )
        mock_client.get_object = AsyncMock(return_value=minimal_object)

        result = await get_cordra_object("test", "minimal")
        parsed_result = json.loads(result)

        assert parsed_result["id"] == "test/minimal"
        assert parsed_result["type"] == ""
        assert parsed_result["content"]["id"] == "test/minimal"
        assert parsed_result["metadata"] is None
        assert parsed_result["acl"] is None
        assert parsed_result["payloads"] is None


class TestSchemaResourceFunctions:
    """Test the schema resource functions."""

    @patch('mcp_cordra.server.cordra_client')
    async def test_create_schema_resource_success(self, mock_client):
        """Test successful schema resource creation."""
        mock_schema = DigitalObject(
            id="test/user-schema",
            type="Schema",
            content={"name": "User", "type": "object", "properties": {}}
        )
        mock_client.get_schema = AsyncMock(return_value=mock_schema)

        from mcp_cordra.server import create_schema_resource
        result = await create_schema_resource("User")

        # Verify the result is valid JSON
        parsed_result = json.loads(result)
        assert parsed_result["id"] == "test/user-schema"
        assert parsed_result["type"] == "Schema"
        assert parsed_result["content"]["name"] == "User"

        # Verify the client was called with correct schema name
        mock_client.get_schema.assert_called_once_with("User")

    @patch('mcp_cordra.server.cordra_client')
    async def test_create_schema_resource_not_found(self, mock_client):
        """Test schema resource creation with schema not found."""
        mock_client.get_schema = AsyncMock(side_effect=CordraNotFoundError("Schema not found"))

        from mcp_cordra.server import create_schema_resource
        with pytest.raises(RuntimeError) as exc_info:
            await create_schema_resource("NonExistent")

        assert "Schema not found: NonExistent" in str(exc_info.value)
        mock_client.get_schema.assert_called_once_with("NonExistent")

    @patch('mcp_cordra.server.cordra_client')
    async def test_register_schema_resources_success(self, mock_client):
        """Test successful schema resource registration."""
        mock_schemas = [
            {"content": {"name": "User"}, "id": "test/user-schema"},
            {"content": {"name": "Project"}, "id": "test/project-schema"},
            {"content": {"name": "Document"}, "id": "test/doc-schema"}
        ]
        mock_client.find = AsyncMock(return_value=mock_schemas)

        # Mock the mcp.add_resource method
        with patch('mcp_cordra.server.mcp') as mock_mcp:
            from mcp_cordra.server import register_schema_resources
            await register_schema_resources()

        # Verify the client was called with correct query
        mock_client.find.assert_called_once_with("type:Schema")
        
        # Verify add_resource was called for each schema
        assert mock_mcp.add_resource.call_count == 3

    @patch('mcp_cordra.server.cordra_client')
    async def test_register_schema_resources_missing_name(self, mock_client):
        """Test schema resource registration with objects missing name field."""
        mock_schemas = [
            {"content": {"name": "User"}, "id": "test/user-schema"},
            {"content": {}, "id": "test/no-name-schema"},  # Missing name field
            {"content": {"name": "Project"}, "id": "test/project-schema"}
        ]
        mock_client.find = AsyncMock(return_value=mock_schemas)

        with patch('mcp_cordra.server.mcp') as mock_mcp:
            from mcp_cordra.server import register_schema_resources
            await register_schema_resources()

        # Only 2 schemas should be registered (those with name field)
        assert mock_mcp.add_resource.call_count == 2

    @patch('mcp_cordra.server.cordra_client')
    async def test_register_schema_resources_client_error(self, mock_client):
        """Test schema resource registration with client error."""
        mock_client.find = AsyncMock(side_effect=CordraClientError("Search failed"))

        # Should not raise an exception, just log a warning
        from mcp_cordra.server import register_schema_resources
        await register_schema_resources()  # Should complete without raising

        mock_client.find.assert_called_once_with("type:Schema")
