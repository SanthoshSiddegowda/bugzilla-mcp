"""Tests for the 12 new MCP tool wrapper functions."""

import pytest
from unittest.mock import AsyncMock
from fastmcp.exceptions import ToolError

import bugzilla_mcp.utils as utils
from bugzilla_mcp.tools.bugzilla import (
    create_bug,
    update_bug,
    bug_history,
    bugs_advanced_search,
    bug_dependencies,
    duplicate_chain,
    get_user,
    search_users,
    list_products,
    get_product_components,
    upload_attachment,
    tag_comment,
)


# ---------------------------------------------------------------------------
# create_bug tool
# ---------------------------------------------------------------------------
class TestCreateBugTool:
    @pytest.mark.asyncio
    async def test_create_bug_success(self, set_bugzilla_client):
        result = await create_bug(
            product="Firefox",
            component="General",
            summary="New bug from agent",
            version="120.0",
            description="Steps to repro",
        )
        assert result["id"] == 99999
        set_bugzilla_client.create_bug.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_bug_with_all_fields(self, set_bugzilla_client):
        await create_bug(
            product="Firefox",
            component="Networking",
            summary="P1 crash",
            version="121.0",
            description="Crash details",
            severity="critical",
            priority="P1",
            assigned_to="dev@example.com",
            keywords=["crash", "regression"],
            target_milestone="121",
        )
        call_kwargs = set_bugzilla_client.create_bug.call_args.kwargs
        assert call_kwargs["severity"] == "critical"
        assert call_kwargs["priority"] == "P1"
        assert call_kwargs["assigned_to"] == "dev@example.com"

    @pytest.mark.asyncio
    async def test_create_bug_no_client(self, reset_bugzilla_client):
        with pytest.raises(ToolError, match="not initialized"):
            await create_bug("P", "C", "S", "1.0", "D")

    @pytest.mark.asyncio
    async def test_create_bug_client_raises(self, set_bugzilla_client):
        set_bugzilla_client.create_bug = AsyncMock(side_effect=Exception("API failure"))
        with pytest.raises(ToolError, match="API failure"):
            await create_bug("P", "C", "S", "1.0", "D")


# ---------------------------------------------------------------------------
# update_bug tool
# ---------------------------------------------------------------------------
class TestUpdateBugTool:
    @pytest.mark.asyncio
    async def test_update_bug_success(self, set_bugzilla_client):
        result = await update_bug(ids=[12345], status="ASSIGNED")
        assert result["bugs"][0]["id"] == 12345
        set_bugzilla_client.update_bug.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_bug_version(self, set_bugzilla_client):
        await update_bug(ids=[12345], version="OS")
        call_kwargs = set_bugzilla_client.update_bug.call_args.kwargs
        assert call_kwargs["version"] == "OS"

    @pytest.mark.asyncio
    async def test_update_bug_all_parameters(self, set_bugzilla_client):
        await update_bug(
            ids=[12345],
            summary="New summary",
            product="New product",
            component="New component",
            op_sys="Windows",
            platform="x86_64",
            qa_contact="qa@example.com",
            url="https://example.com/bug",
            keywords={"add": ["perf"]},
            cc={"add": ["cc@example.com"]},
            see_also={"add": ["https://seealso.com"]},
            blocks={"add": [222]},
            depends_on={"add": [333]},
            extra_fields={"cf_custom_field": "custom_val"}
        )
        call_kwargs = set_bugzilla_client.update_bug.call_args.kwargs
        assert call_kwargs["summary"] == "New summary"
        assert call_kwargs["product"] == "New product"
        assert call_kwargs["component"] == "New component"
        assert call_kwargs["op_sys"] == "Windows"
        assert call_kwargs["platform"] == "x86_64"
        assert call_kwargs["qa_contact"] == "qa@example.com"
        assert call_kwargs["url"] == "https://example.com/bug"
        assert call_kwargs["keywords"] == {"add": ["perf"]}
        assert call_kwargs["cc"] == {"add": ["cc@example.com"]}
        assert call_kwargs["see_also"] == {"add": ["https://seealso.com"]}
        assert call_kwargs["blocks"] == {"add": [222]}
        assert call_kwargs["depends_on"] == {"add": [333]}
        assert call_kwargs["extra_fields"] == {"cf_custom_field": "custom_val"}

    @pytest.mark.asyncio
    async def test_update_bug_duplicate(self, set_bugzilla_client):
        await update_bug(
            ids=[12345],
            status="RESOLVED",
            resolution="DUPLICATE",
            dupe_of=11111,
            comment="Dup of 11111",
        )
        call_kwargs = set_bugzilla_client.update_bug.call_args.kwargs
        assert call_kwargs["resolution"] == "DUPLICATE"
        assert call_kwargs["dupe_of"] == 11111

    @pytest.mark.asyncio
    async def test_update_bug_no_client(self, reset_bugzilla_client):
        with pytest.raises(ToolError, match="not initialized"):
            await update_bug(ids=[12345], status="ASSIGNED")

    @pytest.mark.asyncio
    async def test_update_bug_client_raises(self, set_bugzilla_client):
        set_bugzilla_client.update_bug = AsyncMock(side_effect=Exception("forbidden"))
        with pytest.raises(ToolError, match="forbidden"):
            await update_bug(ids=[12345])


# ---------------------------------------------------------------------------
# bug_history tool
# ---------------------------------------------------------------------------
class TestBugHistoryTool:
    @pytest.mark.asyncio
    async def test_bug_history_success(self, set_bugzilla_client):
        result = await bug_history(bug_id=12345)
        assert isinstance(result, list)
        assert result[0]["who"] == "dev@example.com"
        set_bugzilla_client.bug_history.assert_called_once_with(
            bug_id=12345, new_since=None
        )

    @pytest.mark.asyncio
    async def test_bug_history_with_new_since(self, set_bugzilla_client):
        await bug_history(bug_id=12345, new_since="2024-01-01T00:00:00Z")
        call_kwargs = set_bugzilla_client.bug_history.call_args.kwargs
        assert call_kwargs["new_since"] == "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_bug_history_no_client(self, reset_bugzilla_client):
        with pytest.raises(ToolError, match="not initialized"):
            await bug_history(bug_id=12345)

    @pytest.mark.asyncio
    async def test_bug_history_client_raises(self, set_bugzilla_client):
        set_bugzilla_client.bug_history = AsyncMock(side_effect=Exception("not found"))
        with pytest.raises(ToolError, match="not found"):
            await bug_history(bug_id=12345)


# ---------------------------------------------------------------------------
# bugs_advanced_search tool
# ---------------------------------------------------------------------------
class TestBugsAdvancedSearchTool:
    @pytest.mark.asyncio
    async def test_advanced_search_success(self, set_bugzilla_client):
        result = await bugs_advanced_search(product=["Firefox"], status=["NEW"])
        assert len(result) == 1
        assert result[0]["id"] == 12345

    @pytest.mark.asyncio
    async def test_advanced_search_passes_all_params(self, set_bugzilla_client):
        await bugs_advanced_search(
            product=["Firefox"],
            component=["General"],
            status=["NEW"],
            resolution=["---"],
            assigned_to="dev@example.com",
            creator="reporter@example.com",
            severity=["critical"],
            priority=["P1"],
            creation_time="2024-01-01T00:00:00Z",
            last_change_time="2024-01-10T00:00:00Z",
            keywords=["crash"],
            version=["120.0"],
            target_milestone=["120"],
            limit=25,
            offset=10,
        )
        call_kwargs = set_bugzilla_client.bugs_advanced_search.call_args.kwargs
        assert call_kwargs["product"] == ["Firefox"]
        assert call_kwargs["limit"] == 25
        assert call_kwargs["offset"] == 10

    @pytest.mark.asyncio
    async def test_advanced_search_no_client(self, reset_bugzilla_client):
        with pytest.raises(ToolError, match="not initialized"):
            await bugs_advanced_search()


# ---------------------------------------------------------------------------
# bug_dependencies tool
# ---------------------------------------------------------------------------
class TestBugDependenciesTool:
    @pytest.mark.asyncio
    async def test_bug_dependencies_success(self, set_bugzilla_client):
        result = await bug_dependencies(bug_id=12345)
        assert result["blocks"] == [12346, 12347]
        assert result["depends_on"] == [12300]

    @pytest.mark.asyncio
    async def test_bug_dependencies_no_client(self, reset_bugzilla_client):
        with pytest.raises(ToolError, match="not initialized"):
            await bug_dependencies(bug_id=12345)

    @pytest.mark.asyncio
    async def test_bug_dependencies_client_raises(self, set_bugzilla_client):
        set_bugzilla_client.bug_dependencies = AsyncMock(side_effect=Exception("oops"))
        with pytest.raises(ToolError, match="oops"):
            await bug_dependencies(bug_id=12345)


# ---------------------------------------------------------------------------
# duplicate_chain tool
# ---------------------------------------------------------------------------
class TestDuplicateChainTool:
    @pytest.mark.asyncio
    async def test_duplicate_chain_success(self, set_bugzilla_client):
        result = await duplicate_chain(bug_id=99999)
        assert len(result) == 2
        assert result[0]["id"] == 99999
        assert result[1]["dupe_of"] is None

    @pytest.mark.asyncio
    async def test_duplicate_chain_custom_depth(self, set_bugzilla_client):
        await duplicate_chain(bug_id=99999, max_depth=5)
        call_kwargs = set_bugzilla_client.duplicate_chain.call_args.kwargs
        assert call_kwargs["max_depth"] == 5

    @pytest.mark.asyncio
    async def test_duplicate_chain_no_client(self, reset_bugzilla_client):
        with pytest.raises(ToolError, match="not initialized"):
            await duplicate_chain(bug_id=99999)


# ---------------------------------------------------------------------------
# get_user tool
# ---------------------------------------------------------------------------
class TestGetUserTool:
    @pytest.mark.asyncio
    async def test_get_user_by_name(self, set_bugzilla_client):
        result = await get_user(names=["alice@example.com"])
        assert result[0]["real_name"] == "Alice Dev"

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, set_bugzilla_client):
        await get_user(ids=[42])
        call_kwargs = set_bugzilla_client.get_user.call_args.kwargs
        assert call_kwargs["ids"] == [42]

    @pytest.mark.asyncio
    async def test_get_user_no_client(self, reset_bugzilla_client):
        with pytest.raises(ToolError, match="not initialized"):
            await get_user(names=["alice@example.com"])


# ---------------------------------------------------------------------------
# search_users tool
# ---------------------------------------------------------------------------
class TestSearchUsersTool:
    @pytest.mark.asyncio
    async def test_search_users_success(self, set_bugzilla_client):
        result = await search_users(match="alice", limit=5)
        assert result[0]["name"] == "alice@example.com"
        call_kwargs = set_bugzilla_client.search_users.call_args.kwargs
        assert call_kwargs["match"] == "alice"
        assert call_kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_search_users_no_client(self, reset_bugzilla_client):
        with pytest.raises(ToolError, match="not initialized"):
            await search_users(match="alice")


# ---------------------------------------------------------------------------
# list_products tool
# ---------------------------------------------------------------------------
class TestListProductsTool:
    @pytest.mark.asyncio
    async def test_list_products_success(self, set_bugzilla_client):
        result = await list_products()
        assert len(result) == 2
        assert result[0]["name"] == "Firefox"

    @pytest.mark.asyncio
    async def test_list_products_no_client(self, reset_bugzilla_client):
        with pytest.raises(ToolError, match="not initialized"):
            await list_products()

    @pytest.mark.asyncio
    async def test_list_products_client_raises(self, set_bugzilla_client):
        set_bugzilla_client.list_products = AsyncMock(side_effect=Exception("access denied"))
        with pytest.raises(ToolError, match="access denied"):
            await list_products()


# ---------------------------------------------------------------------------
# get_product_components tool
# ---------------------------------------------------------------------------
class TestGetProductComponentsTool:
    @pytest.mark.asyncio
    async def test_get_product_components_success(self, set_bugzilla_client):
        result = await get_product_components(product_name="Firefox")
        assert result["name"] == "Firefox"
        assert len(result["components"]) == 2
        assert result["components"][0]["name"] == "General"

    @pytest.mark.asyncio
    async def test_get_product_components_no_client(self, reset_bugzilla_client):
        with pytest.raises(ToolError, match="not initialized"):
            await get_product_components(product_name="Firefox")

    @pytest.mark.asyncio
    async def test_get_product_components_client_raises(self, set_bugzilla_client):
        set_bugzilla_client.get_product_components = AsyncMock(
            side_effect=ValueError("Product 'X' not found")
        )
        with pytest.raises(ToolError, match="not found"):
            await get_product_components(product_name="X")


# ---------------------------------------------------------------------------
# upload_attachment tool
# ---------------------------------------------------------------------------
class TestUploadAttachmentTool:
    @pytest.mark.asyncio
    async def test_upload_attachment_success(self, set_bugzilla_client, tmp_path):
        f = tmp_path / "log.txt"
        f.write_text("crash log")
        result = await upload_attachment(
            bug_id=12345,
            file_path=str(f),
            summary="Crash log",
        )
        assert result["attachment_id"] == 8001
        assert result["bug_id"] == 12345

    @pytest.mark.asyncio
    async def test_upload_attachment_with_patch_flag(self, set_bugzilla_client, tmp_path):
        f = tmp_path / "fix.patch"
        f.write_bytes(b"diff content")
        await upload_attachment(
            bug_id=12345,
            file_path=str(f),
            summary="Fix patch",
            is_patch=True,
            comment="Auto-generated patch",
        )
        call_kwargs = set_bugzilla_client.upload_attachment.call_args.kwargs
        assert call_kwargs["is_patch"] is True

    @pytest.mark.asyncio
    async def test_upload_attachment_no_client(self, reset_bugzilla_client, tmp_path):
        f = tmp_path / "log.txt"
        f.write_text("data")
        with pytest.raises(ToolError, match="not initialized"):
            await upload_attachment(bug_id=12345, file_path=str(f), summary="Log")

    @pytest.mark.asyncio
    async def test_upload_attachment_client_raises(self, set_bugzilla_client, tmp_path):
        set_bugzilla_client.upload_attachment = AsyncMock(
            side_effect=FileNotFoundError("File not found")
        )
        with pytest.raises(ToolError, match="File not found"):
            await upload_attachment(bug_id=12345, file_path="/missing.txt", summary="X")


# ---------------------------------------------------------------------------
# tag_comment tool
# ---------------------------------------------------------------------------
class TestTagCommentTool:
    @pytest.mark.asyncio
    async def test_tag_comment_add(self, set_bugzilla_client):
        result = await tag_comment(comment_id=1001, add=["fix-candidate"])
        assert "fix-candidate" in result["tags"]
        call_kwargs = set_bugzilla_client.tag_comment.call_args.kwargs
        assert call_kwargs["add"] == ["fix-candidate"]

    @pytest.mark.asyncio
    async def test_tag_comment_remove(self, set_bugzilla_client):
        await tag_comment(comment_id=1001, remove=["old-tag"])
        call_kwargs = set_bugzilla_client.tag_comment.call_args.kwargs
        assert call_kwargs["remove"] == ["old-tag"]

    @pytest.mark.asyncio
    async def test_tag_comment_add_and_remove(self, set_bugzilla_client):
        await tag_comment(comment_id=1001, add=["new"], remove=["old"])
        call_kwargs = set_bugzilla_client.tag_comment.call_args.kwargs
        assert call_kwargs["add"] == ["new"]
        assert call_kwargs["remove"] == ["old"]

    @pytest.mark.asyncio
    async def test_tag_comment_no_client(self, reset_bugzilla_client):
        with pytest.raises(ToolError, match="not initialized"):
            await tag_comment(comment_id=1001, add=["tag"])

    @pytest.mark.asyncio
    async def test_tag_comment_client_raises(self, set_bugzilla_client):
        set_bugzilla_client.tag_comment = AsyncMock(side_effect=Exception("forbidden"))
        with pytest.raises(ToolError, match="forbidden"):
            await tag_comment(comment_id=1001, add=["tag"])
