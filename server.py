from dotenv import load_dotenv
from fastmcp import FastMCP
from bugzilla_mcp.middleware import ValidateHeaders
from bugzilla_mcp.tools.bugzilla import register_tools

# Load environment variables from .env file
load_dotenv()

mcp = FastMCP("Bugzilla")

mcp.add_middleware(ValidateHeaders())

register_tools(mcp)


# start the MCP server (only when run directly, not during import/inspection)
if __name__ == "__main__":
    mcp.run(transport="http")
