import pytest

from agent_setup_cases import AgentSetupCases


class TestSetupClaude(AgentSetupCases):
    agent = "claude"

    def test_should_replace_legacy_and_current_idea_at_user_scope(self, script, fake_bin, calls, tmp_path):
        fake_bin("fnm")
        fake_bin("claude")
        fake_bin("npx")
        result = script("setup-claude", prefix_root=tmp_path)
        assert result.returncode == 0, result.stderr
        assert calls("claude") == [
            ["mcp", "remove", "--scope", "user", "jetbrains"],
            ["mcp", "remove", "--scope", "user", "idea"],
            ["mcp", "add", "--scope", "user", "--transport", "http", "idea", "http://127.0.0.1:64342/stream"],
        ]

    @pytest.mark.parametrize("failed_command,expected", [("remove", 0), ("add", 3)])
    def test_should_tolerate_missing_registrations_but_surface_failed_adds(
            self, script, fake_bin, tmp_path, failed_command, expected):
        fake_bin("fnm")
        fake_bin("claude", script=f'[[ $2 == {failed_command} ]] && exit 3\nexit 0\n')
        fake_bin("npx")
        result = script("setup-claude", prefix_root=tmp_path)
        assert result.returncode == expected, result.stderr
