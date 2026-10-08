import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, NamedTuple


def dump_input(text, filename):
    destination = Path(tempfile.gettempdir()) / filename
    dump = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=destination.parent,
        prefix=f".{destination.stem}-", delete=False)
    try:
        with dump:
            dump.write(text)
        Path(dump.name).replace(destination)
    finally:
        Path(dump.name).unlink(missing_ok=True)


def read_json(text):
    try:
        value = json.loads(text)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def field(value, *path):
    for key in path:
        value = value.get(key) if isinstance(value, dict) else None
    return value


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


class Icons(NamedTuple):
    """Semantic glyphs and a percentage gauge for a status line."""

    session: str
    model: str
    agent: str
    gauge: Callable[[int], str]
    tokens: str
    clock: str
    calendar: str
    restart: str
    remote: str
    yolo: str


_BAR = [("\uee00", "\uee03"), *[("\uee01", "\uee04")] * 8, ("\uee02", "\uee05")]
_CIRCLES = [(12, "○"), (37, "◔"), (62, "◑"), (87, "◕"), (math.inf, "●")]


def _bar(pct):
    return "".join(full if pct >= 5 + 10 * i else empty for i, (empty, full) in enumerate(_BAR))


def _circle(pct):
    return next(glyph for bound, glyph in _CIRCLES if pct < bound)


# tokens and restart are blank on purpose; their parts render without an icon.
_NERD_ICONS = Icons(
    session="\uf292",
    model="\ue28c",
    agent="\U000f06a9",
    gauge=_bar,
    tokens="",
    clock="\uf017",
    calendar="\uf272",
    restart="",
    remote="\uf0ac",
    yolo="\uf071",
)

# U+FE0E keeps characters with emoji presentation monochrome.
_TEXT_ICONS = Icons(
    session="#",
    model="⚙\ufe0e",
    agent="웃",
    gauge=_circle,
    tokens="",
    clock="⏱\ufe0e",
    calendar="⧗\ufe0e",
    restart="",
    remote="↗",
    yolo="⚠\ufe0e",
)


def select_icons(override):
    """Return semantic icons using the override, NERD_FONTS, then font detection.

    Only "0" and "1" force a mode. Detection uses a shared cache under
    XDG_CACHE_HOME/agent-statusline, defaulting to ~/.cache/agent-statusline, and probes
    again after font-directory changes. Cache I/O failures trigger a fresh probe.
    """
    return _NERD_ICONS if _nerd_fonts_supported(override) else _TEXT_ICONS


def _nerd_fonts_supported(override):
    for forced in (override, os.environ.get("NERD_FONTS")):
        if forced in ("0", "1"):
            return forced == "1"
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "agent-statusline" / "nerd-font-support"
    try:
        if not cache.is_file() or _fonts_changed_since(cache):
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text("1" if _nerd_fonts_installed() else "0")
        return cache.read_text().strip() == "1"
    except OSError:
        return _nerd_fonts_installed()


def _fonts_changed_since(path):
    since = path.stat().st_mtime_ns
    return any(Path(directory).stat().st_mtime_ns > since
               for root in _font_directories() for directory, _, _ in os.walk(root))


def _font_directories():
    if sys.platform == "darwin":
        return [Path.home() / "Library/Fonts", Path("/Library/Fonts")]
    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return [data / "fonts", Path.home() / ".fonts", Path("/usr/local/share/fonts"), Path("/usr/share/fonts")]


def _nerd_fonts_installed():
    if sys.platform == "darwin":
        for directory in _font_directories():
            if directory.is_dir() and any("nerd" in entry.name.lower() for entry in directory.iterdir()):
                return True
    if shutil.which("fc-list"):
        fonts = subprocess.run(["fc-list"], capture_output=True, text=True).stdout
        return "nerd font" in fonts.lower()
    return False


def link(url, text):
    return f"\033]8;;{url}\033\\{text}\033]8;;\033\\"


def part_session(session_id=None, name=None, url=None, *, override=None):
    id_part = ""
    if session_id:
        text = session_id[:8]
        if url:
            text = link(url, text)
        id_part = f"{select_icons(override).session} {text}"
    name_part = f"\033[3m{name}\033[0m" if name else ""
    return render_parts([id_part, name_part], separator=" ")


def render_parts(parts, separator=" · "):
    return separator.join(part for part in parts if part)
