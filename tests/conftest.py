import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

from repo import FUNCTIONS_SOURCE, SYSTEM_PATH, isolated_env, module_path, scripts
from agent_integration import CAPABILITIES


def pytest_addoption(parser):
    parser.addoption("--live-agent", choices=("claude", "copilot"), default=None,
                     help="Explicitly opt into authenticated, billable capability smoke tests")
    parser.addoption("--agent-capability", action="append", choices=CAPABILITIES,
                     help="Test only this capability (repeatable); default: all four")

# The only real tools a subject can reach, besides the fakes and the other scripts under test: shells,
# coreutils and text tools. Everything else (docker, aws, node, claude, a Homebrew package) is not on the
# sandbox PATH at all, so an unfaked call fails whether or not the machine has the tool installed.
# A new subject that needs another real tool adds it here. They are taken from TOOL_DIRECTORIES, not from
# the caller's PATH, so the same tool is found on every machine (bash must be Homebrew's 4.4+ on macOS).
REAL_TOOLS = ("awk", "base64", "basename", "bash", "cat", "chmod", "cp", "cut", "date", "dirname", "env",
              "false", "find", "getconf", "grep", "gzip", "head", "jq", "ls", "mkdir", "mkfifo", "mktemp", "mv",
              "nohup", "python3", "rg", "rm", "rmdir", "sed", "seq", "sh", "shasum", "sleep", "sort", "stat",
              "tail", "tar", "test", "touch", "tr", "true", "uname", "uniq", "wc", "zsh")
TOOL_DIRECTORIES = ":".join(SYSTEM_PATH)

# Tools that reach the network, a vault, system state or the user's own state (repositories,
# processes, the clipboard, container machines), or ignore `HOME` (`ssh-keygen -R` edits the
# passwd-database home's known_hosts). A guard stands in for each so a subject under test can never
# call the real one; a test that needs one installs a fake with fake_bin. `docker` is a script under
# test here, so its podman fallback is what gets guarded.
GUARDED = ("op", "keepassxc-cli", "gh", "glab", "gcloud", "idp", "curl", "wget", "ssh", "scp", "ssh-keygen",
           "openssl", "brew", "open", "osascript", "launchctl", "defaults", "sudo", "xcrun",
           "git", "chezmoi", "podman", "npm", "npx", "yarn", "composer", "gem", "uv",
           "mas", "softwareupdate", "security", "dscacheutil", "pbcopy", "pbpaste", "lsof", "killall", "pkill")
# A record is written by one printf, so two fakes in a pipeline cannot interleave their records.
# NUL cannot occur inside an argument, so it ends one; a record ends with RS followed by NUL.
ARG_SEPARATOR = "\0"
RECORD_SEPARATOR = "\x1e\0"


@pytest.fixture(scope="session")
def bin_links(tmp_path_factory):
    links = tmp_path_factory.mktemp("bin")
    for _, name, source in scripts():
        (links / name).symlink_to(source)
    return links


@pytest.fixture(scope="session")
def real_tools(tmp_path_factory):
    """Symlinks to the REAL_TOOLS, found in TOOL_DIRECTORIES in order."""
    found = {name: shutil.which(name, path=TOOL_DIRECTORIES) for name in REAL_TOOLS}
    if missing := [name for name, path in found.items() if path is None]:
        pytest.exit(f"REAL_TOOLS not found in {TOOL_DIRECTORIES}: {' '.join(missing)}", returncode=2)
    links = tmp_path_factory.mktemp("real-tools")
    for name, path in found.items():
        (links / name).symlink_to(path)
    return links


@pytest.fixture
def sandbox(tmp_path, bin_links, real_tools):
    return Sandbox(tmp_path / "home", tmp_path / "fakes", bin_links, real_tools)


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
    def __init__(self, home: Path, fakes: Path, bin_links: Path, real_tools: Path):
        self.home = home
        self.fakes = fakes
        self.bin_links = bin_links
        self.calls_dir = fakes / ".calls"
        self.real_tools = real_tools
        self.calls_dir.mkdir(parents=True)
        self.env = isolated_env(home, [str(fakes), str(bin_links), str(real_tools)])
        for name in GUARDED:
            self._write(name, "printf '%s: not faked in this test\\n' \"${0##*/}\" >&2\nexit 127\n",
                        record=False)

    def run(self, name, *args, stdin=None, timeout=10):
        feed = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
        return subprocess.run([name, *args], env=self.env, cwd=self.home, **feed,
                              capture_output=True, text=True, timeout=timeout)

    def only_tools(self, *names):
        """PATH becomes the fakes plus bash (which they run on) and the named REAL_TOOLS, so a glab, node or claude installed on the machine cannot leak in."""
        bare = self.fakes.parent / "bare"
        bare.mkdir(exist_ok=True)
        for name in dict.fromkeys(("bash", *names)):
            tool = self.real_tools / name
            if not tool.is_symlink():
                pytest.fail(f"only_tools: {name} is not one of the REAL_TOOLS")
            (bare / name).symlink_to(tool.readlink())
        self.env["PATH"] = f"{self.fakes}:{bare}"

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
        recorder = f"printf '%s\\0' \"$@\" $'\\036' >> {log}\n" if record else ""
        path = self.fakes / name
        path.write_text(f"#!/usr/bin/env bash\n{recorder}{body}")
        path.chmod(0o755)
