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