import shlex

import pytest

from repo import module_path

# What zsh-defer does with its arguments: queue them, to be run once zle is idle. With -c the list
# is eval'd as written; otherwise every word is quoted first, so a "$(...)" was already expanded.
ZSH_DEFER = """\
queue=()
zsh-defer() {
  if [[ $1 == -c ]]; then queue+=("$2"); else queue+=("${(j: :)${(q)@}}"); fi
}
"""
RUN_QUEUE = 'for entry in $queue; do eval "$entry"; done'
SHOW = 'print -r -- "${INITIALIZED:-no}"'
TOOLS = [("10-fzf.zsh", "fzf"), ("10-zoxide.zsh", "zoxide")]


def start(zsh, module, *, defer, then=""):
    """Source the module as .zshrc does, with or without zsh-defer loaded, and run `then` afterwards."""
    return zsh("\n".join([ZSH_DEFER if defer else "", f"source {shlex.quote(str(module_path(module)))}", then]))


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


@pytest.fixture(params=TOOLS, ids=[tool for _, tool in TOOLS])
def tool(request, fake_bin):
    module, name = request.param
    fake_bin(name, stdout="export INITIALIZED=1\n")
    return module, name


class TestDeferredToolInit:
    class TestOnZshDefer:
        def test_should_not_start_the_tool_while_the_shell_starts(self, zsh, tool, calls):
            module, name = tool
            start(zsh, module, defer=True)
            assert calls(name) == []

        def test_should_initialise_the_tool_once_the_deferred_command_runs(self, zsh, tool, calls):
            module, name = tool
            result = start(zsh, module, defer=True, then=f"{SHOW}\n{RUN_QUEUE}\n{SHOW}")
            assert (result.stdout, result.stderr) == ("no\n1\n", "")
            assert len(calls(name)) == 1

    class TestOnNoZshDefer:
        def test_should_initialise_the_tool_right_away(self, zsh, tool):
            module, _ = tool
            result = start(zsh, module, defer=False, then=SHOW)
            assert (result.stdout, result.stderr) == ("1\n", "")

    class TestOnNoTool:
        @pytest.mark.parametrize("defer", [True, False])
        def test_should_stay_silent_and_queue_nothing(self, zsh, tool, sandbox, defer):
            module, name = tool
            (sandbox.fakes / name).unlink()
            result = start(zsh, module, defer=defer, then='print -r -- "${#queue}"')
            assert (result.stdout, result.stderr) == ("0\n", "")
