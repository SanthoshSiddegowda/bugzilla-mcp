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
- **`bugzilla_url`** (Required) - The base URL of your Bugzilla instance
  - Example: `https://bugzilla.test.org`

## Usage

### With Claude Desktop

Add this to your `claude_desktop_config.json`:

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
pip install fastmcp httpx python-dotenv
python server.py
```

The server will start at `http://127.0.0.1:8000/mcp/`

**Production Server**: A hosted version is available at `https://bugzilla.fastmcp.app/mcp` - you can use this URL directly in your MCP client configuration without running the server locally.

## Development

```bash
# Clone the repository
git clone <repository-url>
cd bugzilla-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
uv sync

# Inspect the server
fastmcp inspect server.py:mcp
```

## Security Considerations

- Never commit API keys or credentials
- Use API keys with minimal required permissions
- Consider implementing rate limiting for production use
- Use HTTPS for the Bugzilla URL in production

## Security Best Practices

This MCP implementation requires Bugzilla API access to function. For security:

1. **Create a dedicated Bugzilla API key** with minimal permissions
2. **Never use administrative accounts** or full-access API keys
3. **Restrict API key permissions** to only necessary operations
4. **Regular security reviews** of API key usage

⚠️ **IMPORTANT**: Always follow the principle of least privilege when configuring API access.

## Acknowledgments

This project was inspired by [Sai Karthik's mcp-bugzilla](https://kskarthik.gitlab.io/logs/mcp-server-bugzilla/) project. His work on building an MCP server for Bugzilla using FastMCP provided valuable insights and inspiration. Thank you for sharing your experience and contributing to the MCP ecosystem!

## License

Apache 2.0 License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
