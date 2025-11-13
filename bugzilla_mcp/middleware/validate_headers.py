"""Middleware to validate required HTTP headers"""

from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ValidationError
from bugzilla_mcp.utils import Bugzilla
import bugzilla_mcp.utils as utils


class ValidateHeaders(Middleware):
    """Validate incoming HTTP headers
    
    Requires both `api_key` and `bugzilla_url` headers to be present.
    Creates a Bugzilla instance and stores it in utils.bz for use by all tools.
    """

    async def on_message(self, middleware_context: MiddlewareContext, call_next):
        headers = get_http_headers()
        
        # During inspection or when headers are not available, skip validation
        # and create a dummy Bugzilla instance for inspection purposes
        if not headers or len(headers) == 0:
            # Create a dummy instance with placeholder values for inspection
            # This allows fastmcp inspect to work without actual credentials
            utils.bz = Bugzilla(url="https://bugzilla.example.com", api_key="inspection-placeholder")
            result = call_next(middleware_context)
            return await result
        
        # Check for required headers
        if "api_key" not in headers:
            raise ValidationError("`api_key` header is required")
        
        if "bugzilla_url" not in headers:
            raise ValidationError("`bugzilla_url` header is required")
        
        bugzilla_url = headers["bugzilla_url"]
        
        # Normalize URL: add https:// if no protocol is specified
        if bugzilla_url and not bugzilla_url.startswith(("http://", "https://")):
            bugzilla_url = f"https://{bugzilla_url}"
        
        # all the tools & prompts will use this for making api calls
        utils.bz = Bugzilla(url=bugzilla_url, api_key=headers["api_key"])

        result = call_next(middleware_context)

        return await result

