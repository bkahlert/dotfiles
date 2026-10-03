import shlex
import subprocess

import pytest

from repo import HOME_SOURCE, module_path

MODULE = "89-scratch-workflow.zsh"
TARGET = ".config/zsh/conf.d/90-scratch.zsh"
ZSHRC = HOME_SOURCE / "private_dot_config/zsh/dot_zshrc"
DRAFT = "drafted() { print -r -- drafted; }"


@pytest.fixture
def zdotdir(sandbox):
    """A config directory with the real .zshrc, which sources conf.d/*.zsh, as chezmoi lays it out."""
    zdotdir = sandbox.home / ".config/zsh"
    (zdotdir / "conf.d").mkdir(parents=True)
    (zdotdir / ".zshrc").write_text(ZSHRC.read_text())
    sandbox.env["ZDOTDIR"] = str(zdotdir)
    return zdotdir


@pytest.fixture
def chezmoi_with_source(sandbox, fake_bin):
    """chezmoi fakes that manage the scratch module: source-path names a source file, apply copies it to the target."""
    source = sandbox.home / "source/90-scratch.zsh"
    source.parent.mkdir()
    source.write_text("# scratch\n")
    fake_bin("chezmoi", script=(
        f'case $1 in\n  source-path) echo {source} ;;\n'
        '  apply) mkdir -p "$(dirname "$2")"; cp ' + f'{source} "$2" ;;\nesac\n'))
    return source


def edit_with(sandbox, fake_bin, text):
    """An $EDITOR that appends text to the file it is given."""
    fake_bin("editor", script=f'printf "%s\\n" {shlex.quote(text)} >> "$1"\n')
    sandbox.env["EDITOR"] = "editor"


class TestEc:
    def test_should_open_the_source_in_the_editor_and_apply_the_target(self, zsh, fake_bin, calls, sandbox):
        fake_bin("chezmoi", script='[[ $1 == source-path ]] && echo /src/90-scratch.zsh\nexit 0\n')
        fake_bin("editor")
        sandbox.env["EDITOR"] = "editor"
        result = zsh("ec", modules=[MODULE])
        assert result.returncode == 0
        assert calls("editor") == [["/src/90-scratch.zsh"]]
        assert calls("chezmoi") == [["source-path", f"{sandbox.home}/{TARGET}"],
                                    ["apply", f"{sandbox.home}/{TARGET}"]]

    class TestOnUnmanagedTarget:
        def test_should_return_1_without_opening_the_editor(self, zsh, fake_bin, calls, sandbox):
            fake_bin("chezmoi", exit_code=1)
            fake_bin("editor")
            sandbox.env["EDITOR"] = "editor"
            result = zsh("ec", modules=[MODULE])
            assert result.returncode == 1
            assert calls("editor") == []


class TestSc:
    def test_should_reload_zshrc_at_top_level_so_its_typesets_stay_global(self, zsh, zdotdir):
        (zdotdir / ".zshrc").write_text("typeset -A table; table[a]=1\n")
        # zsh -c parses the whole script before sourcing the module; eval parses the alias use afterward.
        result = zsh("eval sc; print -r -- ${(k)table}", modules=[MODULE])
        assert result.stdout == "a\n"


class TestWorkflow:
    def test_should_make_a_draft_live_from_edit_to_reload(self, zsh, zdotdir, chezmoi_with_source, sandbox, fake_bin):
        edit_with(sandbox, fake_bin, DRAFT)
        result = zsh("ec; eval sc; drafted", modules=[MODULE])
        assert (result.stdout, result.stderr, result.returncode) == ("drafted\n", "", 0)
        assert (zdotdir / "conf.d/90-scratch.zsh").read_text().endswith(DRAFT + "\n")


class TestScratchModule:
    def test_should_parse(self):
        result = subprocess.run(["zsh", "-n", str(module_path("90-scratch.zsh"))], capture_output=True, text=True)
        assert (result.returncode, result.stderr) == (0, "")

    def test_should_print_nothing_when_loaded(self, zsh):
        result = zsh("true", modules=["90-scratch.zsh"])
        assert (result.stdout, result.stderr) == ("", "")
