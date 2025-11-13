from dotenv import load_dotenv
from fastmcp import FastMCP
from bugzilla_mcp.middleware import ValidateHeaders
from bugzilla_mcp.tools.bugzilla import (
    bug_info,
    bug_comments,
    add_comment,
    bugs_quicksearch,
    learn_quicksearch_syntax,
    server_url,
    bug_url,
)

# Load environment variables from .env file
load_dotenv()

mcp = FastMCP("Bugzilla")

mcp.add_middleware(ValidateHeaders())

# Register tools from bugzilla_mcp module
mcp.tool()(bug_info)
mcp.tool()(bug_comments)
mcp.tool()(add_comment)
mcp.tool()(bugs_quicksearch)
mcp.tool()(learn_quicksearch_syntax)
mcp.tool()(server_url)
mcp.tool()(bug_url)


# start the MCP server (only when run directly, not during import/inspection)
if __name__ == "__main__":
    mcp.run(transport="http")
