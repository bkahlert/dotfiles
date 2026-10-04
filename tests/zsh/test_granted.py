import pytest

MODULE = "10-granted.zsh"
# `assume` is sourced, not run: it sets a variable in the calling shell.
ASSUME = 'ASSUMED=$1\n'


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh", "chmod")


class TestGranted:
    def test_should_silence_the_alias_warning_of_granted(self, zsh):
        result = zsh('print -r -- "$GRANTED_ALIAS_CONFIGURED"', modules=[MODULE])
        assert result.stdout == "true\n"

    def test_should_source_assume_into_the_current_shell(self, zsh, fake_bin, calls):
        fake_bin("assume", script=ASSUME)
        result = zsh('assume org; print -r -- "$ASSUMED"', modules=[MODULE])
        assert (result.stdout, result.returncode) == ("org\n", 0)
        assert calls("brew") == []

    def test_should_fail_without_installing_anything_when_granted_is_missing(self, zsh, calls):
        result = zsh('assume org || echo failed', modules=[MODULE])
        assert (result.stdout, calls("brew")) == ("failed\n", [])
