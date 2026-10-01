"""Unit tests for ValidateHeaders middleware"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastmcp.exceptions import ValidationError
from bugzilla_mcp.middleware.validate_headers import ValidateHeaders
import bugzilla_mcp.utils as utils


class TestValidateHeadersMiddleware:
    """Tests for ValidateHeaders middleware"""

    @pytest.fixture
    def middleware(self):
        """Create a ValidateHeaders middleware instance"""
        return ValidateHeaders()

    @pytest.fixture
    def mock_context(self):
        """Create a mock middleware context"""
        return MagicMock()

    @pytest.fixture
    def seen(self):
        """Clients visible to the handler, captured while the request runs"""
        return []

    @pytest.fixture
    def mock_call_next(self, seen):
        """Create a mock call_next that records the current client and returns an awaitable result"""
        async def call_next(ctx):
            seen.append(utils.current_bz.get())
            return "success"
        return MagicMock(side_effect=call_next)

    async def test_valid_headers_creates_bugzilla_client(self, middleware, mock_context, mock_call_next, seen):
        """Test that valid headers create a Bugzilla client"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "https://bugzilla.example.com"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert seen[0] is not None
        assert seen[0].base_url == "https://bugzilla.example.com"
        assert seen[0].api_key == "test-api-key"

    async def test_missing_api_key_raises_validation_error(self, middleware, mock_context, mock_call_next):
        """Test that missing api_key header raises ValidationError"""
        headers = {
            "bugzilla_url": "https://bugzilla.example.com"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            with pytest.raises(ValidationError) as exc_info:
                await middleware.on_message(mock_context, mock_call_next)
        
        assert "api_key" in str(exc_info.value)

    async def test_missing_bugzilla_url_raises_validation_error(self, middleware, mock_context, mock_call_next):
        """Test that missing bugzilla_url header raises ValidationError"""
        headers = {
            "api_key": "test-api-key"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            with pytest.raises(ValidationError) as exc_info:
                await middleware.on_message(mock_context, mock_call_next)
        
        assert "bugzilla_url" in str(exc_info.value)

    async def test_url_normalization_adds_https(self, middleware, mock_context, mock_call_next, seen):
        """Test that URL without protocol gets https:// added"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "bugzilla.example.com"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert seen[0].base_url == "https://bugzilla.example.com"

    async def test_url_normalization_preserves_http(self, middleware, mock_context, mock_call_next, seen):
        """Test that URL with http:// is preserved"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "http://bugzilla.example.com"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert seen[0].base_url == "http://bugzilla.example.com"

    async def test_url_normalization_preserves_https(self, middleware, mock_context, mock_call_next, seen):
        """Test that URL with https:// is preserved"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "https://bugzilla.example.com"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert seen[0].base_url == "https://bugzilla.example.com"

    async def test_empty_headers_creates_dummy_client(self, middleware, mock_context, mock_call_next, seen):
        """Test that empty headers (inspection mode) creates a dummy client"""
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value={}):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert seen[0] is not None
        assert seen[0].base_url == "https://bugzilla.example.com"
        assert seen[0].api_key == "inspection-placeholder"

    async def test_none_headers_creates_dummy_client(self, middleware, mock_context, mock_call_next, seen):
        """Test that None headers (inspection mode) creates a dummy client"""
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=None):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert seen[0] is not None
        assert seen[0].base_url == "https://bugzilla.example.com"

    async def test_middleware_calls_next(self, middleware, mock_context, mock_call_next):
        """Test that middleware calls the next handler"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "https://bugzilla.example.com"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            result = await middleware.on_message(mock_context, mock_call_next)
        
        mock_call_next.assert_called_once_with(mock_context)
        assert result == "success"

    async def test_middleware_returns_result_from_next(self, middleware, mock_context):
        """Test that middleware returns the result from next handler"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "https://bugzilla.example.com"
        }
        
        expected_result = {"data": "test_data"}
        async_result = AsyncMock(return_value=expected_result)
        mock_call_next = MagicMock(side_effect=lambda ctx: async_result())
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            result = await middleware.on_message(mock_context, mock_call_next)
        
        assert result == expected_result


class TestValidateHeadersUrlEdgeCases:
    """Edge case tests for URL handling in ValidateHeaders middleware"""

    @pytest.fixture
    def middleware(self):
        return ValidateHeaders()

    @pytest.fixture
    def mock_context(self):
        return MagicMock()

    @pytest.fixture
    def seen(self):
        return []

    @pytest.fixture
    def mock_call_next(self, seen):
        async def call_next(ctx):
            seen.append(utils.current_bz.get())
            return "success"
        return MagicMock(side_effect=call_next)

    async def test_url_with_path(self, middleware, mock_context, mock_call_next, seen):
        """Test URL with path is handled correctly"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "https://bugzilla.example.com/bugzilla"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert seen[0].base_url == "https://bugzilla.example.com/bugzilla"
        assert seen[0].api_url == "https://bugzilla.example.com/bugzilla/rest"

    async def test_url_with_trailing_slash_normalization_not_needed(self, middleware, mock_context, mock_call_next, seen):
        """Test URL with trailing slash (normalization may vary)"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "bugzilla.example.com/path"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        # Should have https:// added
        assert seen[0].base_url.startswith("https://")


class TestValidateHeadersRequestIsolation:
    """Each request gets its own client, which is cleared and closed afterwards"""

    async def test_client_cleared_and_closed_after_request(self):
        headers = {"api_key": "k", "bugzilla_url": "https://bugzilla.example.com"}
        seen = []

        async def call_next(ctx):
            seen.append(utils.current_bz.get())
            return "ok"

        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await ValidateHeaders().on_message(MagicMock(), call_next)

        assert utils.current_bz.get() is None
        assert seen[0].client.is_closed

    async def test_concurrent_requests_do_not_share_credentials(self):
        """Request A must keep its own key even if request B starts while A is in flight"""
        a_started, b_done = asyncio.Event(), asyncio.Event()
        keys = {}

        async def call_next_a(ctx):
            a_started.set()
            await b_done.wait()
            keys["a"] = utils.current_bz.get().api_key
            return "a"

        async def call_next_b(ctx):
            keys["b"] = utils.current_bz.get().api_key
            b_done.set()
            return "b"

        headers = [
            {"api_key": "key-a", "bugzilla_url": "https://a.example.com"},
            {"api_key": "key-b", "bugzilla_url": "https://b.example.com"},
        ]
        middleware = ValidateHeaders()
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", side_effect=headers):
            task_a = asyncio.create_task(middleware.on_message(MagicMock(), call_next_a))
            await a_started.wait()
            await middleware.on_message(MagicMock(), call_next_b)
            await task_a

        assert keys == {"a": "key-a", "b": "key-b"}
