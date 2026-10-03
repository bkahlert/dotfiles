import os
from pathlib import Path

import pytest

TOOLBOX_MAC = "Library/Application Support/JetBrains/Toolbox/scripts/idea"
TOOLBOX_LINUX = ".local/share/JetBrains/Toolbox/scripts/idea"
APP_BUNDLES = ("/Applications/IntelliJ IDEA.app/Contents/MacOS/idea",
               "/Applications/IntelliJ IDEA CE.app/Contents/MacOS/idea")


class TestIdea:
    class TestOnToolboxLauncher:
        def test_should_run_it_with_all_arguments_and_its_exit_code(self, run, sandbox):
            launcher(sandbox.home / TOOLBOX_LINUX, 'printf "linux:%s|" "$@"; exit 4')
            result = run("idea", "--wait", "a b.txt")
            assert (result.stdout, result.returncode) == ("linux:--wait|linux:a b.txt|", 4)

        def test_should_prefer_the_macos_location_over_the_linux_one(self, run, sandbox):
            launcher(sandbox.home / TOOLBOX_MAC, "echo mac")
            launcher(sandbox.home / TOOLBOX_LINUX, "echo linux")
            assert run("idea").stdout == "mac\n"

    @pytest.mark.skipif(any(os.access(path, os.X_OK) for path in APP_BUNDLES), reason="IntelliJ IDEA is installed here")
    class TestOnNoLauncher:
        def test_should_exit_127_and_explain_how_to_set_it_up(self, run):
            result = run("idea")
            assert (result.returncode, result.stdout) == (127, "")
            assert result.stderr.startswith("idea: command not found\n\nTo set up the IntelliJ IDEA CLI, choose one of:\n")
            assert "Tools → Create Command-line Launcher" in result.stderr


def launcher(path: Path, body: str):
    path.parent.mkdir(parents=True)
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(0o755)
