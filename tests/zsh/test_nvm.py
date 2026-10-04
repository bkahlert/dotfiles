import pytest

MODULE = "10-nvm.zsh"
# What a real nvm.sh does when sourced: define nvm, leave a trace of each load.
NVM_SH = 'nvm() {{ echo real-nvm "$@"; }}\necho loaded >> {trace}\n'


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


@pytest.fixture
def installed(sandbox):
    """The nvm.sh where run_once_before_02-install-nvm puts it, with a trace of how often it was sourced."""
    nvm_dir = sandbox.home / ".nvm"
    nvm_dir.mkdir()
    trace = sandbox.home / "nvm.trace"
    (nvm_dir / "nvm.sh").write_text(NVM_SH.format(trace=trace))
    return trace


class TestNvm:
    def test_should_keep_nvm_dir_at_home(self, zsh, sandbox):
        result = zsh('print -r -- "$NVM_DIR"', modules=[MODULE])
        assert result.stdout == f"{sandbox.home}/.nvm\n"

    class TestOnInstalledNvm:
        def test_should_not_load_nvm_sh_at_shell_start(self, zsh, installed):
            zsh("true", modules=[MODULE])
            assert not installed.exists()

        def test_should_load_nvm_sh_on_the_first_nvm_call_and_run_the_real_nvm(self, zsh, installed):
            result = zsh("nvm ls", modules=[MODULE])
            assert (result.stdout, result.stderr, result.returncode) == ("real-nvm ls\n", "", 0)

        def test_should_load_nvm_sh_only_once(self, zsh, installed):
            result = zsh("nvm ls; nvm current", modules=[MODULE])
            assert (result.stdout, installed.read_text()) == ("real-nvm ls\nreal-nvm current\n", "loaded\n")

        @pytest.mark.parametrize("tool", ["node", "npm", "npx"])
        def test_should_leave_the_tools_of_the_default_node_to_the_path(self, zsh, installed, tool):
            result = zsh(f"print -r -- ${{+functions[{tool}]}}", modules=[MODULE])
            assert result.stdout == "0\n"

    class TestOnNoNvm:
        def test_should_define_no_nvm_and_stay_silent(self, zsh):
            result = zsh("print -r -- ${+functions[nvm]}", modules=[MODULE])
            assert (result.stdout, result.stderr) == ("0\n", "")
