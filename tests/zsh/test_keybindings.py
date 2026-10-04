import shlex
import shutil
import subprocess

import pytest

from repo import module_path

MODULE = shlex.quote(str(module_path("04-keybindings.zsh")))
# Bound whatever the terminal: xterm, application keypad mode and the linux console.
FIXED = {
    "^[[A": "history-substring-search-up",
    "^[[B": "history-substring-search-down",
    "^[[H": "beginning-of-line",
    "^[[F": "end-of-line",
    "^[OH": "beginning-of-line",
    "^[OF": "end-of-line",
    "^[[1~": "beginning-of-line",
    "^[[4~": "end-of-line",
}
# What a terminal that reports its own key sequences gets bound to: its up, down, home and end keys.
TERMINFO_SOURCE = """\
testterm|test terminal,
\tcols#80, lines#24,
\tkcuu1=\\E[1;9A, kcud1=\\E[1;9B, khome=\\E[9~, kend=\\E[10~,
"""
CUSTOM = {
    "^[[1;9A": "history-substring-search-up",
    "^[[1;9B": "history-substring-search-down",
    "^[[9~": "beginning-of-line",
    "^[[10~": "end-of-line",
}


@pytest.fixture(autouse=True)
def bare(sandbox):
    sandbox.only_tools("zsh")


@pytest.fixture
def testterm(sandbox):
    """A terminal whose up, down, home and end sequences differ from the hard-coded ones."""
    if not shutil.which("tic"):
        pytest.skip("tic is not installed")
    source = sandbox.home / "testterm.src"
    source.write_text(TERMINFO_SOURCE)
    subprocess.run(["tic", "-x", "-o", sandbox.home / "terminfo", source], check=True, capture_output=True)
    sandbox.env.update(TERMINFO=str(sandbox.home / "terminfo"), TERM="testterm")


def bindings(zsh, before=""):
    """The main keymap after the module ran, as {key sequence: widget}, plus anything written to stderr."""
    result = zsh(f"{before}\nsource {MODULE}\nbindkey")
    pairs = (line.rsplit(" ", 1) for line in result.stdout.splitlines())
    return {key.strip('"'): widget for key, widget in pairs}, result.stderr


class TestKeybindings:
    def test_should_switch_the_main_keymap_to_emacs_even_after_vi_was_chosen(self, zsh):
        result = zsh(f"bindkey -v\nsource {MODULE}\nbindkey -lL main")
        assert result.stdout == "bindkey -A emacs main\n"

    @pytest.mark.parametrize("key, widget", FIXED.items())
    def test_should_bind_the_common_sequences_whatever_the_terminal(self, zsh, key, widget):
        keymap, stderr = bindings(zsh)
        assert (keymap[key], stderr) == (widget, "")

    class TestOnTerminalWithKeyCapabilities:
        @pytest.mark.parametrize("key, widget", CUSTOM.items())
        def test_should_bind_the_sequences_the_terminal_reports(self, zsh, testterm, key, widget):
            keymap, stderr = bindings(zsh)
            assert (keymap[key], stderr) == (widget, "")

    class TestOnTerminalWithoutKeyCapabilities:
        def test_should_stay_silent_and_keep_the_common_sequences(self, zsh, sandbox):
            sandbox.env["TERM"] = "dumb"
            keymap, stderr = bindings(zsh)
            assert stderr == ""
            assert {key: keymap.get(key) for key in FIXED} == FIXED
