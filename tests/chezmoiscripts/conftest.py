import re
import shutil
import subprocess

import pytest

from repo import HOME_SOURCE, chezmoiscripts

SOURCES = dict(chezmoiscripts())

# The sandbox guards `chezmoi`, so the real one is resolved here, before any sandbox PATH exists.
CHEZMOI = shutil.which("chezmoi")


HOMEBREW_PREFIXES = ("/opt/homebrew", "/usr/local")


@pytest.fixture
def script(sandbox, fake_bin, tmp_path):
    def run(key, *args, uname="Darwin", stdin=None, env=None, timeout=30, prefix_root=None):
        if uname:
            fake_bin("uname", stdout=f"{uname}\n")
        source = SOURCES[key]
        if prefix_root:
            source = prefix_root / source.name
            source.write_text(rebased(SOURCES[key].read_text(), prefix_root))
        elif source.suffix == ".tmpl":
            source = tmp_path / source.name.removesuffix(".tmpl")
            source.write_text(without_template_lines(SOURCES[key].read_text()))
        feed = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
        return subprocess.run(["bash", str(source), *args], env={**sandbox.env, **(env or {})},
                              cwd=sandbox.home, **feed, capture_output=True, text=True, timeout=timeout)
    return run


@pytest.fixture
def rendered(sandbox, tmp_path):
    """Renders a `.tmpl` script with the real chezmoi, seeing the sandbox PATH the way `lookPath` does at apply time."""
    if CHEZMOI is None:
        pytest.skip("chezmoi is not installed")

    def render(key, *, company="ista"):
        config = tmp_path / "chezmoi.toml"
        config.write_text(f'[data]\n  email = "a@b.c"\n  name = "n"\n  company = "{company}"\n')
        result = subprocess.run([CHEZMOI, "execute-template", "--config", str(config), "--source", str(HOME_SOURCE)],
                                input=SOURCES[key].read_text(), env=sandbox.env, cwd=sandbox.home,
                                capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        return result.stdout
    return render


@pytest.fixture
def homebrew_at(sandbox, tmp_path):
    """Puts a brew that is not on PATH (the guard that fails an unfaked brew goes too) under one of the standard prefixes, moved below a temp root so the real /opt/homebrew stays out of the test; pass the returned root as `prefix_root` to `script`."""
    root = tmp_path / "prefixes"
    root.mkdir()

    def install(prefix):
        (sandbox.fakes / "brew").unlink(missing_ok=True)
        bin_dir = root / prefix.lstrip("/") / "bin"
        bin_dir.mkdir(parents=True)
        brew = bin_dir / "brew"
        brew.write_text(f'''#!/usr/bin/env bash
if [[ $1 == shellenv ]]; then
  printf 'export PATH="%s:$PATH"\\n' "${{0%/*}}"
else
  printf '%s\\0' "$@" $'\\036' >> "{sandbox.calls_dir / "brew"}"
fi
''')
        brew.chmod(0o755)
        return root

    return install


def without_template_lines(text):
    """The comment lines that carry template actions removed, so the rest runs as bash without chezmoi."""
    return "".join(line for line in text.splitlines(keepends=True) if not re.match(r"#.*\{\{.*\}\}$", line.rstrip("\n")))


def rebased(text, root):
    for prefix in HOMEBREW_PREFIXES:
        text = text.replace(prefix, f"{root}{prefix}")
    return text
