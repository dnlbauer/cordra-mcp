"""Unit tests for the Cordra client."""

from unittest.mock import patch

import pytest

from mcp_cordra.client import (
    CordraClient,
    CordraClientError,
    CordraNotFoundError,
    DigitalObject,
)
from mcp_cordra.config import CordraConfig


@pytest.fixture
def config():
    """Create a test configuration."""
    return CordraConfig(
        cordra_url="https://test.example.com",
        username="testuser",
        password="testpass",
        verify_ssl=False,
    )


@pytest.fixture
def client(config):
    """Create a test client."""
    return CordraClient(config)


@pytest.fixture
def mock_cordra_object():
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
                "mediaType": "text/plain"
            },
            {
                "name": "file2.pdf", 
                "filename": "file2.pdf",
                "size": 2048,
                "mediaType": "application/pdf"
            }
        ]
    }


class TestDigitalObject:
    """Test the DigitalObject model."""

    def test_digital_object_creation(self):
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
                    "filename": "file1.txt"
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

    def test_digital_object_optional_fields(self):
        """Test DigitalObject with only required fields."""
        obj = DigitalObject(
            id="test/123",
            type="TestType",
            content={"title": "Test"}
        )

        assert obj.id == "test/123"
        assert obj.type == "TestType"
        assert obj.content == {"title": "Test"}
        assert obj.metadata is None
        assert obj.acl is None
        assert obj.payloads is None


class TestCordraClient:
    """Test the CordraClient class."""

    def test_client_initialization(self, config):
        """Test client initialization."""
        client = CordraClient(config)
        assert client.config == config

    @patch('mcp_cordra.client.cordra.CordraObject.read')
    async def test_get_object_success(self, mock_read, client, mock_cordra_object):
        """Test successful object retrieval."""
        mock_read.return_value = mock_cordra_object

        result = await client.get_object("test/123")

        assert isinstance(result, DigitalObject)
        assert result.id == "test/123"
        assert result.type == "TestType"
        assert result.content == {"title": "Test Object", "description": "A test object"}
        assert result.metadata == {"created": "2023-01-01", "modified": "2023-01-02"}
        assert result.acl == {"read": ["public"], "write": ["admin"]}
        assert result.payloads and len(result.payloads) == 2

        mock_read.assert_called_once_with(
            host="https://test.example.com",
            obj_id="test/123",
            username="testuser",
            password="testpass",
            verify=False,
            full=True
        )

    @patch('mcp_cordra.client.cordra.CordraObject.read')
    async def test_get_object_not_found(self, mock_read, client):
        """Test object not found exception."""
        mock_read.side_effect = Exception("Object not found")

        with pytest.raises(CordraNotFoundError) as exc_info:
            await client.get_object("test/nonexistent")

        assert "Object not found: test/nonexistent" in str(exc_info.value)

    @patch('mcp_cordra.client.cordra.CordraObject.read')
    async def test_get_object_general_error(self, mock_read, client):
        """Test general error handling."""
        mock_read.side_effect = Exception("Connection failed")

        with pytest.raises(CordraClientError) as exc_info:
            await client.get_object("test/123")

        assert "Failed to retrieve object test/123" in str(exc_info.value)

    @patch('mcp_cordra.client.cordra.CordraObject.find')
    async def test_find_success(self, mock_find, client):
        """Test successful find operation."""
        mock_response = {
            "results": [
                {"name": "User", "identifier": "test/user-schema"},
                {"name": "Project", "identifier": "test/project-schema"},
                {"name": "Document", "identifier": "test/doc-schema"}
            ],
            "size": 3
        }
        mock_find.return_value = mock_response
        
        result = await client.find("type:Schema")
        
        assert len(result) == 3
        assert result[0]["name"] == "User"
        assert result[1]["name"] == "Project"
        assert result[2]["name"] == "Document"
        
        mock_find.assert_called_once_with(
            client.config.cordra_url,
            "type:Schema"
        )

    @patch('mcp_cordra.client.cordra.CordraObject.find')
    async def test_find_empty_results(self, mock_find, client):
        """Test find with empty results."""
        mock_response = {"results": [], "size": 0}
        mock_find.return_value = mock_response
        
        result = await client.find("type:NonExistent")
        
        assert result == []
        mock_find.assert_called_once_with(
            client.config.cordra_url,
            "type:NonExistent"
        )

    @patch('mcp_cordra.client.cordra.CordraObject.find')
    async def test_find_no_results_key(self, mock_find, client):
        """Test find with response missing results key."""
        mock_response = {"size": 0}  # No results key
        mock_find.return_value = mock_response
        
        result = await client.find("type:Schema")
        
        assert result == []

    @patch('mcp_cordra.client.cordra.CordraObject.find')
    async def test_find_error(self, mock_find, client):
        """Test find error handling."""
        mock_find.side_effect = Exception("Search failed")
        
        with pytest.raises(CordraClientError) as exc_info:
            await client.find("invalid:query")
        
        assert "Failed to search with query 'invalid:query'" in str(exc_info.value)
        assert "Search failed" in str(exc_info.value)


class TestCordraConfig:
    """Test the CordraConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CordraConfig()
        assert config.cordra_url == "https://localhost:8443"
        assert config.username is None
        assert config.password is None
        assert config.max_search_results == 1000
        assert config.verify_ssl is True
        assert config.timeout == 30
