"""Tests for new Bugzilla utility client methods."""

import base64
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import httpx
from bugzilla_mcp.utils.bugzilla import Bugzilla


def _make_response(status_code: int, json_body: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.text = ""
    return resp


@pytest.fixture
def bz():
    client = Bugzilla(url="https://bz.example.com", api_key="test-key")
    client.client = MagicMock()
    client.client.get = AsyncMock()
    client.client.post = AsyncMock()
    client.client.put = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# create_bug
# ---------------------------------------------------------------------------
class TestCreateBug:
    @pytest.mark.asyncio
    async def test_create_bug_minimal(self, bz: Bugzilla):
        bz.client.post = AsyncMock(
            return_value=_make_response(200, {"id": 99999, "aliases": []})
        )
        result = await bz.create_bug(
            product="Firefox",
            component="General",
            summary="New test bug",
            version="120.0",
            description="Steps to reproduce",
        )
        assert result["id"] == 99999
        call_json = bz.client.post.call_args.kwargs["json"]
        assert call_json["product"] == "Firefox"
        assert call_json["summary"] == "New test bug"

    @pytest.mark.asyncio
    async def test_create_bug_with_optionals(self, bz: Bugzilla):
        bz.client.post = AsyncMock(
            return_value=_make_response(200, {"id": 88888})
        )
        result = await bz.create_bug(
            product="Firefox",
            component="Networking",
            summary="P1 network bug",
            version="121.0",
            description="Crash on connect",
            severity="critical",
            priority="P1",
            assigned_to="dev@example.com",
            keywords=["crash"],
            target_milestone="121.0",
        )
        assert result["id"] == 88888
        payload = bz.client.post.call_args.kwargs["json"]
        assert payload["severity"] == "critical"
        assert payload["priority"] == "P1"

    @pytest.mark.asyncio
    async def test_create_bug_http_error(self, bz: Bugzilla):
        bz.client.post = AsyncMock(
            return_value=_make_response(401, {})
        )
        with pytest.raises(httpx.TransportError, match="401"):
            await bz.create_bug("P", "C", "S", "1.0", "D")


# ---------------------------------------------------------------------------
# update_bug
# ---------------------------------------------------------------------------
class TestUpdateBug:
    @pytest.mark.asyncio
    async def test_update_bug_status(self, bz: Bugzilla):
        bz.client.put = AsyncMock(
            return_value=_make_response(
                200,
                {"bugs": [{"id": 12345, "last_change_time": "2024-01-01T00:00:00Z", "changes": []}]},
            )
        )
        result = await bz.update_bug(ids=[12345], status="ASSIGNED")
        assert result["bugs"][0]["id"] == 12345
        payload = bz.client.put.call_args.kwargs["json"]
        assert payload["status"] == "ASSIGNED"

    @pytest.mark.asyncio
    async def test_update_bug_version(self, bz: Bugzilla):
        bz.client.put = AsyncMock(
            return_value=_make_response(
                200,
                {"bugs": [{"id": 12345, "last_change_time": "2024-01-01T00:00:00Z", "changes": []}]},
            )
        )
        result = await bz.update_bug(ids=[12345], version="OS")
        assert result["bugs"][0]["id"] == 12345
        payload = bz.client.put.call_args.kwargs["json"]
        assert payload["version"] == "OS"

    @pytest.mark.asyncio
    async def test_update_bug_all_parameters(self, bz: Bugzilla):
        bz.client.put = AsyncMock(
            return_value=_make_response(
                200,
                {"bugs": [{"id": 12345, "last_change_time": "2024-01-01T00:00:00Z", "changes": []}]},
            )
        )
        result = await bz.update_bug(
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
        assert result["bugs"][0]["id"] == 12345
        payload = bz.client.put.call_args.kwargs["json"]
        assert payload["summary"] == "New summary"
        assert payload["product"] == "New product"
        assert payload["component"] == "New component"
        assert payload["op_sys"] == "Windows"
        assert payload["platform"] == "x86_64"
        assert payload["qa_contact"] == "qa@example.com"
        assert payload["url"] == "https://example.com/bug"
        assert payload["keywords"] == {"add": ["perf"]}
        assert payload["cc"] == {"add": ["cc@example.com"]}
        assert payload["see_also"] == {"add": ["https://seealso.com"]}
        assert payload["blocks"] == {"add": [222]}
        assert payload["depends_on"] == {"add": [333]}
        assert payload["cf_custom_field"] == "custom_val"

    @pytest.mark.asyncio
    async def test_update_bug_resolve_duplicate(self, bz: Bugzilla):
        bz.client.put = AsyncMock(
            return_value=_make_response(200, {"bugs": [{"id": 12345, "changes": []}]})
        )
        await bz.update_bug(
            ids=[12345],
            status="RESOLVED",
            resolution="DUPLICATE",
            dupe_of=11111,
            comment="Duplicate of #11111",
        )
        payload = bz.client.put.call_args.kwargs["json"]
        assert payload["resolution"] == "DUPLICATE"
        assert payload["dupe_of"] == 11111
        assert payload["comment"]["body"] == "Duplicate of #11111"

    @pytest.mark.asyncio
    async def test_update_bug_http_error(self, bz: Bugzilla):
        bz.client.put = AsyncMock(return_value=_make_response(403, {}))
        with pytest.raises(httpx.TransportError, match="403"):
            await bz.update_bug(ids=[12345], status="ASSIGNED")


# ---------------------------------------------------------------------------
# bug_history
# ---------------------------------------------------------------------------
class TestBugHistory:
    @pytest.mark.asyncio
    async def test_bug_history_returns_list(self, bz: Bugzilla):
        history_entry = {
            "when": "2024-01-15T10:00:00Z",
            "who": "triage@example.com",
            "changes": [{"field_name": "priority", "removed": "P3", "added": "P1"}],
        }
        bz.client.get = AsyncMock(
            return_value=_make_response(
                200, {"bugs": [{"id": 12345, "history": [history_entry]}]}
            )
        )
        result = await bz.bug_history(bug_id=12345)
        assert len(result) == 1
        assert result[0]["who"] == "triage@example.com"

    @pytest.mark.asyncio
    async def test_bug_history_with_new_since(self, bz: Bugzilla):
        bz.client.get = AsyncMock(
            return_value=_make_response(200, {"bugs": [{"id": 12345, "history": []}]})
        )
        await bz.bug_history(bug_id=12345, new_since="2024-01-01T00:00:00Z")
        params = bz.client.get.call_args.kwargs["params"]
        assert params["new_since"] == "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_bug_history_empty_response(self, bz: Bugzilla):
        bz.client.get = AsyncMock(return_value=_make_response(200, {"bugs": []}))
        result = await bz.bug_history(bug_id=12345)
        assert result == []

    @pytest.mark.asyncio
    async def test_bug_history_http_error(self, bz: Bugzilla):
        bz.client.get = AsyncMock(return_value=_make_response(404, {}))
        with pytest.raises(httpx.TransportError, match="404"):
            await bz.bug_history(bug_id=12345)


# ---------------------------------------------------------------------------
# bugs_advanced_search
# ---------------------------------------------------------------------------
class TestBugsAdvancedSearch:
    @pytest.mark.asyncio
    async def test_advanced_search_returns_essential_fields(self, bz: Bugzilla):
        raw_bug = {
            "id": 12345,
            "summary": "Test bug",
            "status": "NEW",
            "resolution": "",
            "product": "Firefox",
            "component": "General",
            "assigned_to": "dev@example.com",
            "priority": "P1",
            "severity": "critical",
            "creation_time": "2024-01-01T00:00:00Z",
            "last_change_time": "2024-01-10T00:00:00Z",
            "creator": "reporter@example.com",  # not in essential_keys — should be dropped
        }
        bz.client.get = AsyncMock(
            return_value=_make_response(200, {"bugs": [raw_bug]})
        )
        result = await bz.bugs_advanced_search(product=["Firefox"])
        assert len(result) == 1
        assert result[0]["id"] == 12345
        assert "creator" not in result[0]

    @pytest.mark.asyncio
    async def test_advanced_search_builds_params(self, bz: Bugzilla):
        bz.client.get = AsyncMock(
            return_value=_make_response(200, {"bugs": []})
        )
        await bz.bugs_advanced_search(
            product=["Firefox"],
            status=["NEW", "ASSIGNED"],
            priority=["P1"],
            limit=10,
            offset=5,
        )
        params = bz.client.get.call_args.kwargs["params"]
        assert params["product"] == ["Firefox"]
        assert params["status"] == ["NEW", "ASSIGNED"]
        assert params["limit"] == 10
        assert params["offset"] == 5

    @pytest.mark.asyncio
    async def test_advanced_search_http_error(self, bz: Bugzilla):
        bz.client.get = AsyncMock(return_value=_make_response(500, {}))
        with pytest.raises(httpx.TransportError, match="500"):
            await bz.bugs_advanced_search()


# ---------------------------------------------------------------------------
# bug_dependencies
# ---------------------------------------------------------------------------
class TestBugDependencies:
    @pytest.mark.asyncio
    async def test_dependencies_returned(self, bz: Bugzilla):
        bz.client.get = AsyncMock(
            return_value=_make_response(200, {"bugs": [{
                "id": 12345,
                "summary": "Root bug",
                "status": "NEW",
                "blocks": [100, 200],
                "depends_on": [50],
            }]})
        )
        result = await bz.bug_dependencies(bug_id=12345)
        assert result["blocks"] == [100, 200]
        assert result["depends_on"] == [50]

    @pytest.mark.asyncio
    async def test_dependencies_http_error(self, bz: Bugzilla):
        bz.client.get = AsyncMock(return_value=_make_response(404, {}))
        with pytest.raises(httpx.TransportError, match="404"):
            await bz.bug_dependencies(bug_id=12345)


# ---------------------------------------------------------------------------
# duplicate_chain
# ---------------------------------------------------------------------------
class TestDuplicateChain:
    @pytest.mark.asyncio
    async def test_chain_stops_at_root(self, bz: Bugzilla):
        child = {"id": 999, "summary": "Child", "status": "RESOLVED", "dupe_of": 12345}
        root = {"id": 12345, "summary": "Root", "status": "RESOLVED", "dupe_of": None}

        responses = [
            _make_response(200, {"bugs": [child]}),
            _make_response(200, {"bugs": [root]}),
        ]
        bz.client.get = AsyncMock(side_effect=responses)
        chain = await bz.duplicate_chain(bug_id=999)
        assert len(chain) == 2
        assert chain[0]["id"] == 999
        assert chain[1]["id"] == 12345
        assert chain[1]["dupe_of"] is None

    @pytest.mark.asyncio
    async def test_chain_respects_max_depth(self, bz: Bugzilla):
        """When max_depth=1 only the starting bug is returned."""
        bz.client.get = AsyncMock(
            return_value=_make_response(200, {"bugs": [
                {"id": 999, "summary": "Child", "status": "RESOLVED", "dupe_of": 12345}
            ]})
        )
        chain = await bz.duplicate_chain(bug_id=999, max_depth=1)
        assert len(chain) == 1

    @pytest.mark.asyncio
    async def test_chain_http_error(self, bz: Bugzilla):
        bz.client.get = AsyncMock(return_value=_make_response(404, {}))
        with pytest.raises(httpx.TransportError, match="404"):
            await bz.duplicate_chain(bug_id=999)


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------
class TestGetUser:
    @pytest.mark.asyncio
    async def test_get_user_by_name(self, bz: Bugzilla):
        bz.client.get = AsyncMock(
            return_value=_make_response(200, {"users": [
                {"id": 42, "real_name": "Alice", "name": "alice@example.com",
                 "email": "alice@example.com", "can_login": True}
            ]})
        )
        result = await bz.get_user(names=["alice@example.com"])
        assert result[0]["real_name"] == "Alice"
        params = bz.client.get.call_args.kwargs["params"]
        assert params["names"] == ["alice@example.com"]

    @pytest.mark.asyncio
    async def test_get_user_by_ids(self, bz: Bugzilla):
        bz.client.get = AsyncMock(
            return_value=_make_response(200, {"users": [{"id": 42}]})
        )
        await bz.get_user(ids=[42])
        params = bz.client.get.call_args.kwargs["params"]
        assert params["ids"] == [42]

    @pytest.mark.asyncio
    async def test_get_user_http_error(self, bz: Bugzilla):
        bz.client.get = AsyncMock(return_value=_make_response(401, {}))
        with pytest.raises(httpx.TransportError, match="401"):
            await bz.get_user(names=["alice@example.com"])


# ---------------------------------------------------------------------------
# search_users
# ---------------------------------------------------------------------------
class TestSearchUsers:
    @pytest.mark.asyncio
    async def test_search_passes_match_param(self, bz: Bugzilla):
        bz.client.get = AsyncMock(
            return_value=_make_response(200, {"users": [{"id": 42, "name": "alice@example.com"}]})
        )
        result = await bz.search_users(match="alice", limit=5)
        assert len(result) == 1
        params = bz.client.get.call_args.kwargs["params"]
        assert params["match"] == "alice"
        assert params["limit"] == 5

    @pytest.mark.asyncio
    async def test_search_users_http_error(self, bz: Bugzilla):
        bz.client.get = AsyncMock(return_value=_make_response(403, {}))
        with pytest.raises(httpx.TransportError, match="403"):
            await bz.search_users(match="alice")


# ---------------------------------------------------------------------------
# list_products
# ---------------------------------------------------------------------------
class TestListProducts:
    @pytest.mark.asyncio
    async def test_list_products_returns_products(self, bz: Bugzilla):
        products = [
            {"id": 1, "name": "Firefox", "description": "Browser", "is_active": True},
            {"id": 2, "name": "Thunderbird", "description": "Email", "is_active": True},
        ]
        bz.client.get = AsyncMock(side_effect=[
            _make_response(200, {"ids": [1, 2]}),
            _make_response(200, {"products": products}),
        ])
        result = await bz.list_products()
        assert len(result) == 2
        assert result[0]["name"] == "Firefox"

    @pytest.mark.asyncio
    async def test_list_products_empty(self, bz: Bugzilla):
        bz.client.get = AsyncMock(
            return_value=_make_response(200, {"ids": []})
        )
        result = await bz.list_products()
        assert result == []

    @pytest.mark.asyncio
    async def test_list_products_http_error(self, bz: Bugzilla):
        bz.client.get = AsyncMock(return_value=_make_response(500, {}))
        with pytest.raises(httpx.TransportError, match="500"):
            await bz.list_products()


# ---------------------------------------------------------------------------
# get_product_components
# ---------------------------------------------------------------------------
class TestGetProductComponents:
    @pytest.mark.asyncio
    async def test_returns_components(self, bz: Bugzilla):
        bz.client.get = AsyncMock(
            return_value=_make_response(200, {"products": [{
                "id": 1,
                "name": "Firefox",
                "components": [
                    {"name": "General", "description": "General issues",
                     "default_assignee": "nobody@example.com"},
                ]
            }]})
        )
        result = await bz.get_product_components("Firefox")
        assert result["name"] == "Firefox"
        assert len(result["components"]) == 1
        assert result["components"][0]["name"] == "General"

    @pytest.mark.asyncio
    async def test_product_not_found(self, bz: Bugzilla):
        bz.client.get = AsyncMock(
            return_value=_make_response(200, {"products": []})
        )
        with pytest.raises(ValueError, match="not found"):
            await bz.get_product_components("NonExistentProduct")

    @pytest.mark.asyncio
    async def test_http_error(self, bz: Bugzilla):
        bz.client.get = AsyncMock(return_value=_make_response(404, {}))
        with pytest.raises(httpx.TransportError, match="404"):
            await bz.get_product_components("Firefox")


# ---------------------------------------------------------------------------
# upload_attachment
# ---------------------------------------------------------------------------
class TestUploadAttachment:
    @pytest.mark.asyncio
    async def test_upload_success(self, bz: Bugzilla, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello attachment!")

        bz.client.post = AsyncMock(
            return_value=_make_response(201, {"attachments": {"8001": {"id": 8001}}})
        )
        result = await bz.upload_attachment(
            bug_id=12345,
            file_path=str(test_file),
            summary="Test attachment",
        )
        assert result["attachment_id"] == 8001
        assert result["bug_id"] == 12345

        payload = bz.client.post.call_args.kwargs["json"]
        assert payload["summary"] == "Test attachment"
        assert payload["file_name"] == "test.txt"
        # Verify base64 encoding
        decoded = base64.b64decode(payload["data"]).decode("utf-8")
        assert decoded == "Hello attachment!"

    @pytest.mark.asyncio
    async def test_upload_content_type_txt(self, bz: Bugzilla, tmp_path):
        test_file = tmp_path / "log.txt"
        test_file.write_bytes(b"log content")
        bz.client.post = AsyncMock(
            return_value=_make_response(201, {"attachments": {"9000": {}}})
        )
        await bz.upload_attachment(bug_id=12345, file_path=str(test_file), summary="Log")
        payload = bz.client.post.call_args.kwargs["json"]
        assert payload["content_type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_upload_patch_auto_content_type(self, bz: Bugzilla, tmp_path):
        patch_file = tmp_path / "fix.patch"
        patch_file.write_bytes(b"diff --git a/foo.py b/foo.py")
        bz.client.post = AsyncMock(
            return_value=_make_response(201, {"attachments": {"9001": {}}})
        )
        await bz.upload_attachment(bug_id=12345, file_path=str(patch_file), summary="Patch")
        payload = bz.client.post.call_args.kwargs["json"]
        assert payload["content_type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_upload_file_not_found(self, bz: Bugzilla):
        with pytest.raises(FileNotFoundError):
            await bz.upload_attachment(
                bug_id=12345, file_path="/nonexistent/file.txt", summary="Missing"
            )

    @pytest.mark.asyncio
    async def test_upload_http_error(self, bz: Bugzilla, tmp_path):
        test_file = tmp_path / "err.txt"
        test_file.write_bytes(b"data")
        bz.client.post = AsyncMock(return_value=_make_response(500, {}))
        with pytest.raises(httpx.TransportError, match="500"):
            await bz.upload_attachment(
                bug_id=12345, file_path=str(test_file), summary="Fail"
            )


# ---------------------------------------------------------------------------
# tag_comment
# ---------------------------------------------------------------------------
class TestTagComment:
    @pytest.mark.asyncio
    async def test_add_tags(self, bz: Bugzilla):
        bz.client.put = AsyncMock(
            return_value=_make_response(200, ["fix-candidate", "ai-generated"])
        )
        result = await bz.tag_comment(
            comment_id=1001, add=["fix-candidate", "ai-generated"]
        )
        assert "fix-candidate" in result["tags"]
        payload = bz.client.put.call_args.kwargs["json"]
        assert payload["add"] == ["fix-candidate", "ai-generated"]

    @pytest.mark.asyncio
    async def test_remove_tags(self, bz: Bugzilla):
        bz.client.put = AsyncMock(return_value=_make_response(200, []))
        result = await bz.tag_comment(comment_id=1001, remove=["old-tag"])
        assert result["tags"] == []
        payload = bz.client.put.call_args.kwargs["json"]
        assert payload["remove"] == ["old-tag"]

    @pytest.mark.asyncio
    async def test_tag_comment_http_error(self, bz: Bugzilla):
        bz.client.put = AsyncMock(return_value=_make_response(403, {}))
        with pytest.raises(httpx.TransportError, match="403"):
            await bz.tag_comment(comment_id=1001, add=["tag"])
