"""Unit tests for the Bugzilla API client"""

import json
import pytest
import httpx
from bugzilla_mcp.utils import Bugzilla
from bugzilla_mcp.utils import bugzilla as bugzilla_module


class TestBugzillaInit:
    """Tests for Bugzilla class initialization"""

    def test_init_sets_api_url(self):
        """Test that API URL is constructed correctly"""
        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        assert bz.api_url == "https://bugzilla.mozilla.org/rest"

    def test_init_sets_base_url(self):
        """Test that base URL is stored correctly"""
        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        assert bz.base_url == "https://bugzilla.mozilla.org"

    def test_init_sets_api_key(self):
        """Test that API key is stored correctly"""
        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="my-api-key")
        assert bz.api_key == "my-api-key"


    def test_init_strips_trailing_slash(self):
        """Test that a trailing slash does not produce '//rest'"""
        bz = Bugzilla(url="https://bugzilla.mozilla.org/", api_key="test-key")
        assert bz.base_url == "https://bugzilla.mozilla.org"
        assert bz.api_url == "https://bugzilla.mozilla.org/rest"

    def test_init_creates_async_client(self):
        """Test that async client is created"""
        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        assert isinstance(bz.client, httpx.AsyncClient)


class TestBugzillaBugInfo:
    """Tests for bug_info method"""

    @pytest.fixture
    def mock_response(self):
        """Create a mock response with bug data"""
        response = httpx.Response(
            status_code=200,
            json={
                "bugs": [{
                    "id": 12345,
                    "product": "Firefox",
                    "component": "General",
                    "summary": "Test bug",
                    "status": "NEW",
                }]
            },
            request=httpx.Request("GET", "http://test/rest/bug/12345"),
        )
        return response

    async def test_bug_info_success(self, httpx_mock):
        """Test successful bug_info call"""
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/12345",
            match_headers={"X-BUGZILLA-API-KEY": "test-key"},
            json={
                "bugs": [{
                    "id": 12345,
                    "product": "Firefox",
                    "component": "General",
                    "summary": "Test bug",
                    "status": "NEW",
                }]
            },
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bug_info(12345)

        assert result["id"] == 12345
        assert result["product"] == "Firefox"
        assert result["status"] == "NEW"
        
        await bz.close()

    async def test_bug_info_failure_status_code(self, httpx_mock):
        """Test bug_info raises exception on non-200 status"""
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/99999",
            status_code=404,
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        
        with pytest.raises(httpx.TransportError) as exc_info:
            await bz.bug_info(99999)
        
        assert "Status code: 404" in str(exc_info.value)
        
        await bz.close()

    async def test_bug_info_returns_first_bug(self, httpx_mock):
        """Test that bug_info returns the first bug from response"""
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/12345",
            json={
                "bugs": [
                    {"id": 12345, "summary": "First bug"},
                    {"id": 12346, "summary": "Second bug"},
                ]
            },
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bug_info(12345)

        assert result["id"] == 12345
        assert result["summary"] == "First bug"
        
        await bz.close()


class TestBugzillaBugComments:
    """Tests for bug_comments method"""

    async def test_bug_comments_success(self, httpx_mock):
        """Test successful bug_comments call"""
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/12345/comment",
            json={
                "bugs": {
                    "12345": {
                        "comments": [
                            {"id": 1, "text": "First comment", "is_private": False},
                            {"id": 2, "text": "Second comment", "is_private": True},
                        ]
                    }
                }
            },
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bug_comments(12345)

        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["text"] == "First comment"
        assert result[1]["is_private"] is True
        
        await bz.close()

    async def test_bug_comments_failure_status_code(self, httpx_mock):
        """Test bug_comments raises exception on non-200 status"""
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/99999/comment",
            status_code=404,
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        
        with pytest.raises(httpx.TransportError) as exc_info:
            await bz.bug_comments(99999)
        
        assert "Status code: 404" in str(exc_info.value)
        
        await bz.close()

    async def test_bug_comments_empty(self, httpx_mock):
        """Test bug_comments with no comments"""
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/12345/comment",
            json={
                "bugs": {
                    "12345": {
                        "comments": []
                    }
                }
            },
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.bug_comments(12345)

        assert result == []
        
        await bz.close()


class TestBugzillaAddComment:
    """Tests for add_comment method"""

    async def test_add_comment_public_success(self, httpx_mock):
        """Test successful public comment creation"""
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/12345/comment",
            method="POST",
            status_code=201,
            json={"id": 2001},
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.add_comment(12345, "Test comment", is_private=False)

        assert result["id"] == 2001
        
        await bz.close()

    async def test_add_comment_private_success(self, httpx_mock):
        """Test successful private comment creation"""
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/12345/comment",
            method="POST",
            status_code=201,
            json={"id": 2002},
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        result = await bz.add_comment(12345, "Private comment", is_private=True)

        assert result["id"] == 2002
        
        await bz.close()

    async def test_add_comment_failure_status_code(self, httpx_mock):
        """Test add_comment raises exception on non-201 status"""
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/12345/comment",
            method="POST",
            status_code=403,
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        
        with pytest.raises(httpx.TransportError) as exc_info:
            await bz.add_comment(12345, "Test comment", is_private=False)
        
        assert "Status code: 403" in str(exc_info.value)
        
        await bz.close()

    async def test_add_comment_sends_correct_payload(self, httpx_mock):
        """Test that add_comment sends the correct JSON payload"""
        httpx_mock.add_response(
            url="https://bugzilla.mozilla.org/rest/bug/12345/comment",
            method="POST",
            status_code=201,
            json={"id": 2003},
        )

        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        await bz.add_comment(12345, "My comment text", is_private=True)

        # Verify the request was made with correct parameters
        request = httpx_mock.get_request()
        payload = json.loads(request.content)
        assert payload["comment"] == "My comment text"
        assert payload["is_private"] is True
        
        await bz.close()


class TestBugzillaClose:
    """Tests for close method"""

    async def test_close_closes_client(self, httpx_mock):
        """Test that close properly closes the async client"""
        bz = Bugzilla(url="https://bugzilla.mozilla.org", api_key="test-key")
        
        # Ensure client exists
        assert bz.client is not None
        
        # Close the client
        await bz.close()
        
        # Client should be closed - verify using the client's is_closed property
        assert bz.client.is_closed is True


class TestBugzillaAuth:
    """API key goes in the header where supported, query string otherwise"""

    URL = "https://legacy.example.com"
    PROBE = "https://legacy.example.com/rest/bug/1?include_fields=id"

    @pytest.fixture(autouse=True)
    def unknown_instance(self):
        bugzilla_module._header_auth_support.pop(self.URL, None)
        yield
        bugzilla_module._header_auth_support.pop(self.URL, None)

    async def test_uses_header_when_instance_reads_it(self, httpx_mock):
        httpx_mock.add_response(url=self.PROBE, json={"error": True, "code": 306})
        bz = Bugzilla(url=self.URL, api_key="secret")

        assert await bz.auth() == ({"X-BUGZILLA-API-KEY": "secret"}, {})
        # cached: second call doesn't probe again
        assert await bz.auth() == ({"X-BUGZILLA-API-KEY": "secret"}, {})
        assert len(httpx_mock.get_requests()) == 1

    async def test_probe_never_sends_real_key(self, httpx_mock):
        httpx_mock.add_response(url=self.PROBE, json={"error": True, "code": 306})
        await Bugzilla(url=self.URL, api_key="secret").auth()

        probe = httpx_mock.get_requests()[0]
        assert "secret" not in str(probe.url)
        assert probe.headers["X-BUGZILLA-API-KEY"] != "secret"

    async def test_falls_back_to_query_when_header_ignored(self, httpx_mock, caplog):
        """Stock Bugzilla 5.x ignores the header and answers anonymously"""
        httpx_mock.add_response(url=self.PROBE, json={"bugs": [{"id": 1}], "faults": []})
        bz = Bugzilla(url=self.URL, api_key="secret")

        assert await bz.auth() == ({}, {"api_key": "secret"})
        assert "deprecated" in caplog.text

    async def test_falls_back_to_query_when_login_required(self, httpx_mock):
        """Instances with requirelogin answer 410 when the header is ignored"""
        httpx_mock.add_response(url=self.PROBE, status_code=401, json={"error": True, "code": 410})
        assert await Bugzilla(url=self.URL, api_key="secret").auth() == ({}, {"api_key": "secret"})

    async def test_probe_failure_falls_back_without_caching(self, httpx_mock):
        httpx_mock.add_exception(httpx.ConnectError("down"), url=self.PROBE)
        bz = Bugzilla(url=self.URL, api_key="secret")

        assert await bz.auth() == ({}, {"api_key": "secret"})
        assert self.URL not in bugzilla_module._header_auth_support

    async def test_bug_info_uses_query_on_legacy_instance(self, httpx_mock):
        httpx_mock.add_response(url=self.PROBE, json={"bugs": [{"id": 1}]})
        httpx_mock.add_response(
            url="https://legacy.example.com/rest/bug/7?api_key=secret",
            json={"bugs": [{"id": 7}]},
        )
        assert (await Bugzilla(url=self.URL, api_key="secret").bug_info(7))["id"] == 7
