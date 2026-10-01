"""Unit tests for Bugzilla MCP attachment tools"""

import pytest
from unittest.mock import AsyncMock
from fastmcp.exceptions import ToolError
from bugzilla_mcp.tools.bugzilla import download_attachments, download_attachment


class TestDownloadAttachmentsTool:
    """Tests for download_attachments tool"""

    async def test_download_attachments_success(self, set_bugzilla_client):
        """Test successful download_attachments tool call"""
        result = await download_attachments(12345, dest_dir="/tmp/test")

        assert len(result) == 1
        assert result[0]["id"] == 9001
        assert result[0]["bug_id"] == 12345
        assert result[0]["file_name"] == "test_attachment.txt"
        assert result[0]["path"] == "/mock/path/tmp/9001_test_attachment.txt"
        set_bugzilla_client.download_attachments.assert_called_once_with(12345, "/tmp/test")

    async def test_download_attachments_raises_on_missing_client(self, reset_bugzilla_client):
        """Test download_attachments raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await download_attachments(12345)

        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_download_attachments_raises_on_api_error(self, set_bugzilla_client):
        """Test download_attachments raises ToolError on client error"""
        set_bugzilla_client.download_attachments = AsyncMock(
            side_effect=Exception("Connection failure")
        )

        with pytest.raises(ToolError) as exc_info:
            await download_attachments(12345)

        assert "Failed to download attachments" in str(exc_info.value)
        assert "Connection failure" in str(exc_info.value)


class TestDownloadAttachmentTool:
    """Tests for download_attachment tool"""

    async def test_download_attachment_success(self, set_bugzilla_client):
        """Test successful download_attachment tool call"""
        result = await download_attachment(9001, dest_dir="/tmp/test")

        assert result["id"] == 9001
        assert result["bug_id"] == 12345
        assert result["file_name"] == "test_attachment.txt"
        assert result["path"] == "/mock/path/tmp/9001_test_attachment.txt"
        set_bugzilla_client.download_attachment.assert_called_once_with(9001, "/tmp/test")

    async def test_download_attachment_raises_on_missing_client(self, reset_bugzilla_client):
        """Test download_attachment raises ToolError when client not initialized"""
        with pytest.raises(ToolError) as exc_info:
            await download_attachment(9001)

        assert "Bugzilla client not initialized" in str(exc_info.value)

    async def test_download_attachment_raises_on_api_error(self, set_bugzilla_client):
        """Test download_attachment raises ToolError on client error"""
        set_bugzilla_client.download_attachment = AsyncMock(
            side_effect=Exception("Not found")
        )

        with pytest.raises(ToolError) as exc_info:
            await download_attachment(9001)

        assert "Failed to download attachment" in str(exc_info.value)
        assert "Not found" in str(exc_info.value)
