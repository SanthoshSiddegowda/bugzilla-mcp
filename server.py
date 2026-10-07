"""Hosted / multi-user HTTP server. FastMCP Cloud loads `server.py:mcp`.

Same as `bugzilla-mcp --transport http`.
"""
from dotenv import load_dotenv
from bugzilla_mcp.cli import build_http_server

load_dotenv()

# Read-only unless BUGZILLA_READ_ONLY=false, or the client sends `read_only: false`
mcp = build_http_server()


if __name__ == "__main__":
    mcp.run(transport="http")
