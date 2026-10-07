"""`bugzilla-mcp` command and the server builders shared by server.py / server_local.py"""

import argparse
import os
from importlib.metadata import PackageNotFoundError, version

from dotenv import load_dotenv
from fastmcp import FastMCP

import bugzilla_mcp.utils as utils
from bugzilla_mcp.middleware import ValidateHeaders
from bugzilla_mcp.middleware.read_only import ReadOnlyMode, read_only_default
from bugzilla_mcp.tools.bugzilla import WRITE_TOOL_NAMES, register_tools
from bugzilla_mcp.utils import Bugzilla


def build_local_server(url: str, api_key: str, read_only: bool | None = None) -> FastMCP:
    """Single-user server: one Bugzilla client for the whole process.

    It may read and write files on this machine (attachment downloads, uploads
    from a path), because the only user is whoever started it.
    """
    # asyncio.run copies this context into the server's tasks, so every tool sees it
    utils.current_bz.set(Bugzilla(url=url, api_key=api_key, allow_local_files=True))

    mcp = FastMCP("Bugzilla")
    mcp.add_middleware(ReadOnlyMode(
        WRITE_TOOL_NAMES,
        read_only_default() if read_only is None else read_only,
        allow_header_override=False,
    ))
    register_tools(mcp, local_files=True)
    return mcp


def build_http_server(read_only: bool | None = None) -> FastMCP:
    """Multi-user server: each request brings its own `api_key` / `bugzilla_url` headers.

    Never touches this machine's disk, and clients may send `read_only: false`.
    """
    mcp = FastMCP("Bugzilla")
    mcp.add_middleware(ValidateHeaders())
    mcp.add_middleware(ReadOnlyMode(
        WRITE_TOOL_NAMES,
        read_only_default() if read_only is None else read_only,
        allow_header_override=True,
    ))
    register_tools(mcp, local_files=False)
    return mcp


def _version() -> str:
    try:
        return version("bugzilla-mcp")
    except PackageNotFoundError:  # running from a checkout that isn't installed
        return "unknown"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="bugzilla-mcp",
        description=(
            "Bugzilla MCP server. stdio (default) reads BUGZILLA_URL and BUGZILLA_API_KEY "
            "from the environment or a .env file; http takes them from each request's headers."
        ),
    )
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1", help="http only (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="http only (default: 8000)")
    parser.add_argument(
        "--allow-writes",
        action="store_true",
        help="enable tools that change Bugzilla (same as BUGZILLA_READ_ONLY=false)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    args = parser.parse_args(argv)

    load_dotenv()  # optional .env in the current directory
    read_only = False if args.allow_writes else None  # None: BUGZILLA_READ_ONLY decides

    if args.transport == "stdio":
        # The API key only comes from the environment: command-line arguments
        # show up in process lists and shell history.
        url = os.environ.get("BUGZILLA_URL", "")
        api_key = os.environ.get("BUGZILLA_API_KEY", "")
        if not url or not api_key:
            parser.error("set BUGZILLA_URL and BUGZILLA_API_KEY (environment or .env)")
        build_local_server(url, api_key, read_only).run(transport="stdio", show_banner=False)
    else:
        build_http_server(read_only).run(transport="http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
