# Bugzilla MCP Server

[![PyPI](https://img.shields.io/pypi/v/bugzilla-mcp)](https://pypi.org/project/bugzilla-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/bugzilla-mcp)](https://pypi.org/project/bugzilla-mcp/)
[![License](https://img.shields.io/pypi/l/bugzilla-mcp)](https://github.com/SanthoshSiddegowda/bugzilla-mcp/blob/main/LICENSE)
[![Tests](https://github.com/SanthoshSiddegowda/bugzilla-mcp/actions/workflows/tests.yml/badge.svg)](https://github.com/SanthoshSiddegowda/bugzilla-mcp/actions/workflows/tests.yml)

An MCP server that lets Claude and other AI assistants search, read, triage and update bugs in any Bugzilla 5.0+ instance.

- **Runs on your machine**: your Bugzilla API key never leaves it.
- **Read-only by default**: tools that change Bugzilla stay off until you turn them on, and `update_bug` has a dry run.
- **Built for triage**: batch reads, history, duplicates, classification, and screenshots that come through as images.

📖 **Docs:** [bugzilla-mcp.vercel.app](https://bugzilla-mcp.vercel.app/getting-started/installation)

## Install

### Claude Desktop: one click

1. Download **[bugzilla-mcp.mcpb](https://github.com/SanthoshSiddegowda/bugzilla-mcp/releases/latest/download/bugzilla-mcp.mcpb)** from the latest release.
2. Double-click it (or open **Settings → Extensions** and install it there).
3. Enter your Bugzilla URL and [API key](#api-key). Leave **Read-only** ticked unless you want Claude to update bugs.

No Python or terminal needed. Claude Desktop stores the API key as a secret.

### Claude Code

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) once, then:

```bash
claude mcp add bugzilla --scope user \
  -e BUGZILLA_URL=https://bugzilla.example.com \
  -e BUGZILLA_API_KEY=your-api-key \
  -- uvx bugzilla-mcp
```

Add `--allow-writes` after `bugzilla-mcp` to enable write tools. Check it with `claude mcp list`.

### Cursor, VS Code and other MCP clients

```json
{
  "mcpServers": {
    "bugzilla": {
      "command": "uvx",
      "args": ["bugzilla-mcp"],
      "env": {
        "BUGZILLA_URL": "https://bugzilla.example.com",
        "BUGZILLA_API_KEY": "your-api-key"
      }
    }
  }
}
```

If the client can't find `uvx` (desktop apps don't always load your shell's `PATH`), use the full path from `which uvx`.

### pip

Requires **Python 3.12+**.

```bash
pip install bugzilla-mcp
bugzilla-mcp --help
```

On macOS, `pip`/`python3` is often Apple's Python 3.9, and pip then reports *"No matching distribution found"*. Use `uv tool install bugzilla-mcp` (or `uvx bugzilla-mcp`), which picks a suitable Python for you.

### Options

| Setting | How | Default |
|---|---|---|
| Bugzilla URL | `BUGZILLA_URL` | required |
| API key | `BUGZILLA_API_KEY` (environment or `.env` only, never a flag) | required |
| Write tools | `--allow-writes` or `BUGZILLA_READ_ONLY=false` | off |
| Remove tools | `BUGZILLA_DISABLED_TOOLS=update_bug,create_bug` | none |
| HTTP server for several users | `bugzilla-mcp --transport http --host 0.0.0.0 --port 8000` | stdio |

See [Configuration](https://bugzilla-mcp.vercel.app/getting-started/configuration) for every option.

### API key

Create one in Bugzilla under **Preferences → API Keys** (`https://your-bugzilla/userprefs.cgi?tab=apikey`). The key has the same permissions as your account, so a dedicated account with limited access is safest.

## Tools

28 tools, grouped by what they do. Full reference: [Usage](https://bugzilla-mcp.vercel.app/getting-started/usage).

| Group | Tools |
|---|---|
| Read | `bug_info` (compact by default, `full` / `include_fields`), `bug_comments`, `bug_history`, `bug_dependencies`, `duplicate_chain`, `bug_url`, `server_url` |
| Search | `bugs_quicksearch`, `bugs_advanced_search`, `learn_quicksearch_syntax` |
| Attachments | `bug_attachments`, `get_attachment` (images as images, logs and patches as text), `upload_attachment` |
| Batch and triage | `bugs_info`, `bugs_comments`, `bugs_analysis_context`, `classify_bugs_heuristics`, `analyze_bugs_statistics` |
| Users and products | `get_user`, `search_users`, `list_products`, `get_product_components` |
| Change (off until writes are enabled) | `update_bug` (with `dry_run`), `create_bug`, `add_comment`, `tag_comment` |
| Local only | `download_attachments`, `download_attachment` (save to disk) |

Every tool carries MCP hints (read-only / destructive), so clients can run reads without asking and confirm before changes.

## Try the hosted server

To try it without installing anything, point your client at `https://bugzilla.fastmcp.app/mcp` and send `api_key` and `bugzilla_url` as headers ([examples](https://bugzilla-mcp.vercel.app/getting-started/configuration#hosted-server)). Your API key passes through that server on its way to your Bugzilla, so for real use, install locally.

## Security

- The server starts read-only. Enable writes only for an account that should be allowed to change bugs.
- Use a dedicated Bugzilla account with limited access; never an admin account.
- Your key goes to Bugzilla in the `X-BUGZILLA-API-KEY` header. Stock Bugzilla 5.0/5.2 ignore that header, so for them it falls back to `?api_key=` (deprecated; keep query strings out of your web server's access logs).

More: [Security](https://bugzilla-mcp.vercel.app/getting-started/security).

## Development

```bash
git clone https://github.com/SanthoshSiddegowda/bugzilla-mcp.git
cd bugzilla-mcp
uv sync --all-extras
uv run pytest tests
uv run bugzilla-mcp --help
```

Contributor notes are in [CLAUDE.md](https://github.com/SanthoshSiddegowda/bugzilla-mcp/blob/main/CLAUDE.md). Releases publish to PyPI and attach the Claude Desktop extension automatically when a GitHub release is published.

## Acknowledgments

Inspired by [Sai Karthik's mcp-bugzilla](https://kskarthik.gitlab.io/logs/mcp-server-bugzilla/). Thank you for sharing your work with the MCP community. Looking for openSUSE's server? That's [`mcp-bugzilla`](https://github.com/openSUSE/mcp-bugzilla), a separate project.

## License

[Apache 2.0](https://github.com/SanthoshSiddegowda/bugzilla-mcp/blob/main/LICENSE)
