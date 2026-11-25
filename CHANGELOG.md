# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).
Before 1.0.0, minor versions may contain breaking changes; they are marked **Breaking** below.

## [Unreleased]

## [0.7.0] - 2026-11-25

### Added
- `create_bug` accepts `extra_fields` for custom fields (e.g. `{"cf_after_release": "false"}`), matching `update_bug`.

## [0.6.1] - 2026-11-04

### Changed
- **Breaking:** downloaded attachments default to `~/.cache/bugzilla-mcp/attachments` instead of `tmp/` in the working directory.
- HTTP requests to Bugzilla time out after 30 seconds.

### Security
- The API key is no longer put in the URL when the header-auth probe fails.

## [0.6.0] - 2026-10-07

### Added
- Published on PyPI: run with `uvx bugzilla-mcp` or install with `pipx`.
- Claude Desktop extension (`.mcpb`) attached to each GitHub release.

### Changed
- **Breaking:** requires FastMCP 4.

## [0.5.0] - 2026-10-01

### Added
- `update_bug` dry run: shows planned changes and current values without writing.
- Tool parameters accept a single value or a list where it makes sense.

### Changed
- **Breaking:** read-only mode is the default. Write tools are hidden until enabled with the `read_only: false` header or `BUGZILLA_READ_ONLY=false`.

## [0.4.0] - 2026-10-01

### Added
- Write tools: `create_bug`, `update_bug` (incl. custom fields), `tag_comment`, `upload_attachment`.
- Read tools: bug history, advanced search, `analyze_bugs_statistics`, batch bug tools, attachment downloads.
- Local stdio server (`server_local.py`) reading credentials from environment variables.

### Security
- Bugzilla client is isolated per request, so concurrent users of the hosted server never share credentials.
- API key sent in the `X-BUGZILLA-API-KEY` header; the query-string fallback is kept only for stock Bugzilla 5.x.
- Tools that read or write the server's disk only work on the local server.

## [0.3.0] - 2025-11-29

### Added
- Unit test suite and GitHub Actions CI.

## [0.2.0] - 2025-11-24

### Fixed
- Error when a tool returned no object.

## [0.1.0] - 2025-11-14

### Added
- Initial release of the Bugzilla MCP server (bug search, bug info, comments, `add_comment`) and documentation site.

[Unreleased]: https://github.com/SanthoshSiddegowda/bugzilla-mcp/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/SanthoshSiddegowda/bugzilla-mcp/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/SanthoshSiddegowda/bugzilla-mcp/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/SanthoshSiddegowda/bugzilla-mcp/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/SanthoshSiddegowda/bugzilla-mcp/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/SanthoshSiddegowda/bugzilla-mcp/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/SanthoshSiddegowda/bugzilla-mcp/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/SanthoshSiddegowda/bugzilla-mcp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/SanthoshSiddegowda/bugzilla-mcp/releases/tag/v0.1.0
