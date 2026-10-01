"""Local stdio server — reads credentials from env vars instead of HTTP headers."""
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from bugzilla_mcp.middleware.read_only import ReadOnlyMode, read_only_default
from bugzilla_mcp.tools.bugzilla import register_tools, WRITE_TOOL_NAMES
from bugzilla_mcp.utils import Bugzilla
import bugzilla_mcp.utils as utils

# Load environment variables from .env file
load_dotenv()

BUGZILLA_URL = os.environ.get("BUGZILLA_URL", "")
BUGZILLA_API_KEY = os.environ.get("BUGZILLA_API_KEY", "")

if not BUGZILLA_URL or not BUGZILLA_API_KEY:
    raise RuntimeError("BUGZILLA_URL and BUGZILLA_API_KEY env vars are required")

# Single-user process: one client for the whole session.
# asyncio.run copies this context into the server's tasks, so every tool sees it.
utils.current_bz.set(Bugzilla(url=BUGZILLA_URL, api_key=BUGZILLA_API_KEY, allow_local_files=True))

mcp = FastMCP("Bugzilla")

# Read-only unless BUGZILLA_READ_ONLY=false
mcp.add_middleware(ReadOnlyMode(WRITE_TOOL_NAMES, read_only_default(), allow_header_override=False))

register_tools(mcp, local_files=True)


if __name__ == "__main__":
    mcp.run(transport="stdio")
