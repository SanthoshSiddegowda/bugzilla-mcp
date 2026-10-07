"""Tests for hosted-server safety, attachments, create_bug status codes and compact output"""

import base64
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastmcp import FastMCP
from mcp.types import ImageContent
from bugzilla_mcp.utils import Bugzilla
from bugzilla_mcp.tools.bugzilla import (
    bug_info,
    get_attachment,
    register_tools,
    READ_ONLY_TOOLS,
    ADDITIVE_TOOLS,
    DESTRUCTIVE_TOOLS,
)


def _response(status_code: int, body: dict) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = body
    r.text = json.dumps(body)
    return r


@pytest.fixture
def hosted_bz():
    """A client as the hosted server creates it: no local file access"""
    bz = Bugzilla(url="https://bz.example.com", api_key="test-key")
    bz.client = MagicMock()
    return bz


class TestHostedServerFileAccess:
    """On a shared server, tools must not read or write the server's filesystem"""

    async def test_upload_from_file_path_refused(self, hosted_bz, tmp_path):
        secret = tmp_path / "secret.env"
        secret.write_text("TOKEN=abc")
        hosted_bz.client.post = AsyncMock()

        with pytest.raises(PermissionError):
            await hosted_bz.upload_attachment(bug_id=1, file_path=str(secret), summary="x")
        hosted_bz.client.post.assert_not_called()

    async def test_download_attachments_refused(self, hosted_bz, tmp_path):
        hosted_bz.client.get = AsyncMock()
        with pytest.raises(PermissionError):
            await hosted_bz.download_attachments(1, dest_dir=str(tmp_path))
        hosted_bz.client.get.assert_not_called()

    async def test_download_attachment_refused(self, hosted_bz, tmp_path):
        hosted_bz.client.get = AsyncMock()
        with pytest.raises(PermissionError):
            await hosted_bz.download_attachment(5, dest_dir=str(tmp_path))
        assert list(tmp_path.iterdir()) == []


class TestUploadInlineContent:
    async def test_upload_text(self, hosted_bz):
        hosted_bz.client.post = AsyncMock(return_value=_response(201, {"ids": [8001]}))

        result = await hosted_bz.upload_attachment(bug_id=7, text="log line", summary="Log")

        payload = hosted_bz.client.post.call_args.kwargs["json"]
        assert base64.b64decode(payload["data"]) == b"log line"
        assert payload["file_name"] == "attachment.txt"
        assert payload["content_type"] == "text/plain"
        # Bugzilla returns {"ids": [...]}
        assert result == {"attachment_id": 8001, "bug_id": 7}

    async def test_upload_base64(self, hosted_bz):
        data = base64.b64encode(b"\x89PNG").decode()
        hosted_bz.client.post = AsyncMock(return_value=_response(201, {"ids": [9]}))

        await hosted_bz.upload_attachment(
            bug_id=7, data_base64=data, file_name="shot.png", content_type="image/png", summary="Shot"
        )

        payload = hosted_bz.client.post.call_args.kwargs["json"]
        assert payload["data"] == data
        assert payload["content_type"] == "image/png"

    async def test_upload_base64_requires_file_name(self, hosted_bz):
        with pytest.raises(ValueError, match="file_name"):
            await hosted_bz.upload_attachment(bug_id=7, data_base64="aGk=", summary="x")

    async def test_upload_invalid_base64(self, hosted_bz):
        with pytest.raises(ValueError, match="base64"):
            await hosted_bz.upload_attachment(bug_id=7, data_base64="not base64!", file_name="a", summary="x")

    async def test_upload_needs_exactly_one_source(self, hosted_bz):
        with pytest.raises(ValueError, match="exactly one"):
            await hosted_bz.upload_attachment(bug_id=7, summary="x")
        with pytest.raises(ValueError, match="exactly one"):
            await hosted_bz.upload_attachment(bug_id=7, text="a", data_base64="YQ==", summary="x")

    async def test_upload_requires_summary(self, hosted_bz):
        with pytest.raises(ValueError, match="summary"):
            await hosted_bz.upload_attachment(bug_id=7, text="a")


class TestCreateBugStatus:
    async def test_create_bug_accepts_201(self, hosted_bz):
        """Bugzilla answers 201 Created; treating it as failure makes the assistant retry and file duplicates"""
        hosted_bz.client.post = AsyncMock(return_value=_response(201, {"id": 42}))
        result = await hosted_bz.create_bug(
            product="P", component="C", summary="S", version="unspecified", description="D"
        )
        assert result == {"id": 42}


class TestBatchCommentsErrors:
    async def test_failed_bug_reported_not_hidden(self, hosted_bz):
        async def comments(bug_id):
            if bug_id == 2:
                raise RuntimeError("boom")
            return [{"text": "hi"}]

        hosted_bz.bug_comments = comments
        result = await hosted_bz.bugs_comments([1, 2])

        assert result["1"] == [{"text": "hi"}]
        assert "boom" in result["2"]["error"]


class TestBugInfoCompact:
    BUG = {
        "id": 1, "summary": "S", "cf_unused": "", "cf_none": None, "keywords": [],
        "flags": [], "is_open": False, "votes": 0, "update_token": "csrf-123",
    }

    async def test_compact_by_default(self, set_bugzilla_client):
        set_bugzilla_client.bug_info = AsyncMock(return_value=dict(self.BUG))
        result = await bug_info(1)
        assert result == {"id": 1, "summary": "S", "is_open": False, "votes": 0}

    async def test_full_keeps_empty_fields_but_not_token(self, set_bugzilla_client):
        set_bugzilla_client.bug_info = AsyncMock(return_value=dict(self.BUG))
        result = await bug_info(1, full=True)
        assert "cf_unused" in result
        assert "update_token" not in result


class TestGetAttachmentTool:
    def _att(self, content_type: str, raw: bytes, **extra):
        return {
            "id": 5, "bug_id": 1, "file_name": "f", "content_type": content_type,
            "size": len(raw), "data": base64.b64encode(raw).decode(), **extra,
        }

    async def test_image_returned_as_image(self, set_bugzilla_client):
        set_bugzilla_client.get_attachment = AsyncMock(return_value=self._att("image/png", b"\x89PNG"))
        meta, image = await get_attachment(5)
        assert isinstance(image, ImageContent)
        assert image.mime_type == "image/png"
        assert base64.b64decode(image.data) == b"\x89PNG"
        assert json.loads(meta.text)["content_type"] == "image/png"
        assert "data" not in json.loads(meta.text)

    async def test_text_returned_as_text(self, set_bugzilla_client):
        set_bugzilla_client.get_attachment = AsyncMock(return_value=self._att("text/plain", b"stack trace"))
        _, text = await get_attachment(5)
        assert text.text == "stack trace"

    async def test_patch_returned_as_text(self, set_bugzilla_client):
        set_bugzilla_client.get_attachment = AsyncMock(
            return_value=self._att("application/octet-stream", b"--- a\n+++ b", is_patch=True)
        )
        _, text = await get_attachment(5)
        assert text.text.startswith("---")

    async def test_binary_returns_link_only(self, set_bugzilla_client):
        set_bugzilla_client.get_attachment = AsyncMock(return_value=self._att("application/zip", b"PK"))
        (meta,) = await get_attachment(5)
        assert json.loads(meta.text)["url"].endswith("/attachment.cgi?id=5")

    async def test_large_file_not_inlined(self, set_bugzilla_client, monkeypatch):
        import bugzilla_mcp.tools.bugzilla as tools
        monkeypatch.setattr(tools, "MAX_INLINE_ATTACHMENT_BYTES", 3)
        set_bugzilla_client.get_attachment = AsyncMock(return_value=self._att("image/png", b"1234"))
        (meta,) = await get_attachment(5)
        assert "Too large" in json.loads(meta.text)["note"]


class TestToolRegistration:
    async def test_annotations(self):
        mcp = FastMCP("t")
        register_tools(mcp)
        tools = {t.name: t for t in await mcp.list_tools()}

        assert len(tools) == len(READ_ONLY_TOOLS) + len(ADDITIVE_TOOLS) + len(DESTRUCTIVE_TOOLS)
        assert tools["bug_info"].annotations.read_only_hint is True
        assert tools["add_comment"].annotations.read_only_hint is False
        assert tools["update_bug"].annotations.destructive_hint is True
