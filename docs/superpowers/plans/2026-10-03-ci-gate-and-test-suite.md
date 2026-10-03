# CI Gate and Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merges to `main` require a green `ci` check that proves the dotfiles apply and start a silent zsh in every context on Linux and macOS, that the scripts behave as claimed, and that no script or function slips in untested.

**Architecture:** Three `make` targets (`lint`, `unit`, `integration` plus `integration-native`) are the whole interface; a GitHub Actions workflow only calls them. The real scripts run under pytest in a sandbox whose `HOME`, `XDG_*` and `PATH` point into a temp dir with fake commands first on `PATH`. The integration legs apply the source tree with fake `op` and `keepassxc-cli`, in a Fedora container on Linux and into a temp home on macOS, and assert exit 0 plus empty stderr from `zsh -li -c true`. A conventions test keeps an allowlist of untested files honest.

**Tech Stack:** pytest 9 via uv, node:test (existing driver test), shellcheck, actionlint, zizmor, Podman (Docker-compatible), GitHub Actions, GitHub repository rulesets.

**Spec:** [docs/superpowers/specs/2026-10-03-ci-and-tests-design.md](../specs/2026-10-03-ci-and-tests-design.md)

## Global Constraints

- Branch `ci/test-gate-and-suite` already exists and holds the spec; all work lands there. Never commit on `main`. Commit messages follow Conventional Commits with the Angular types; PR title is the squash commit header.
- The worktree has an uncommitted change to `home/private_dot_config/zsh/exact_conf.d/90-scratch.zsh` that belongs to the user. Never stage it; always `git add` explicit paths.
- Python `>=3.12`, pytest `>=9.1.1`, pinned via `uv.lock`; `uv run --locked` everywhere.
- zizmor `1.30.1` via `uvx`; actionlint `v1.7.12`; `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`; `astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7 # v10.2.0`.
- Contexts are exactly `""`, `"bkahlert"`, `"ista"`, in that order, test ids `none`, `bkahlert`, `ista`.
- Test files follow [testing.md](../../../home/private_dot_config/exact_agents/exact_rules/testing.md): classes per subject, nested classes for `On...` contexts, `test_should_...` methods, test cases first and helpers at the bottom, no comments or docstrings in tests.
- Bash scripts (shims, entrypoint) follow [bash.md](../../../home/private_dot_config/exact_agents/exact_rules/bash.md): header with `Purpose:`/`Usage:`, `set -euo pipefail`, no extension, executable.
- Containerfiles follow [docker.md](../../../home/private_dot_config/exact_agents/exact_rules/docker.md): `HEALTHCHECK NONE` with its reason stays.
- While the JetBrains MCP tools are connected, run `mcp__idea__get_file_problems` with `errorsOnly: false` on every file a task changed, before that task's commit ([ide-inspections.md](../../../home/private_dot_config/exact_agents/exact_rules/ide-inspections.md)).
- Unit tests never reach the network, a vault or system state: the sandbox installs failing guards for `op keepassxc-cli gh glab gcloud idp curl wget ssh scp brew open osascript launchctl defaults sudo`; a test that needs one fakes it.
- Startup code under `conf.d` writes only under `HOME`, `ZDOTDIR` or an `XDG_*` directory, and stays silent when a tool it wraps is absent.

## Review Focus

1. A fake command called with arguments that contain spaces, or with a single empty argument, must be recorded exactly; pinned by `TestFakeBin` in Task 1.
2. A script that calls a network or secret tool nobody faked must fail with exit 127 and a message, never reach the real binary; pinned by `TestRun.test_should_fail_loudly_on_a_guarded_tool` in Task 1.
3. The fake `keepassxc-cli` must not block when nothing is piped to it; pinned by `TestShow.test_should_not_block_without_a_password_on_stdin` in Task 5.
4. `make lint` must survive tracked paths with spaces (`home/Library/private_Application Support/...`); pinned by running it in Task 3 against the real tree, which contains such a path.
5. The aggregator job must fail when an upstream job is `skipped` or `cancelled`, not only on `failure`; pinned by the result loop in Task 10 and checked by reading the first run's `ci` job log.

---

### Task 1: Python test project and the sandbox fixtures

**Files:**
- Create: `pyproject.toml`, `uv.lock` (generated), `tests/repo.py`, `tests/conftest.py`, `tests/test_sandbox.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `repo.ROOT`, `repo.HOME_SOURCE`, `repo.BIN_SOURCE`, `repo.FUNCTIONS_SOURCE`, `repo.CONF_D_SOURCE`, `repo.SHIMS`, `repo.CONTEXTS`, `repo.SYSTEM_PATH`, `repo.module_path(name) -> Path`, `repo.isolated_env(home: Path, path: list[str]) -> dict[str, str]`.
- Produces fixtures: `sandbox` (a `Sandbox` with `.home`, `.env`, `.run(name, *args, stdin=None, timeout=10)`, `.zsh(snippet, *, function=None, modules=(), timeout=10)`, `.fake_bin(name, *, stdout="", stderr="", exit_code=0, script=None)`, `.calls(name) -> list[list[str]]`), and the shortcuts `run`, `fake_bin`, `zsh`, `calls`.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "dotfiles-tests"
version = "0"
description = "Test suite for this dotfiles repository; not a package"
requires-python = ">=3.12"

[dependency-groups]
dev = ["pytest>=9.1.1"]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["tests"]
addopts = "--import-mode=importlib --strict-markers -ra"
markers = [
    "integration: applies the dotfiles end to end; slow, needs a container engine or macOS",
]
```

- [ ] **Step 2: Lock and add ignores**

Run: `uv lock && uv sync`
Expected: `uv.lock` exists, `.venv/` created, pytest 9.x resolved.

Append to `.gitignore`:

```
# python test project
.venv/
.pytest_cache/
__pycache__/
# node
node_modules/
```

- [ ] **Step 3: Create `tests/repo.py`**

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME_SOURCE = ROOT / "home"
BIN_SOURCE = HOME_SOURCE / "dot_local" / "exact_bin"
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
```

- [ ] **Step 4: Write the failing sandbox tests in `tests/test_sandbox.py`**

```python
class TestSandbox:
    class TestRun:
        def test_should_resolve_scripts_by_their_target_name(self, run):
            result = run("gh-latest", "--help")
            assert result.returncode == 0
            assert result.stdout.startswith("Purpose:")

        def test_should_keep_the_real_home_out_of_reach(self, run, sandbox):
            result = run("sh", "-c", 'echo "$HOME" "$XDG_CONFIG_HOME"')
            assert result.stdout.split() == [str(sandbox.home), str(sandbox.home / ".config")]

        def test_should_fail_loudly_on_a_guarded_tool(self, run):
            result = run("op", "read", "op://x/y/z")
            assert result.returncode == 127
            assert result.stderr == "op: not faked in this test\n"

    class TestFakeBin:
        def test_should_record_every_call_with_its_arguments(self, run, fake_bin, calls):
            fake_bin("gh")
            run("gh", "pr", "view", "--json", "title and body")
            run("gh", "")
            run("gh")
            assert calls("gh") == [["pr", "view", "--json", "title and body"], [""], []]

        def test_should_return_the_canned_output_and_exit_code(self, run, fake_bin):
            fake_bin("gh", stdout="out", stderr="err", exit_code=3)
            result = run("gh")
            assert (result.stdout, result.stderr, result.returncode) == ("out", "err", 3)

        def test_should_run_a_script_body_with_the_arguments(self, run, fake_bin):
            fake_bin("gh", script='[[ $1 == pr ]] && echo yes || echo no\n')
            result = run("gh", "pr")
            assert result.stdout == "yes\n"

        def test_should_replace_a_guard(self, run, fake_bin):
            fake_bin("curl", stdout="{}")
            result = run("curl", "https://example.test")
            assert result.returncode == 0

    class TestZsh:
        def test_should_autoload_a_function_from_the_source_tree(self, zsh):
            result = zsh("whence -w zsh-scratch", function="zsh-scratch")
            assert result.stdout == "zsh-scratch: function\n"

        def test_should_source_modules_in_order(self, zsh):
            result = zsh("whence -w printf_info", modules=["08-print.zsh"])
            assert result.stdout == "printf_info: function\n"
```

- [ ] **Step 5: Run to verify failure**

Run: `uv run --locked pytest tests/test_sandbox.py -q`
Expected: errors, `fixture 'run' not found`.

- [ ] **Step 6: Create `tests/conftest.py`**

```python
import shlex
import subprocess
from pathlib import Path

import pytest

from repo import BIN_SOURCE, FUNCTIONS_SOURCE, SYSTEM_PATH, isolated_env, module_path

# Tools that reach the network, a vault or system state. A guard stands in for each so a subject
# under test can never call the real one; a test that needs one installs a fake with fake_bin.
GUARDED = ("op", "keepassxc-cli", "gh", "glab", "gcloud", "idp", "curl", "wget", "ssh", "scp",
           "brew", "open", "osascript", "launchctl", "defaults", "sudo")
ARG_SEPARATOR = "\x1f"


@pytest.fixture(scope="session")
def bin_links(tmp_path_factory):
    links = tmp_path_factory.mktemp("bin")
    for source in BIN_SOURCE.iterdir():
        if source.name.startswith("executable_"):
            (links / source.name.removeprefix("executable_")).symlink_to(source)
    return links


@pytest.fixture
def sandbox(tmp_path, bin_links):
    return Sandbox(tmp_path / "home", tmp_path / "fakes", bin_links)


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
    def __init__(self, home: Path, fakes: Path, bin_links: Path):
        self.home = home
        self.fakes = fakes
        self.calls_dir = fakes / ".calls"
        self.calls_dir.mkdir(parents=True)
        self.env = isolated_env(home, [str(fakes), str(bin_links), *SYSTEM_PATH])
        for name in GUARDED:
            self._write(name, "printf '%s: not faked in this test\\n' \"${0##*/}\" >&2\nexit 127\n",
                        record=False)

    def run(self, name, *args, stdin=None, timeout=10):
        return subprocess.run([name, *args], env=self.env, cwd=self.home, input=stdin,
                              capture_output=True, text=True, timeout=timeout)

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
        return [line.split(ARG_SEPARATOR)[:-1] for line in log.read_text().split("\n")[:-1]]

    def _write(self, name, body, record=True):
        log = shlex.quote(str(self.calls_dir / name))
        recorder = f"{{ (( $# )) && printf '%s\\x1f' \"$@\"; printf '\\n'; }} >> {log}\n" if record else ""
        path = self.fakes / name
        path.write_text(f"#!/usr/bin/env bash\n{recorder}{body}")
        path.chmod(0o755)
```

- [ ] **Step 7: Run to verify the sandbox tests pass**

Run: `uv run --locked pytest tests/test_sandbox.py -v`
Expected: 9 passed.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock .gitignore tests/repo.py tests/conftest.py tests/test_sandbox.py
git commit -m "test: pytest project with a sandbox for running the scripts in isolation"
```

---

### Task 2: First subject tests: `gh-latest` and `zsh-scratch`

**Files:**
- Create: `tests/bin/test_gh_latest.py`, `tests/functions/test_zsh_scratch.py`

**Interfaces:**
- Consumes: fixtures `run`, `fake_bin`, `calls`, `zsh`, `sandbox` from Task 1.

- [ ] **Step 1: Write `tests/bin/test_gh_latest.py`**

```python
class TestGhLatest:
    def test_should_print_the_latest_tag(self, run, fake_bin, calls):
        fake_bin("curl", stdout='{"tag_name":"v2.101.0"}')
        result = run("gh-latest", "cli/cli")
        assert result.returncode == 0
        assert result.stdout == "v2.101.0\n"
        assert calls("curl") == [["-LfsS", "https://api.github.com/repos/cli/cli/releases/latest"]]

    class TestOnUnknownOption:
        def test_should_exit_2_and_name_the_option(self, run):
            result = run("gh-latest", "--nope")
            assert result.returncode == 2
            assert result.stderr == "gh-latest: unknown option: --nope\nSee 'gh-latest --help'\n"

    class TestOnMissingArgument:
        def test_should_print_the_help_to_stderr_and_exit_2(self, run):
            result = run("gh-latest")
            assert result.returncode == 2
            assert result.stderr.startswith("Purpose:")
            assert result.stdout == ""

    class TestOnMalformedRepository:
        def test_should_exit_2_and_say_what_was_expected(self, run):
            result = run("gh-latest", "nodash")
            assert result.returncode == 2
            assert "not an <owner>/<repo>: nodash" in result.stderr
```

- [ ] **Step 2: Write `tests/functions/test_zsh_scratch.py`**

```python
TARGET = ".config/zsh/conf.d/90-scratch.zsh"


class TestZshScratch:
    def test_should_open_the_source_in_the_editor_and_apply_the_target(self, zsh, fake_bin, calls, sandbox):
        fake_bin("chezmoi", script='[[ $1 == source-path ]] && echo /src/90-scratch.zsh\nexit 0\n')
        fake_bin("editor")
        sandbox.env["EDITOR"] = "editor"
        result = zsh("zsh-scratch", function="zsh-scratch")
        assert result.returncode == 0
        assert calls("editor") == [["/src/90-scratch.zsh"]]
        assert calls("chezmoi") == [["source-path", f"{sandbox.home}/{TARGET}"],
                                    ["apply", f"{sandbox.home}/{TARGET}"]]

    class TestOnUnmanagedTarget:
        def test_should_return_1_without_opening_the_editor(self, zsh, fake_bin, calls, sandbox):
            fake_bin("chezmoi", exit_code=1)
            fake_bin("editor")
            sandbox.env["EDITOR"] = "editor"
            result = zsh("zsh-scratch", function="zsh-scratch")
            assert result.returncode == 1
            assert calls("editor") == []
```

- [ ] **Step 3: Run both files**

Run: `uv run --locked pytest tests/bin tests/functions -v`
Expected: 6 passed. If `jq` is missing from the sandbox PATH on this machine, the first test fails with exit 127 from the script; `jq` must be in `/opt/homebrew/bin` (macOS) or `/usr/bin` (Linux). Install it rather than widening `SYSTEM_PATH`.

- [ ] **Step 4: Commit**

```bash
git add tests/bin/test_gh_latest.py tests/functions/test_zsh_scratch.py
git commit -m "test(bin): cover gh-latest and the zsh-scratch function"
```

---

### Task 3: Makefile with `lint` and `unit`, and a clean shellcheck baseline

**Files:**
- Modify: `Makefile` (rewrite), `home/dot_local/exact_bin/executable_box:39`, `home/dot_local/exact_bin/executable_gcloud-login:54,107,143,169`, `home/private_dot_claude/executable_statusline:1-2,29,243,258`

**Interfaces:**
- Produces: targets `ci`, `lint`, `lint-shell`, `lint-zsh`, `unit`, `integration`, `integration-native`, `image`, `run`, `vnc`, `stop`, `clean`; variable `CONTAINER_ENGINE` (default `podman`). `integration*` and `image` targets reference files that later tasks create.

- [ ] **Step 1: Replace `Makefile`**

```make
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

CONTAINER_ENGINE ?= podman
IMAGE := dotfiles-test
CONTAINER_NAME := dotfiles-test
VNC_PORT := 5901

.PHONY: ci lint lint-shell lint-zsh unit integration integration-native image run vnc stop clean

ci: lint unit integration

lint: lint-shell lint-zsh

# Every tracked file with a bash shebang or a .sh/.bash suffix. Templates are not shell before
# rendering, and quick-access/ holds symlinks to files that are already covered.
lint-shell:
	git ls-files -z -- ':!quick-access' ':!*.tmpl' | while IFS= read -r -d '' file; do \
	  if [[ $$file == *.sh || $$file == *.bash ]] || head -n 1 "$$file" | grep -qE '^#!.*bash'; then printf '%s\0' "$$file"; fi; \
	done | xargs -0 shellcheck

lint-zsh:
	git ls-files -z -- 'home/**/*.zsh' | xargs -0 -n 1 zsh -n

unit:
	uv run --locked pytest -m "not integration"
	node --test tests/

integration:
	uv run --locked pytest tests/integration/test_apply_container.py

integration-native:
	uv run --locked pytest tests/integration/test_apply_native.py

image:
	$(CONTAINER_ENGINE) build --target base -t $(IMAGE):base .

run:
	$(CONTAINER_ENGINE) build --target vnc -t $(IMAGE):vnc .
	$(CONTAINER_ENGINE) run -d --rm \
		--name $(CONTAINER_NAME) \
		-p $(VNC_PORT):5901 \
		-v $(CURDIR):/dotfiles:ro \
		$(IMAGE):vnc vnc

vnc:
	@echo "Connecting to VNC on localhost:$(VNC_PORT)..."
	open vnc://localhost:$(VNC_PORT) 2>/dev/null || \
		echo "Open a VNC viewer and connect to localhost:$(VNC_PORT)"

stop:
	$(CONTAINER_ENGINE) stop $(CONTAINER_NAME) 2>/dev/null || true

clean: stop
	$(CONTAINER_ENGINE) rmi $(IMAGE):base $(IMAGE):vnc 2>/dev/null || true
```

- [ ] **Step 2: Run lint to see the baseline fail**

Run: `make lint`
Expected: `lint-zsh` clean; `lint-shell` reports 11 findings in `executable_box`, `executable_gcloud-login`, `executable_statusline` and exits non-zero. The path with a space under `home/Library/` is handled (no "does not exist" error).

- [ ] **Step 3: Fix the findings without changing behaviour**

`executable_box:39`: `default_shell=sh` becomes `default_shell='sh'` (SC2209: `sh` is a command name).

`executable_gcloud-login:54`: `mode=admin && shift` becomes `mode='admin' && shift`; line 169: `profile=admin;` becomes `profile='admin';` (SC2209: `admin` is an SCCS command on macOS).

`executable_gcloud-login:106-108`, SC2012, keep `ls` and state why:

```bash
chromium_bin() {
  # shellcheck disable=SC2012  # the build directories are ours and newline-free; ls -d sorts them
  ls -d "$CACHE_DIR"/chromium/*-"$CHROMIUM_BUILD"/chrome-mac/Chromium.app/Contents/MacOS/Chromium 2>/dev/null | head -1
}
```

`executable_gcloud-login:143`, SC2329:

```bash
# shellcheck disable=SC2329  # invoked by the EXIT trap below
cleanup() {
```

`executable_statusline`, SC1003 three times: the `\\` in `'\033]8;;%s\033\\%s\033]8;;\033\\'` is the OSC 8 string terminator. Add one file-level directive on line 2, right after the shebang:

```bash
#!/usr/bin/env bash
# shellcheck disable=SC1003  # printf '\\' is the OSC 8 string terminator (ESC \), not an escaped quote
```

`executable_statusline:29`, SC2010, same semantics (case-insensitive "nerd" anywhere in a font file name):

```bash
    if [[ -n $(find ~/Library/Fonts /Library/Fonts -maxdepth 1 -iname '*nerd*' -print -quit 2>/dev/null) ]]; then
```

`executable_statusline:243` and `:258`, SC2155:

```bash
  local out
  out="${style}$(icon "$IC_CLOCK" "$IC_CLOCK_FB") ${pct}%"
```

```bash
  local out
  out="${style}$(icon "$IC_CAL" "$IC_CAL_FB") ${pct}%"
```

- [ ] **Step 4: Run lint and unit**

Run: `make lint unit`
Expected: shellcheck exits 0, `zsh -n` exits 0, pytest reports 15 passed, `node --test` reports the driver tests (they skip without Chromium, which Task 9 changes for CI).

- [ ] **Step 5: Run the statusline harness once by hand**

Run: `home/private_dot_claude/executable_statusline-test`
Expected: three rendered status lines, no error. This is the only check the statusline has until PR 2 converts the harness.

- [ ] **Step 6: Commit**

```bash
git add Makefile home/dot_local/exact_bin/executable_box home/dot_local/exact_bin/executable_gcloud-login home/private_dot_claude/executable_statusline
git commit -m "build: make lint and unit targets with a clean shellcheck baseline"
```

---

### Task 4: Conventions test and the baseline allowlist

**Files:**
- Create: `tests/test_conventions.py`, `tests/untested.toml`

**Interfaces:**
- Consumes: `repo.BIN_SOURCE`, `repo.FUNCTIONS_SOURCE`, `repo.CONF_D_SOURCE`, `repo.ROOT`.
- Produces: the allowlist format `[bin]`, `[functions]`, `[conf_d]` with `key = "reason"`.

- [ ] **Step 1: Write `tests/test_conventions.py`**

```python
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pytest

from repo import BIN_SOURCE, CONF_D_SOURCE, FUNCTIONS_SOURCE, ROOT

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
    for source in sorted(BIN_SOURCE.iterdir()):
        if source.name.startswith("executable_"):
            key = source.name.removeprefix("executable_")
            found.append(Subject("bin", key, source, (
                TESTS / "bin" / f"test_{key.replace('-', '_')}.py",
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
```

- [ ] **Step 2: Create an empty allowlist and run to see the failures**

`tests/untested.toml`:

```toml
[bin]

[functions]

[conf_d]
```

Run: `uv run --locked pytest tests/test_conventions.py -q`
Expected: 29 `bin/...` failures and 8 `conf_d/...` failures; `bin/gh-latest`, `bin/gcloud-login-driver` and `functions/zsh-scratch` pass.

- [ ] **Step 3: Write the baseline**

`tests/untested.toml`:

```toml
# Files without a test, each with its reason. A "legacy" entry goes when the file's behaviour is
# next changed: that change adds the test and removes the line. tests/test_conventions.py fails on
# a missing entry, a stale entry and an empty reason.

[bin]
ansi-test = "legacy: test when next touched"
box = "legacy: test when next touched"
cert-get = "legacy: test when next touched"
cert-print = "legacy: test when next touched"
cleanup = "legacy: test when next touched"
docker = "legacy: test when next touched"
dscleanup = "legacy: test when next touched"
explain = "legacy: test when next touched"
flushdns = "legacy: test when next touched"
gcloud-login = "legacy: test when next touched"
gcloud-login-browser = "legacy: test when next touched"
grepr = "legacy: test when next touched"
idea = "legacy: test when next touched"
idea-wait = "legacy: test when next touched"
intellij-workspace-fix = "legacy: test when next touched"
killport = "legacy: test when next touched"
known-hosts-fix = "legacy: test when next touched"
mir = "legacy: test when next touched"
notify = "legacy: test when next touched"
omlx = "legacy: test when next touched"
op-agent = "legacy: test when next touched"
pbcopy-dir = "legacy: test when next touched"
pbpaste-dir = "legacy: test when next touched"
pick-port = "legacy: test when next touched"
print-port = "legacy: test when next touched"
serve = "legacy: test when next touched"
serve-live = "legacy: test when next touched"
timeout = "legacy: test when next touched"
upgrade-all = "legacy: test when next touched"

[functions]

[conf_d]
08-print = "legacy: test when next touched"
10-glab = "legacy: test when next touched"
10-gradle = "legacy: test when next touched"
10-granted = "legacy: test when next touched"
10-italics = "legacy: test when next touched"
10-nvm = "legacy: test when next touched"
20-claude = "legacy: test when next touched"
90-scratch = "legacy: test when next touched"
```

If Step 2 reported a subject not in this list (the tree moved on), add it with the same reason.

- [ ] **Step 4: Run to verify the baseline passes, then prove the stale check**

Run: `uv run --locked pytest tests/test_conventions.py -q`
Expected: all passed.

Temporarily add `gh-latest = "x"` under `[bin]`, run again, expect one failure `tested by tests/bin/test_gh_latest.py; remove the entry`, then remove the line.

- [ ] **Step 5: Commit**

```bash
git add tests/test_conventions.py tests/untested.toml
git commit -m "test: require a test or a listed reason for every script, function and module"
```

---

### Task 5: Fake secret CLIs

**Files:**
- Create: `tests/shims/op`, `tests/shims/keepassxc-cli` (both `chmod 755`), `tests/test_shims.py`

**Interfaces:**
- Produces: `tests/shims/` mounted or prepended to `PATH` by Tasks 6 to 8. `op --version` → `2.30.0`; `op read [--no-newline] op://<vault>/<item>/<field>` → `fake:<item>/<field>`. `keepassxc-cli --version` → `2.7.9`; `keepassxc-cli show [opts] <db> <entry>` → `Title/UserName/Password/URL/Notes` block with `Password: fake:<entry>`; `show ... --attributes <attr>` → `fake:<entry>/<attr>`; `attachment-export ...` → `fake-attachment`. Anything else: exit 1, `<name>: unsupported in tests: <args>` on stderr.

- [ ] **Step 1: Write `tests/test_shims.py`**

```python
import subprocess

from repo import SHIMS


class TestOp:
    def test_should_report_a_version(self):
        result = op("--version")
        assert result.stdout == "2.30.0\n"

    class TestRead:
        def test_should_print_a_placeholder_for_the_item_and_field(self):
            result = op("read", "op://Employee/GitLab Token/credential")
            assert result.stdout == "fake:GitLab Token/credential\n"

        def test_should_omit_the_newline_on_request(self):
            result = op("read", "--no-newline", "op://Employee/GitLab Token/credential")
            assert result.stdout == "fake:GitLab Token/credential"

    class TestOnAnythingElse:
        def test_should_exit_1_and_say_so(self):
            result = op("item", "get", "x")
            assert result.returncode == 1
            assert result.stderr == "op: unsupported in tests: item get x\n"


class TestKeepassxcCli:
    def test_should_report_a_version(self):
        result = keepassxc_cli("--version")
        assert result.stdout == "2.7.9\n"

    class TestShow:
        def test_should_print_the_entry_with_a_placeholder_password(self):
            result = keepassxc_cli("show", "/vault.kdbx", "--quiet", "--show-protected", "CONTEXT7_API_KEY",
                                   stdin="dummy-password\n")
            assert result.stdout == ("Title: CONTEXT7_API_KEY\nUserName: fake-user\n"
                                     "Password: fake:CONTEXT7_API_KEY\nURL: \nNotes: \n")

        def test_should_print_a_placeholder_for_a_requested_attribute(self):
            result = keepassxc_cli("show", "--key-file", "/k", "/vault.kdbx", "example.com",
                                   "--attributes", "host-name", "--quiet", "--show-protected")
            assert result.stdout == "fake:example.com/host-name\n"

        def test_should_not_block_without_a_password_on_stdin(self):
            result = keepassxc_cli("show", "/vault.kdbx", "--quiet", "--show-protected", "x")
            assert result.returncode == 0

    class TestOnAnythingElse:
        def test_should_exit_1_and_say_so(self):
            result = keepassxc_cli("db-info", "/vault.kdbx")
            assert result.returncode == 1
            assert result.stderr == "keepassxc-cli: unsupported in tests: db-info /vault.kdbx\n"


def op(*args, stdin=None):
    return shim("op", *args, stdin=stdin)


def keepassxc_cli(*args, stdin=None):
    return shim("keepassxc-cli", *args, stdin=stdin)


def shim(name, *args, stdin):
    options = {"input": stdin} if stdin is not None else {"stdin": subprocess.DEVNULL}
    return subprocess.run([str(SHIMS / name), *args], capture_output=True, text=True, timeout=5, **options)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --locked pytest tests/test_shims.py -q`
Expected: 9 errors, `FileNotFoundError`.

- [ ] **Step 3: Write `tests/shims/op`**

```bash
#!/usr/bin/env bash
# Purpose: Stand in for the 1Password CLI in tests; answers the calls chezmoi makes.
# Usage:   op --version | op read [--no-newline] op://<vault>/<item>/<field>
#
# Examples:
#   op read op://Employee/GitLab Token/credential   # fake:GitLab Token/credential

set -euo pipefail

case ${1:-} in
  --version) echo 2.30.0 ;;
  read)
    shift
    newline=1
    [[ ${1:-} == --no-newline ]] && { newline=0; shift; }
    ref=${1:?op read: missing reference}
    item=${ref#op://*/}
    item=${item%/*}
    printf 'fake:%s/%s' "$item" "${ref##*/}"
    (( newline )) && printf '\n'
    ;;
  *) printf 'op: unsupported in tests: %s\n' "$*" >&2; exit 1 ;;
esac
```

- [ ] **Step 4: Write `tests/shims/keepassxc-cli`**

```bash
#!/usr/bin/env bash
# Purpose: Stand in for keepassxc-cli in tests; answers the calls chezmoi makes and ignores the password on stdin.
# Usage:   keepassxc-cli --version
#          keepassxc-cli show [--key-file <f>] <database> [--attributes <name>] [--quiet] [--show-protected] <entry>
#          keepassxc-cli attachment-export <args>...
#
# Examples:
#   keepassxc-cli show vault.kdbx --quiet --show-protected CONTEXT7_API_KEY   # Password: fake:CONTEXT7_API_KEY

set -euo pipefail

# chezmoi pipes the database password in; a terminal would block here.
[[ -t 0 ]] || cat >/dev/null

case ${1:-} in
  --version) echo 2.7.9 ;;
  show)
    shift
    positionals=()
    attribute=''
    while (( $# )); do
      case $1 in
        --attributes) attribute=$2; shift 2 ;;
        --key-file)   shift 2 ;;
        --*)          shift ;;
        *)            positionals+=("$1"); shift ;;
      esac
    done
    entry=${positionals[1]:?keepassxc-cli show: missing entry}
    if [[ -n $attribute ]]; then
      printf 'fake:%s/%s\n' "$entry" "$attribute"
    else
      printf 'Title: %s\nUserName: fake-user\nPassword: fake:%s\nURL: \nNotes: \n' "$entry" "$entry"
    fi
    ;;
  attachment-export) echo fake-attachment ;;
  *) printf 'keepassxc-cli: unsupported in tests: %s\n' "$*" >&2; exit 1 ;;
esac
```

Run: `chmod 755 tests/shims/op tests/shims/keepassxc-cli`

- [ ] **Step 5: Run the shim tests and lint**

Run: `uv run --locked pytest tests/test_shims.py -v && make lint-shell`
Expected: 9 passed; shellcheck clean (the shims have bash shebangs, so `lint-shell` picks them up).

- [ ] **Step 6: Commit**

```bash
git add tests/shims/op tests/shims/keepassxc-cli tests/test_shims.py
git commit -m "test: fake op and keepassxc-cli for applying every context without a vault"
```

---

### Task 6: Two-stage Containerfile and the entrypoint contract

**Files:**
- Modify: `Containerfile` (rewrite), `entrypoint.sh` (rewrite)

**Interfaces:**
- Produces: image stages `base` and `vnc`. Entrypoint reads `DOTFILES_COMPANY`, prepends `/opt/shims` to `PATH` when present, sends everything `chezmoi init --apply` prints to stdout, leaves stdin to chezmoi (one password line) and then to zsh, and `exec`s `zsh -li "$@"`.

- [ ] **Step 1: Replace `Containerfile`**

```dockerfile
# base: what `make integration` runs. One-shot: the entrypoint applies the dotfiles and exits,
# so there is no service contract to probe (Podman warns that OCI images drop the directive).
FROM fedora:latest AS base

RUN dnf install -y zsh git curl jq findutils procps-ng \
    && dnf clean all

RUN sh -c "$(curl -fsLS get.chezmoi.io)" -- -b /usr/local/bin

RUN curl --proto '=https' -fLsS https://rossmacarthur.github.io/install/crate.sh \
    | bash -s -- --repo rossmacarthur/sheldon --to /usr/local/bin

RUN curl -sS https://starship.rs/install.sh | sh -s -- --yes

RUN curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh

RUN chsh -s /bin/zsh root

HEALTHCHECK NONE

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# vnc: manual inspection of the applied shell in Ghostty; `make run` and `make vnc`.
FROM base AS vnc

RUN dnf install -y tigervnc-server fluxbox xterm \
    && dnf clean all

# Ghostty via the COPR the Ghostty docs recommend (https://ghostty.org/docs/install/binary#fedora).
RUN dnf install -y 'dnf-command(copr)' \
    && dnf copr enable -y scottames/ghostty \
    && dnf install -y ghostty \
    && dnf clean all

RUN mkdir -p /root/.vnc \
    && echo "password" | vncpasswd -f > /root/.vnc/passwd \
    && chmod 600 /root/.vnc/passwd

EXPOSE 5901
```

- [ ] **Step 2: Replace `entrypoint.sh`**

```bash
#!/usr/bin/env bash
# Purpose: Apply the mounted dotfiles for one context, then start zsh or the VNC inspection session.
# Usage:   entrypoint.sh [vnc | <zsh arguments>...]
#
# Environment:
#   DOTFILES_COMPANY   Context written to the chezmoi config: "", "bkahlert" or "ista" (default: "").
#
# The apply's output goes to stdout so that stderr carries only what the zsh startup prints; the
# integration test asserts that it stays empty. Stdin is left untouched: chezmoi reads one line as
# the KeePassXC password when a template needs it. Fakes for op and keepassxc-cli are expected
# under /opt/shims.

set -euo pipefail

[[ -d /opt/shims ]] && export PATH="/opt/shims:$PATH"

if [[ -d /dotfiles/home ]]; then
  mkdir -p ~/.config/chezmoi
  cat > ~/.config/chezmoi/chezmoi.toml <<TOML
[data]
    email = "test@example.com"
    name = "Test User"
    company = "${DOTFILES_COMPANY:-}"
TOML
  chezmoi init --apply --no-tty --source /dotfiles/home 2>&1
fi

if [[ ${1:-} == vnc ]]; then
  vncserver :1 -geometry 1920x1080 -depth 24 -SecurityTypes None
  DISPLAY=:1 fluxbox &
  echo "VNC server started on port 5901"
  exec tail -f /root/.vnc/*:1.log
else
  exec zsh -li "$@"
fi
```

- [ ] **Step 3: Build and smoke-run the base image**

Run:

```bash
make image
printf 'dummy-password\n' | podman run --rm -i -e TERM=xterm-256color -e DOTFILES_COMPANY= \
  -v "$PWD":/dotfiles:ro -v "$PWD"/tests/shims:/opt/shims:ro dotfiles-test:base -c 'echo shell-ok'
```

Expected: apply output, then `shell-ok`, exit 0. Note anything on stderr; Task 7 asserts on it.

- [ ] **Step 4: Lint and commit**

Run: `make lint-shell`
Expected: clean.

```bash
git add Containerfile entrypoint.sh
git commit -m "build(container): base and vnc stages, apply per context with fake secret CLIs"
```

---

### Task 7: Container integration test, and a silent startup in every context

**Files:**
- Create: `tests/integration/test_apply_container.py`
- Modify: whichever `conf.d` modules or templates print on a fresh home (found by running the test)

**Interfaces:**
- Consumes: `repo.ROOT`, `repo.CONTEXTS`, `repo.SHIMS`; image `dotfiles-test:base`; env `CONTAINER_ENGINE`.

- [ ] **Step 1: Write `tests/integration/test_apply_container.py`**

```python
import os
import shutil
import subprocess

import pytest

from repo import CONTEXTS, ROOT, SHIMS

pytestmark = pytest.mark.integration

ENGINE = os.environ.get("CONTAINER_ENGINE", "podman")
IMAGE = "dotfiles-test:base"


@pytest.fixture(scope="module")
def image():
    if shutil.which(ENGINE) is None:
        pytest.fail(f"{ENGINE} not found; install it or point CONTAINER_ENGINE at docker")
    subprocess.run([ENGINE, "build", "--target", "base", "-t", IMAGE, str(ROOT)], check=True, timeout=1200)
    return IMAGE


class TestApplyInContainer:
    @pytest.mark.parametrize("company", CONTEXTS, ids=lambda c: c or "none")
    def test_should_apply_and_start_a_silent_interactive_login_shell(self, image, company):
        result = subprocess.run(
            [ENGINE, "run", "--rm", "-i",
             "-e", "TERM=xterm-256color", "-e", f"DOTFILES_COMPANY={company}",
             "-v", f"{ROOT}:/dotfiles:ro", "-v", f"{SHIMS}:/opt/shims:ro",
             image, "-c", "true"],
            input="dummy-password\n", capture_output=True, text=True, timeout=900)
        assert result.returncode == 0, report("apply or shell failed", result)
        assert result.stderr == "", report("zsh startup wrote to stderr", result)


def report(headline, result):
    return f"{headline} (exit {result.returncode})\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
```

- [ ] **Step 2: Run it**

Run: `make integration`
Expected on the first run: the `none` context passes (it is what `make validate` covered); `bkahlert` and `ista` may fail. Read each failure's `--- stderr ---` block.

- [ ] **Step 3: Fix each stderr line at its source**

For every line, identify the module from the message and apply the matching rule. Do not blanket-redirect a module's stderr to `/dev/null`; #23 is what that costs.

- A tool is missing (`command not found`, `no such file`): the module returns early when its tool is absent, the way `07-plugins.zsh` does:
  ```zsh
  command -v <tool> &>/dev/null || return 0
  ```
- A module needs a credential or agent that a fresh machine lacks (an SSH agent, a token file): it checks that precondition and returns quietly when unmet. `exact_ista/10-dev-chapter.zsh` pulls from GitLab at startup; without `SSH_AUTH_SOCK` it must not attempt the pull.
- A template fails to render in one context: fix the template or gate the file in `.chezmoiignore` for that context, following the existing entries there.
- An apply-time script fails: guard it on its tool as `run_onchange_after_setup-mcp-servers.sh` does.

Re-run `make integration` after each fix until all three contexts pass. Keep these fixes in their own commits by area, for example:

```bash
git add home/private_dot_config/zsh/exact_conf.d/exact_ista/10-dev-chapter.zsh
git commit -m "fix(zsh): skip the dev-chapter pull when no SSH agent is available"
```

- [ ] **Step 4: Confirm the gate bites**

Append `echo noisy >&2` to `home/private_dot_config/zsh/exact_conf.d/01-options.zsh`, run `make integration`, expect three failures whose stderr block reads `noisy`, then `git checkout -- home/private_dot_config/zsh/exact_conf.d/01-options.zsh`.

- [ ] **Step 5: Commit the test**

```bash
git add tests/integration/test_apply_container.py
git commit -m "test(container): apply every context and require a silent zsh startup"
```

---

### Task 8: Native macOS integration test

**Files:**
- Create: `tests/integration/test_apply_native.py`
- Possibly modify: `home/.chezmoiscripts/run_onchange_after_dump-ssh-from-kdbx.tmpl:26`

**Interfaces:**
- Consumes: `repo.ROOT`, `repo.HOME_SOURCE`, `repo.CONTEXTS`, `repo.SHIMS`, `repo.SYSTEM_PATH`, `repo.isolated_env`.

- [ ] **Step 1: Write `tests/integration/test_apply_native.py`**

```python
import json
import shutil
import subprocess
import sys

import pytest

from repo import CONTEXTS, HOME_SOURCE, SHIMS, SYSTEM_PATH, isolated_env

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(sys.platform != "darwin", reason="native apply targets macOS"),
]

CORE_TOOLS = ("chezmoi", "sheldon", "starship", "zoxide")
CHEZMOI_CONFIG = '[data]\n    email = "test@example.com"\n    name = "Test User"\n    company = "{company}"\n'


@pytest.fixture(scope="module")
def core_tools():
    missing = [tool for tool in CORE_TOOLS if shutil.which(tool) is None]
    if missing:
        pytest.fail(f"missing on PATH: {' '.join(missing)}; brew install {' '.join(missing)}")


class TestApplyNatively:
    @pytest.mark.parametrize("company", CONTEXTS, ids=lambda c: c or "none")
    def test_should_apply_and_start_a_silent_interactive_login_shell(self, core_tools, tmp_path, company):
        home = tmp_path / "home"
        env = isolated_env(home, [str(SHIMS), *SYSTEM_PATH])
        seen = chezmoi("data", "--format", "json", env=env)
        assert json.loads(seen.stdout)["chezmoi"]["homeDir"] == str(home), "chezmoi does not see the temp home; refusing to apply"

        (home / ".config" / "chezmoi").mkdir(parents=True)
        (home / ".config" / "chezmoi" / "chezmoi.toml").write_text(CHEZMOI_CONFIG.format(company=company))
        applied = chezmoi("init", "--apply", "--exclude=scripts", "--no-tty", env=env, stdin="dummy-password\n")
        assert applied.returncode == 0, report("apply failed", applied)
        locked = subprocess.run(["sheldon", "lock"], env=env, capture_output=True, text=True, timeout=600)
        assert locked.returncode == 0, report("sheldon lock failed", locked)

        shell = subprocess.run(["zsh", "-li", "-c", "true"], env=env, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=120)
        assert shell.returncode == 0, report("shell failed", shell)
        assert shell.stderr == "", report("zsh startup wrote to stderr", shell)


def chezmoi(*args, env, stdin=None):
    return subprocess.run(["chezmoi", *args, "--source", str(HOME_SOURCE)], env=env, input=stdin,
                          capture_output=True, text=True, timeout=600)


def report(headline, result):
    return f"{headline} (exit {result.returncode})\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
```

`sheldon lock` stands in for the excluded `run_onchange_after_sheldon-lock.sh.tmpl`; without it `sheldon source` locks during the first shell start and prints progress on stderr.

- [ ] **Step 2: Run it on this Mac**

Run: `make integration-native`
Expected: three passes, or failures to fix as in Task 7 Step 3. Two known candidates:

- `shasum: ... choam.kdbx: No such file or directory` while applying means chezmoi renders script templates even when scripts are excluded. Fix the template so a missing vault does not abort applying (a fresh Mac before iCloud sync hits the same path). Replace line 26 of `run_onchange_after_dump-ssh-from-kdbx.tmpl`:
  ```
  {{- $kdbx := joinPath .chezmoi.homeDir "Library/Mobile Documents/com~apple~CloudDocs/Vault/choam.kdbx" }}
  # kdbx-hash: {{ if stat $kdbx }}{{ output "shasum" "-a" "256" $kdbx }}{{ else }}vault not present{{ end }}
  ```
  This changes the rendered script once on the user's machines, so the dump re-runs on their next `chezmoi apply`; say so in the commit body.
- A darwin-only module that prints when its Homebrew tool is absent: same guard as Task 7.

Confirm nothing escaped: `ls -la ~/.config/chezmoi ~/.local/share/chezmoi 2>&1 | head` must show no new files with the test's timestamp, and `chezmoi status` in the real home must be unchanged from before the run.

- [ ] **Step 3: Confirm the skip reason off macOS**

Run: `uv run --locked pytest tests/integration/test_apply_native.py --co -q`
Expected: three tests collected. The skip itself shows in the Linux `checks` job later: `make unit` runs `-m "not integration"`, so the file is deselected there, and a direct run on Linux would report `native apply targets macOS` under `-ra`.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_apply_native.py
git commit -m "test(macos): apply every context into a temp home and require a silent zsh startup"
```

(Plus a separate `fix(chezmoi): ...` commit if Step 2 changed the dump-ssh template.)

---

### Task 9: Driver test finds Chrome through `CHROMIUM_BIN` and never skips on CI

**Files:**
- Modify: `tests/gcloud-login-driver.test.js:14-26`

- [ ] **Step 1: Replace the Chromium lookup**

Replace lines 24 to 26 (`const CHROMIUM = findChromium();` and the `describe(` opener's skip clause) so that:

```js
const CHROMIUM = process.env.CHROMIUM_BIN || findChromium();
if (!CHROMIUM && process.env.CI) {
  throw new Error('no Chromium found; set CHROMIUM_BIN (the driver test must not skip on CI)');
}

describe('gcloud-login-driver', { skip: CHROMIUM ? false : 'Chromium not installed (run gcloud-login once, or set CHROMIUM_BIN)' }, () => {
  // ... the existing tests and helpers stay as they are
});
```

- [ ] **Step 2: Run three ways**

```bash
node --test tests/                                                                        # local cache lookup, as before
CHROMIUM_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" node --test tests/   # explicit binary
CI=1 CHROMIUM_BIN=/nonexistent node --test tests/                                         # must fail, not skip
```

Expected: the first two pass (4 tests), the third exits non-zero with the "no Chromium found" message. If Google Chrome is not installed locally, use the cached Chromium path printed by `ls ~/.cache/gcloud-login/chromium/*/chrome-mac/Chromium.app/Contents/MacOS/Chromium` for the second command.

- [ ] **Step 3: Commit**

```bash
git add tests/gcloud-login-driver.test.js
git commit -m "test(gcloud-login): take the browser from CHROMIUM_BIN and fail instead of skipping on CI"
```

---

### Task 10: Workflow, Dependabot and workflow lint

**Files:**
- Create: `.github/workflows/ci.yml`, `.github/dependabot.yml`
- Modify: `Makefile` (`lint` gains `lint-workflows`)

**Interfaces:**
- Produces: the check context `ci` that Task 12 makes required.

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: ci

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  schedule:
    - cron: '17 5 * * 1'  # weekly: the image and the macOS job install the latest chezmoi, sheldon, starship, zoxide
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  checks:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7 # v10.2.0
      - name: Install zsh and actionlint
        run: |
          sudo apt-get update
          sudo apt-get install -y --no-install-recommends zsh
          curl -fsSL https://raw.githubusercontent.com/rhysd/actionlint/v1.7.12/scripts/download-actionlint.bash | sudo bash -s -- 1.7.12 /usr/local/bin
      - run: make lint unit
        env:
          CHROMIUM_BIN: /usr/bin/google-chrome

  integration:
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7 # v10.2.0
      - run: make integration

  macos:
    runs-on: macos-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7 # v10.2.0
      - run: brew install chezmoi sheldon starship zoxide
      - run: make unit integration-native
        env:
          CHROMIUM_BIN: /Applications/Google Chrome.app/Contents/MacOS/Google Chrome

  ci:
    if: always()
    needs: [checks, integration, macos]
    runs-on: ubuntu-24.04
    timeout-minutes: 2
    steps:
      - name: Require every job to succeed
        env:
          RESULTS: ${{ join(needs.*.result, ' ') }}
        run: |
          for result in $RESULTS; do
            [[ $result == success ]] || { echo "job results: $RESULTS"; exit 1; }
          done
```

- [ ] **Step 2: Create `.github/dependabot.yml`**

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    cooldown:
      default-days: 3
  - package-ecosystem: uv
    directory: /
    schedule:
      interval: weekly
    cooldown:
      default-days: 3
```

- [ ] **Step 3: Add `lint-workflows` to the Makefile**

Change `lint: lint-shell lint-zsh` to `lint: lint-shell lint-zsh lint-workflows`, add `lint-workflows` to `.PHONY`, and add the target after `lint-zsh`:

```make
lint-workflows:
	actionlint
	uvx zizmor==1.30.1 .github/workflows
```

- [ ] **Step 4: Run lint**

Run: `make lint`
Expected: no output from actionlint, `No findings` from zizmor, exit 0. The `run:` blocks are shellchecked by actionlint as well. Fix any finding in the workflow rather than suppressing it.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/ci.yml .github/dependabot.yml Makefile
git commit -m "ci: lint, unit, container and macOS jobs behind one required check"
```

---

### Task 11: Documentation and the Brewfile

**Files:**
- Modify: `AGENTS.md`, `quick-access/README.md`, `README.md`, `home/private_dot_config/exact_agents/exact_rules/testing.md`, `home/.chezmoiscripts/run_once_before_01-install-packages.sh`

- [ ] **Step 1: AGENTS.md, replace the final `## Testing` section**

Replace the block from `## Testing` to the end of the file with:

````markdown
## Testing

```sh
make lint                # shellcheck, zsh -n, actionlint + zizmor
make unit                # pytest (tests/bin, tests/functions, tests/zsh, conventions, shims) + node driver test
make integration         # apply all three contexts in a Fedora container, require a silent zsh (needs Podman)
make integration-native  # same, into a temp HOME on this Mac; what CI's macOS job runs. Opt-in locally.
make ci                  # lint unit integration
chezmoi diff             # preview changes to $HOME
chezmoi apply -n         # dry run
```

CI runs the same targets on every pull request and on `main`; the `ci` check is required to merge.

### Where a test lives

| Subject | Test |
|---|---|
| `bin/executable_<name>` | `tests/bin/test_<name>.py` (hyphens as underscores) |
| `functions/<name>` | `tests/functions/test_<name>.py` |
| `conf.d/NN-<name>.zsh` that defines a function | `tests/zsh/test_<name>.py`; `conf.d/exact_ista/...` under `tests/zsh/ista/` |
| every `conf.d` module | loaded by the integration legs; a module that prints on a fresh machine fails them |

`tests/test_conventions.py` fails when a script, function or function-defining module has neither a test nor an entry in `tests/untested.toml`, and when an entry is stale. A `"legacy: ..."` entry goes when the file's **behaviour** is next changed: that change adds the test and removes the line. Lint or formatting edits do not trigger it. A file with no logic of its own (a wrapper around `open`, `osascript`, `pbcopy`) keeps a permanent entry with that reason.

### Writing a unit test

Fixtures in [tests/conftest.py](tests/conftest.py) run the real script or function:

- `run("name", *args)` runs a `bin/` script by its target name in a sandbox: temp `HOME`, `XDG_*` and `TMPDIR`; `PATH` is fakes first, then the other `bin/` scripts, then system directories only.
- `fake_bin("tool", stdout=..., exit_code=..., script=...)` puts a fake on `PATH`; `calls("tool")` returns its recorded argument lists.
- `zsh("snippet", function="name")` or `zsh("snippet", modules=["08-print.zsh"])` runs `zsh -f` with the source tree's functions and modules.
- Network, vault and system-state tools (`op`, `gh`, `gcloud`, `curl`, `brew`, `open`, `osascript`, `launchctl`, `defaults`, `sudo`, ...) are guarded: calling one unfaked fails with exit 127. Fake what the subject needs; coreutils, `awk`, `sed`, `jq` are real.

Classes nest as [testing.md](home/private_dot_config/exact_agents/exact_rules/testing.md) asks: `TestGhLatest` > `TestOnUnknownOption` > `test_should_exit_2_and_name_the_option`.

### Integration legs

Both legs write a chezmoi config with the context's `company`, apply the source tree with `tests/shims/op` and `tests/shims/keepassxc-cli` first on `PATH` and `--no-tty` with a dummy password on stdin, then run `zsh -li -c true` and require exit 0 and an empty stderr.

- Container ([Containerfile](Containerfile) stage `base`, [entrypoint.sh](entrypoint.sh)): Fedora with chezmoi, sheldon, starship, zoxide. `make run` builds the `vnc` stage for manual inspection.
- Native macOS: a temp home, `--exclude=scripts` (no `brew bundle`, no LaunchAgent, no `defaults write`), `sheldon lock` by hand, and a preflight that `chezmoi data` reports the temp home. Every path chezmoi and the startup files touch derives from `HOME`, `ZDOTDIR` or an `XDG_*` variable, which is why this is safe to run on a developer Mac. **Startup code must keep it that way: write only under those directories, and stay silent when a tool you wrap is absent.**
````

- [ ] **Step 2: AGENTS.md, ship flow**

In "Offer 2 — Ship it", replace the default flow with:

```markdown
1. `git push -u origin <branch>`
2. `gh pr create` with a concise title and bulleted summary
3. `gh pr checks <n> --watch --fail-fast` — the `ci` check is required; the merge is rejected while it runs
4. `gh pr merge <n> --squash --delete-branch`
5. `git checkout main && git pull --ff-only`
```

In "When *not* to offer", replace `` (`make build && make validate`) `` with `` (`make integration`) ``.

- [ ] **Step 3: quick-access/README.md**

Directly under the Map table add:

```markdown
Tests live beside the map: `bin` → `tests/bin/`, `functions` → `tests/functions/`, `conf.d` →
`tests/zsh/` (`conf.d/exact_ista` → `tests/zsh/ista/`); see [AGENTS.md](../AGENTS.md#testing).
```

In "Where does a new thing go?", after item 5 add:

```markdown
6. **Whatever you add, its test goes with it**: `tests/bin/test_<name>.py` for a script,
   `tests/functions/test_<name>.py` for a function, `tests/zsh/test_<name>.py` for a module that
   defines functions. `make unit` tells you when one is missing; a file with no logic of its own is
   listed in `tests/untested.toml` with the reason instead. See [AGENTS.md](../AGENTS.md#testing).
```

- [ ] **Step 4: README.md**

Replace the "Testing in a container" section with:

````markdown
## Testing

```sh
make lint                # shellcheck, zsh -n, workflow lint
make unit                # pytest unit tests + node driver test
make integration         # apply all three contexts in a Fedora container (needs Podman)
make integration-native  # same, natively into a temp HOME (macOS)
make ci                  # lint unit integration
make run                 # start the VNC inspection container on :5901
make vnc                 # open a VNC viewer
make stop                # stop it
make clean               # remove the images
```

CI runs the same targets on every pull request; `main` requires the `ci` check. Details in [AGENTS.md](AGENTS.md#testing).
````

- [ ] **Step 5: testing.md, Framework Adaptability**

Add after the JUnit 5 line:

```markdown
- **pytest**: a class per subject, nested classes for `On...` contexts, `test_should_...` methods for the claims.
```

- [ ] **Step 6: Brewfile**

In `run_once_before_01-install-packages.sh`, after the `brew "jq"` line add:

```
brew "shellcheck"                  # Shell script linter; make lint runs it on every bash file
brew "actionlint"                  # GitHub Actions workflow linter; make lint runs it on .github/workflows
```

This is a `run_once` script, so existing machines install by hand: `brew install shellcheck actionlint` (both already present on this one).

- [ ] **Step 7: Inspect and commit**

Run `mcp__idea__get_file_problems` on the five files; fix or explain each finding.

```bash
git add AGENTS.md quick-access/README.md README.md home/private_dot_config/exact_agents/exact_rules/testing.md home/.chezmoiscripts/run_once_before_01-install-packages.sh
git commit -m "docs: testing guide, test locations, and the ship flow with a required check"
```

---

### Task 12: Ship, then make `ci` required

This task talks to GitHub. Follow the two offers in AGENTS.md: the user confirms before the push, and again before the merge. Ask whether the spec and plan under `docs/` stay in the PR; the user removed `docs/` once before (#56) once the work had landed.

- [ ] **Step 1: Full local run**

Run: `make ci && make integration-native`
Expected: everything green.

- [ ] **Step 2: Push and open the PR** (after the user's go)

```bash
git push -u origin ci/test-gate-and-suite
gh pr create --title "ci: gate merges on lint, unit and integration tests" --body "$(cat <<'EOF'
- pytest sandbox that runs the real scripts with fake commands; tests for gh-latest and zsh-scratch
- conventions test: every script, function and function-defining module has a test or a listed reason
- fake op and keepassxc-cli; apply all three contexts in a Fedora container and natively on macOS, require a silent zsh
- GitHub Actions: checks, integration and macos jobs behind one required check named ci; Dependabot for actions and uv
- make lint / unit / integration / integration-native / ci, used identically by CI
EOF
)"
gh pr checks --watch --fail-fast
```

- [ ] **Step 3: Fix what the runners show**

Known places the first run can differ from a Mac:

- `integration` job: rootless Podman building Fedora. If `podman build` fails on the runner but `docker` is present, run that job with `CONTAINER_ENGINE=docker` (`run: make integration CONTAINER_ENGINE=docker`) and keep Podman as the local default.
- `checks` job: Chrome's sandbox. If the driver test reports `No usable sandbox`, add before `make lint unit`: `sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`.
- `macos` job: `brew install` output or a darwin-only module on a bare runner. Guard the module as in Task 7.
- `checks` job: `node --test tests/` needs Node 21 or newer to take a directory. If the runner's default Node is older, add `actions/setup-node` pinned by SHA with `node-version: 22` before `make lint unit`, and keep the pin under Dependabot like the others.
- Read the `ci` job log once: it must list three `success` results.

Commit fixes on the branch; the PR updates.

- [ ] **Step 4: Make the check required and tighten the repository** (once the PR is green)

```bash
gh api repos/bkahlert/dotfiles/rulesets/15788010 | jq '{
  name, target, enforcement, conditions, bypass_actors,
  rules: (.rules + [
    {type: "pull_request", parameters: {
      required_approving_review_count: 0, dismiss_stale_reviews_on_push: false,
      require_code_owner_review: false, require_last_push_approval: false,
      required_review_thread_resolution: false, allowed_merge_methods: ["squash"]}},
    {type: "required_status_checks", parameters: {
      strict_required_status_checks_policy: false, do_not_enforce_on_create: false,
      required_status_checks: [{context: "ci", integration_id: 15368}]}}
  ])}' | gh api -X PUT repos/bkahlert/dotfiles/rulesets/15788010 --input -

gh api -X PUT repos/bkahlert/dotfiles/actions/permissions/workflow \
  -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false

gh api -X PUT repos/bkahlert/dotfiles/actions/permissions \
  -F enabled=true -f allowed_actions=all -F sha_pinning_required=true
```

Verify: `gh api repos/bkahlert/dotfiles/rulesets/15788010 -q '.rules[].type'` lists `deletion`, `non_fast_forward`, `pull_request`, `required_status_checks`; `gh pr view --json mergeStateStatus -q .mergeStateStatus` reports `CLEAN`.

- [ ] **Step 5: Merge** (after the user's go)

```bash
gh pr merge --squash --delete-branch
git checkout main && git pull --ff-only
```

Then confirm the gate is in effect without pushing anything: `gh api repos/bkahlert/dotfiles/rules/branches/main -q '.[].type'` must list `pull_request` and `required_status_checks` next to `deletion` and `non_fast_forward`. If it does not, Step 4 did not take; repeat it.

---

## Follow-up: PR 2

A separate plan after this one lands: convert `executable_statusline-test` into `tests/bin/test_statusline.py` (three modes asserted against `statusline-input.json`), then unit tests for the scripts with real logic (`timeout`, `killport`, `pick-port`, `print-port`, `upgrade-all`, `cleanup`, `known-hosts-fix`, `cert-get`, `cert-print`, `gcloud-login`, `op-agent`), each removing its allowlist line.
