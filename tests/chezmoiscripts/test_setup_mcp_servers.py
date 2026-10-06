import pytest


@pytest.fixture
def script(script, tmp_path):
    def run(key, **kwargs):
        kwargs.setdefault("prefix_root", tmp_path)
        return script(key, **kwargs)
    return run


class TestSetupMcpServers:
    class TestOnClaude:
        def test_should_register_the_idea_server_over_http_at_user_scope(self, script, fake_bin, calls):
            fake_bin("claude")
            result = script("setup-mcp-servers")
            assert result.returncode == 0, result.stderr
            assert ["mcp", "add", "--scope", "user", "--transport", "http", "idea", "http://127.0.0.1:64342/stream"] in calls("claude")

        def test_should_replace_the_legacy_jetbrains_key_and_any_earlier_idea_entry(self, script, fake_bin, calls):
            fake_bin("claude")
            script("setup-mcp-servers")
            removed = [call[-1] for call in calls("claude") if call[:2] == ["mcp", "remove"]]
            assert removed.index("jetbrains") < removed.index("idea")
            assert removed.index("idea") < next(i for i, call in enumerate(calls("claude")) if call[:2] == ["mcp", "add"])

        def test_should_leave_the_retired_servers_alone(self, script, fake_bin, calls):
            fake_bin("claude")
            script("setup-mcp-servers")
            removed = [call[-1] for call in calls("claude") if call[:2] == ["mcp", "remove"]]
            assert not {"context7", "serena", "gcloud-observability"} & set(removed)

        def test_should_tolerate_a_server_that_was_never_registered(self, script, fake_bin):
            fake_bin("claude", script='[[ $2 == remove ]] && exit 1\nexit 0\n')
            result = script("setup-mcp-servers")
            assert result.returncode == 0, result.stderr

    class TestOnFailedRegistration:
        def test_should_fail(self, script, fake_bin):
            fake_bin("claude", script='[[ $2 == add ]] && exit 1\nexit 0\n')
            result = script("setup-mcp-servers")
            assert result.returncode == 1

    class TestOnCopilot:
        def test_should_register_idea_without_requiring_claude(self, script, fake_bin, calls):
            fake_bin("copilot")
            result = script("setup-mcp-servers")
            assert result.returncode == 0, result.stderr
            assert calls("copilot") == [
                ["mcp", "remove", "idea"],
                ["mcp", "add", "--transport", "http", "idea", "http://127.0.0.1:64342/stream"],
            ]
            assert calls("claude") == []

        def test_should_register_idea_for_both_available_clis(self, script, fake_bin, calls):
            fake_bin("claude")
            fake_bin("copilot")
            result = script("setup-mcp-servers")
            assert result.returncode == 0, result.stderr
            assert calls("claude")[-1] == [
                "mcp", "add", "--scope", "user", "--transport", "http", "idea",
                "http://127.0.0.1:64342/stream",
            ]
            assert calls("copilot")[-1] == [
                "mcp", "add", "--transport", "http", "idea", "http://127.0.0.1:64342/stream",
            ]

        def test_should_tolerate_a_server_that_was_never_registered(self, script, fake_bin):
            fake_bin("copilot", script='[[ $2 == remove ]] && exit 1\nexit 0\n')
            result = script("setup-mcp-servers")
            assert result.returncode == 0, result.stderr

        def test_should_fail_when_registration_fails(self, script, fake_bin):
            fake_bin("copilot", script='[[ $2 == add ]] && exit 1\nexit 0\n')
            result = script("setup-mcp-servers")
            assert result.returncode == 1

        def test_should_replace_only_idea_on_repeated_runs(self, script, fake_bin, calls):
            fake_bin("copilot")
            for _ in range(2):
                result = script("setup-mcp-servers")
                assert result.returncode == 0, result.stderr
            assert calls("copilot") == [
                ["mcp", "remove", "idea"],
                ["mcp", "add", "--transport", "http", "idea", "http://127.0.0.1:64342/stream"],
            ] * 2

    class TestOnCliOffPath:
        @pytest.mark.parametrize("cli", ["claude", "copilot"])
        @pytest.mark.parametrize("prefix", ["/opt/homebrew", "/usr/local", ".local"])
        def test_should_use_each_cli_in_an_install_location(self, script, sandbox, tmp_path, prefix, cli):
            sandbox.only_tools()
            local_bin = (sandbox.home / prefix if prefix == ".local" else tmp_path / prefix.lstrip("/")) / "bin"
            local_bin.mkdir(parents=True)
            (local_bin / cli).write_text(f'#!/bin/sh\necho "$*" >> "$HOME/{cli}-calls"\n')
            (local_bin / cli).chmod(0o755)
            result = script("setup-mcp-servers", prefix_root=tmp_path)
            assert result.returncode == 0, result.stderr
            scope = "--scope user " if cli == "claude" else ""
            assert f"mcp add {scope}--transport http idea http://127.0.0.1:64342/stream" in (
                sandbox.home / f"{cli}-calls").read_text().splitlines()

    class TestOnMissingClaude:
        @pytest.mark.parametrize("os", ["Darwin", "Linux"])
        def test_should_skip_setup_when_neither_cli_is_installed(self, script, sandbox, tmp_path, calls, os):
            sandbox.only_tools()
            result = script("setup-mcp-servers", prefix_root=tmp_path, uname=os)
            assert result.returncode == 0
            assert result.stdout == result.stderr == ""
            assert calls("claude") == []
            assert calls("copilot") == []
