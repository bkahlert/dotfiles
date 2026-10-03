import pytest

MODULES = ["06-aliases.zsh"]


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


class TestAliases:
    class TestOnPip:
        def test_should_run_pip3_even_when_it_reaches_the_path_after_the_module_loaded(self, zsh, sandbox):
            late = sandbox.home / "late-bin"
            late.mkdir()
            (late / "pip3").write_text('#!/bin/sh\necho "pip3 $*"\n')
            (late / "pip3").chmod(0o755)
            # An alias is expanded when a line is parsed, so the call goes through eval.
            result = zsh(f'PATH={late}:$PATH\neval "pip install requests"', modules=MODULES)
            assert (result.stdout, result.stderr) == ("pip3 install requests\n", "")
