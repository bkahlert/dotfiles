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

        def test_should_tolerate_a_server_that_was_never_registered(self, script, fake_bin):
            fake_bin("claude", script='[[ $2 == remove ]] && exit 1\nexit 0\n')
            result = script("setup-mcp-servers")
            assert result.returncode == 0, result.stderr

    class TestOnFailedRegistration:
        def test_should_fail(self, script, fake_bin):
            fake_bin("claude", script='[[ $2 == add ]] && exit 1\nexit 0\n')
            result = script("setup-mcp-servers")
            assert result.returncode == 1

    class TestOnClaudeOffPath:
        def test_should_use_the_one_install_claude_put_in_local_bin(self, script, sandbox):
            sandbox.only_tools()
            local_bin = sandbox.home / ".local" / "bin"
            local_bin.mkdir(parents=True)
            (local_bin / "claude").write_text('#!/bin/sh\necho "$*" >> "$HOME/claude-calls"\n')
            (local_bin / "claude").chmod(0o755)
            result = script("setup-mcp-servers")
            assert result.returncode == 0, result.stderr
            assert "mcp add --scope user --transport http idea http://127.0.0.1:64342/stream" in (
                sandbox.home / "claude-calls").read_text().splitlines()

    class TestOnMissingClaude:
        def test_should_fail_and_name_the_script_that_installs_it(self, script, sandbox):
            sandbox.only_tools()
            result = script("setup-mcp-servers")
            assert result.returncode == 1
            assert result.stderr == "claude not found; run_once_before_03-install-claude installs it\n"
