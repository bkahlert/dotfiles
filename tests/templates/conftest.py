import json
import re
import shutil
import subprocess

import pytest

from repo import HOME_SOURCE, SHIMS, SYSTEM_PATH, isolated_env

# The sandbox guards `chezmoi` (calling it unfaked fails), so the real one is resolved here, before any
# sandbox PATH exists. CI's macOS job installs it; the lint-and-unit job does not, and skips these.
CHEZMOI = shutil.which("chezmoi")


class Chezmoi:
    """The real chezmoi, run against the source tree with the op and keepassxc-cli shims as the vaults."""

    def __init__(self, home, config_dir):
        self.env = isolated_env(home, [str(SHIMS), *SYSTEM_PATH])
        self.config_dir = config_dir

    def run(self, *args, config=None, stdin="dummy-password\n"):
        command = [CHEZMOI, *args, "--source", str(HOME_SOURCE), "--no-tty"]
        if config:
            command += ["--config", str(config)]
        feed = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
        return subprocess.run(command, env=self.env, **feed, capture_output=True, text=True, timeout=60)

    def config(self, company):
        """The chezmoi.toml that `chezmoi init` writes for the context, rendered from the real template."""
        template = (HOME_SOURCE / ".chezmoi.toml.tmpl").read_text()
        answers = {"Email address": "test@example.com", "Full name": "Test User",
                   "Context name (bkahlert, ista, or empty for none)": company}
        prompts = [arg for prompt, answer in answers.items() for arg in ("--promptString", f"{prompt}={answer}")]
        result = self.run("execute-template", "--init", *prompts, template, stdin=None)
        assert result.returncode == 0, result.stderr
        path = self.config_dir / f"{company or 'none'}.toml"
        path.write_text(result.stdout)
        return path

    def render(self, source, *, company="", os="darwin"):
        """The template at `source` (relative to home/) as it renders in the context on the given OS."""
        result = self.run("execute-template", "--override-data", json.dumps({"chezmoi": {"os": os}}),
                          (HOME_SOURCE / source).read_text(), config=self.config(company))
        assert result.returncode == 0, result.stderr
        # execute-template prints keepassxc's password prompt to stdout; apply writes it to the terminal.
        return re.sub(r"Enter password to unlock [^\n]*?\.kdbx: ", "", result.stdout)

    def ignored(self, company):
        """The target paths .chezmoiignore drops in the context."""
        result = self.run("ignored", config=self.config(company), stdin=None)
        assert result.returncode == 0, result.stderr
        return result.stdout.split()


@pytest.fixture
def chezmoi(sandbox, tmp_path):
    if CHEZMOI is None:
        pytest.skip("chezmoi is not installed")
    configs = tmp_path / "configs"
    configs.mkdir()
    return Chezmoi(sandbox.home, configs)
