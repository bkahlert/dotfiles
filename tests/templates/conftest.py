import json
import re
import subprocess

import pytest

from repo import HOME_SOURCE, SHIMS, SYSTEM_PATH, isolated_env, require_chezmoi


class Chezmoi:
    """The real chezmoi, run against the source tree with the keepassxc-cli shim as the vault."""

    def __init__(self, executable, home, config_dir):
        self.executable = executable
        self.env = isolated_env(home, [str(SHIMS), *SYSTEM_PATH])
        self.config_dir = config_dir

    def run(self, *args, config=None, source=HOME_SOURCE, stdin="dummy-password\n"):
        command = [self.executable, *args, "--source", str(source), "--no-tty"]
        if config:
            command += ["--config", str(config)]
        feed = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
        return subprocess.run(command, env=self.env, **feed, capture_output=True, text=True, timeout=60)

    def config(self, *, source=HOME_SOURCE):
        """The chezmoi.toml that `chezmoi init --source <source>` writes for the context, rendered from the real template."""
        template = (HOME_SOURCE / ".chezmoi.toml.tmpl").read_text()
        answers = {"Email address": "test@example.com", "Full name": "Test User"}
        prompts = [arg for prompt, answer in answers.items() for arg in ("--promptString", f"{prompt}={answer}")]
        result = self.run("execute-template", "--init", *prompts, template, source=source, stdin=None)
        assert result.returncode == 0, result.stderr
        path = self.config_dir / "default.toml"
        path.write_text(result.stdout)
        return path

    def render(self, source, *, os="darwin"):
        """The template at `source` (relative to home/) as it renders on the given OS."""
        result = self.run("execute-template", "--override-data", json.dumps({"chezmoi": {"os": os}}),
                          (HOME_SOURCE / source).read_text(), config=self.config())
        assert result.returncode == 0, result.stderr
        # execute-template prints keepassxc's password prompt to stdout; apply writes it to the terminal.
        return re.sub(r"Enter password to unlock [^\n]*?\.kdbx: ", "", result.stdout)

    def ignored(self, *, os=None):
        """The target paths .chezmoiignore drops on this OS or the default OS."""
        override = ("--override-data", json.dumps({"chezmoi": {"os": os}})) if os else ()
        result = self.run("ignored", *override, config=self.config(), stdin=None)
        assert result.returncode == 0, result.stderr
        return result.stdout.split()


@pytest.fixture
def chezmoi(sandbox, tmp_path):
    configs = tmp_path / "configs"
    configs.mkdir()
    return Chezmoi(require_chezmoi(), sandbox.home, configs)
