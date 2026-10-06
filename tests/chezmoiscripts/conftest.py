import subprocess

import pytest

from repo import HOME_SOURCE, chezmoiscripts, require_chezmoi

SOURCES = dict(chezmoiscripts())


HOMEBREW_PREFIXES = ("/opt/homebrew", "/usr/local")


@pytest.fixture
def script(sandbox, fake_bin, tmp_path):
    def run(key, *args, uname="Darwin", stdin=None, env=None, timeout=30, prefix_root=None, company=""):
        if uname:
            fake_bin("uname", stdout=f"{uname}\n")
        source = SOURCES[key]
        content = source.read_text()
        if source.suffix == ".tmpl":
            config = tmp_path / f"{company or 'none'}.toml"
            config.write_text(f'[data]\n  company = "{company}"\n')
            rendered = subprocess.run(
                [require_chezmoi(), "execute-template", "--config", str(config), "--source", str(HOME_SOURCE)],
                input=content, env=sandbox.env, cwd=sandbox.home, capture_output=True, text=True, timeout=timeout)
            assert rendered.returncode == 0, rendered.stderr
            content = rendered.stdout
            source = tmp_path / source.name.removesuffix(".tmpl")
        if prefix_root:
            source = prefix_root / source.name
        if source.parent == tmp_path or prefix_root:
            source.write_text(rebased(content, prefix_root) if prefix_root else content)
        feed = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
        return subprocess.run(["bash", str(source), *args], env={**sandbox.env, **(env or {})},
                              cwd=sandbox.home, **feed, capture_output=True, text=True, timeout=timeout)
    return run


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


def rebased(text, root):
    for prefix in HOMEBREW_PREFIXES:
        text = text.replace(prefix, f"{root}{prefix}")
    return text
