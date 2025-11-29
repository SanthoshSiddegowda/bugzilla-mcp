"""Unit tests for ValidateHeaders middleware"""

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
    def mock_call_next(self):
        """Create a mock call_next function that returns an awaitable result"""
        async_result = AsyncMock(return_value="success")
        return MagicMock(side_effect=lambda ctx: async_result())

    @pytest.fixture(autouse=True)
    def reset_global_bz(self):
        """Reset the global bz before and after each test"""
        original_bz = utils.bz
        utils.bz = None
        yield
        utils.bz = original_bz

    async def test_valid_headers_creates_bugzilla_client(self, middleware, mock_context, mock_call_next):
        """Test that valid headers create a Bugzilla client"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "https://bugzilla.example.com"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert utils.bz is not None
        assert utils.bz.base_url == "https://bugzilla.example.com"
        assert utils.bz.api_key == "test-api-key"

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

    async def test_url_normalization_adds_https(self, middleware, mock_context, mock_call_next):
        """Test that URL without protocol gets https:// added"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "bugzilla.example.com"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert utils.bz.base_url == "https://bugzilla.example.com"

    async def test_url_normalization_preserves_http(self, middleware, mock_context, mock_call_next):
        """Test that URL with http:// is preserved"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "http://bugzilla.example.com"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert utils.bz.base_url == "http://bugzilla.example.com"

    async def test_url_normalization_preserves_https(self, middleware, mock_context, mock_call_next):
        """Test that URL with https:// is preserved"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "https://bugzilla.example.com"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert utils.bz.base_url == "https://bugzilla.example.com"

    async def test_empty_headers_creates_dummy_client(self, middleware, mock_context, mock_call_next):
        """Test that empty headers (inspection mode) creates a dummy client"""
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value={}):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert utils.bz is not None
        assert utils.bz.base_url == "https://bugzilla.example.com"
        assert utils.bz.api_key == "inspection-placeholder"

    async def test_none_headers_creates_dummy_client(self, middleware, mock_context, mock_call_next):
        """Test that None headers (inspection mode) creates a dummy client"""
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=None):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert utils.bz is not None
        assert utils.bz.base_url == "https://bugzilla.example.com"

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
    def mock_call_next(self):
        async_result = AsyncMock(return_value="success")
        return MagicMock(side_effect=lambda ctx: async_result())

    @pytest.fixture(autouse=True)
    def reset_global_bz(self):
        original_bz = utils.bz
        utils.bz = None
        yield
        utils.bz = original_bz

    async def test_url_with_path(self, middleware, mock_context, mock_call_next):
        """Test URL with path is handled correctly"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "https://bugzilla.example.com/bugzilla"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        assert utils.bz.base_url == "https://bugzilla.example.com/bugzilla"
        assert utils.bz.api_url == "https://bugzilla.example.com/bugzilla/rest"

    async def test_url_with_trailing_slash_normalization_not_needed(self, middleware, mock_context, mock_call_next):
        """Test URL with trailing slash (normalization may vary)"""
        headers = {
            "api_key": "test-api-key",
            "bugzilla_url": "bugzilla.example.com/path"
        }
        
        with patch("bugzilla_mcp.middleware.validate_headers.get_http_headers", return_value=headers):
            await middleware.on_message(mock_context, mock_call_next)
        
        # Should have https:// added
        assert utils.bz.base_url.startswith("https://")
