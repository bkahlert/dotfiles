import pytest

from agent_setup_cases import AgentSetupCases, skill_calls


class TestSetupCopilot(AgentSetupCases):
    agent = "copilot"

    @pytest.mark.parametrize("registered", [False, True])
    def test_should_replace_managed_mcps_and_install_superpowers_and_skills(
            self, script, fake_bin, calls, tmp_path, registered):
        inventory = '[{"name":"superpowers-marketplace"}]' if registered else "[]"
        fake_bin("copilot", script=f'[[ $2 == marketplace && $3 == list ]] && printf \'%s\\n\' \'{inventory}\'\nexit 0\n')
        fake_bin("fnm")
        fake_bin("npx")
        for _ in range(2):
            result = script("setup-copilot", prefix_root=tmp_path)
            assert result.returncode == 0, result.stderr
        expected = [
            ["mcp", "remove", "idea"],
            ["mcp", "add", "--transport", "http", "idea", "http://127.0.0.1:64342/stream"],
            ["mcp", "remove", "context7"],
            ["mcp", "add", "context7", "--", "npx", "--yes", "@upstash/context7-mcp@latest"],
            ["mcp", "remove", "chrome-devtools"],
            ["mcp", "add", "chrome-devtools", "--", "npx", "--yes", "chrome-devtools-mcp@latest",
             "--headless", "--isolated", "--no-usage-statistics"],
            ["plugin", "marketplace", "list", "--json"],
        ]
        if not registered:
            expected.append(["plugin", "marketplace", "add", "obra/superpowers-marketplace"])
        expected.append(["plugin", "install", "superpowers@superpowers-marketplace"])
        assert calls("copilot") == expected * 2
        assert calls("npx") == skill_calls("copilot") * 2

    @pytest.mark.parametrize("failure", ["idea", "context7", "chrome-devtools", "list", "add", "install"])
    def test_should_stop_and_surface_setup_failures(self, script, fake_bin, calls, tmp_path, failure):
        fake_bin("fnm")
        fake_bin("npx")
        fake_bin("copilot", script=(
            f'[[ ($1 == mcp && $2 == add && ($3 == {failure} || $5 == {failure})) || '
            f'($1 == plugin && ($2 == {failure} || $3 == {failure})) ]] && exit 3\n'
            '[[ $2 == marketplace && $3 == list ]] && printf "[]\\n"\nexit 0\n'))
        result = script("setup-copilot", prefix_root=tmp_path)
        assert result.returncode == 3, result.stderr
        assert calls("npx") == []

    def test_should_reject_invalid_marketplace_inventory(self, script, fake_bin, tmp_path):
        fake_bin("fnm")
        fake_bin("copilot", stdout="not JSON")
        result = script("setup-copilot", prefix_root=tmp_path)
        assert result.returncode != 0
        assert "parse error" in result.stderr

    def test_should_tolerate_missing_mcp_registrations(self, script, fake_bin, tmp_path):
        fake_bin("fnm")
        fake_bin("npx")
        fake_bin("copilot", script=(
            '[[ $1 == mcp && $2 == remove ]] && exit 1\n'
            '[[ $2 == marketplace && $3 == list ]] && printf "[]\\n"\nexit 0\n'))
        result = script("setup-copilot", prefix_root=tmp_path)
        assert result.returncode == 0, result.stderr
