from dotenv import load_dotenv
from fastmcp import FastMCP
from bugzilla_mcp.middleware import ValidateHeaders
from bugzilla_mcp.middleware.read_only import ReadOnlyMode, read_only_default
from bugzilla_mcp.tools.bugzilla import register_tools, WRITE_TOOL_NAMES

# Load environment variables from .env file
load_dotenv()

mcp = FastMCP("Bugzilla")

mcp.add_middleware(ValidateHeaders())
# Read-only unless BUGZILLA_READ_ONLY=false, or the client sends `read_only: false`
mcp.add_middleware(ReadOnlyMode(WRITE_TOOL_NAMES, read_only_default(), allow_header_override=True))

# Shared, multi-user server: never register tools that write to this machine's disk
register_tools(mcp, local_files=False)


# start the MCP server (only when run directly, not during import/inspection)
if __name__ == "__main__":
    mcp.run(transport="http")
