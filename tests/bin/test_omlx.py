import os
import pty
import subprocess
from pathlib import Path

import pytest

ABSOLUTE = ("/opt/homebrew/bin/omlx", "/usr/local/bin/omlx", "/Applications/oMLX.app/Contents/MacOS/omlx-cli")
installed_here = pytest.mark.skipif(any(os.access(path, os.X_OK) for path in ABSOLUTE), reason="oMLX is installed here")
INSTALL_BREW = 'mkdir -p "$HOME/.omlx/bin"\nprintf \'#!/bin/sh\\necho installed\\n\' >"$HOME/.omlx/bin/omlx"\nchmod +x "$HOME/.omlx/bin/omlx"\n'


class TestOmlx:
    class TestOnInstalled:
        def test_should_run_the_app_managed_shim_with_all_arguments(self, run, sandbox):
            shim = sandbox.home / ".omlx/bin/omlx"
            shim.parent.mkdir(parents=True)
            shim.write_text('#!/bin/sh\nprintf "%s|" "$@"; exit 5\n')
            shim.chmod(0o755)
            result = run("omlx", "serve", "--port", "8000")
            assert (result.stdout, result.returncode) == ("serve|--port|8000|", 5)

    @installed_here
    class TestOnNotInstalled:
        def test_should_exit_127_with_install_hints_and_never_call_brew_without_a_terminal(self, run, fake_bin, calls):
            fake_bin("brew")
            result = run("omlx", "serve")
            assert (result.returncode, result.stdout) == (127, "")
            assert result.stderr.startswith("omlx: oMLX not installed\n\nTo install oMLX, choose one of:\n")
            assert "brew tap jundot/omlx https://github.com/jundot/omlx && brew install jundot/omlx/omlx" in result.stderr
            assert "https://github.com/jundot/omlx/releases" in result.stderr
            assert calls("brew") == []

        def test_should_decline_the_homebrew_offer_on_n(self, sandbox, fake_bin, calls):
            fake_bin("brew")
            returncode, output = on_terminal(sandbox, "n\n")
            assert returncode == 127
            assert "Install oMLX via Homebrew (jundot/omlx)? [y/N]" in output
            assert "To install oMLX, choose one of:" in output
            assert calls("brew") == []

        def test_should_install_then_run_on_y(self, sandbox, fake_bin, calls):
            fake_bin("brew", script=INSTALL_BREW)
            returncode, output = on_terminal(sandbox, "y\n")
            assert returncode == 0
            assert output.rstrip().endswith("installed")
            assert calls("brew") == [["tap", "jundot/omlx", "https://github.com/jundot/omlx"],
                                     ["install", "jundot/omlx/omlx"]]

        def test_should_exit_127_when_the_install_leaves_no_binary(self, sandbox, fake_bin):
            fake_bin("brew")
            returncode, output = on_terminal(sandbox, "y\n")
            assert returncode == 127
            assert "omlx: install finished but no omlx binary found" in output


def on_terminal(sandbox, answer: str) -> tuple[int, str]:
    master, slave = pty.openpty()
    try:
        process = subprocess.Popen(["omlx"], env=sandbox.env, cwd=sandbox.home, stdin=slave,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        os.write(master, answer.encode())
        output, _ = process.communicate(timeout=10)
    finally:
        os.close(master)
        os.close(slave)
    return process.returncode, output
