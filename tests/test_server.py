"""Unit tests for the MCP server."""

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from cordra_mcp.client import (
    CordraAuthenticationError,
    CordraClientError,
    CordraNotFoundError,
    DigitalObject,
)
from cordra_mcp.server import (
    count_objects,
    get_cordra_design,
    get_cordra_object,
    get_object,
    search_objects,
)


@pytest.fixture
def sample_digital_object() -> DigitalObject:
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
                "mediaType": "image/jpeg",
            }
        ],
    )


class TestGetCordraObject:
    """Test the get_cordra_object resource handler."""

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_object_success(
        self, mock_client: Any, sample_digital_object: DigitalObject
    ) -> None:
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

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_object_not_found(self, mock_client: Any) -> None:
        """Test object not found exception."""
        mock_client.get_object = AsyncMock(
            side_effect=CordraNotFoundError("Object not found: people/nonexistent")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await get_cordra_object("people", "nonexistent")

        assert "Object not found: people/nonexistent" in str(exc_info.value)
        mock_client.get_object.assert_called_once_with("people/nonexistent")

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_object_client_error(self, mock_client: Any) -> None:
        """Test general client error handling."""
        mock_client.get_object = AsyncMock(
            side_effect=CordraClientError("Connection failed")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await get_cordra_object("people", "john-doe-123")

        assert "Failed to retrieve object people/john-doe-123" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)
        mock_client.get_object.assert_called_once_with("people/john-doe-123")

    @patch("cordra_mcp.server.cordra_client")
    async def test_object_id_construction(
        self, mock_client: Any, sample_digital_object: DigitalObject
    ) -> None:
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

    @patch("cordra_mcp.server.cordra_client")
    async def test_json_formatting(
        self, mock_client: Any, sample_digital_object: DigitalObject
    ) -> None:
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

    @patch("cordra_mcp.server.cordra_client")
    async def test_minimal_object(self, mock_client: Any) -> None:
        """Test handling of object with minimal data."""
        minimal_object = DigitalObject(
            id="test/minimal",
            type="",
            content={"id": "test/minimal"},
            metadata=None,
            acl=None,
            payloads=None,
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


class TestGetObject:
    """Test the get_object tool."""

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_object_success(
        self, mock_client: Any, sample_digital_object: DigitalObject
    ) -> None:
        """Test successful object retrieval with complete ID."""
        mock_client.get_object = AsyncMock(return_value=sample_digital_object)

        result = await get_object("people/john-doe-123")

        # Verify the result is valid JSON
        parsed_result = json.loads(result)
        assert parsed_result["id"] == "people/john-doe-123"
        assert parsed_result["type"] == "Person"
        assert parsed_result["content"]["name"] == "John Doe"

        # Verify the client was called with the correct object ID
        mock_client.get_object.assert_called_once_with("people/john-doe-123")

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_object_not_found(self, mock_client: Any) -> None:
        """Test object not found exception."""
        mock_client.get_object = AsyncMock(
            side_effect=CordraNotFoundError("Object not found: test/nonexistent")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await get_object("test/nonexistent")

        assert "Object not found: test/nonexistent" in str(exc_info.value)
        mock_client.get_object.assert_called_once_with("test/nonexistent")

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_object_client_error(self, mock_client: Any) -> None:
        """Test general client error handling."""
        mock_client.get_object = AsyncMock(
            side_effect=CordraClientError("Connection failed")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await get_object("test/obj123")

        assert "Failed to retrieve object test/obj123" in str(exc_info.value)
        mock_client.get_object.assert_called_once_with("test/obj123")

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_object_authentication_error(self, mock_client: Any) -> None:
        """Test authentication error handling."""
        mock_client.get_object = AsyncMock(
            side_effect=CordraAuthenticationError("Authentication failed")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await get_object("test/obj123")

        assert "Authentication failed" in str(exc_info.value)
        mock_client.get_object.assert_called_once_with("test/obj123")


class TestSchemaResourceFunctions:
    """Test the schema resource functions."""

    @patch("cordra_mcp.server.cordra_client")
    async def test_create_schema_resource_success(self, mock_client: Any) -> None:
        """Test successful schema resource creation."""
        mock_schema = DigitalObject(
            id="test/user-schema",
            type="Schema",
            content={"name": "User", "type": "object", "properties": {}},
        )
        mock_client.get_schema = AsyncMock(return_value=mock_schema)

        from cordra_mcp.server import create_schema_resource

        result = await create_schema_resource("User")

        # Verify the result is valid JSON
        parsed_result = json.loads(result)
        assert parsed_result["id"] == "test/user-schema"
        assert parsed_result["type"] == "Schema"
        assert parsed_result["content"]["name"] == "User"

        # Verify the client was called with correct schema name
        mock_client.get_schema.assert_called_once_with("User")

    @patch("cordra_mcp.server.cordra_client")
    async def test_create_schema_resource_not_found(self, mock_client: Any) -> None:
        """Test schema resource creation with schema not found."""
        mock_client.get_schema = AsyncMock(
            side_effect=CordraNotFoundError("Schema not found")
        )

        from cordra_mcp.server import create_schema_resource

        with pytest.raises(RuntimeError) as exc_info:
            await create_schema_resource("NonExistent")

        assert "Schema not found: NonExistent" in str(exc_info.value)
        mock_client.get_schema.assert_called_once_with("NonExistent")

    @patch("cordra_mcp.server.cordra_client")
    async def test_register_schema_resources_success(self, mock_client: Any) -> None:
        """Test successful schema resource registration."""
        mock_search_result = {
            "results": [
                {"content": {"name": "User"}, "id": "test/user-schema"},
                {"content": {"name": "Project"}, "id": "test/project-schema"},
                {"content": {"name": "Document"}, "id": "test/doc-schema"},
            ],
            "total_size": 3,
            "page_num": 0,
            "page_size": 20,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        # Mock the mcp.add_resource method
        with patch("cordra_mcp.server.mcp") as mock_mcp:
            from cordra_mcp.server import register_schema_resources

            await register_schema_resources()

        # Verify the client was called with correct query
        mock_client.find.assert_called_once_with(
            "type:Schema", page_size=20, page_num=0
        )

        # Verify add_resource was called for each schema
        assert mock_mcp.add_resource.call_count == 3

    @patch("cordra_mcp.server.cordra_client")
    async def test_register_schema_resources_missing_name(
        self, mock_client: Any
    ) -> None:
        """Test schema resource registration with objects missing name field."""
        mock_search_result = {
            "results": [
                {"content": {"name": "User"}, "id": "test/user-schema"},
                {"content": {}, "id": "test/no-name-schema"},  # Missing name field
                {"content": {"name": "Project"}, "id": "test/project-schema"},
            ],
            "total_size": 3,
            "page_num": 0,
            "page_size": 20,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        with patch("cordra_mcp.server.mcp") as mock_mcp:
            from cordra_mcp.server import register_schema_resources

            await register_schema_resources()

        # Only 2 schemas should be registered (those with name field)
        assert mock_mcp.add_resource.call_count == 2

    @patch("cordra_mcp.server.cordra_client")
    async def test_register_schema_resources_client_error(
        self, mock_client: Any
    ) -> None:
        """Test schema resource registration with client error."""
        mock_client.find = AsyncMock(side_effect=CordraClientError("Search failed"))

        # Should not raise an exception, just log a warning
        from cordra_mcp.server import register_schema_resources

        await register_schema_resources()  # Should complete without raising

        mock_client.find.assert_called_once_with(
            "type:Schema", page_size=20, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_register_schema_resources_pagination(self, mock_client: Any) -> None:
        """Test schema resource registration with pagination."""
        # Mock multiple pages of results
        # First page with full 20 results (simulating more schemas)
        first_page_schemas = [
            {"content": {"name": f"Schema{i}"}, "id": f"test/schema{i}"}
            for i in range(20)
        ]
        first_page = {
            "results": first_page_schemas,
            "total_size": 25,
            "page_num": 0,
            "page_size": 20,
        }

        # Second page with fewer results (indicating last page)
        second_page = {
            "results": [
                {"content": {"name": "Document"}, "id": "test/doc-schema"},
            ],
            "total_size": 25,
            "page_num": 1,
            "page_size": 20,
        }

        # Return first page, then second page (with fewer results indicating last page)
        mock_client.find = AsyncMock(side_effect=[first_page, second_page])

        with patch("cordra_mcp.server.mcp") as mock_mcp:
            from cordra_mcp.server import register_schema_resources

            await register_schema_resources()

        # Verify pagination calls
        assert mock_client.find.call_count == 2
        mock_client.find.assert_any_call("type:Schema", page_size=20, page_num=0)
        mock_client.find.assert_any_call("type:Schema", page_size=20, page_num=1)

        # Verify all 21 schemas were registered (20 from first page + 1 from second page)
        assert mock_mcp.add_resource.call_count == 21


class TestSearchObjects:
    """Test the search_objects tool."""

    @patch("cordra_mcp.server.cordra_client")
    async def test_search_objects_success(self, mock_client: Any) -> None:
        """Test successful object search."""
        mock_search_result = {
            "results": [
                {
                    "id": "people/john-doe",
                    "type": "Person",
                    "content": {"name": "John Doe"},
                },
                {
                    "id": "people/jane-smith",
                    "type": "Person",
                    "content": {"name": "Jane Smith"},
                },
            ],
            "total_size": 2,
            "page_num": 0,
            "page_size": 1000,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        result = await search_objects("name:John")

        # Verify the result is valid JSON
        parsed_result = json.loads(result)
        assert parsed_result["results"] == ["people/john-doe", "people/jane-smith"]
        assert parsed_result["total_count"] == 2
        assert parsed_result["page_num"] == 0
        assert parsed_result["page_size"] == 1000

        # Verify the client was called with correct parameters
        mock_client.find.assert_called_once_with(
            "name:John", object_type=None, page_size=25, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_search_objects_with_type_filter(self, mock_client: Any) -> None:
        """Test object search with type filter."""
        mock_search_result = {
            "results": [
                {
                    "id": "people/john-doe",
                    "type": "Person",
                    "content": {"name": "John Doe"},
                },
            ],
            "total_size": 1,
            "page_num": 0,
            "page_size": 1000,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        result = await search_objects("name:John", type="Person")

        # Verify the result is valid JSON
        parsed_result = json.loads(result)
        assert parsed_result["results"] == ["people/john-doe"]
        assert parsed_result["total_count"] == 1

        # Verify the client was called with type filter
        mock_client.find.assert_called_once_with(
            "name:John", object_type="Person", page_size=25, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_search_objects_with_limit(self, mock_client: Any) -> None:
        """Test object search with custom limit."""
        mock_search_result = {
            "results": [
                {
                    "id": "people/john-doe",
                    "type": "Person",
                    "content": {"name": "John Doe"},
                },
            ],
            "total_size": 1,
            "page_num": 0,
            "page_size": 50,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        result = await search_objects("name:John", limit=50)

        # Verify the result is valid JSON with new format
        parsed_result = json.loads(result)
        assert parsed_result["results"] == ["people/john-doe"]
        assert parsed_result["page_size"] == 50

        # Verify the client was called with custom limit
        mock_client.find.assert_called_once_with(
            "name:John", object_type=None, page_size=50, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_search_objects_with_all_parameters(self, mock_client: Any) -> None:
        """Test object search with all parameters."""
        mock_search_result = {
            "results": [
                {
                    "id": "documents/report-123",
                    "type": "Document",
                    "content": {"title": "Report"},
                },
            ],
            "total_size": 1,
            "page_num": 0,
            "page_size": 25,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        result = await search_objects("title:Report", type="Document", limit=25)

        # Verify the result is valid JSON
        parsed_result = json.loads(result)
        assert parsed_result["results"] == ["documents/report-123"]
        assert parsed_result["total_count"] == 1

        # Verify the client was called with all parameters
        mock_client.find.assert_called_once_with(
            "title:Report", object_type="Document", page_size=25, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_search_objects_empty_results(self, mock_client: Any) -> None:
        """Test object search with no results."""
        mock_search_result = {
            "results": [],
            "total_size": 0,
            "page_num": 0,
            "page_size": 1000,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        result = await search_objects("nonexistent:data")

        # Verify the result is valid JSON with empty array
        parsed_result = json.loads(result)
        assert parsed_result["results"] == []
        assert parsed_result["total_count"] == 0

        mock_client.find.assert_called_once_with(
            "nonexistent:data", object_type=None, page_size=25, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_search_objects_with_slash_prefixed_properties(
        self, mock_client: Any
    ) -> None:
        """Test object search with correct slash-prefixed property syntax."""
        mock_search_result = {
            "results": [
                {
                    "id": "reports/2024-annual",
                    "type": "Document",
                    "content": {"title": "Annual Report 2024"},
                },
            ],
            "total_size": 1,
            "page_num": 0,
            "page_size": 25,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        # Test with slash-prefixed property and nested property
        result = await search_objects("/title:*report* AND /author/name:Daniel")

        parsed_result = json.loads(result)
        assert parsed_result["results"] == ["reports/2024-annual"]
        assert parsed_result["total_count"] == 1

        mock_client.find.assert_called_once_with(
            "/title:*report* AND /author/name:Daniel",
            object_type=None,
            page_size=25,
            page_num=0,
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_search_objects_client_error(self, mock_client: Any) -> None:
        """Test object search with client error."""
        mock_client.find = AsyncMock(side_effect=CordraClientError("Search failed"))

        with pytest.raises(RuntimeError) as exc_info:
            await search_objects("test:query")

        assert "Search failed:" in str(exc_info.value)
        mock_client.find.assert_called_once_with(
            "test:query", object_type=None, page_size=25, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_search_objects_value_error(self, mock_client: Any) -> None:
        """Test object search with value error."""
        mock_client.find = AsyncMock(side_effect=ValueError("Invalid query"))

        with pytest.raises(RuntimeError) as exc_info:
            await search_objects("invalid:query")

        assert "Invalid search parameters:" in str(exc_info.value)
        mock_client.find.assert_called_once_with(
            "invalid:query", object_type=None, page_size=25, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_search_objects_json_formatting(self, mock_client: Any) -> None:
        """Test that search results are properly formatted as JSON."""
        mock_search_result = {
            "results": [
                {"id": "test/object", "type": "Test", "content": {"data": "value"}},
            ],
            "total_size": 1,
            "page_num": 0,
            "page_size": 1000,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        result = await search_objects("test:query")

        # Verify it's valid JSON with proper indentation
        parsed_result = json.loads(result)
        assert isinstance(parsed_result, dict)

        # Check that the result contains indentation (pretty-printed)
        assert "  " in result  # Should have 2-space indentation

        # Verify the content is correctly formatted
        assert parsed_result["results"] == ["test/object"]
        assert parsed_result["total_count"] == 1

    @patch("cordra_mcp.server.cordra_client")
    async def test_search_objects_with_page_num(self, mock_client: Any) -> None:
        """Test object search with page number parameter."""
        mock_search_result = {
            "results": [
                {
                    "id": "documents/doc-21",
                    "type": "Document",
                    "content": {"title": "Page 2 Doc"},
                },
            ],
            "total_size": 50,
            "page_num": 1,
            "page_size": 20,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        await search_objects("type:Document", page_num=1)

        # Verify the client was called with correct page number
        mock_client.find.assert_called_once_with(
            "type:Document", object_type=None, page_size=25, page_num=1
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_search_objects_with_all_pagination_params(
        self, mock_client: Any
    ) -> None:
        """Test object search with all pagination parameters."""
        mock_search_result = {
            "results": [
                {
                    "id": "reports/report-51",
                    "type": "Report",
                    "content": {"title": "Report 51"},
                },
            ],
            "total_size": 100,
            "page_num": 5,
            "page_size": 10,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        await search_objects("type:Report", type="Report", limit=10, page_num=5)

        # Verify the client was called with all parameters
        mock_client.find.assert_called_once_with(
            "type:Report", object_type="Report", page_size=10, page_num=5
        )


class TestGetCordraDesign:
    """Test the get_cordra_design resource handler."""

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_design_success(self, mock_client: Any) -> None:
        """Test successful design object retrieval."""
        mock_design = DigitalObject(
            id="design",
            type="CordraDesign",
            content={
                "types": {"User": {}, "Project": {}},
                "workflows": {},
                "systemConfig": {"serverName": "test-cordra"},
            },
            metadata={"created": "2023-01-01", "modified": "2023-06-15"},
        )
        mock_client.get_design = AsyncMock(return_value=mock_design)

        result = await get_cordra_design()

        # Verify the result is valid JSON
        parsed_result = json.loads(result)
        assert parsed_result["id"] == "design"
        assert parsed_result["type"] == "CordraDesign"
        assert parsed_result["content"]["systemConfig"]["serverName"] == "test-cordra"
        assert "types" in parsed_result["content"]
        assert "workflows" in parsed_result["content"]

        # Verify the client was called
        mock_client.get_design.assert_called_once()

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_design_not_found(self, mock_client: Any) -> None:
        """Test design object not found exception."""
        mock_client.get_design = AsyncMock(
            side_effect=CordraNotFoundError("Design object not found")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await get_cordra_design()

        assert "Design object not found" in str(exc_info.value)
        mock_client.get_design.assert_called_once()

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_design_authentication_error(self, mock_client: Any) -> None:
        """Test design object authentication error."""
        mock_client.get_design = AsyncMock(
            side_effect=CordraAuthenticationError("Authentication failed")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await get_cordra_design()

        assert "Authentication failed" in str(exc_info.value)
        mock_client.get_design.assert_called_once()

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_design_client_error(self, mock_client: Any) -> None:
        """Test design object general client error."""
        mock_client.get_design = AsyncMock(
            side_effect=CordraClientError("Connection failed")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await get_cordra_design()

        assert "Failed to retrieve design object" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)
        mock_client.get_design.assert_called_once()

    @patch("cordra_mcp.server.cordra_client")
    async def test_get_design_json_formatting(self, mock_client: Any) -> None:
        """Test that the design object is properly formatted as JSON."""
        mock_design = DigitalObject(
            id="design",
            type="CordraDesign",
            content={"data": "value"},
            metadata={"created": "2023-01-01"},
        )
        mock_client.get_design = AsyncMock(return_value=mock_design)

        result = await get_cordra_design()

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


class TestCountObjects:
    """Test the count_objects tool."""

    @patch("cordra_mcp.server.cordra_client")
    async def test_count_objects_success(self, mock_client: Any) -> None:
        """Test successful object count."""
        mock_search_result = {
            "results": [{"id": "people/john-doe", "type": "Person"}],
            "total_size": 42,
            "page_num": 0,
            "page_size": 1,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        result = await count_objects("name:John")

        # Verify the result is a string representation of the count
        assert result == "42"

        # Verify the client was called with correct parameters
        mock_client.find.assert_called_once_with(
            "name:John", object_type=None, page_size=1, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_count_objects_with_type_filter(self, mock_client: Any) -> None:
        """Test object count with type filter."""
        mock_search_result = {
            "results": [{"id": "people/john-doe", "type": "Person"}],
            "total_size": 15,
            "page_num": 0,
            "page_size": 1,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        result = await count_objects("name:John", type="Person")

        # Verify the result is a string representation of the count
        assert result == "15"

        # Verify the client was called with type filter
        mock_client.find.assert_called_once_with(
            "name:John", object_type="Person", page_size=1, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_count_objects_zero_results(self, mock_client: Any) -> None:
        """Test object count with zero results."""
        mock_search_result = {
            "results": [],
            "total_size": 0,
            "page_num": 0,
            "page_size": 1,
        }
        mock_client.find = AsyncMock(return_value=mock_search_result)

        result = await count_objects("nonexistent:data")

        # Verify the result is "0"
        assert result == "0"

        mock_client.find.assert_called_once_with(
            "nonexistent:data", object_type=None, page_size=1, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_count_objects_client_error(self, mock_client: Any) -> None:
        """Test object count with client error."""
        mock_client.find = AsyncMock(side_effect=CordraClientError("Search failed"))

        with pytest.raises(RuntimeError) as exc_info:
            await count_objects("test:query")

        assert "Count failed:" in str(exc_info.value)
        mock_client.find.assert_called_once_with(
            "test:query", object_type=None, page_size=1, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_count_objects_value_error(self, mock_client: Any) -> None:
        """Test object count with value error."""
        mock_client.find = AsyncMock(side_effect=ValueError("Invalid query"))

        with pytest.raises(RuntimeError) as exc_info:
            await count_objects("invalid:query")

        assert "Invalid search parameters:" in str(exc_info.value)
        mock_client.find.assert_called_once_with(
            "invalid:query", object_type=None, page_size=1, page_num=0
        )

    @patch("cordra_mcp.server.cordra_client")
    async def test_count_objects_authentication_error(self, mock_client: Any) -> None:
        """Test object count with authentication error."""
        mock_client.find = AsyncMock(
            side_effect=CordraAuthenticationError("Authentication failed")
        )

        with pytest.raises(RuntimeError) as exc_info:
            await count_objects("test:query")

        assert "Authentication failed:" in str(exc_info.value)
        mock_client.find.assert_called_once_with(
            "test:query", object_type=None, page_size=1, page_num=0
        )
