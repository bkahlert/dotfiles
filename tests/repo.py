import os
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOME_SOURCE = ROOT / "home"
CHEZMOISCRIPTS_SOURCE = HOME_SOURCE / ".chezmoiscripts"
BIN_SOURCE = HOME_SOURCE / "dot_local" / "exact_bin"
CLAUDE_SOURCE = HOME_SOURCE / "private_dot_claude"
COPILOT_SOURCE = HOME_SOURCE / "private_dot_copilot"
SCRIPT_SOURCES = (("bin", BIN_SOURCE), ("claude", CLAUDE_SOURCE), ("copilot", COPILOT_SOURCE))
FUNCTIONS_SOURCE = HOME_SOURCE / "private_dot_config" / "zsh" / "exact_functions"
CONF_D_SOURCE = HOME_SOURCE / "private_dot_config" / "zsh" / "exact_conf.d"
SHIMS = ROOT / "tests" / "shims"
# The directories of the tests that run the real chezmoi, which lives in Homebrew's. The unit-test
# sandbox does not use them: it exposes only the REAL_TOOLS of conftest.py.
SYSTEM_PATH = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")
if sys.platform == "darwin":
    SYSTEM_PATH = ("/opt/homebrew/bin", "/usr/local/bin", *SYSTEM_PATH)


def require_chezmoi() -> str:
    """The path of the real chezmoi, which the sandbox guards, so it is resolved from the caller's PATH. Missing,
    a test skips on a developer machine and fails on CI, where a skip would hide that it never ran."""
    path = shutil.which("chezmoi")
    if path is None:
        if os.environ.get("CI", "").lower() not in ("", "0", "false"):
            pytest.fail("chezmoi is not installed; install it in the CI job instead of skipping", pytrace=False)
        pytest.skip("chezmoi is not installed")
    return path


def module_path(name: str) -> Path:
    *dirs, file = name.split("/")
    return CONF_D_SOURCE.joinpath(*(f"exact_{d}" for d in dirs), file)


def isolated_env(home: Path, path: list[str]) -> dict[str, str]:
    for sub in ("", ".config", ".local/share", ".local/state", ".cache", "tmp"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    return {
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "TMPDIR": str(home / "tmp"),
        "PATH": ":".join(path),
        "TERM": "dumb",
        "LANG": "C.UTF-8",
    }


def scripts() -> list[tuple[str, str, Path]]:
    """Every file in bin/, so one missing its `executable_` prefix is still a script, and each `executable_` file
    in ~/.claude and ~/.copilot, which also hold their respective configuration files."""
    return [(area, source.name.removeprefix("executable_"), source)
            for area, root in SCRIPT_SOURCES for source in sorted(root.iterdir())
            if source.is_file() and (area == "bin" or source.name.startswith("executable_"))]


def chezmoiscripts() -> list[tuple[str, Path]]:
    """Each script in .chezmoiscripts/ keyed by its name without the run_ prefix, ordering digits and extensions."""
    return [(re.sub(r"^\d+-", "", re.sub(r"^run_(?:once|onchange)_(?:before|after)_|(?:\.sh)?(?:\.tmpl)?$", "", source.name)), source)
            for source in sorted(CHEZMOISCRIPTS_SOURCE.iterdir())]


def target_key(name: str) -> str:
    """A source file's name as a test file stem: chezmoi attributes, a leading dot or ordering digits and the
    template suffix dropped, other non-alphanumerics as underscores (`private_dot_x.tmpl` -> `x`)."""
    name = re.sub(r"\.tmpl$", "", name)
    name = re.sub(r"^(?:(?:modify|executable|private|exact|empty|dot)_)+", "", name)
    return re.sub(r"[^A-Za-z0-9]+", "_", re.sub(r"^\.?(?:\d+-)?", "", name))


def modify_scripts() -> list[tuple[str, Path]]:
    """Every modify_ script, wherever it sits (`modify_settings.json` -> `settings_json`)."""
    return [(target_key(source.name), source) for source in sorted(HOME_SOURCE.rglob("modify_*")) if source.is_file()]


def templates() -> list[tuple[str, Path]]:
    """Every template that is not a .chezmoiscripts/ script (`dot_gitconfig.tmpl` -> `gitconfig`), and
    `.chezmoiignore`, which chezmoi templates without the suffix."""
    sources = [*sorted(HOME_SOURCE.rglob("*.tmpl")), HOME_SOURCE / ".chezmoiignore"]
    return [(target_key(source.name), source) for source in sources
            if source.is_file() and CHEZMOISCRIPTS_SOURCE not in source.parents]


def brewfile_lines() -> list[str]:
    """The Brewfile heredoc of the package install script, one entry per line."""
    source = dict(chezmoiscripts())["install-packages"].read_text()
    return re.search(r"<<EOF\n(.*?)\nEOF\n", source, re.DOTALL).group(1).splitlines()
