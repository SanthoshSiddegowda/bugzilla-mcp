"""Middleware that hides and blocks write tools unless writes are enabled"""

import os
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext

READ_ONLY_ENV = "BUGZILLA_READ_ONLY"
READ_ONLY_HEADER = "read_only"

_FALSE = {"0", "false", "no", "off"}


def read_only_default() -> bool:
    """Read-only unless BUGZILLA_READ_ONLY is explicitly false/0/no/off"""
    return os.environ.get(READ_ONLY_ENV, "true").strip().lower() not in _FALSE


class ReadOnlyMode(Middleware):
    """Hide write tools from tools/list and refuse calls to them in read-only mode.

    The mode defaults to `default` (from BUGZILLA_READ_ONLY). On the HTTP server a
    client can override it per request with a `read_only: false` header.
    """

    def __init__(self, write_tools: set[str], default: bool, allow_header_override: bool):
        self.write_tools = write_tools
        self.default = default
        self.allow_header_override = allow_header_override

    def _read_only(self) -> bool:
        if self.allow_header_override:
            value = (get_http_headers() or {}).get(READ_ONLY_HEADER)
            if value is not None:
                return value.strip().lower() not in _FALSE
        return self.default

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        tools = await call_next(context)
        if not self._read_only():
            return tools
        return [t for t in tools if t.name not in self.write_tools]

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        if context.message.name in self.write_tools and self._read_only():
            how = (
                f"send the `{READ_ONLY_HEADER}: false` header"
                if self.allow_header_override
                else f"set {READ_ONLY_ENV}=false"
            )
            raise ToolError(
                f"`{context.message.name}` changes data, and this server is in read-only mode. "
                f"To enable write tools, {how}."
            )
        return await call_next(context)
