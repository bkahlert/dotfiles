import pytest

MODULE = "10-nvm.zsh"
STUBS = "nvm node npm npx"
LIST_STUBS = f"for f in {STUBS}; do (( $+functions[$f] )) && echo $f; done; true"
# What a real nvm.sh does: define nvm, put node/npm/npx on the PATH, leave a trace of each load.
NVM_SH = """\\
nvm() {{ echo real-nvm "$@"; }}
export PATH={bin}:$PATH
echo loaded >> {trace}
"""


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh", "mkdir")


@pytest.fixture
def installed(sandbox):
    """The nvm.sh at the official location, with a trace of how often it was sourced."""
    nvm_dir = sandbox.home / ".nvm"
    bin_dir = sandbox.home / "node-bin"
    nvm_dir.mkdir()
    bin_dir.mkdir()
    for tool in ("node", "npm", "npx"):
        (bin_dir / tool).write_text(f"#!/bin/sh\necho real-{tool} \"$@\"\n")
        (bin_dir / tool).chmod(0o755)
    trace = sandbox.home / "nvm.trace"
    (nvm_dir / "nvm.sh").write_text(NVM_SH.format(bin=bin_dir, trace=trace))
    return trace


def stubs(zsh):
    return zsh(LIST_STUBS, modules=[MODULE]).stdout.split()


class TestNvm:
    class TestOnNoNvm:
        def test_should_leave_node_and_npm_alone_without_forking_brew(self, zsh, calls):
            result = zsh(LIST_STUBS, modules=[MODULE])
            assert (result.stdout, result.stderr, calls("brew")) == ("", "", [])

        def test_should_leave_them_alone_when_homebrew_has_no_nvm_either(self, zsh, sandbox):
            sandbox.env["HOMEBREW_PREFIX"] = str(sandbox.home / "prefix")
            assert stubs(zsh) == []

    class TestOnOfficialInstall:
        def test_should_stub_nvm_node_npm_and_npx(self, zsh, installed):
            assert stubs(zsh) == STUBS.split()

        def test_should_keep_nvm_dir_at_home(self, zsh, installed, sandbox):
            result = zsh('print -r -- "$NVM_DIR"', modules=[MODULE])
            assert result.stdout == f"{sandbox.home}/.nvm\n"

        def test_should_not_ask_brew_for_a_prefix(self, zsh, installed, calls):
            stubs(zsh)
            assert calls("brew") == []

        def test_should_load_nvm_on_the_first_call_and_dispatch_to_the_real_one(self, zsh, installed):
            result = zsh("nvm ls", modules=[MODULE])
            assert (result.stdout, result.returncode) == ("real-nvm ls\n", 0)

        @pytest.mark.parametrize("tool", ["node", "npm", "npx"])
        def test_should_dispatch_a_stubbed_tool_to_the_binary_nvm_puts_on_the_path(self, zsh, installed, tool):
            result = zsh(f"{tool} -v", modules=[MODULE])
            assert (result.stdout, result.returncode) == (f"real-{tool} -v\n", 0)

        def test_should_load_nvm_only_once_and_drop_every_stub(self, zsh, installed):
            result = zsh(f"npm -v; node -v; nvm ls; {LIST_STUBS}", modules=[MODULE])
            assert result.stdout.splitlines() == ["real-npm -v", "real-node -v", "real-nvm ls", "nvm"]
            assert installed.read_text() == "loaded\n"

    class TestOnHomebrewInstall:
        @pytest.fixture
        def prefix(self, sandbox):
            opt = sandbox.home / "prefix" / "opt" / "nvm"
            opt.mkdir(parents=True)
            (opt / "nvm.sh").write_text('nvm() { echo brew-nvm "$@"; }\n')
            sandbox.env["HOMEBREW_PREFIX"] = str(sandbox.home / "prefix")

        def test_should_stub_the_tools_and_load_the_brew_nvm_sh(self, zsh, prefix):
            result = zsh(f"{LIST_STUBS}; nvm ls", modules=[MODULE])
            assert result.stdout.splitlines() == [*STUBS.split(), "brew-nvm ls"]

        def test_should_not_fork_brew_for_the_prefix(self, zsh, prefix, calls):
            zsh("true", modules=[MODULE])
            assert calls("brew") == []

        def test_should_create_nvm_dir_at_home_not_in_the_cellar(self, zsh, prefix, sandbox):
            zsh("true", modules=[MODULE])
            assert (sandbox.home / ".nvm").is_dir()

        def test_should_find_the_brew_nvm_sh_under_the_prefix_brew_sits_in_on_unset_homebrew_prefix(self, zsh, uninherited_brew):
            opt = uninherited_brew / "opt" / "nvm"
            opt.mkdir(parents=True)
            (opt / "nvm.sh").write_text('nvm() { echo brew-nvm "$@"; }\n')
            result = zsh("nvm ls", modules=[MODULE])
            assert (result.stdout, result.stderr) == ("brew-nvm ls\n", "")
