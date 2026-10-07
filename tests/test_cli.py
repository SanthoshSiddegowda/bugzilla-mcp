"""Tests for the `bugzilla-mcp` command and the packaging metadata it relies on"""

import json
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp import Client

import bugzilla_mcp.utils as utils
from bugzilla_mcp.cli import build_http_server, build_local_server, main
from bugzilla_mcp.tools.bugzilla import LOCAL_ONLY_TOOLS, WRITE_TOOL_NAMES

ROOT = Path(__file__).resolve().parent.parent
LOCAL_ONLY = {fn.__name__ for fn in LOCAL_ONLY_TOOLS}


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    """No real .env, no leftover client between tests"""
    monkeypatch.setattr("bugzilla_mcp.cli.load_dotenv", lambda: None)
    for var in ("BUGZILLA_URL", "BUGZILLA_API_KEY", "BUGZILLA_READ_ONLY", "BUGZILLA_DISABLED_TOOLS"):
        monkeypatch.delenv(var, raising=False)
    token = utils.current_bz.set(None)
    yield
    utils.current_bz.reset(token)


async def _names(mcp) -> set[str]:
    async with Client(mcp) as c:
        return {t.name for t in await c.list_tools()}


class TestMain:
    def test_version(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(["--version"])
        assert exc.value.code == 0
        assert capsys.readouterr().out.startswith("bugzilla-mcp ")

    def test_stdio_requires_credentials(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main([])
        assert exc.value.code == 2
        assert "BUGZILLA_URL and BUGZILLA_API_KEY" in capsys.readouterr().err

    def test_stdio_runs_local_server(self, monkeypatch):
        monkeypatch.setenv("BUGZILLA_URL", "https://bugzilla.example.com/")
        monkeypatch.setenv("BUGZILLA_API_KEY", "secret")
        with patch("fastmcp.FastMCP.run") as run:
            main([])
        run.assert_called_once_with(transport="stdio", show_banner=False)
        bz = utils.current_bz.get()
        assert bz.base_url == "https://bugzilla.example.com"
        assert bz.allow_local_files is True

    def test_api_key_is_not_a_flag(self):
        """Keys on the command line leak into `ps` and shell history"""
        with pytest.raises(SystemExit):
            main(["--api-key", "secret"])

    def test_http_runs_header_server(self):
        with patch("fastmcp.FastMCP.run") as run:
            main(["--transport", "http", "--host", "0.0.0.0", "--port", "9000"])
        run.assert_called_once_with(transport="http", host="0.0.0.0", port=9000)
        assert utils.current_bz.get() is None  # credentials come per request

    @pytest.mark.parametrize("argv,env,writes", [
        ([], {}, False),
        (["--allow-writes"], {}, True),
        ([], {"BUGZILLA_READ_ONLY": "false"}, True),
        (["--allow-writes"], {"BUGZILLA_READ_ONLY": "true"}, True),
    ])
    async def test_read_only_resolution(self, monkeypatch, argv, env, writes):
        monkeypatch.setenv("BUGZILLA_URL", "https://bugzilla.example.com")
        monkeypatch.setenv("BUGZILLA_API_KEY", "secret")
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        built = []

        def capture(*args, **kwargs):
            built.append(build_local_server(*args, **kwargs))
            return built[-1]

        with patch("bugzilla_mcp.cli.build_local_server", side_effect=capture), patch("fastmcp.FastMCP.run"):
            main(argv)
        assert ("update_bug" in await _names(built[0])) is writes


class TestServers:
    async def test_local_server_read_only_by_default(self):
        names = await _names(build_local_server("https://bugzilla.example.com", "k"))
        assert not names & WRITE_TOOL_NAMES

    async def test_local_server_offers_local_only_tools_with_writes(self):
        names = await _names(build_local_server("https://bugzilla.example.com", "k", read_only=False))
        assert LOCAL_ONLY <= names

    async def test_http_server_never_offers_local_only_tools(self):
        with patch("bugzilla_mcp.middleware.read_only.get_http_headers", return_value={}):
            names = await _names(build_http_server(read_only=False))
        assert not names & LOCAL_ONLY
        assert "update_bug" in names


class TestPackagingMetadata:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    manifest = json.loads((ROOT / "manifest.json").read_text())

    def test_versions_match(self):
        assert self.manifest["version"] == self.pyproject["project"]["version"]

    def test_console_script(self):
        assert self.pyproject["project"]["scripts"]["bugzilla-mcp"] == "bugzilla_mcp.cli:main"

    def test_extension_runs_the_console_script(self):
        config = self.manifest["server"]["mcp_config"]
        assert config["command"] == "uv"
        assert config["args"][-1] in self.pyproject["project"]["scripts"]
        assert (ROOT / self.manifest["server"]["entry_point"]).is_file()

    def test_extension_form_feeds_the_cli_env(self):
        env = self.manifest["server"]["mcp_config"]["env"]
        user_config = self.manifest["user_config"]
        assert env == {
            "BUGZILLA_URL": "${user_config.bugzilla_url}",
            "BUGZILLA_API_KEY": "${user_config.api_key}",
            "BUGZILLA_READ_ONLY": "${user_config.read_only}",
        }
        assert user_config["api_key"]["sensitive"] is True
        assert user_config["read_only"]["default"] is True

    def test_icon_exists(self):
        assert (ROOT / self.manifest["icon"]).is_file()
