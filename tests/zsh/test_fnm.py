import pytest

MODULE = "10-fnm.zsh"
# What `fnm env` prints, as far as the module cares: shell code to evaluate.
FNM_ENV = 'export FNM_MULTISHELL_PATH="$HOME/multishell"'


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


class TestFnm:
    class TestOnInstalledFnm:
        def test_should_evaluate_its_env_for_zsh_with_the_switch_on_cd(self, zsh, fake_bin, calls, sandbox):
            fake_bin("fnm", stdout=FNM_ENV)
            result = zsh('print -r -- "$FNM_MULTISHELL_PATH"', modules=[MODULE])
            assert (result.stdout, result.stderr) == (f"{sandbox.home}/multishell\n", "")
            assert calls("fnm") == [["env", "--use-on-cd", "--shell", "zsh"]]

    class TestOnMissingFnm:
        def test_should_change_nothing_and_stay_silent(self, zsh):
            result = zsh('print -r -- "${FNM_MULTISHELL_PATH-unset}"', modules=[MODULE])
            assert (result.stdout, result.stderr, result.returncode) == ("unset\n", "", 0)
