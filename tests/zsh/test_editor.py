import shlex

import pytest

from repo import module_path


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


class TestEditor:
    class TestOnMacOS:
        def test_should_wait_for_intellij(self, zsh):
            result = editors_after(zsh, "OSTYPE=darwin24.0\nunset SSH_CONNECTION")
            assert result.stdout == "idea-wait idea-wait\n"

        class TestOverSsh:
            def test_should_use_nano(self, zsh):
                result = editors_after(zsh, "OSTYPE=darwin24.0\nexport SSH_CONNECTION='10.0.0.2 50000 10.0.0.1 22'")
                assert result.stdout == "nano nano\n"

    class TestOnLinux:
        def test_should_use_nano(self, zsh):
            result = editors_after(zsh, "OSTYPE=linux-gnu\nunset SSH_CONNECTION")
            assert result.stdout == "nano nano\n"


def editors_after(zsh, setup):
    """VISUAL and EDITOR after the module ran on a shell set up by the given lines."""
    return zsh(f"{setup}\nsource {shlex.quote(str(module_path('10-editor.zsh')))}\nprint -r -- \"$VISUAL $EDITOR\"")
