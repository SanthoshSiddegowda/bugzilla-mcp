# Bugzilla MCP Server - Developer Guide

This document acts as the source of truth for developer tools, build/test commands, project architecture, and code styling rules for the Bugzilla Model Context Protocol (MCP) server.

---

## 🛠 Build & Run Commands

This project uses `uv` for python package and dependency management.

### Environment Setup
```bash
# Sync all dependencies (including test suite)
uv sync --all-extras
```

### Local Development Server (HTTP)
Starts the FastMCP HTTP server locally:
```bash
# Start the local development server (binds to http://127.0.0.1:8000/mcp)
uv run python server.py
```

### Package, CLI and Releases
- `bugzilla_mcp/cli.py` is the single place that builds servers: `build_local_server()` (stdio, single user, disk tools allowed) and `build_http_server()` (headers per request, never touches disk). `server.py` (FastMCP Cloud loads `server.py:mcp`) and `server_local.py` are thin wrappers around them.
- `bugzilla-mcp` console script → `cli.main()`. Build with `uv build` (backend: `uv_build`).
- `manifest.json` + `.mcpbignore` + `icon.png` make the Claude Desktop extension: `npx @anthropic-ai/mcpb pack`. Keep `manifest.json` `version` equal to `pyproject.toml` (a test checks it).
- Publishing a GitHub release `vX.Y.Z` runs `.github/workflows/release.yml`: tests, PyPI upload (trusted publishing), `.mcpb` attached to the release.

### Local Development Server (stdio)
Reads credentials from environment variables instead of HTTP headers:
```bash
export BUGZILLA_URL=https://bugzilla.example.com
export BUGZILLA_API_KEY=your-api-key
uv run python server_local.py
```

### Server Inspection
Inspect server tools, prompts, and configurations using the FastMCP CLI:
```bash
# Inspect the MCP server schemas and interface (should list 28 tools)
uv run fastmcp inspect server.py:mcp
```

---

## 🧪 Testing Commands

We use `pytest` with async/httpx plugins for writing and executing tests.

### Run All Tests
```bash
uv run pytest
```

### Run Tests with Coverage
```bash
uv run pytest --cov=bugzilla_mcp
```

### Run Specific Test Suites
```bash
# Run middleware tests only
uv run pytest tests/test_middleware

# Run tool wrapper tests only
uv run pytest tests/test_tools

# Run utility client tests only
uv run pytest tests/test_utils

# Run only the new tools tests
uv run pytest tests/test_utils/test_new_tools.py tests/test_tools/test_new_tools_tool.py

# Run a single specific test file
uv run pytest tests/test_tools/test_bugzilla.py
```

---

## 🚀 RTK - Rust Token Killer Integration

The repository integrates **RTK** to optimize CLI execution and save context tokens.

### RTK Core Commands
```bash
rtk gain              # Show token savings analytics
rtk gain --history    # Show command usage history with savings
rtk discover          # Analyze Claude Code history for missed opportunities
rtk proxy <cmd>       # Execute raw command without filtering (for debugging)
rtk --version         # Verify installation & view version
which rtk             # Verify binary path
```

### Hook-Based Transparent Execution
All standard CLI and git operations are transparently intercepted and rewritten by the Claude Code hook.
- Run them normally in your terminal (e.g., `git status`, `git diff`) and they are transparently mapped to `rtk <command>` without manual prefixing.

---

## 🏗 Codebase Architecture

The project is a standard Python application built with **FastMCP** implementing the **Model Context Protocol** (MCP) for communicating securely with Bugzilla REST endpoints.

```
bugzilla-mcp/
├── bugzilla_mcp/             # Main application package
│   ├── middleware/           # MCP Middleware (Header validation & client configuration)
│   │   ├── __init__.py
│   │   └── validate_headers.py
│   ├── tools/                # MCP Tool registration and execution
│   │   ├── __init__.py
│   │   └── bugzilla.py       # Tool functions + register_tools() (annotations)
│   ├── utils/                # Bugzilla REST client; current_bz ContextVar
│   │   ├── __init__.py
│   │   └── bugzilla.py       # Bugzilla REST API client class
│   └── __init__.py           # Package exports for all tools
├── tests/                    # PyTest suite (`uv run pytest tests`)
│   ├── test_middleware/      # Headers validation & edge case coverage
│   ├── test_tools/           # MCP tools wrapper tests
│   │   ├── test_bugzilla.py
│   │   ├── test_batch_tool.py
│   │   ├── test_attachments_tool.py
│   │   └── test_new_tools_tool.py  # New tools wrapper tests
│   ├── test_utils/           # Mocked API client unit tests
│   │   ├── test_bugzilla.py
│   │   ├── test_batch.py
│   │   └── test_new_tools.py       # New utility client tests
│   └── conftest.py           # Shared fixtures and mock definitions
├── docs/                     # Static NuxtJS-based documentation site
├── pyproject.toml            # Project dependencies & Python metadata
├── server.py                 # HTTP entrypoint (FastMCP, reads headers per-request)
├── server_local.py           # stdio entrypoint (reads from env vars)
├── CLAUDE.md                 # Developer guide (this file)
└── README.md                 # Public overview and integration guides
```

### Key Architectural Concepts

1. **Dynamic Client Initialization (`ValidateHeaders` Middleware)**:
   Because MCP servers are designed to be stateless or multi-tenant, authentication is passed dynamically per request through HTTP headers (`api_key` and `bugzilla_url`). The `ValidateHeaders` middleware extracts these headers on each request and binds a `Bugzilla` client to the `bugzilla_mcp.utils.current_bz` ContextVar for that request only, then closes it. Never store the client in a module global: on the shared hosted server, concurrent users would get each other's credentials. `server_local.py` (single user) sets `current_bz` once at startup.

   The client sends the API key in the `X-BUGZILLA-API-KEY` header when the instance supports it, and falls back to `?api_key=` (deprecated) for stock Bugzilla 5.0/5.2. Every request goes through `Bugzilla._request()`, which handles auth and status checks.

   Tools that touch the server's filesystem (`download_attachment(s)`, `upload_attachment(file_path=...)`) call `_require_local_files()` and only work when the client was created with `allow_local_files=True` (local server only).

2. **Graceful Inspection Fallback**:
   During FastMCP server inspection (via `fastmcp inspect`), HTTP headers are absent. The middleware detects this and initializes a dummy client reference (`https://bugzilla.example.com` / `inspection-placeholder`) to ensure schema discovery works seamlessly without auth failures.

3. **Token Budget Optimization**:
   - `bugs_quicksearch` and `bugs_advanced_search` return only essential fields (`id`, `summary`, `status`, `resolution`, `product`, `component`, `assigned_to`, `priority`, `severity`, `creation_time`, `last_change_time`).
   - `bugs_analysis_context` compresses comment threads longer than 4 messages to first 2 + last 2 with a placeholder.
   - Use `bug_info` / `bug_comments` for full uncompressed detail on a specific bug.

4. **Attachment Handling**:
   - `download_attachments` / `download_attachment` — decode base64 and write to `tmp/` for analysis.
   - `upload_attachment` — read a local file, base64-encode it, and POST to the Bugzilla attachment API. Content-type is auto-detected from file extension.

5. **Write Operations**:
   - `create_bug` — POST /rest/bug (file new bugs from agents/CI).
   - `update_bug` — PUT /rest/bug/(id) (change status, assign, escalate, mark duplicate, append comment in one call).
   - `add_comment` — POST /rest/bug/(id)/comment.
   - `tag_comment` — PUT /rest/bug/comment/(id)/tags (semantic labelling).

---

## 📋 Tool List

See the Features section of `README.md`. Tools are grouped in `READ_ONLY_TOOLS`, `ADDITIVE_TOOLS` and `DESTRUCTIVE_TOOLS` in `bugzilla_mcp/tools/bugzilla.py`, which decides their MCP annotations.

---

## 🎨 Code Style & Development Guidelines

### Python Guidelines
- **Python Version Compatibility**: Enforce compatibility with Python `>=3.12`.
- **Type Annotations**: Always include full type annotations for new functions, methods, and variables. Use standard generic types (e.g. `dict[str, Any]`, `list[Any]`).
- **Asynchronous Execution**: Always use `async`/`await` for HTTP calls and file interactions. Use the shared asynchronous `httpx.AsyncClient` from the `Bugzilla` utility client class (`self.client`) for any Bugzilla REST APIs.
- **Error Handling**:
  - Raise `fastmcp.exceptions.ToolError` inside MCP tools to convey user-friendly or LLM-friendly errors.
  - Raise `fastmcp.exceptions.PromptError` / `ValidationError` for malformed inputs or validation failures in middleware/prompts.
- **Docstrings**: Document every module, class, tool, and utility method with clear Python docstrings. Keep docstrings updated when refactoring function signatures.
- **Imports Sorting**: Follow PEP 8 guidelines. Group imports:
  1. Standard library imports
  2. Third-party imports (e.g., `fastmcp`, `httpx`, `dotenv`)
  3. Local package imports (e.g., `bugzilla_mcp`)

### Adding a New Tool (Checklist)
When adding a new MCP tool, follow these steps in order:

1. **Utility client** (`bugzilla_mcp/utils/bugzilla.py`): Add the `async` method to the `Bugzilla` class. Call the API through `self._request(...)`; don't build auth or status checks by hand.
2. **Tool wrapper** (`bugzilla_mcp/tools/bugzilla.py`): Add the `async` function. Get the client with `bz = _client()` and wrap failures in `ToolError`.
3. **Registration**: Add the function to `READ_ONLY_TOOLS`, `ADDITIVE_TOOLS`, `DESTRUCTIVE_TOOLS` or (if it touches the server's disk) `LOCAL_ONLY_TOOLS`. Anything outside `READ_ONLY_TOOLS` is a write tool: `ReadOnlyMode` hides it until writes are enabled (`read_only: false` header or `BUGZILLA_READ_ONLY=false`). `register_tools()` is shared by `server.py` and `server_local.py`; local-only tools are only registered by the latter.
4. **Package export** (`bugzilla_mcp/__init__.py`): Add to both the import block and `__all__`.
5. **Mock** (`tests/conftest.py`): Add `client.your_method = AsyncMock(...)` to `mock_bugzilla_client`.
6. **Tests** (`tests/test_utils/`, `tests/test_tools/`): Write unit tests for both the utility client and the tool wrapper.
7. **Docs** (`README.md` Features): Mention the new tool.
