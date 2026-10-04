import ast
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pytest

import repo
from repo import CONF_D_SOURCE, FUNCTIONS_SOURCE, HOME_SOURCE, ROOT, chezmoiscripts, modify_scripts, scripts, templates

TESTS = ROOT / "tests"
ALLOWLIST = tomllib.loads((TESTS / "untested.toml").read_text())
DEFINES_A_FUNCTION = re.compile(
    r"^\s*(?:function\s+)?[A-Za-z_][A-Za-z0-9_-]*\s*\(\)\s*\{?|^\s*function\s+[A-Za-z_]", re.MULTILINE)
JS_TEST = re.compile(r"^\s*(?:test|it)\(", re.MULTILINE)
MIN_REASON_WORDS = 3


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
    def tested(self):
        return self.test is not None and defines_a_test(self.test)

    @property
    def listed(self):
        return self.key in ALLOWLIST.get(self.section, {})


def subjects():
    found = []
    for area, key, source in scripts():
        found.append(Subject(area, key, source, (
            TESTS / area / f"test_{key.replace('-', '_')}.py",
            TESTS / f"{key}.test.js")))
    for source in sorted(FUNCTIONS_SOURCE.glob("[!.]*")):
        found.append(Subject("functions", source.name, source,
                             (TESTS / "functions" / f"test_{source.name.replace('-', '_')}.py",)))
    for key, source in chezmoiscripts():
        found.append(Subject("chezmoiscripts", key, source,
                             (TESTS / "chezmoiscripts" / f"test_{key.replace('-', '_')}.py",)))
    for section, files in (("modify", modify_scripts()), ("templates", templates())):
        for key, source in files:
            found.append(Subject(section, key, source, (TESTS / section / f"test_{key}.py",)))
    found.append(Subject("startup", "zshenv", HOME_SOURCE / "dot_zshenv", (TESTS / "zsh" / "test_zshenv.py",)))
    for source in conf_d_modules():
        if DEFINES_A_FUNCTION.search(source.read_text()):
            found.append(Subject("conf_d", conf_d_key(source), source, (conf_d_test(source),)))
    return found


def conf_d_modules():
    return [s for s in sorted(CONF_D_SOURCE.rglob("*.zsh*")) if s.suffix in (".zsh", ".tmpl")]


def conf_d_key(source: Path) -> str:
    dirs = [d.removeprefix("exact_") for d in source.relative_to(CONF_D_SOURCE).parts[:-1]]
    return "/".join([*dirs, source.name.removesuffix(".tmpl").removesuffix(".zsh")])


def conf_d_test(source: Path) -> Path:
    *dirs, stem = conf_d_key(source).split("/")
    return TESTS.joinpath("zsh", *dirs, f"test_{re.sub(r'^\d+-', '', stem).replace('-', '_')}.py")


def defines_a_test(path: Path) -> bool:
    """Whether pytest would collect a test from the file, or a `test(`/`it(` call sits in a JS one."""
    if path.suffix == ".js":
        return bool(JS_TEST.search(path.read_text()))
    return any(True for _ in collected_tests(ast.parse(path.read_text())))


def collected_tests(node: ast.AST, skipped: bool = False):
    """The `test*` functions and `Test*` class methods under node that no unconditional skip mark disables."""
    for child in ast.iter_child_nodes(node):
        skip = skipped or any(skips_unconditionally(d) for d in getattr(child, "decorator_list", ()))
        if isinstance(child, ast.ClassDef) and child.name.startswith("Test"):
            yield from collected_tests(child, skip)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test") and not skip:
            yield child


def skips_unconditionally(decorator: ast.expr) -> bool:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    return ast.unparse(target) == "pytest.mark.skip"


def all_test_files(root: Path = TESTS) -> list[Path]:
    return sorted([*root.rglob("test_*.py"), *root.glob("*.test.js")])


def orphans(files: list[Path], expected: set[Path], root: Path = TESTS) -> list[Path]:
    """Test files not in `expected`. Those directly in tests/ and under tests/integration/ test the
    repository itself (conventions, sandbox, shims, a whole apply), not one file of it."""
    cross_cutting = lambda f: f.suffix == ".py" and (f.parent == root or root / "integration" in f.parents)
    return [f for f in files if f not in expected and not cross_cutting(f)]


def states_a_reason(reason: str) -> bool:
    return len(reason.split()) >= MIN_REASON_WORDS


SUBJECTS = subjects()
TEST_FILES = all_test_files()
EXPECTED_TEST_FILES = {c for s in SUBJECTS for c in s.candidates} | {conf_d_test(m) for m in conf_d_modules()}
ENTRIES = [(section, key, reason) for section, entries in ALLOWLIST.items() for key, reason in entries.items()]


class TestEverySubject:
    @pytest.mark.parametrize("subject", SUBJECTS, ids=lambda s: f"{s.section}/{s.key}")
    def test_should_have_a_test_or_a_listed_reason(self, subject):
        assert subject.tested or subject.listed, (
            f"{subject.source.relative_to(ROOT)} has no test at "
            f"{' or '.join(str(c.relative_to(ROOT)) for c in subject.candidates)} "
            f"and no entry under [{subject.section}] in tests/untested.toml"
            + (f"; {subject.test.relative_to(ROOT)} exists but defines no test that runs" if subject.test else ""))


class TestEveryAllowlistEntry:
    @pytest.mark.parametrize("section,key,reason", ENTRIES, ids=[f"{s}/{k}" for s, k, _ in ENTRIES])
    def test_should_name_an_existing_untested_subject_with_a_reason(self, section, key, reason):
        subject = next((s for s in SUBJECTS if s.section == section and s.key == key), None)
        assert subject is not None, f"[{section}] {key}: no such file, or it no longer defines a function; remove the entry"
        assert not subject.tested, f"[{section}] {key}: tested by {subject.test.relative_to(ROOT)}; remove the entry"
        assert states_a_reason(reason), f"[{section}] {key}: the reason {reason!r} needs at least {MIN_REASON_WORDS} words"


class TestEveryTestFile:
    @pytest.mark.parametrize("file", TEST_FILES, ids=lambda f: str(f.relative_to(TESTS)))
    def test_should_belong_to_a_subject(self, file):
        assert file not in orphans(TEST_FILES, EXPECTED_TEST_FILES), (
            f"{file.relative_to(ROOT)} tests no existing file; rename it after its subject or delete it")


class TestScripts:
    def test_should_cover_every_file_in_bin(self):
        assert {s.name for _, _, s in scripts() if s.parent == repo.BIN_SOURCE} == {
            p.name for p in repo.BIN_SOURCE.iterdir()}

    def test_should_cover_a_bin_file_without_the_executable_prefix(self, tmp_path, monkeypatch):
        (tmp_path / "executable_a").touch()
        (tmp_path / "b").touch()
        monkeypatch.setattr(repo, "SCRIPT_SOURCES", (("bin", tmp_path),))
        assert [(area, key) for area, key, _ in scripts()] == [("bin", "b"), ("bin", "a")]

    def test_should_cover_only_executable_files_in_claude(self, tmp_path, monkeypatch):
        (tmp_path / "executable_a").touch()
        (tmp_path / "CLAUDE.md").touch()
        (tmp_path / "skills").mkdir()
        monkeypatch.setattr(repo, "SCRIPT_SOURCES", (("claude", tmp_path),))
        assert [(area, key) for area, key, _ in scripts()] == [("claude", "a")]


class TestDefinesATest:
    class TestOnPython:
        def test_should_hold_for_a_test_function(self, tmp_path):
            assert defines_a_test(file(tmp_path, "def test_a():\n    pass\n"))

        def test_should_hold_for_a_method_of_a_test_class(self, tmp_path):
            assert defines_a_test(file(tmp_path, "class TestA:\n    class TestB:\n        def test_c(self):\n            pass\n"))

        def test_should_fail_on_an_empty_file(self, tmp_path):
            assert not defines_a_test(file(tmp_path, ""))

        def test_should_fail_on_helpers_only(self, tmp_path):
            assert not defines_a_test(file(tmp_path, "def helper():\n    pass\n\n\nclass Helper:\n    def test_a(self):\n        pass\n"))

        def test_should_fail_on_a_test_nested_in_a_function(self, tmp_path):
            assert not defines_a_test(file(tmp_path, "def helper():\n    def test_a():\n        pass\n"))

        def test_should_fail_when_every_test_is_skipped(self, tmp_path):
            assert not defines_a_test(file(tmp_path, (
                "import pytest\n\n\n@pytest.mark.skip(reason='x')\ndef test_a():\n    pass\n\n\n"
                "@pytest.mark.skip\nclass TestB:\n    def test_c(self):\n        pass\n")))

        def test_should_hold_on_a_conditional_skip(self, tmp_path):
            assert defines_a_test(file(tmp_path, (
                "import pytest\n\n\n@pytest.mark.skipif(True, reason='x')\ndef test_a():\n    pass\n")))

        def test_should_hold_when_one_test_is_skipped_and_another_is_not(self, tmp_path):
            assert defines_a_test(file(tmp_path, (
                "import pytest\n\n\n@pytest.mark.skip\ndef test_a():\n    pass\n\n\ndef test_b():\n    pass\n")))

    class TestOnJavaScript:
        def test_should_hold_for_a_test_call(self, tmp_path):
            assert defines_a_test(file(tmp_path, "describe('x', () => {\n  test('y', () => {});\n});\n", "x.test.js"))

        def test_should_fail_on_a_describe_without_tests(self, tmp_path):
            assert not defines_a_test(file(tmp_path, "describe('x', () => {});\n", "x.test.js"))


class TestOrphans:
    def test_should_name_a_test_file_no_subject_expects(self, tmp_path):
        gone = file(tmp_path / "bin", "", "test_gone.py")
        assert orphans([gone], {tmp_path / "bin" / "test_kept.py"}, tmp_path) == [gone]

    def test_should_spare_a_test_file_a_subject_expects(self, tmp_path):
        kept = file(tmp_path / "bin", "", "test_kept.py")
        assert orphans([kept], {kept}, tmp_path) == []

    def test_should_spare_a_python_test_directly_in_the_tests_directory(self, tmp_path):
        assert orphans([file(tmp_path, "", "test_sandbox.py")], set(), tmp_path) == []

    def test_should_spare_a_test_under_integration(self, tmp_path):
        assert orphans([file(tmp_path / "integration", "", "test_apply.py")], set(), tmp_path) == []

    def test_should_name_a_javascript_test_without_a_subject(self, tmp_path):
        gone = file(tmp_path, "", "gone.test.js")
        assert orphans([gone], set(), tmp_path) == [gone]


class TestStatesAReason:
    def test_should_hold_for_a_sentence(self):
        assert states_a_reason("one guarded `clone`; nothing of ours to assert")

    @pytest.mark.parametrize("reason", ["", "  ", "x", "todo", "no test"])
    def test_should_fail_on_fewer_than_three_words(self, reason):
        assert not states_a_reason(reason)


def file(directory: Path, content: str, name: str = "test_x.py") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(content)
    return directory / name
