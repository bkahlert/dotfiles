import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pytest

from repo import CONF_D_SOURCE, FUNCTIONS_SOURCE, ROOT, scripts

TESTS = ROOT / "tests"
ALLOWLIST = tomllib.loads((TESTS / "untested.toml").read_text())
DEFINES_A_FUNCTION = re.compile(
    r"^\s*(?:function\s+)?[A-Za-z_][A-Za-z0-9_-]*\s*\(\)\s*\{?|^\s*function\s+[A-Za-z_]", re.MULTILINE)


@dataclass(frozen=True)
class Subject:
    section: str
    key: str
    source: Path
    candidates: tuple[Path, ...]

    @property
    def test(self):
        return next((c for c in self.candidates if c.exists()), None)

    @property
    def listed(self):
        return self.key in ALLOWLIST.get(self.section, {})


def subjects():
    found = []
    for area, key, source in scripts():
        found.append(Subject(area, key, source, (
            TESTS / area / f"test_{key.replace('-', '_')}.py",
            TESTS / f"{key}.test.js")))
    for source in sorted(FUNCTIONS_SOURCE.iterdir()):
        found.append(Subject("functions", source.name, source,
                             (TESTS / "functions" / f"test_{source.name.replace('-', '_')}.py",)))
    for source in sorted(CONF_D_SOURCE.rglob("*.zsh*")):
        if source.suffix not in (".zsh", ".tmpl") or not DEFINES_A_FUNCTION.search(source.read_text()):
            continue
        dirs = [d.removeprefix("exact_") for d in source.relative_to(CONF_D_SOURCE).parts[:-1]]
        stem = source.name.removesuffix(".tmpl").removesuffix(".zsh")
        found.append(Subject("conf_d", "/".join([*dirs, stem]), source, (
            TESTS.joinpath("zsh", *dirs, f"test_{re.sub(r'^\d+-', '', stem).replace('-', '_')}.py"),)))
    return found


SUBJECTS = subjects()
ENTRIES = [(section, key, reason) for section, entries in ALLOWLIST.items() for key, reason in entries.items()]


class TestEverySubject:
    @pytest.mark.parametrize("subject", SUBJECTS, ids=lambda s: f"{s.section}/{s.key}")
    def test_should_have_a_test_or_a_listed_reason(self, subject):
        assert subject.test or subject.listed, (
            f"{subject.source.relative_to(ROOT)} has no test at "
            f"{' or '.join(str(c.relative_to(ROOT)) for c in subject.candidates)} "
            f"and no entry under [{subject.section}] in tests/untested.toml")


class TestEveryAllowlistEntry:
    @pytest.mark.parametrize("section,key,reason", ENTRIES, ids=[f"{s}/{k}" for s, k, _ in ENTRIES])
    def test_should_name_an_existing_untested_subject_with_a_reason(self, section, key, reason):
        subject = next((s for s in SUBJECTS if s.section == section and s.key == key), None)
        assert subject is not None, f"[{section}] {key}: no such file, or it no longer defines a function; remove the entry"
        assert subject.test is None, f"[{section}] {key}: tested by {subject.test.relative_to(ROOT)}; remove the entry"
        assert reason.strip(), f"[{section}] {key}: needs a reason"
