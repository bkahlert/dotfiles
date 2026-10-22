import pytest

from agent_setup_cases import AgentSetupCases, skill_calls


class TestSetupCodex(AgentSetupCases):
    agent = "codex"

    @pytest.mark.parametrize("registered", [False, True])
    def test_should_install_superpowers_and_skills(
            self, script, fake_bin, calls, tmp_path, registered):
        inventory = '{"marketplaces":[{"name":"superpowers-dev"}]}' if registered else '{"marketplaces":[]}'
        fake_bin("codex", script=f'[[ $2 == marketplace && $3 == list ]] && printf \'%s\\n\' \'{inventory}\'\nexit 0\n')
        fake_bin("fnm")
        fake_bin("npx")
        for _ in range(2):
            result = script("setup-codex", prefix_root=tmp_path)
            assert result.returncode == 0, result.stderr
        expected = [
            ["plugin", "marketplace", "list", "--json"],
        ]
        if not registered:
            expected.append(["plugin", "marketplace", "add", "obra/superpowers"])
        expected.append(["plugin", "add", "superpowers@superpowers-dev"])
        assert calls("codex") == expected * 2
        assert calls("npx") == skill_calls("codex") * 2

    @pytest.mark.parametrize("failure", ["list", "marketplace-add", "plugin-add"])
    def test_should_stop_and_surface_setup_failures(self, script, fake_bin, calls, tmp_path, failure):
        fake_bin("fnm")
        fake_bin("npx")
        fake_bin("codex", script=(
            f'[[ $3 == {failure} || "$2-$3" == {failure} || "$1-$2" == {failure} ]] && exit 3\n'
            '[[ $2 == marketplace && $3 == list ]] && printf \'%s\\n\' \'{"marketplaces":[]}\'\nexit 0\n'))
        result = script("setup-codex", prefix_root=tmp_path)
        assert result.returncode == 3, result.stderr
        assert calls("npx") == []

    @pytest.mark.parametrize("inventory", ["not JSON", "[]", "{}"])
    def test_should_reject_invalid_marketplace_inventory(self, script, fake_bin, calls, tmp_path, inventory):
        fake_bin("fnm")
        fake_bin("codex", stdout=inventory)
        result = script("setup-codex", prefix_root=tmp_path)
        assert result.returncode != 0
        assert calls("npx") == []
