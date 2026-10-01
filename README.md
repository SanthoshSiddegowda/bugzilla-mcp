# Bugzilla MCP Server

![Tests](https://github.com/SanthoshSiddegowda/bugzilla-mcp/actions/workflows/tests.yml/badge.svg)

A Model Context Protocol (MCP) server that enables secure interaction with Bugzilla instances. This server facilitates communication between AI applications and Bugzilla bug tracking systems through a controlled interface.

## Quick Start

**Hosted Server**: Use the production server at `https://bugzilla.fastmcp.app/mcp` - no local setup required! Just add it to your MCP client configuration with your Bugzilla API key and instance URL.

## Features

- Query bug information and comments
- Search bugs using Bugzilla's quicksearch syntax
- Add comments to bugs (public or private)
- Secure access through HTTP headers
- Comprehensive error handling

## Configuration

The server requires HTTP headers for authentication. Configure your MCP client with the following headers:

- **`api_key`** (Required) - Your Bugzilla API key
  - Get your API key from: `https://your-bugzilla-instance.com/userprefs.cgi?tab=apikey`
- **`bugzilla_url`** (Required) - The base URL of your Bugzilla instance (Bugzilla 5.0+)
  - Example: `https://bugzilla.test.org`

> **How the key is sent**: the server forwards your key to Bugzilla in the `X-BUGZILLA-API-KEY` header. Stock Bugzilla 5.0/5.2 don't support that header, so for them it falls back to `?api_key=` (deprecated, see [Deprecations](#deprecations)).
>
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

For local development:

```bash
# Using uv (recommended)
uv sync
uv run python server.py

# Or with standard Python
pip install .
python server.py
```

The server will start at `http://127.0.0.1:8000/mcp/`

**Production Server**: A hosted version is available at `https://bugzilla.fastmcp.app/mcp` - you can use this URL directly in your MCP client configuration without running the server locally.

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

## Deprecations

### API key in the query string (Bugzilla 5.0 / 5.2)

The server sends your API key to Bugzilla in the `X-BUGZILLA-API-KEY` header, which keeps it out of URLs and access logs. Stock Bugzilla **5.0 and 5.2 don't read that header**, so for those instances the server falls back to sending the key as `?api_key=` (the previous behaviour) and logs a deprecation warning.

- **Nothing breaks**: existing setups keep working with no config changes.
- The server detects support automatically, once per Bugzilla URL, using a probe that never sends your real key.
- bugzilla.mozilla.org and Bugzilla `master` already use the header.
- The query-string fallback will be removed once a stable Bugzilla release supports the header. Until then, if your Bugzilla runs 5.0/5.2, make sure its web server and any proxies don't keep query strings in access logs.

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
