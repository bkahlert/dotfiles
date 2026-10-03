import pytest

MODULE = "10-granted.zsh"
# `assume` is sourced, not run: it sets a variable in the calling shell.
ASSUME = 'ASSUMED=$1\n'


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh", "chmod")


def install_assume(sandbox):
    """A brew fake whose `install` puts a sourceable `assume` on the PATH."""
    sandbox.fake_bin("brew", script=f"printf 'ASSUMED=$1\\n' > {sandbox.fakes}/assume\nchmod +x {sandbox.fakes}/assume\n")


class TestGranted:
    def test_should_silence_the_alias_warning_of_granted(self, zsh):
        result = zsh('print -r -- "$GRANTED_ALIAS_CONFIGURED"', modules=[MODULE])
        assert result.stdout == "true\n"

    def test_should_source_assume_into_the_current_shell(self, zsh, fake_bin, calls):
        fake_bin("assume", script=ASSUME)
        result = zsh('assume org; print -r -- "$ASSUMED"', modules=[MODULE])
        assert (result.stdout, result.returncode) == ("org\n", 0)
        assert calls("brew") == []

    class TestOnMissingAssume:
        def test_should_install_granted_through_brew_and_then_source_assume(self, zsh, sandbox, calls):
            install_assume(sandbox)
            result = zsh('assume org; print -r -- "$ASSUMED"', modules=[MODULE])
            assert result.stdout.splitlines()[-1] == "org"
            assert "installing via Homebrew" in result.stdout + result.stderr
            assert calls("brew") == [["install", "common-fate/granted/granted"]]

        def test_should_return_1_when_brew_fails(self, zsh, fake_bin):
            fake_bin("brew", exit_code=1)
            result = zsh('assume org; echo "status $?"', modules=[MODULE])
            assert result.stdout.splitlines()[-1] == "status 1"
            assert "ASSUMED" not in result.stdout

        def test_should_return_1_and_say_so_without_brew(self, zsh, sandbox):
            (sandbox.fakes / "brew").unlink()
            result = zsh('assume org; echo "status $?"', modules=[MODULE])
            assert result.stdout.splitlines()[-1] == "status 1"
            assert "Homebrew is not available" in result.stdout + result.stderr
