"""Tests for read-only mode, tool registration, dry-run and flexible parameters"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastmcp import FastMCP, Client
from fastmcp.exceptions import ToolError
import bugzilla_mcp.utils as utils
from bugzilla_mcp.utils import Bugzilla
from bugzilla_mcp.middleware.read_only import ReadOnlyMode, read_only_default
from bugzilla_mcp.tools.bugzilla import (
    register_tools,
    WRITE_TOOL_NAMES,
    READ_ONLY_TOOLS,
    ADDITIVE_TOOLS,
    DESTRUCTIVE_TOOLS,
    LOCAL_ONLY_TOOLS,
)

HEADERS = "bugzilla_mcp.middleware.read_only.get_http_headers"


def _server(read_only: bool, header_override: bool = True, local_files: bool = False) -> FastMCP:
    mcp = FastMCP("t")
    mcp.add_middleware(ReadOnlyMode(WRITE_TOOL_NAMES, read_only, allow_header_override=header_override))
    register_tools(mcp, local_files=local_files)
    return mcp


async def _tool_names(mcp: FastMCP) -> set[str]:
    async with Client(mcp) as c:
        return {t.name for t in await c.list_tools()}


@pytest.fixture
def client_mock():
    bz = MagicMock()
    bz.base_url = "https://bz.example.com"
    bz.add_comment = AsyncMock(return_value={"id": 1})
    bz.bug_info = AsyncMock(return_value={"id": 1, "summary": "S"})
    token = utils.current_bz.set(bz)
    yield bz
    utils.current_bz.reset(token)


class TestReadOnlyDefault:
    @pytest.mark.parametrize("value,expected", [
        (None, True), ("1", True), ("true", True), ("anything", True),
        ("0", False), ("false", False), ("FALSE", False), ("no", False), ("off", False),
    ])
    def test_env(self, monkeypatch, value, expected):
        if value is None:
            monkeypatch.delenv("BUGZILLA_READ_ONLY", raising=False)
        else:
            monkeypatch.setenv("BUGZILLA_READ_ONLY", value)
        assert read_only_default() is expected


class TestReadOnlyMode:
    async def test_write_tools_hidden(self):
        with patch(HEADERS, return_value={}):
            names = await _tool_names(_server(read_only=True))
        assert names == {fn.__name__ for fn in READ_ONLY_TOOLS}
        assert not names & WRITE_TOOL_NAMES

    async def test_write_tools_listed_when_writes_enabled(self):
        with patch(HEADERS, return_value={}):
            names = await _tool_names(_server(read_only=False))
        assert {"update_bug", "add_comment", "create_bug"} <= names

    async def test_write_call_refused(self, client_mock):
        with patch(HEADERS, return_value={}):
            async with Client(_server(read_only=True)) as c:
                with pytest.raises(ToolError, match="read-only"):
                    await c.call_tool("add_comment", {"bug_id": 1, "comment": "hi"})
        client_mock.add_comment.assert_not_called()

    async def test_read_call_allowed(self, client_mock):
        with patch(HEADERS, return_value={}):
            async with Client(_server(read_only=True)) as c:
                r = await c.call_tool("bug_info", {"id": 1})
        assert "S" in r.content[0].text

    async def test_header_enables_writes(self, client_mock):
        with patch(HEADERS, return_value={"read_only": "false"}):
            async with Client(_server(read_only=True)) as c:
                await c.call_tool("add_comment", {"bug_id": 1, "comment": "hi"})
                assert "update_bug" in {t.name for t in await c.list_tools()}
        client_mock.add_comment.assert_called_once()

    async def test_header_can_force_read_only(self):
        with patch(HEADERS, return_value={"read_only": "true"}):
            names = await _tool_names(_server(read_only=False))
        assert "update_bug" not in names

    async def test_local_server_ignores_header(self, client_mock):
        """The stdio server has no request headers; only the env var decides"""
        with patch(HEADERS, return_value={"read_only": "false"}):
            async with Client(_server(read_only=True, header_override=False)) as c:
                with pytest.raises(ToolError, match="BUGZILLA_READ_ONLY=false"):
                    await c.call_tool("add_comment", {"bug_id": 1, "comment": "hi"})


class TestRegistration:
    async def test_hosted_does_not_register_local_only_tools(self):
        names = await _tool_names(_server(read_only=False, local_files=False))
        assert not names & {fn.__name__ for fn in LOCAL_ONLY_TOOLS}

    async def test_local_registers_local_only_tools(self):
        names = await _tool_names(_server(read_only=False, local_files=True))
        assert {"download_attachment", "download_attachments"} <= names

    async def test_all_tools_registered(self):
        names = await _tool_names(_server(read_only=False, local_files=True))
        expected = READ_ONLY_TOOLS + ADDITIVE_TOOLS + LOCAL_ONLY_TOOLS + DESTRUCTIVE_TOOLS
        assert names == {fn.__name__ for fn in expected}

    async def test_disabled_tools_env(self, monkeypatch):
        monkeypatch.setenv("BUGZILLA_DISABLED_TOOLS", "update_bug, create_bug ,")
        names = await _tool_names(_server(read_only=False))
        assert "update_bug" not in names and "create_bug" not in names
        assert "add_comment" in names


class TestFlexibleParameters:
    async def test_single_status_string_accepted(self, client_mock):
        """`status: "CONFIRMED"` used to fail schema validation on a list-only filter"""
        client_mock.bugs_advanced_search = AsyncMock(return_value=[])
        async with Client(_server(read_only=True)) as c:
            await c.call_tool("bugs_advanced_search", {"status": "CONFIRMED", "product": ["A", "B"]})
        kwargs = client_mock.bugs_advanced_search.call_args.kwargs
        assert kwargs["status"] == "CONFIRMED"
        assert kwargs["product"] == ["A", "B"]

    async def test_single_bug_id_accepted(self, client_mock):
        client_mock.bugs_info = AsyncMock(return_value=[])
        async with Client(_server(read_only=True)) as c:
            await c.call_tool("bugs_info", {"ids": 5})
        client_mock.bugs_info.assert_called_once_with([5])

    async def test_parameters_have_descriptions(self):
        async with Client(_server(read_only=False)) as c:
            tools = {t.name: t for t in await c.list_tools()}
        props = tools["bugs_advanced_search"].inputSchema["properties"]
        assert "NEW" in props["status"]["description"]
        assert "dry_run" in tools["update_bug"].inputSchema["properties"]


class TestUpdateBugDryRun:
    async def test_dry_run_reads_but_does_not_write(self):
        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="k")
        bz.client = MagicMock()
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"bugs": [{"id": 1, "status": "NEW", "assigned_to": "a@x"}]}
        bz.client.get = AsyncMock(return_value=resp)
        bz.client.put = AsyncMock()

        result = await bz.update_bug(ids=[1, 2], status="RESOLVED", resolution="FIXED", comment="done", dry_run=True)

        bz.client.put.assert_not_called()
        params = bz.client.get.call_args.kwargs["params"]
        assert params["id"] == "1,2"
        assert set(params["include_fields"].split(",")) == {"id", "status", "resolution"}
        assert result["dry_run"] is True
        assert result["changes"]["status"] == "RESOLVED"
        assert result["changes"]["comment"]["body"] == "done"
        assert result["current"] == {"1": {"status": "NEW", "resolution": None}}
        assert result["not_found"] == [2]


class TestBugInfoIncludeFields:
    async def test_include_fields_sent_to_bugzilla(self):
        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="k")
        bz.client = MagicMock()
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"bugs": [{"id": 1, "status": "NEW"}]}
        bz.client.get = AsyncMock(return_value=resp)

        await bz.bug_info(1, include_fields=["id", "status"])

        assert bz.client.get.call_args.kwargs["params"]["include_fields"] == "id,status"
