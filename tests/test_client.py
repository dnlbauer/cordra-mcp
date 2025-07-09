"""Unit tests for the Cordra client."""

from typing import Any
from unittest.mock import patch

import pytest

from cordra_mcp.client import (
    CordraAuthenticationError,
    CordraClient,
    CordraClientError,
    CordraNotFoundError,
    DigitalObject,
)
from cordra_mcp.config import CordraConfig


@pytest.fixture
def config() -> CordraConfig:
    """Create a test configuration."""
    return CordraConfig(
        base_url="https://test.example.com",
        username="testuser",
        password="testpass",
        verify_ssl=False,
    )


@pytest.fixture
def client(config: CordraConfig) -> CordraClient:
    """Create a test client."""
    return CordraClient(config)


@pytest.fixture
def mock_cordra_object() -> dict[str, Any]:
    """Create a mock CordraObject response (dictionary)."""
    return {
        "type": "TestType",
        "content": {"title": "Test Object", "description": "A test object"},
        "metadata": {"created": "2023-01-01", "modified": "2023-01-02"},
        "acl": {"read": ["public"], "write": ["admin"]},
        "payloads": [
            {
                "name": "file1.txt",
                "filename": "file1.txt",
                "size": 1024,
                "mediaType": "text/plain",
            },
            {
                "name": "file2.pdf",
                "filename": "file2.pdf",
                "size": 2048,
                "mediaType": "application/pdf",
            },
        ],
    }


class TestDigitalObject:
    """Test the DigitalObject model."""

    def test_digital_object_creation(self) -> None:
        """Test creating a DigitalObject."""
        obj = DigitalObject(
            id="test/123",
            type="TestType",
            content={"title": "Test"},
            metadata={"created": "2023-01-01"},
            acl={"read": ["public"]},
            payloads=[
                {
                    "name": "file1.txt",
                    "mediaType": "text/plain",
                    "size": 1024,
                    "filename": "file1.txt",
                }
            ],
        )

        assert obj.id == "test/123"
        assert obj.type == "TestType"
        assert obj.content == {"title": "Test"}
        assert obj.metadata == {"created": "2023-01-01"}
        assert obj.acl == {"read": ["public"]}
        assert obj.payloads and len(obj.payloads) == 1
        payload = obj.payloads[0]
        assert payload["name"] == "file1.txt"
        assert payload["mediaType"] == "text/plain"
        assert payload["size"] == 1024
        assert payload["filename"] == "file1.txt"

    def test_digital_object_optional_fields(self) -> None:
        """Test DigitalObject with only required fields."""
        obj = DigitalObject(id="test/123", type="TestType", content={"title": "Test"})

        assert obj.id == "test/123"
        assert obj.type == "TestType"
        assert obj.content == {"title": "Test"}
        assert obj.metadata is None
        assert obj.acl is None
        assert obj.payloads is None


class TestCordraClient:
    """Test the CordraClient class."""

    def test_client_initialization(self, config: CordraConfig) -> None:
        """Test client initialization."""
        client = CordraClient(config)
        assert client.config == config

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_get_object_success(self, mock_get: Any, client: CordraClient, mock_cordra_object: dict[str, Any]) -> None:
        """Test successful object retrieval."""
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = mock_cordra_object
        mock_response.raise_for_status.return_value = None

        result = await client.get_object("test/123")

        assert isinstance(result, DigitalObject)
        assert result.id == "test/123"
        assert result.type == "TestType"
        assert result.content == {
            "title": "Test Object",
            "description": "A test object",
        }
        assert result.metadata == {"created": "2023-01-01", "modified": "2023-01-02"}
        assert result.acl == {"read": ["public"], "write": ["admin"]}
        assert result.payloads and len(result.payloads) == 2

        mock_get.assert_called_once_with(
            "https://test.example.com/objects/test/123",
            params={"full": "true"},
            timeout=30,
        )

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_get_object_not_found(self, mock_get: Any, client: CordraClient) -> None:
        """Test object not found exception."""
        mock_response = mock_get.return_value
        mock_response.status_code = 404
        mock_response.ok = False

        with pytest.raises(CordraNotFoundError) as exc_info:
            await client.get_object("test/nonexistent")

        assert "Resource not found" in str(exc_info.value)

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_get_object_general_error(self, mock_get: Any, client: CordraClient) -> None:
        """Test general error handling."""
        from requests import RequestException

        mock_get.side_effect = RequestException("Connection failed")

        with pytest.raises(CordraClientError) as exc_info:
            await client.get_object("test/123")

        assert "Failed to retrieve object test/123" in str(exc_info.value)

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_find_success(self, mock_get: Any, client: CordraClient) -> None:
        """Test successful find operation."""
        mock_response_data = {
            "results": [
                {"name": "User", "identifier": "test/user-schema"},
                {"name": "Project", "identifier": "test/project-schema"},
                {"name": "Document", "identifier": "test/doc-schema"},
            ],
            "size": 3,
            "pageNum": 0,
            "pageSize": 20,
        }
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None

        result = await client.find("type:Schema")

        assert isinstance(result, dict)
        assert len(result["results"]) == 3
        assert result["results"][0]["name"] == "User"
        assert result["results"][1]["name"] == "Project"
        assert result["results"][2]["name"] == "Document"
        assert result["total_size"] == 3
        assert result["page_num"] == 0
        assert result["page_size"] == 20

        mock_get.assert_called_once_with(
            "https://test.example.com/search",
            params={"query": "type:Schema", "pageSize": "20", "pageNum": "0"},
            timeout=30,
        )

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_find_empty_results(self, mock_get: Any, client: CordraClient) -> None:
        """Test find with empty results."""
        mock_response_data = {"results": [], "size": 0, "pageNum": 0, "pageSize": 20}
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None

        result = await client.find("type:NonExistent")

        assert isinstance(result, dict)
        assert result["results"] == []
        assert result["total_size"] == 0
        assert result["page_num"] == 0
        assert result["page_size"] == 20
        mock_get.assert_called_once_with(
            "https://test.example.com/search",
            params={"query": "type:NonExistent", "pageSize": "20", "pageNum": "0"},
            timeout=30,
        )

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_find_error(self, mock_get: Any, client: CordraClient) -> None:
        """Test find error handling."""
        from requests import RequestException

        mock_get.side_effect = RequestException("Search failed")

        with pytest.raises(CordraClientError) as exc_info:
            await client.find("invalid:query")

        assert "Failed to search with query 'invalid:query'" in str(exc_info.value)
        assert "Search failed" in str(exc_info.value)

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_find_with_type_filter(self, mock_get: Any, client: CordraClient) -> None:
        """Test find operation with type filter constructs correct query."""
        mock_response_data = {"results": [], "size": 0, "pageNum": 0, "pageSize": 20}
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.ok = True

        await client.find("name:John", object_type="Person")

        mock_get.assert_called_once_with(
            "https://test.example.com/search",
            params={"query": "type:Person AND (name:John)", "pageSize": "20", "pageNum": "0"},
            timeout=30,
        )

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_find_with_page_size(self, mock_get: Any, client: CordraClient) -> None:
        """Test find operation with custom page size."""
        mock_response_data = {"results": [], "size": 0, "pageNum": 0, "pageSize": 50}
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.ok = True

        await client.find("type:Test", page_size=50)

        mock_get.assert_called_once_with(
            "https://test.example.com/search",
            params={"query": "type:Test", "pageSize": "50", "pageNum": "0"},
            timeout=30,
        )

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_find_with_type_and_page_size(self, mock_get: Any, client: CordraClient) -> None:
        """Test find operation with both type filter and page size."""
        mock_response_data = {"results": [], "size": 0, "pageNum": 0, "pageSize": 25}
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.ok = True

        await client.find("title:Report", object_type="Document", page_size=25)

        mock_get.assert_called_once_with(
            "https://test.example.com/search",
            params={"query": "type:Document AND (title:Report)", "pageSize": "25", "pageNum": "0"},
            timeout=30,
        )

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_find_default_params(self, mock_get: Any, client: CordraClient) -> None:
        """Test find operation with default parameters."""
        mock_response_data = {"results": [], "size": 0, "pageNum": 0, "pageSize": 20}
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.ok = True

        await client.find("content:test")

        mock_get.assert_called_once_with(
            "https://test.example.com/search",
            params={"query": "content:test", "pageSize": "20", "pageNum": "0"},
            timeout=30,
        )

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_find_with_page_num(self, mock_get: Any, client: CordraClient) -> None:
        """Test find operation with specific page number."""
        mock_response_data = {"results": [], "size": 100, "pageNum": 2, "pageSize": 20}
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.ok = True

        result = await client.find("type:Schema", page_num=2)

        assert result["page_num"] == 2
        assert result["page_size"] == 20
        assert result["total_size"] == 100
        mock_get.assert_called_once_with(
            "https://test.example.com/search",
            params={"query": "type:Schema", "pageSize": "20", "pageNum": "2"},
            timeout=30,
        )

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_find_with_custom_page_size_and_num(self, mock_get: Any, client: CordraClient) -> None:
        """Test find operation with custom page size and page number."""
        mock_response_data = {"results": [], "size": 500, "pageNum": 5, "pageSize": 10}
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.ok = True

        result = await client.find("type:Document", page_size=10, page_num=5)

        assert result["page_num"] == 5
        assert result["page_size"] == 10
        assert result["total_size"] == 500
        mock_get.assert_called_once_with(
            "https://test.example.com/search",
            params={"query": "type:Document", "pageSize": "10", "pageNum": "5"},
            timeout=30,
        )

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_get_design_success(self, mock_get: Any, client: CordraClient) -> None:
        """Test successful design object retrieval."""
        mock_design_data = {
            "type": "CordraDesign",
            "content": {
                "types": {"User": {}, "Project": {}},
                "workflows": {},
                "systemConfig": {"serverName": "test-cordra"}
            },
            "metadata": {"created": "2023-01-01", "modified": "2023-06-15"}
        }
        mock_response = mock_get.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = mock_design_data
        mock_response.ok = True

        result = await client.get_design()

        assert isinstance(result, DigitalObject)
        assert result.id == "design"
        assert result.type == "CordraDesign"
        assert result.content["systemConfig"]["serverName"] == "test-cordra"

        mock_get.assert_called_once_with(
            "https://test.example.com/api/objects/design",
            timeout=30,
        )

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_get_design_authentication_error(self, mock_get: Any, client: CordraClient) -> None:
        """Test design object retrieval with authentication error."""
        mock_response = mock_get.return_value
        mock_response.status_code = 403
        mock_response.ok = False

        with pytest.raises(CordraAuthenticationError) as exc_info:
            await client.get_design()

        assert "Authentication failed" in str(exc_info.value)

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_get_design_not_found(self, mock_get: Any, client: CordraClient) -> None:
        """Test design object retrieval with not found error."""
        mock_response = mock_get.return_value
        mock_response.status_code = 404
        mock_response.ok = False

        with pytest.raises(CordraNotFoundError) as exc_info:
            await client.get_design()

        assert "Resource not found" in str(exc_info.value)

    @patch("cordra_mcp.client.requests.Session.get")
    async def test_get_design_request_error(self, mock_get: Any, client: CordraClient) -> None:
        """Test design object retrieval with request error."""
        from requests import RequestException

        mock_get.side_effect = RequestException("Connection failed")

        with pytest.raises(CordraClientError) as exc_info:
            await client.get_design()

        assert "Failed to retrieve design object" in str(exc_info.value)


class TestCordraConfig:
    """Test the CordraConfig class."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CordraConfig()
        assert config.base_url == "https://localhost:8443"
        assert config.username is None
        assert config.password is None
        assert config.verify_ssl is True
        assert config.timeout == 30
