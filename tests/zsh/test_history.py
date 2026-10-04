import os
import pty
import re
import select
import shlex
import signal
import time

import pytest

from repo import module_path

MODULE = shlex.quote(str(module_path("02-history.zsh")))
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")


class Shell:
    """An interactive zsh on a pty, driven the way a person drives it: type a line, wait for what it prints."""

    def __init__(self, env, timeout=10):
        self.timeout = timeout
        self.marks = 0
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.execvpe("zsh", ["zsh", "-f", "-i", "+Z"], env)
        self.run("PS1='' PROMPT_EOL_MARK=''")
        self.run(f"source {MODULE}")

    def run(self, line):
        """Type the line, return everything printed until it finished. The marker is split in the typed text so only its output matches."""
        self.marks += 1
        marker = f"MARKER{self.marks}"
        os.write(self.fd, f"{line}\nprint -r -- {marker[:3]}''{marker[3:]}\n".encode())
        seen = ""
        deadline = time.time() + self.timeout
        while f"{marker}\n" not in seen:
            if time.time() > deadline:
                raise TimeoutError(f"no output of {line!r} within {self.timeout}s; saw {seen!r}")
            if select.select([self.fd], [], [], 0.05)[0]:
                try:
                    seen += ANSI.sub("", os.read(self.fd, 65536).decode(errors="replace")).replace("\r", "")
                except OSError:
                    break
        return seen

    def close(self):
        os.kill(self.pid, signal.SIGKILL)
        os.waitpid(self.pid, 0)
        os.close(self.fd)


@pytest.fixture
def shells(sandbox):
    sandbox.only_tools("zsh", "mkdir")
    env = {**sandbox.env, "TERM": "xterm-256color"}
    opened = []

    def start():
        opened.append(Shell(env))
        return opened[-1]
    yield start
    for shell in opened:
        shell.close()


class TestHistory:
    def test_should_keep_the_history_file_under_the_xdg_state_directory(self, zsh, sandbox):
        result = zsh('print -r -- "$HISTFILE"\n[[ -d ${HISTFILE:h} ]] && print created', modules=["02-history.zsh"])
        assert (result.stdout, result.stderr) == (f"{sandbox.home}/.local/state/zsh/history\ncreated\n", "")

    def test_should_remember_more_than_it_keeps_in_the_file_never_less(self, zsh):
        result = zsh('print -r -- "$HISTSIZE $SAVEHIST"', modules=["02-history.zsh"])
        histsize, savehist = map(int, result.stdout.split())
        assert savehist >= 10000 and histsize >= savehist

    def test_should_show_a_command_to_another_shell_that_is_already_running(self, shells):
        first, second = shells(), shells()
        first.run("echo typed-in-the-first-shell")
        assert "echo typed-in-the-first-shell" in second.run("fc -l 1")

    def test_should_keep_only_the_latest_of_repeated_commands(self, shells):
        shell = shells()
        for line in ("echo same", "echo other", "echo same"):
            shell.run(line)
        assert shell.run("fc -l 1").count("echo same") == 1

    def test_should_store_a_command_without_its_superfluous_blanks(self, shells):
        shell = shells()
        shell.run("echo   spaced     out")
        listing = shell.run("fc -l 1")
        assert "echo spaced out" in listing and "echo   spaced" not in listing
