# Bugzilla MCP Server

![Tests](https://github.com/SanthoshSiddegowda/bugzilla-mcp/actions/workflows/tests.yml/badge.svg)

A Model Context Protocol (MCP) server that enables secure interaction with Bugzilla instances. This server facilitates communication between AI applications and Bugzilla bug tracking systems through a controlled interface.

## Quick Start

**Hosted Server**: Use the production server at `https://bugzilla.fastmcp.app/mcp` - no local setup required! Just add it to your MCP client configuration with your Bugzilla API key and instance URL.

## Features

This MCP server provides a comprehensive interface for AI agents to interact with Bugzilla, exposing **28 specialized tools** categorized into:

- **🔍 Advanced Search & Discovery**:
  - Full-text search with Bugzilla's fast `bugs_quicksearch` syntax.
  - Multi-criteria `bugs_advanced_search` (filter by product, component, status, severity, keywords, and more).
  - Browse accessible products (`list_products`) and component schemas (`get_product_components`).
  - Read a bug (`bug_info`) in compact form by default: empty fields (e.g. unused `cf_*` custom fields) and the `update_token` are dropped. Pass `full=True` for every field.

- **✏️ Write & Comprehensive Updates**:
  - File new bugs (`create_bug`) with assignees, keywords, severities, and descriptions.
  - Tools carry MCP hints (`readOnlyHint` / `destructiveHint`), so clients can auto-approve reads and ask before `update_bug` changes a bug.
  - Atomically update any bug property (`update_bug`) — supports status, resolution, assignments, priority/severity, milestone, version, CC list, keywords, and any custom fields (e.g. `cf_qatouch_id`).
  - Append public or private comments (`add_comment`) and tag comments semantically (`tag_comment`).

- **📊 Bulk Triage & Analytics**:
  - Parallel batch retrieval of metadata (`bugs_info`) and comments (`bugs_comments`).
  - Compress long discussion threads dynamically (`bugs_analysis_context`) to fit in standard LLM context windows.
  - Categorize bug batches automatically (`classify_bugs_heuristics`) and generate statistical metrics (`analyze_bugs_statistics`).

- **📎 Robust Attachment Handling**:
  - List a bug's attachments (`bug_attachments`) and read one (`get_attachment`): screenshots come back as images, logs and patches as text.
  - Attach logs, patches or files (`upload_attachment`) by passing `text` or `data_base64`, with automatic content-type detection.
  - **Local server only** (`server_local.py`): save attachments to disk (`download_attachments`, `download_attachment`) and upload from a `file_path`. The hosted server refuses these so callers can't read or write files on the shared machine.

- **👤 User Management & Auditing**:
  - Audit full change histories (`bug_history`) with time and field filters.
  - Fetch detailed user profiles (`get_user`) and search user databases (`search_users`).
  - Traverse dependency/blocker trees (`bug_dependencies`) and resolve duplicate bug chains (`duplicate_chain`).

## Configuration

The server requires HTTP headers for authentication. Configure your MCP client with the following headers:

- **`api_key`** (Required) - Your Bugzilla API key
  - Get your API key from: `https://your-bugzilla-instance.com/userprefs.cgi?tab=apikey`
- **`bugzilla_url`** (Required) - The base URL of your Bugzilla instance (Bugzilla 5.0+)
  - Example: `https://bugzilla.test.org`

> **Hosted server**: when you use `https://bugzilla.fastmcp.app/mcp`, your API key passes through that server on its way to your Bugzilla instance. If you don't want a third party to handle your key, [run the server locally](#running-the-server-locally).

## Usage

### With Claude Code

```bash
claude mcp add --transport http bugzilla https://bugzilla.fastmcp.app/mcp \
  --scope user \
  --header "api_key: your-api-key-here" \
  --header "bugzilla_url: https://bugzilla.example.com"
```

`--scope user` makes the server available in all projects and keeps your key out of the repo. Verify with `claude mcp list`, then start a new session.

To share the config with a team via a project `.mcp.json`, reference environment variables instead of hardcoding the key:

```json
{
  "mcpServers": {
    "bugzilla": {
      "type": "http",
      "url": "https://bugzilla.fastmcp.app/mcp",
      "headers": {
        "api_key": "${BUGZILLA_API_KEY}",
        "bugzilla_url": "${BUGZILLA_URL}"
      }
    }
  }
}
```

### With Claude Desktop

Claude Desktop's `claude_desktop_config.json` only supports local (stdio) servers, so connect through the [`mcp-remote`](https://www.npmjs.com/package/mcp-remote) bridge (requires Node.js):

```json
{
  "mcpServers": {
    "bugzilla": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://bugzilla.fastmcp.app/mcp",
        "--header",
        "api_key:your-api-key-here",
        "--header",
        "bugzilla_url:https://bugzilla.example.com"
      ]
    }
  }
}
```

Restart Claude Desktop after saving.

> **Note**: For local development, use `http://127.0.0.1:8000/mcp` instead.

### With Cursor IDE

Add this to your `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "bugzilla": {
      "url": "https://bugzilla.fastmcp.app/mcp",
      "headers": {
        "api_key": "your-api-key-here",
        "bugzilla_url": "https://bugzilla.example.com"
      }
    }
  }
}
```

> **Note**: For local development, use `http://127.0.0.1:8000/mcp` instead.

### With Visual Studio Code

Add this to your `mcp.json`:

```json
{
  "servers": {
    "bugzilla": {
      "type": "http",
      "url": "https://bugzilla.fastmcp.app/mcp",
      "headers": {
        "api_key": "your-api-key-here",
        "bugzilla_url": "https://bugzilla.example.com"
      }
    }
  }
}
```

> **Note**: For local development, use `http://127.0.0.1:8000/mcp` instead.

### Running the Server Locally

For local development, testing, or self-hosting, you can run the Bugzilla MCP server in two modes: **Local stdio Server** (recommended for personal use/single user) or **Local HTTP Server** (best for multi-user or remote setups).

#### 🛠️ Environment Configuration

Before running either server type, you should configure your Bugzilla credentials. We provide a `.env.example` file in the root of the project to help you get started.

1. **Create your `.env` file**:
   ```bash
   cp .env.example .env
   ```
2. **Configure your credentials**:
   Open the `.env` file in your preferred editor and fill in your details:
   ```ini
   BUGZILLA_URL=https://bugzilla.example.com
   BUGZILLA_API_KEY=your-api-key-here
   ```
   > [!NOTE]
   > - **`BUGZILLA_URL`**: The base URL of your Bugzilla instance (e.g. `https://bugzilla.mozilla.org`).
   > - **`BUGZILLA_API_KEY`**: Your Bugzilla API key. You can generate one from your Bugzilla User Preferences page (usually under `https://your-bugzilla-instance.com/userprefs.cgi?tab=apikey`).

---

#### 1. Local stdio Server (Recommended)

This runs as a background process managed directly by your MCP client (such as Claude Desktop or Cursor) using standard input/output (stdio) transport. It reads credentials securely from your environment variables or the `.env` file.

##### Step 1: Install Dependencies

```bash
# Using uv (highly recommended)
uv sync

# Or using standard Python virtual environment
python -m venv .venv
source .venv/bin/activate
pip install .
```

##### Step 2: Configure MCP Client

Make sure to replace `/absolute/path/to/bugzilla-mcp` with the actual absolute path to this project directory on your machine.

###### **With Claude Desktop**
Add the following to your `claude_desktop_config.json` (typically located at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS or `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "bugzilla-local": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/bugzilla-mcp",
        "python",
        "server_local.py"
      ],
      "env": {
        "BUGZILLA_URL": "https://bugzilla.example.com",
        "BUGZILLA_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

###### **With Cursor IDE**
You can configure the server in **Cursor Settings -> Features -> MCP** as a `command` type:

- **Name**: `bugzilla-local`
- **Type**: `command`
- **Command**: `uv run --directory /absolute/path/to/bugzilla-mcp python server_local.py`

Or add it directly to your `.cursor/mcp.json` or `mcp.json` if configured programmatically:

```json
{
  "mcpServers": {
    "bugzilla-local": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/bugzilla-mcp",
        "python",
        "server_local.py"
      ],
      "env": {
        "BUGZILLA_URL": "https://bugzilla.example.com",
        "BUGZILLA_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

###### **With Claude Code (CLI)**
To add the Bugzilla MCP server to Claude Code, run the following command in your terminal:

```bash
# Add as a project-scoped server (available only in current project)
claude mcp add bugzilla-local --scope project -- uv run --directory /absolute/path/to/bugzilla-mcp python server_local.py

# Or add as a user-scoped server (available across all projects)
claude mcp add bugzilla-local --scope user -- uv run --directory /absolute/path/to/bugzilla-mcp python server_local.py
```

> [!TIP]
> - By configuring the `.env` file in `/absolute/path/to/bugzilla-mcp`, the server automatically loads your `BUGZILLA_URL` and `BUGZILLA_API_KEY` on startup without needing to pass them explicitly as CLI flags.
> - You can check the server status in Claude Code using `claude mcp list` or by running the `/mcp` command inside Claude Code. Remember to restart your Claude Code session after adding or modifying the server!

---

#### 2. Local HTTP Server

This runs a local HTTP server with Server-Sent Events (SSE) transport. It's dynamic and validates credentials per-request, meaning clients must supply headers on each call.

##### Step 1: Start the HTTP Server

```bash
# Start local HTTP server
uv run python server.py
```
The server will start at `http://127.0.0.1:8000/mcp`.

##### Step 2: Configure Client to Use HTTP Server

Configure your MCP clients to use this local URL and provide authentication headers dynamically:

###### **With Claude Desktop or Cursor**
```json
{
  "mcpServers": {
    "bugzilla-local-http": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "api_key": "your-api-key-here",
        "bugzilla_url": "https://bugzilla.example.com"
      }
    }
  }
}
```

###### **With Visual Studio Code**
Add this to your `mcp.json`:
```json
{
  "servers": {
    "bugzilla-local-http": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "api_key": "your-api-key-here",
        "bugzilla_url": "https://bugzilla.example.com"
      }
    }
  }
}
```

## Development

```bash
git clone https://github.com/SanthoshSiddegowda/bugzilla-mcp.git
cd bugzilla-mcp

# Install dependencies (uv creates the virtual environment)
uv sync --all-extras

# Run the tests
uv run pytest tests

# Inspect the server
uv run fastmcp inspect server.py:mcp
```

## Security Considerations

- Never commit API keys or credentials
- Use API keys with minimal required permissions
- Consider implementing rate limiting for production use
- Use HTTPS for the Bugzilla URL in production

## Security Best Practices

This MCP implementation requires Bugzilla API access to function. For security:

1. **Use a dedicated Bugzilla account**. A Bugzilla API key has the same permissions as the account that created it, so limit the account (group membership, product access) rather than the key
2. **Never use administrative accounts**
3. **Be aware the server can write**: the `add_comment` tool posts comments as that account
4. **Revoke and rotate keys** regularly from `userprefs.cgi?tab=apikey`

⚠️ **IMPORTANT**: Always follow the principle of least privilege when configuring API access.

## Acknowledgments

This project was inspired by [Sai Karthik's mcp-bugzilla](https://kskarthik.gitlab.io/logs/mcp-server-bugzilla/) project. His work on building an MCP server for Bugzilla using FastMCP provided valuable insights and inspiration. Thank you for sharing your experience and contributing to the MCP ecosystem!

## License

Apache 2.0 License - see LICENSE file for details.
