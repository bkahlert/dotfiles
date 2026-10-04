import json

import pytest

from repo import HOME_SOURCE

SCRIPT = HOME_SOURCE / "Library" / "private_Application Support" / "private_Claude" / "modify_private_claude_desktop_config.json"


class TestModifyClaudeDesktopConfigJson:
    class TestOnStdioServers:
        def test_should_copy_command_args_and_env(self, merge):
            result = merge(cli={"fs": {"command": "npx", "args": ["-y", "fs"], "env": {"ROOT": "/tmp"}}})
            assert result["mcpServers"]["fs"] == {"command": "npx", "args": ["-y", "fs"], "env": {"ROOT": "/tmp"}}

        def test_should_drop_fields_the_server_does_not_define(self, merge):
            result = merge(cli={"fs": {"type": "stdio", "command": "fs-server", "cwd": "/elsewhere"}})
            assert result["mcpServers"]["fs"] == {"command": "fs-server"}

    class TestOnRemoteServers:
        @pytest.mark.parametrize("kind", ("http", "sse"))
        def test_should_bridge_them_through_mcp_remote(self, merge, kind):
            result = merge(cli={"docs": {"type": kind, "url": "https://example.com/mcp", "headers": {"X": "1"}}})
            assert result["mcpServers"]["docs"] == {"command": "npx", "args": ["-y", "mcp-remote", "https://example.com/mcp"]}

        def test_should_add_allow_http_to_a_plain_http_url(self, merge):
            result = merge(cli={"local": {"type": "http", "url": "http://localhost:3000/mcp"}})
            assert result["mcpServers"]["local"]["args"] == ["-y", "mcp-remote", "http://localhost:3000/mcp", "--allow-http"]

    class TestOnTheDesktopConfig:
        def test_should_keep_servers_only_desktop_has_and_every_other_key(self, merge):
            current = {"mcpServers": {"desktop-only": {"command": "x"}}, "globalShortcut": "Ctrl+Space"}
            result = merge(cli={"fs": {"command": "fs-server"}}, current=current)
            assert result == {"mcpServers": {"desktop-only": {"command": "x"}, "fs": {"command": "fs-server"}},
                              "globalShortcut": "Ctrl+Space"}

        def test_should_let_the_claude_code_definition_win_on_a_name_clash(self, merge):
            current = {"mcpServers": {"fs": {"command": "old"}}}
            assert merge(cli={"fs": {"command": "new"}}, current=current)["mcpServers"]["fs"] == {"command": "new"}

        @pytest.mark.parametrize("current", ("", "\n"), ids=("empty", "newline"))
        def test_should_start_from_an_empty_object_when_there_is_none(self, modify, sandbox, current):
            write_cli_config(sandbox, {"fs": {"command": "fs-server"}})
            result = modify(SCRIPT, current)
            assert (result.returncode, json.loads(result.stdout)) == (0, {"mcpServers": {"fs": {"command": "fs-server"}}})

        def test_should_add_an_empty_server_list_when_claude_code_has_none(self, modify, sandbox):
            (sandbox.home / ".claude.json").write_text(json.dumps({"projects": {}}))
            result = modify(SCRIPT, json.dumps({"theme": "dark"}))
            assert json.loads(result.stdout) == {"theme": "dark", "mcpServers": {}}

    class TestOnNoClaudeCodeConfig:
        def test_should_hand_the_current_content_back_untouched(self, modify):
            current = '{"mcpServers":   {"a": {"command": "x"}}}'
            result = modify(SCRIPT, current)
            assert (result.returncode, result.stdout) == (0, current + "\n")

    class TestOnInvalidJson:
        def test_should_fail_and_print_no_content_for_chezmoi_to_write(self, modify, sandbox):
            write_cli_config(sandbox, {})
            result = modify(SCRIPT, "{ not json")
            assert result.returncode != 0
            assert result.stdout == ""


def write_cli_config(sandbox, servers):
    (sandbox.home / ".claude.json").write_text(json.dumps({"mcpServers": servers}))


@pytest.fixture
def merge(modify, sandbox):
    def run(*, cli, current=None):
        write_cli_config(sandbox, cli)
        result = modify(SCRIPT, json.dumps(current) if current is not None else "{}")
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    return run
