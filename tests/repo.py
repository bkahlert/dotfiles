import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME_SOURCE = ROOT / "home"
CHEZMOISCRIPTS_SOURCE = HOME_SOURCE / ".chezmoiscripts"
BIN_SOURCE = HOME_SOURCE / "dot_local" / "exact_bin"
CLAUDE_SOURCE = HOME_SOURCE / "private_dot_claude"
SCRIPT_SOURCES = (("bin", BIN_SOURCE), ("claude", CLAUDE_SOURCE))
FUNCTIONS_SOURCE = HOME_SOURCE / "private_dot_config" / "zsh" / "exact_functions"
CONF_D_SOURCE = HOME_SOURCE / "private_dot_config" / "zsh" / "exact_conf.d"
SHIMS = ROOT / "tests" / "shims"
CONTEXTS = ("", "bkahlert", "ista")

# Only system tools (coreutils, awk, sed, jq) are reachable; the user's own PATH is not, so a
# subject that reaches for an unfaked tool fails instead of touching the real one.
SYSTEM_PATH = ("/usr/bin", "/bin", "/usr/sbin", "/sbin")
if sys.platform == "darwin":
    SYSTEM_PATH = ("/opt/homebrew/bin", "/usr/local/bin", *SYSTEM_PATH)


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
    return [(area, source.name.removeprefix("executable_"), source)
            for area, root in SCRIPT_SOURCES for source in sorted(root.iterdir())
            if source.name.startswith("executable_")]
