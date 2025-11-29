"""Unit tests for Bugzilla MCP tools"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastmcp.exceptions import ToolError, PromptError
import bugzilla_mcp.utils as utils
from bugzilla_mcp.tools.bugzilla import (
    bug_info,
    bug_comments,
    add_comment,
    bugs_quicksearch,
    learn_quicksearch_syntax,
    server_url,
    bug_url,
)


class TestBugInfoTool:
    """Tests for bug_info tool"""

    async def test_bug_info_success(self, set_bugzilla_client):
        """Test successful bug_info call"""
        result = await bug_info(12345)
        
        assert result["id"] == 12345
        assert result["product"] == "Firefox"
        set_bugzilla_client.bug_info.assert_called_once_with(12345)

    async def test_bug_info_raises_on_missing_client(self, reset_bugzilla_client):
        """Test bug_info raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await bug_info(12345)
        
        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_bug_info_raises_on_api_error(self, set_bugzilla_client):
        """Test bug_info raises ToolError on API error"""
        set_bugzilla_client.bug_info = AsyncMock(side_effect=Exception("API Error"))
        
        with pytest.raises(ToolError) as exc_info:
            await bug_info(12345)
        
        assert "Failed to fetch bug info" in str(exc_info.value)
        assert "API Error" in str(exc_info.value)


class TestBugCommentsTool:
    """Tests for bug_comments tool"""

    async def test_bug_comments_public_only(self, set_bugzilla_client):
        """Test bug_comments returns only public comments by default"""
        result = await bug_comments(12345)
        
        # Should only include public comments
        assert len(result) == 2
        for comment in result:
            assert comment["is_private"] is False

    async def test_bug_comments_include_private(self, set_bugzilla_client):
        """Test bug_comments includes private comments when requested"""
        result = await bug_comments(12345, include_private_comments=True)
        
        # Should include all comments
        assert len(result) == 3
        private_comments = [c for c in result if c["is_private"]]
        assert len(private_comments) == 1

    async def test_bug_comments_raises_on_missing_client(self, reset_bugzilla_client):
        """Test bug_comments raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await bug_comments(12345)
        
        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_bug_comments_raises_on_api_error(self, set_bugzilla_client):
        """Test bug_comments raises ToolError on API error"""
        set_bugzilla_client.bug_comments = AsyncMock(side_effect=Exception("API Error"))
        
        with pytest.raises(ToolError) as exc_info:
            await bug_comments(12345)
        
        assert "Failed to fetch bug comments" in str(exc_info.value)


class TestAddCommentTool:
    """Tests for add_comment tool"""

    async def test_add_comment_public(self, set_bugzilla_client):
        """Test adding a public comment"""
        result = await add_comment(12345, "Test comment", is_private=False)
        
        assert result["id"] == 2001
        set_bugzilla_client.add_comment.assert_called_once_with(12345, "Test comment", False)

    async def test_add_comment_private(self, set_bugzilla_client):
        """Test adding a private comment"""
        set_bugzilla_client.add_comment = AsyncMock(return_value={"id": 2002})
        result = await add_comment(12345, "Private comment", is_private=True)
        
        assert result["id"] == 2002
        set_bugzilla_client.add_comment.assert_called_once_with(12345, "Private comment", True)

    async def test_add_comment_default_not_private(self, set_bugzilla_client):
        """Test that comments are public by default"""
        await add_comment(12345, "Default comment")
        
        # Verify is_private defaults to False
        set_bugzilla_client.add_comment.assert_called_once_with(12345, "Default comment", False)

    async def test_add_comment_raises_on_missing_client(self, reset_bugzilla_client):
        """Test add_comment raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await add_comment(12345, "Test comment")
        
        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_add_comment_raises_on_api_error(self, set_bugzilla_client):
        """Test add_comment raises ToolError on API error"""
        set_bugzilla_client.add_comment = AsyncMock(side_effect=Exception("Permission denied"))
        
        with pytest.raises(ToolError) as exc_info:
            await add_comment(12345, "Test comment")
        
        assert "Failed to create a comment" in str(exc_info.value)


class TestBugsQuicksearchTool:
    """Tests for bugs_quicksearch tool"""

    async def test_bugs_quicksearch_success(self, set_bugzilla_client):
        """Test successful quicksearch"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bugs": [
                {
                    "id": 12345,
                    "product": "Firefox",
                    "component": "General",
                    "assigned_to": "developer@example.com",
                    "status": "NEW",
                    "resolution": "",
                    "summary": "Test bug",
                    "last_change_time": "2023-01-20T15:45:00Z",
                },
            ]
        }
        set_bugzilla_client.client.get = AsyncMock(return_value=mock_response)
        
        result = await bugs_quicksearch("test query")
        
        assert len(result) == 1
        assert result[0]["bug_id"] == 12345
        assert result[0]["product"] == "Firefox"
        assert result[0]["summary"] == "Test bug"

    async def test_bugs_quicksearch_extracts_essential_fields(self, set_bugzilla_client):
        """Test that quicksearch returns only essential fields"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bugs": [
                {
                    "id": 12345,
                    "product": "Firefox",
                    "component": "General",
                    "assigned_to": "developer@example.com",
                    "status": "NEW",
                    "resolution": "",
                    "summary": "Test bug",
                    "last_change_time": "2023-01-20T15:45:00Z",
                    "extra_field": "should not be included",
                    "creation_time": "2023-01-15T10:30:00Z",
                },
            ]
        }
        set_bugzilla_client.client.get = AsyncMock(return_value=mock_response)
        
        result = await bugs_quicksearch("test")
        
        # Verify only essential fields are included
        expected_keys = {"bug_id", "product", "component", "assigned_to", "status", "resolution", "summary", "last_updated"}
        assert set(result[0].keys()) == expected_keys

    async def test_bugs_quicksearch_with_limit_and_offset(self, set_bugzilla_client):
        """Test quicksearch with limit and offset parameters"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"bugs": []}
        set_bugzilla_client.client.get = AsyncMock(return_value=mock_response)
        
        await bugs_quicksearch("test", limit=10, offset=5)
        
        # Verify the call was made with correct parameters
        call_args = set_bugzilla_client.client.get.call_args
        params = call_args.kwargs["params"]
        assert params["limit"] == 10
        assert params["offset"] == 5
        assert params["quicksearch"] == "test"

    async def test_bugs_quicksearch_raises_on_missing_client(self, reset_bugzilla_client):
        """Test bugs_quicksearch raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await bugs_quicksearch("test")
        
        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_bugs_quicksearch_raises_on_api_error(self, set_bugzilla_client):
        """Test bugs_quicksearch raises ToolError on non-200 status"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json = MagicMock()  # Explicitly set as non-async to avoid warnings
        set_bugzilla_client.client.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(ToolError) as exc_info:
            await bugs_quicksearch("test")
        
        assert "Search failed with status code 500" in str(exc_info.value)


class TestLearnQuicksearchSyntaxTool:
    """Tests for learn_quicksearch_syntax tool"""

    async def test_learn_quicksearch_syntax_success(self, set_bugzilla_client, httpx_mock):
        """Test successful quicksearch syntax retrieval"""
        html_content = "<html><body>Quicksearch documentation</body></html>"
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/page.cgi?id=quicksearch.html",
            text=html_content,
        )
        
        result = await learn_quicksearch_syntax()
        
        assert result == html_content

    async def test_learn_quicksearch_syntax_raises_on_missing_client(self, reset_bugzilla_client):
        """Test learn_quicksearch_syntax raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await learn_quicksearch_syntax()
        
        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_learn_quicksearch_syntax_raises_on_api_error(self, set_bugzilla_client, httpx_mock):
        """Test learn_quicksearch_syntax raises PromptError on non-200 status"""
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/page.cgi?id=quicksearch.html",
            status_code=404,
        )
        
        with pytest.raises(PromptError) as exc_info:
            await learn_quicksearch_syntax()
        
        assert "status code 404" in str(exc_info.value)


class TestServerUrlTool:
    """Tests for server_url tool"""

    async def test_server_url_success(self, set_bugzilla_client):
        """Test successful server_url call"""
        result = await server_url()
        
        assert result == "https://bugzilla.mozilla.org"

    async def test_server_url_raises_on_missing_client(self, reset_bugzilla_client):
        """Test server_url raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await server_url()
        
        assert "Bugzilla client not initialized" in str(exc_info.value)


class TestBugUrlTool:
    """Tests for bug_url tool"""

    async def test_bug_url_success(self, set_bugzilla_client):
        """Test successful bug_url call"""
        result = await bug_url(12345)
        
        assert result == "https://bugzilla.mozilla.org/show_bug.cgi?id=12345"

    async def test_bug_url_raises_on_missing_client(self, reset_bugzilla_client):
        """Test bug_url raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await bug_url(12345)
        
        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_bug_url_with_different_bug_ids(self, set_bugzilla_client):
        """Test bug_url with various bug IDs"""
        result1 = await bug_url(1)
        result2 = await bug_url(999999)
        
        assert result1 == "https://bugzilla.mozilla.org/show_bug.cgi?id=1"
        assert result2 == "https://bugzilla.mozilla.org/show_bug.cgi?id=999999"
