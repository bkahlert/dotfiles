import pytest

MODULES = ["ista/10-idp.zsh"]
# What `idp completion zsh` prints: a wrapper function and its completion setup, to be sourced by the shell.
SCRIPT = "IDP_SCRIPT_SOURCED=1\nidp() { print wrapper \"$@\"; }\n"


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


class TestIdp:
    class TestOnNoIdp:
        def test_should_stay_silent_and_define_nothing(self, zsh, sandbox):
            (sandbox.fakes / "idp").unlink()
            result = zsh('print -r -- "${IDP_SCRIPT_SOURCED-unset} ${+functions[idp]}"', modules=MODULES)
            assert (result.returncode, result.stdout, result.stderr) == (0, "unset 0\n", "")

    class TestOnIdp:
        def test_should_ask_it_once_for_the_zsh_completion_script(self, zsh, fake_bin, calls):
            fake_bin("idp", stdout=SCRIPT)
            zsh("true", modules=MODULES)
            assert calls("idp") == [["completion", "zsh"]]

        def test_should_source_the_script_into_the_current_shell(self, zsh, fake_bin):
            fake_bin("idp", stdout=SCRIPT)
            result = zsh('print -r -- "$IDP_SCRIPT_SOURCED"\nidp use staging', modules=MODULES)
            assert (result.stdout, result.stderr) == ("1\nwrapper use staging\n", "")

        def test_should_let_the_shell_start_when_idp_fails(self, zsh, fake_bin):
            fake_bin("idp", stderr="idp: not logged in\n", exit_code=1)
            result = zsh("print still-running", modules=MODULES)
            assert (result.returncode, result.stdout) == (0, "still-running\n")
