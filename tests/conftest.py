import shlex
import subprocess
from pathlib import Path

import pytest

from repo import BIN_SOURCE, FUNCTIONS_SOURCE, SYSTEM_PATH, isolated_env, module_path

# Tools that reach the network, a vault, system state or the user's own state (repositories,
# processes, the clipboard, container machines). A guard stands in for each so a subject under test
# can never call the real one; a test that needs one installs a fake with fake_bin. `docker` is a
# script under test here, so its podman fallback is what gets guarded.
GUARDED = ("op", "keepassxc-cli", "gh", "glab", "gcloud", "idp", "curl", "wget", "ssh", "scp",
           "brew", "open", "osascript", "launchctl", "defaults", "sudo",
           "git", "chezmoi", "podman", "npm", "npx", "mas", "softwareupdate", "security",
           "dscacheutil", "pbcopy", "pbpaste", "lsof", "killall", "pkill")
# NUL cannot occur inside an argument, so it ends one; a record separator ends the call.
ARG_SEPARATOR = "\0"
RECORD_SEPARATOR = "\x1e"


@pytest.fixture(scope="session")
def bin_links(tmp_path_factory):
    links = tmp_path_factory.mktemp("bin")
    for source in BIN_SOURCE.iterdir():
        if source.name.startswith("executable_"):
            (links / source.name.removeprefix("executable_")).symlink_to(source)
    return links


@pytest.fixture
def sandbox(tmp_path, bin_links):
    return Sandbox(tmp_path / "home", tmp_path / "fakes", bin_links)


@pytest.fixture
def run(sandbox):
    return sandbox.run


@pytest.fixture
def fake_bin(sandbox):
    return sandbox.fake_bin


@pytest.fixture
def calls(sandbox):
    return sandbox.calls


@pytest.fixture
def zsh(sandbox):
    return sandbox.zsh


class Sandbox:
    def __init__(self, home: Path, fakes: Path, bin_links: Path):
        self.home = home
        self.fakes = fakes
        self.calls_dir = fakes / ".calls"
        self.calls_dir.mkdir(parents=True)
        self.env = isolated_env(home, [str(fakes), str(bin_links), *SYSTEM_PATH])
        for name in GUARDED:
            self._write(name, "printf '%s: not faked in this test\\n' \"${0##*/}\" >&2\nexit 127\n",
                        record=False)

    def run(self, name, *args, stdin=None, timeout=10):
        return subprocess.run([name, *args], env=self.env, cwd=self.home, input=stdin,
                              capture_output=True, text=True, timeout=timeout)

    def zsh(self, snippet, *, function=None, modules=(), timeout=10):
        prelude = [f"fpath=({shlex.quote(str(FUNCTIONS_SOURCE))} $fpath)"]
        if function:
            prelude.append(f"autoload -Uz {function}")
        prelude += [f"source {shlex.quote(str(module_path(m)))}" for m in modules]
        return subprocess.run(["zsh", "-f", "-c", "\n".join([*prelude, snippet])], env=self.env,
                              cwd=self.home, capture_output=True, text=True, timeout=timeout)

    def fake_bin(self, name, *, stdout="", stderr="", exit_code=0, script=None):
        body = script if script is not None else (
            f"printf '%s' {shlex.quote(stdout)}\n"
            f"printf '%s' {shlex.quote(stderr)} >&2\n"
            f"exit {exit_code}\n")
        self._write(name, body)

    def calls(self, name):
        log = self.calls_dir / name
        if not log.exists():
            return []
        return [record.split(ARG_SEPARATOR)[:-1] for record in log.read_text().split(RECORD_SEPARATOR)[:-1]]

    def _write(self, name, body, record=True):
        log = shlex.quote(str(self.calls_dir / name))
        recorder = f"{{ (( $# )) && printf '%s\\0' \"$@\"; printf '\\036'; }} >> {log}\n" if record else ""
        path = self.fakes / name
        path.write_text(f"#!/usr/bin/env bash\n{recorder}{body}")
        path.chmod(0o755)
