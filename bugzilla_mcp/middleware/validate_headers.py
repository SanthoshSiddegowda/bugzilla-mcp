"""Middleware to validate required HTTP headers"""

from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ValidationError
from bugzilla_mcp.utils import Bugzilla
import bugzilla_mcp.utils as utils


class ValidateHeaders(Middleware):
    """Validate incoming HTTP headers

    Requires both `api_key` and `bugzilla_url` headers to be present.
    Creates a Bugzilla client scoped to the current request (utils.current_bz)
    and closes it once the request is handled.
    """

    # on_request, not on_message: since fastmcp 4, on_message also sees notifications
    # (initialized, cancelled, progress), which never need a Bugzilla client.
    async def on_request(self, middleware_context: MiddlewareContext, call_next):
        headers = get_http_headers()

        # During inspection or when headers are not available, skip validation
        # and use a dummy Bugzilla instance so `fastmcp inspect` works without credentials
        if not headers:
            bz = Bugzilla(url="https://bugzilla.example.com", api_key="inspection-placeholder")
        else:
            if "api_key" not in headers:
                raise ValidationError("`api_key` header is required")

            if "bugzilla_url" not in headers:
                raise ValidationError("`bugzilla_url` header is required")

            bugzilla_url = headers["bugzilla_url"]

            # Normalize URL: add https:// if no protocol is specified
            if bugzilla_url and not bugzilla_url.startswith(("http://", "https://")):
                bugzilla_url = f"https://{bugzilla_url}"

            bz = Bugzilla(url=bugzilla_url, api_key=headers["api_key"])

        # all the tools & prompts read this for making api calls
        token = utils.current_bz.set(bz)
        try:
            return await call_next(middleware_context)
        finally:
            utils.current_bz.reset(token)
            await bz.close()
