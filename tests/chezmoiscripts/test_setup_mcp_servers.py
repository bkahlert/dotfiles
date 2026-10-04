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

    class TestOnMissingClaude:
        def test_should_skip_with_a_one_line_notice_and_exit_0(self, script, sandbox):
            sandbox.only_tools()
            result = script("setup-mcp-servers")
            assert result.returncode == 0, result.stderr
            assert result.stderr == "claude not available; skipping MCP server setup\n"
            assert result.stdout == ""

    class TestOnChangeDetection:
        def test_should_rerun_once_claude_appears(self, rendered, sandbox, fake_bin):
            sandbox.only_tools()
            without_claude = rendered("setup-mcp-servers")
            fake_bin("claude")
            with_claude = rendered("setup-mcp-servers")
            assert with_claude != without_claude

        def test_should_render_the_same_script_while_claude_stays_as_it_is(self, rendered, sandbox):
            sandbox.only_tools()
            assert rendered("setup-mcp-servers") == rendered("setup-mcp-servers")

        def test_should_render_a_script_that_starts_with_the_shebang(self, rendered):
            assert rendered("setup-mcp-servers").startswith("#!/usr/bin/env bash\n")
