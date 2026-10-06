from itertools import combinations

import pytest


class TestAgents:
    class TestOnAvailableClis:
        @pytest.mark.parametrize("installed", [
            clis for count in range(4) for clis in combinations(("claude", "copilot", "gemini"), count)
        ])
        def test_should_define_only_aliases_for_installed_tools_without_running_them(
                self, zsh, fake_bin, calls, installed):
            for cli in installed:
                fake_bin(cli)
            result = zsh(
                'for cli in claude copilot gemini; do\n'
                '  if (( ${+aliases[${cli}d]} )); then print -r -- "$cli"; fi\n'
                'done',
                modules=["20-agents.zsh"])
            assert result.returncode == 0, result.stderr
            assert result.stdout.splitlines() == list(installed)
            assert result.stderr == ""
            assert all(calls(cli) == [] for cli in ("claude", "copilot", "gemini"))

    class TestOnDangerousAlias:
        @pytest.mark.parametrize("cli,flag", [
            ("claude", "--dangerously-skip-permissions"),
            ("copilot", "--yolo"),
            ("gemini", "--yolo"),
        ])
        def test_should_pass_the_permission_flag_and_preserve_arguments(self, zsh, fake_bin, calls, cli, flag):
            fake_bin(cli)
            result = zsh(f'eval \'{cli}d --resume "a session"\'', modules=["20-agents.zsh"])
            assert result.returncode == 0, result.stderr
            assert calls(cli) == [[flag, "--resume", "a session"]]
            assert result.stdout == result.stderr == ""


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")
