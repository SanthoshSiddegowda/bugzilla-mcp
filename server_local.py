"""Local stdio server from a checkout. Kept for existing configs; prefer `uvx bugzilla-mcp`.

Same as `bugzilla-mcp` (stdio is the default transport).
"""
import os
from dotenv import load_dotenv
from bugzilla_mcp.cli import build_local_server

load_dotenv()

BUGZILLA_URL = os.environ.get("BUGZILLA_URL", "")
BUGZILLA_API_KEY = os.environ.get("BUGZILLA_API_KEY", "")

if not BUGZILLA_URL or not BUGZILLA_API_KEY:
    raise RuntimeError("BUGZILLA_URL and BUGZILLA_API_KEY env vars are required")

# Read-only unless BUGZILLA_READ_ONLY=false
mcp = build_local_server(BUGZILLA_URL, BUGZILLA_API_KEY)


if __name__ == "__main__":
    mcp.run(transport="stdio")
