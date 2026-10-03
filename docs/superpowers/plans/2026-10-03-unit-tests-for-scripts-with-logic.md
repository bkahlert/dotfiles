# Unit Tests for the Scripts with Logic Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PR 2 of the test-suite work: the statusline harness becomes a pytest, and every `bin/` script whose behaviour is more than delegation gets a unit test that runs the real script against fakes, each test removing the script's line from `tests/untested.toml`.

**Ruling against the spec:** the spec names `tests/bin/test_statusline.py`; the test lives at `tests/claude/test_statusline.py` instead, mirroring `private_dot_claude` the way `tests/bin` mirrors `exact_bin` and `tests/zsh` mirrors `conf.d` (decided with the user on 2026-10-03; a test next to the script inside the chezmoi source tree was rejected).

**Architecture:** Every test uses the sandbox from PR 1 (`run`, `fake_bin`, `calls`, `sandbox`): the real script runs with a temp `HOME`, fakes first on `PATH`, guards for everything that reaches the network or the machine. Two sandbox gaps the prototypes exposed are closed first: a fake's call record is written in one `write(2)` so two fakes in one pipeline cannot interleave, and `ssh-keygen`, `openssl`, `xcrun` and the package tools join the guard list. The statusline lives outside `exact_bin`, so script discovery (`bin_links` and the conventions test) learns a second source directory. Two scripts change behaviour because the tests found defects: `known-hosts-fix` edits the known_hosts of the passwd-database home instead of `$HOME`'s, and `gcloud-login` exits silently when the Chromium install fails. A third defect is a packaging one: the statusline needs bash ≥ 4.2 and nothing installs it on a fresh Mac.

**Tech Stack:** pytest 9 via `uv run --locked`, bash fakes written by `tests/conftest.py`, GitHub Actions (one line in the macOS job), chezmoi (`.chezmoiremove`, Brewfile in `run_once_before_01-install-packages.sh`).

**Spec:** [docs/superpowers/specs/2026-10-03-ci-and-tests-design.md](../specs/2026-10-03-ci-and-tests-design.md), section "Delivery", paragraph "PR 2". The PR 1 plan's "Follow-up: PR 2" section in [2026-10-03-ci-gate-and-test-suite.md](2026-10-03-ci-gate-and-test-suite.md) names the scripts.

## Global Constraints

- Branch `test/scripts-with-logic` off `origin/main` (currently `acdcb05`, PR #72 merged after PR #71). Never commit on `main`. Never stage `home/private_dot_config/zsh/exact_conf.d/90-scratch.zsh`: it carries the user's uncommitted work, so `git add` explicit paths only.
- Do not touch `tests/gcloud-login-driver.test.js`, `home/dot_local/exact_bin/executable_gcloud-login-driver`, or the `node --test` line in the Makefile: another session owns the driver test. The gcloud-login tests here fake the driver.
- Test command for every task: `uv run --locked pytest -m "not integration" -q`. Not `make unit` (it runs the node driver test). `make lint` once before the PR.
- JetBrains MCP is connected: run `mcp__idea__get_file_problems` with `errorsOnly: false` on every changed file before each commit; fix or name every finding.
- Tests follow `~/.config/agents/rules/testing.md`: one class per subject (`TestKillport`), nested `TestOn...` contexts, `test_should_...` leaves, result stored before asserting, tests first and helpers/constants last, no comments. Scripts follow `~/.config/agents/rules/bash.md`; shellcheck clean.
- Commits follow `~/.config/agents/rules/git.md`: Conventional Commits, scope = the script's name (`test(killport): ...`, `fix(known-hosts-fix): ...`), one change per commit, no AI attribution trailers. PR title: `test: unit tests for the scripts with logic`.
- A script's task removes its `tests/untested.toml` line in the same commit as the test; `tests/test_conventions.py` fails on a stale entry, so a forgotten removal shows up as a red suite.
- These are characterization tests of scripts that already exist, so a new test passes on first run. Every expected value below was captured from the real script on 2026-10-03 (macOS, bash 5.3, `date +%s` faked to `1893400000`); if a test disagrees with the script, read the script before changing the expectation. Where a task changes a script (Tasks 1, 7, 12), write that test first and watch it fail.
- Nothing real may be reached: fake every tool a subject calls (`lsof`, `openssl`, `gcloud`, `sudo`, ...) before running it. Two hazards are specific to this PR: a `cleanup --apply` test whose fake `sudo -v` succeeds starts a keepalive loop that holds the test's pipes for 60 s (the fake must exit 1), and `ssh-keygen -R` without `-f` edits the real `~/.ssh/known_hosts` (Task 1 guards it; Task 7 adds `-f`).
- The statusline needs bash ≥ 4.2 (`$'\uXXXX'`, `${var,,}`); the sandbox resolves `#!/usr/bin/env bash` to `/opt/homebrew/bin/bash` on a Mac and `/usr/bin/bash` on Linux. The macOS runner ships only bash 3.2, so Task 2 adds `bash` to the job's `brew install` and to the Brewfile.

## Review Focus

1. `gcloud-login` when `npx @puppeteer/browsers install` fails: `set -e` ends the script with npx's status and the "Chromium install failed" message never prints. Pinned in Task 12 (`TestOnAFailingChromiumInstall`), with the fix.
2. `known-hosts-fix <host>` runs `ssh-keygen -R <host>` without `-f`, so it edits the known_hosts of the passwd-database home while the `<line>` branch reads `$HOME/.ssh/known_hosts`. Pinned in Task 7 (`test_should_hand_ssh_keygen_the_known_hosts_under_home`), with the fix.
3. The statusline on a Mac without Homebrew bash renders literal `` and prints `bad substitution`. Pinned by the whole `tests/claude/test_statusline.py` running on the macOS job once Task 2 installs bash there, and by the Brewfile entry for real machines.
4. `op-agent read` with a pid file naming a live process that is not the daemon must fail within the write timeout instead of hanging. Pinned in Task 11 (`TestOnAPidFileOfAForeignProcess`).
5. `cleanup --yes` without `--apply` must delete nothing. Pinned in Task 10 (`test_should_delete_nothing_even_with_yes`).

Noted, not in this PR: the statusline prints jq parse errors to stderr on malformed input but still exits 0; `cleanup` says "system-level steps will be skipped" after a denied `sudo -v` and then still tries `sudo -n rm -rf` and warns; `op-agent read` without a reference prints bash's `${2?...}` message with the script path.

---

### Task 1: Sandbox: atomic call records and more guards

**Files:**
- Modify: `tests/conftest.py:9-19,86-97`
- Modify: `tests/test_sandbox.py` (new tests under `TestRun` and `TestFakeBin`)
- Modify: `AGENTS.md:198` (the guarded-tools example list)

**Interfaces:**
- Consumes: the PR 1 sandbox (`Sandbox.fake_bin`, `Sandbox.calls`, `GUARDED`).
- Produces: `calls(name)` returns complete records even for fakes that ran concurrently; `GUARDED` additionally contains `ssh-keygen`, `openssl`, `xcrun`, `gem`, `uv`, `yarn`, `composer`. Later tasks fake these where the subject needs them (`fake_bin` replaces a guard).

- [ ] **Step 1: Write the failing pipeline test**

Add `import pytest` as the first line of `tests/test_sandbox.py` (it has no imports yet) and this test at the end of `TestFakeBin`:

```python
class TestSandbox:
    class TestFakeBin:
        ...

        def test_should_keep_records_apart_when_two_fakes_share_a_pipeline(self, run, fake_bin, calls):
            fake_bin("tool")
            for _ in range(20):
                run("sh", "-c", "tool a one | tool b two")
            assert sorted(calls("tool")) == sorted([["a", "one"], ["b", "two"]] * 20)
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run --locked pytest tests/test_sandbox.py -q -k pipeline`
Expected: FAIL. The recorder writes a record in two `printf` calls, so records like `['a', 'one', 'b', 'two']` and `[]` appear (the prototype saw 3 corrupted records in 40).

- [ ] **Step 3: Write each record with one printf**

In `tests/conftest.py` replace lines 17-19 with:

```python
# A record is written by one printf, so two fakes in a pipeline cannot interleave their records.
# NUL cannot occur inside an argument, so it ends one; a record ends with RS followed by NUL.
ARG_SEPARATOR = "\0"
RECORD_SEPARATOR = "\x1e\0"
```

Replace line 94 (inside `_write`) with:

```python
recorder = f"printf '%s\\0' \"$@\" $'\\036' >> {log}\n" if record else ""
```

Line 90 (`calls`) stays as it is: `log.read_text().split(RECORD_SEPARATOR)[:-1]` now splits on the two-byte terminator. With no arguments the fake prints just `\x1e\0`, which parses to `[]` as before.

- [ ] **Step 4: Run the sandbox tests to verify they pass**

Run: `uv run --locked pytest tests/test_sandbox.py -q`
Expected: all pass, including the three existing recorder tests (spaces, empty and absent arguments, an argument spanning lines).

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_sandbox.py
git commit -m "test(sandbox): write a fake's call record in one write" -m "Two fakes in one pipeline appended their records concurrently; a record split across two writes interleaved with the other's."
```

- [ ] **Step 6: Write the failing guard test**

Add to `TestRun` in `tests/test_sandbox.py`:

```python
class TestSandbox:
    class TestRun:
        ...

        @pytest.mark.parametrize("command", [
            ["ssh-keygen", "-l", "-f", "/dev/null"], ["openssl", "version"], ["xcrun", "--version"],
            ["gem", "--version"], ["uv", "--version"], ["yarn", "--version"], ["composer", "--version"],
        ], ids=lambda command: command[0])
        def test_should_guard_the_tools_the_script_tests_fake(self, run, command):
            result = run(*command)
            assert result.returncode == 127
            assert result.stderr == f"{command[0]}: not faked in this test\n"
```

- [ ] **Step 7: Run it to verify it fails**

Run: `uv run --locked pytest tests/test_sandbox.py -q -k guard_the_tools`
Expected: 7 failures or errors: `openssl version` exits 0 with a version line, `ssh-keygen -l -f /dev/null` exits 255, tools that are not installed raise `FileNotFoundError` from `subprocess.run`.

- [ ] **Step 8: Extend the guard list**

Replace `GUARDED` in `tests/conftest.py` (lines 13-16) with:

```python
GUARDED = ("op", "keepassxc-cli", "gh", "glab", "gcloud", "idp", "curl", "wget", "ssh", "scp", "ssh-keygen",
           "openssl", "brew", "open", "osascript", "launchctl", "defaults", "sudo", "xcrun",
           "git", "chezmoi", "podman", "npm", "npx", "yarn", "composer", "gem", "uv",
           "mas", "softwareupdate", "security", "dscacheutil", "pbcopy", "pbpaste", "lsof", "killall", "pkill")
```

Extend the comment above it: after "container machines" add ", or ignore `HOME` (`ssh-keygen -R` edits the passwd-database home's known_hosts)".

In `AGENTS.md`, the bullet starting "Network, vault, system-state and user-state tools" lists examples in parentheses; change the list to `op`, `gh`, `gcloud`, `curl`, `openssl`, `ssh-keygen`, `brew`, `git`, `chezmoi`, `podman`, `xcrun`, `open`, `osascript`, `launchctl`, `defaults`, `sudo`, `pbcopy`, `lsof`, `pkill`, ... .

- [ ] **Step 9: Run the whole suite to verify it passes**

Run: `uv run --locked pytest -m "not integration" -q`
Expected: all pass. The `known-hosts-fix`, `cert-get`, `cert-print` and `cleanup` scripts are still allowlisted, so no existing test reaches the new guards.

- [ ] **Step 10: Commit**

```bash
git add tests/conftest.py tests/test_sandbox.py AGENTS.md
git commit -m "test(sandbox): guard ssh-keygen, openssl, xcrun and the package tools"
```

---

### Task 2: Statusline: the harness becomes a test

**Files:**
- Modify: `tests/repo.py` (add `CLAUDE_SOURCE`, `SCRIPT_SOURCES`, `scripts()`)
- Modify: `tests/conftest.py:22-28` (`bin_links` iterates `scripts()`)
- Modify: `tests/test_conventions.py:32-39` (`subjects()` iterates `scripts()`)
- Modify: `tests/test_sandbox.py` (one test under `TestRun`)
- Create: `tests/claude/test_statusline.py`
- Modify: `tests/untested.toml` (empty `[claude]` section)
- Delete: `home/private_dot_claude/executable_statusline-test`, `home/private_dot_claude/statusline-input.json`
- Modify: `home/.chezmoiremove` (two lines)
- Modify: `home/.chezmoiscripts/run_once_before_01-install-packages.sh` (one Brewfile line)
- Modify: `.github/workflows/ci.yml:59`
- Modify: `AGENTS.md:183-188` (table row)

**Interfaces:**
- Consumes: `run(name, *args, stdin=...)`, `fake_bin`, `sandbox.home` from PR 1.
- Produces: `repo.scripts() -> list[tuple[str, str, Path]]`, `(area, target name, source path)` for every `executable_*` file under `home/dot_local/exact_bin` (area `bin`) and `home/private_dot_claude` (area `claude`), bin first, each sorted. `run("statusline", ...)` resolves. The conventions test lists `claude/statusline` as a subject whose test is `tests/claude/test_statusline.py`; `tests/untested.toml` gains a `[claude]` section.

- [ ] **Step 1: Write the failing resolution test**

Add to `TestRun` in `tests/test_sandbox.py`, after `test_should_resolve_scripts_by_their_target_name`:

```python
class TestSandbox:
    class TestRun:
        ...

        def test_should_resolve_a_claude_script_by_its_target_name(self, run):
            result = run("statusline", "--no-nerd-fonts", stdin="{}")
            assert result.returncode == 0
            assert result.stdout.endswith("0%\x1b[0m\n")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run --locked pytest tests/test_sandbox.py -q -k claude_script`
Expected: ERROR `FileNotFoundError: [Errno 2] No such file or directory: 'statusline'`.

- [ ] **Step 3: Teach the sandbox and the conventions test the second script directory**

`tests/repo.py`: after `BIN_SOURCE` add

```python
CLAUDE_SOURCE = HOME_SOURCE / "private_dot_claude"
SCRIPT_SOURCES = (("bin", BIN_SOURCE), ("claude", CLAUDE_SOURCE))
```

Append at the end of the file:

```python
def scripts() -> list[tuple[str, str, Path]]:
    return [(area, source.name.removeprefix("executable_"), source)
            for area, root in SCRIPT_SOURCES for source in sorted(root.iterdir())
            if source.name.startswith("executable_")]
```

`tests/conftest.py`: import `scripts` instead of `BIN_SOURCE` and replace the `bin_links` body:

```python
@pytest.fixture(scope="session")
def bin_links(tmp_path_factory):
    links = tmp_path_factory.mktemp("bin")
    for _, name, source in scripts():
        (links / name).symlink_to(source)
    return links
```

`tests/test_conventions.py`: import `scripts` instead of `BIN_SOURCE` and replace the first loop of `subjects()`; the area is both the allowlist section and the test directory:

```python
def subjects():
    found = []
    for area, key, source in scripts():
        found.append(Subject(area, key, source, (
            TESTS / area / f"test_{key.replace('-', '_')}.py",
            TESTS / f"{key}.test.js")))
    ...
```

`tests/untested.toml`: add an empty `[claude]` section between `[bin]` and `[functions]`, like the empty `[functions]` section, so the next `~/.claude` script has a place to be listed.

- [ ] **Step 4: Run the sandbox and conventions tests**

Run: `uv run --locked pytest tests/test_sandbox.py tests/test_conventions.py -q`
Expected: the resolution test passes; the conventions test fails twice: `claude/statusline` and `claude/statusline-test` have no test at `tests/claude/...` and no entry under `[claude]`. Steps 5 and 6 fix both.

- [ ] **Step 5: Write the statusline test**

Create `tests/claude/test_statusline.py`:

```python
import json

import pytest


class TestStatusline:
    class TestOnNerdFonts:
        def test_should_render_glyphs_and_a_segment_bar(self, run, clock):
            result = run("statusline", "--nerd-fonts", stdin=json.dumps(INPUT))
            assert result.returncode == 0
            assert result.stdout == NERD

    class TestOnNoNerdFonts:
        def test_should_render_text_variant_emoji(self, run, clock):
            result = run("statusline", "--no-nerd-fonts", stdin=json.dumps(INPUT))
            assert result.returncode == 0
            assert result.stdout == FALLBACK

    class TestOnAutoDetection:
        def test_should_cache_the_probe_and_render_accordingly(self, run, clock, sandbox):
            result = run("statusline", stdin=json.dumps(INPUT))
            cached = (sandbox.home / ".cache/claude/nerd-font-support").read_text()
            assert cached in ("0", "1")
            assert result.stdout == {"1": NERD, "0": FALLBACK}[cached]

        def test_should_trust_a_cached_result(self, run, clock, sandbox):
            cache_detection(sandbox, "1")
            result = run("statusline", stdin=json.dumps(INPUT))
            assert result.stdout == NERD

        def test_should_let_the_environment_override_the_cache(self, run, clock, sandbox):
            cache_detection(sandbox, "1")
            result = run("env", "NERD_FONTS=0", "statusline", stdin=json.dumps(INPUT))
            assert result.stdout == FALLBACK

    class TestOnConfiguredModel:
        def test_should_dim_a_model_that_matches_the_settings(self, run, clock, sandbox):
            configure_model(sandbox, "settings.json", "sonnet")
            result = render(run, INPUT)
            assert f"{DIM}⚙︎ claude-sonnet-4-6{RESET}" in result.stdout

        def test_should_highlight_a_model_that_differs_from_the_settings(self, run, clock, sandbox):
            configure_model(sandbox, "settings.json", "opus")
            result = render(run, INPUT)
            assert f"{YELLOW}⚙︎ claude-sonnet-4-6{RESET}" in result.stdout

        def test_should_prefer_the_local_settings(self, run, clock, sandbox):
            configure_model(sandbox, "settings.json", "opus")
            configure_model(sandbox, "settings.local.json", "sonnet")
            result = render(run, INPUT)
            assert f"{DIM}⚙︎ claude-sonnet-4-6{RESET}" in result.stdout

    class TestOnThresholds:
        def test_should_colour_the_cost_yellow_from_5_dollars(self, run, clock):
            result = render(run, {"cost": {"total_cost_usd": 5.0}})
            assert f"{YELLOW}$5.00{RESET}" in result.stdout

        def test_should_colour_the_cost_red_from_10_dollars(self, run, clock):
            result = render(run, {"cost": {"total_cost_usd": 10}})
            assert f"{RED}$10.00{RESET}" in result.stdout

        def test_should_colour_the_context_red_from_75_percent(self, run, clock):
            result = render(run, {"context_window": {"used_percentage": 75.9}})
            assert f"{RED}◕ 75%{RESET}" in result.stdout

        def test_should_mark_an_expired_rate_limit_window(self, run, clock):
            result = render(run, {"rate_limits": {"five_hour": {"used_percentage": 3, "resets_at": 1893399000}}})
            assert link(LIMITS, f"{DIM}⏱︎ 3% ᵉˣᵖⁱʳᵉᵈ{RESET}") in result.stdout

    class TestOnSparseInput:
        def test_should_render_only_the_model_and_the_context(self, run, clock):
            result = render(run, {})
            assert result.returncode == 0
            assert result.stdout == f"⚙︎ ? · {DIM}○ 0%{RESET}\n"


def render(run, fields):
    return run("statusline", "--no-nerd-fonts", stdin=json.dumps(fields))


def cache_detection(sandbox, value):
    cache = sandbox.home / ".cache/claude/nerd-font-support"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(value)


def configure_model(sandbox, name, model):
    (sandbox.home / ".claude").mkdir(exist_ok=True)
    (sandbox.home / ".claude" / name).write_text(json.dumps({"model": model}))


def link(url, text):
    return f"\x1b]8;;{url}\x1b\\{text}\x1b]8;;\x1b\\"


@pytest.fixture
def clock(fake_bin):
    fake_bin("date", stdout="1893400000")


DIM, YELLOW, RED, RESET = "\x1b[2m", "\x1b[33m", "\x1b[31m", "\x1b[0m"
LIMITS = "https://console.anthropic.com/settings/limits"
TRANSCRIPT = "file:///Users/bkahlert/.claude/transcripts/abc123def456.jsonl"
EMPTY_SEGMENTS = "" * 6

INPUT = {
    "cwd": "/Users/bkahlert/Development/com.bkahlert/dotfiles",
    "session_id": "abc123def456",
    "session_name": "my-session",
    "transcript_path": "/Users/bkahlert/.claude/transcripts/abc123def456.jsonl",
    "model": {"id": "claude-sonnet-4-6", "display_name": "Sonnet"},
    "workspace": {
        "current_dir": "/Users/bkahlert/Development/com.bkahlert/dotfiles",
        "project_dir": "/Users/bkahlert/Development/com.bkahlert/dotfiles",
        "added_dirs": [],
    },
    "version": "2.1.90",
    "output_style": {"name": "default"},
    "cost": {
        "total_cost_usd": 0.01234,
        "total_duration_ms": 45000,
        "total_api_duration_ms": 2300,
        "total_lines_added": 156,
        "total_lines_removed": 23,
    },
    "context_window": {
        "total_input_tokens": 15234,
        "total_output_tokens": 4521,
        "context_window_size": 200000,
        "used_percentage": 28,
        "remaining_percentage": 92,
        "current_usage": {
            "input_tokens": 8500,
            "output_tokens": 1200,
            "cache_creation_input_tokens": 5000,
            "cache_read_input_tokens": 2000,
        },
    },
    "agent": {"name": "security-reviewer"},
    "exceeds_200k_tokens": False,
    "rate_limits": {
        "five_hour": {"used_percentage": 28.5, "resets_at": 1893465000},
        "seven_day": {"used_percentage": 92.2, "resets_at": 1893758400},
    },
}

NERD = " · ".join([
    link(TRANSCRIPT, " abc123de:my-session"),
    " claude-sonnet-4-6",
    "\U000f06a9 security-reviewer",
    f"{DIM}{EMPTY_SEGMENTS} 28%{RESET} {DIM}╱200k{RESET}",
    f"{DIM}$0.01{RESET}",
    link(LIMITS, f"{DIM} 28% ¹⁸·¹ʰ{RESET}"),
    link(LIMITS, f"{RED} 92% ⁴·¹ᵈ{RESET}"),
]) + "\n"

FALLBACK = " · ".join([
    link(TRANSCRIPT, "# abc123de:my-session"),
    "⚙︎ claude-sonnet-4-6",
    "웃 security-reviewer",
    f"{DIM}◔ 28%{RESET} {DIM}╱200k{RESET}",
    f"{DIM}$0.01{RESET}",
    link(LIMITS, f"{DIM}⏱︎ 28% ¹⁸·¹ʰ{RESET}"),
    link(LIMITS, f"{RED}⧗︎ 92% ⁴·¹ᵈ{RESET}"),
]) + "\n"
```

The three separators in `" · "`, `¹⁸·¹ʰ` and `⁴·¹ᵈ` are U+00B7; `╱` is U+2571. The clock is frozen at 1893400000 so the 5-hour window (resets at 1893465000) is 18.1 h away and the 7-day window (1893758400) 4.1 d; the superscripts come from the script's `to_sup`.

- [ ] **Step 6: Remove the harness from the source state**

```bash
git rm home/private_dot_claude/executable_statusline-test home/private_dot_claude/statusline-input.json
```

Append to `home/.chezmoiremove` (it already lists `.config/copy-password`):

```
.claude/statusline-test
.claude/statusline-input.json
```

`private_dot_claude` is not an `exact_` directory, so without these lines the two files would stay in every `~/.claude` that already has them.

- [ ] **Step 7: Run the statusline, sandbox and conventions tests**

Run: `uv run --locked pytest tests/claude/test_statusline.py tests/test_sandbox.py tests/test_conventions.py -q`
Expected: all pass. On this Mac `TestOnAutoDetection` caches `0` (no Nerd Font under `/Library/Fonts`) and renders the fallback; on a Mac with a Nerd Font it caches `1` and renders the glyphs, which the test accepts too.

- [ ] **Step 8: Document where the test lives**

In the `AGENTS.md` table "Where a test lives", add a row after the `bin/executable_<name>` row:

```markdown
| `private_dot_claude/executable_<name>` (`~/.claude/<name>`) | `tests/claude/test_<name>.py`, same sandbox; `run("<name>")` resolves it |
```

In the "Writing a unit test" bullets, the `run("name", *args)` line says it "runs a `bin/` script by its target name"; make that "runs a `bin/` or `~/.claude` script by its target name".

- [ ] **Step 9: Run inspections and commit**

Inspect every changed file with `mcp__idea__get_file_problems` (`errorsOnly: false`), then:

```bash
git add tests/repo.py tests/conftest.py tests/test_conventions.py tests/test_sandbox.py tests/untested.toml tests/claude/test_statusline.py home/.chezmoiremove AGENTS.md
git commit -m "test(statusline): replace the harness with a pytest" -m "Three modes asserted against the former statusline-input.json, plus the cache, the model styling and the thresholds. Scripts under private_dot_claude are discovered like bin scripts; their tests mirror them under tests/claude."
```

(`git rm` already staged the two deletions.)

- [ ] **Step 10: Install the bash the statusline needs**

`home/.chezmoiscripts/run_once_before_01-install-packages.sh`, in the Brewfile heredoc after the `brew "coreutils"` line:

```
brew "bash"                        # Bash 5; ~/.claude/statusline needs bash >= 4.2 (unicode escapes, case conversion), macOS ships 3.2
```

The heredoc is unquoted (`<<EOF`), so the comment must not contain `$` or backticks; this wording has neither.

`.github/workflows/ci.yml` line 59:

```yaml
      - run: brew install bash chezmoi sheldon starship zoxide
```

- [ ] **Step 11: Lint and verify**

Run: `make lint`
Expected: clean (shellcheck on the Brewfile script, actionlint and zizmor on the workflow).

Run: `bash -n home/.chezmoiscripts/run_once_before_01-install-packages.sh && sed -n '/<<EOF/,/^EOF/p' home/.chezmoiscripts/run_once_before_01-install-packages.sh | grep bash`
Expected: the `brew "bash"` line prints with its comment intact.

- [ ] **Step 12: Commit**

```bash
git add home/.chezmoiscripts/run_once_before_01-install-packages.sh .github/workflows/ci.yml
git commit -m "fix(claude): install the bash 5 the statusline needs" -m "macOS ships bash 3.2, which renders the statusline's unicode escapes literally and rejects its case conversion. The Brewfile now installs Homebrew's bash and the macOS CI job does the same before running the statusline tests."
```

---

### Task 3: timeout

**Files:**
- Create: `tests/bin/test_timeout.py`
- Modify: `tests/untested.toml` (remove `timeout`)

**Interfaces:**
- Consumes: `run`, `fake_bin`, `calls`, `repo.BIN_SOURCE`.

- [ ] **Step 1: Write the test**

```python
from repo import BIN_SOURCE


class TestTimeout:
    def test_should_forward_everything_to_gtimeout(self, run, fake_bin, calls):
        fake_bin("gtimeout", stdout="ran", exit_code=124)
        result = run("timeout", "-k", "5", "60", "./serve")
        assert (result.stdout, result.returncode) == ("ran", 124)
        assert calls("gtimeout") == [["-k", "5", "60", "./serve"]]

    class TestOnMissingGtimeout:
        def test_should_exit_127_and_name_the_package(self, run):
            result = run("env", "PATH=/usr/bin:/bin", str(BIN_SOURCE / "executable_timeout"), "1", "true")
            assert result.returncode == 127
            assert result.stderr == "timeout: gtimeout not found; install it with: brew install coreutils\n"
```

The second test shortens `PATH` because the sandbox includes `/opt/homebrew/bin`, where this Mac's real `gtimeout` lives; the script is run by its source path since the symlink directory is gone from that `PATH` too.

- [ ] **Step 2: Remove the allowlist line and run**

Delete `timeout = "legacy: test when next touched"` from `tests/untested.toml`.

Run: `uv run --locked pytest tests/bin/test_timeout.py tests/test_conventions.py -q`
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/bin/test_timeout.py tests/untested.toml
git commit -m "test(timeout): cover the gtimeout forwarding and the missing-tool error"
```

---

### Task 4: pick-port

**Files:**
- Create: `tests/bin/test_pick_port.py`
- Modify: `tests/untested.toml` (remove `pick-port`)

- [ ] **Step 1: Write the test**

```python
import contextlib
import socket


class TestPickPort:
    def test_should_print_a_port_that_can_be_bound(self, run):
        result = run("pick-port")
        assert result.returncode == 0
        port = int(result.stdout)
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("0.0.0.0", port))

    class TestOnTaken8080:
        def test_should_pick_another_port(self, run):
            with socket.socket() as holder:
                holder.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                with contextlib.suppress(OSError):
                    holder.bind(("0.0.0.0", 8080))
                    holder.listen()
                result = run("pick-port")
            assert result.returncode == 0
            assert int(result.stdout) != 8080

    class TestOnAnyArgument:
        def test_should_exit_2(self, run):
            result = run("pick-port", "x")
            assert result.returncode == 2
            assert result.stderr == "pick-port: unknown argument: x\nSee 'pick-port --help'\n"
```

macOS lets an unprivileged process bind port 80, so on a Mac the script prints `80` whenever it is free; on Linux it falls through to 8080 or an ephemeral port. Both tests hold on both.

- [ ] **Step 2: Remove the allowlist line and run**

Delete `pick-port = "legacy: test when next touched"` from `tests/untested.toml`.

Run: `uv run --locked pytest tests/bin/test_pick_port.py tests/test_conventions.py -q`
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/bin/test_pick_port.py tests/untested.toml
git commit -m "test(pick-port): cover the bindable port and the argument check"
```

---

### Task 5: print-port

**Files:**
- Create: `tests/bin/test_print_port.py`
- Modify: `tests/untested.toml` (remove `print-port`)

- [ ] **Step 1: Write the test**

```python
import sys

import pytest


class TestPrintPort:
    class TestOnNoArguments:
        @pytest.mark.skipif(sys.platform != "darwin", reason="macOS lists listeners through lsof")
        def test_should_list_every_listener_through_lsof(self, run, fake_bin, calls):
            fake_bin("lsof", stdout="COMMAND PID\nnode 1\n")
            result = run("print-port")
            assert (result.returncode, result.stdout) == (0, "COMMAND PID\nnode 1\n")
            assert calls("lsof") == [["-nP", "-iTCP", "-sTCP:LISTEN"]]

        @pytest.mark.skipif(sys.platform == "darwin", reason="Linux lists listeners through ss")
        def test_should_list_every_listener_through_ss(self, run, fake_bin, calls):
            fake_bin("ss", stdout="Netid State\n")
            result = run("print-port")
            assert (result.returncode, result.stdout) == (0, "Netid State\n")
            assert calls("ss") == [["-tulnp"]]

    class TestOnPorts:
        def test_should_query_lsof_for_all_of_them(self, run, fake_bin, calls):
            fake_bin("lsof", stdout="COMMAND PID\nnode 1\n")
            result = run("print-port", "3000", "8080")
            assert (result.returncode, result.stdout) == (0, "COMMAND PID\nnode 1\n")
            assert calls("lsof") == [["-nP", "-iTCP:3000", "-iTCP:8080"]]

        def test_should_exit_1_when_nothing_is_bound(self, run, fake_bin):
            fake_bin("lsof", exit_code=1)
            result = run("print-port", "3000")
            assert result.returncode == 1
            assert result.stderr == "print-port: nothing bound to port 3000\n"

        def test_should_reject_a_port_that_is_not_a_number(self, run, fake_bin):
            fake_bin("lsof")
            result = run("print-port", "abc")
            assert result.returncode == 2
            assert result.stderr == "print-port: not a port number: abc\nSee 'print-port --help'\n"

    class TestOnUnknownOption:
        def test_should_exit_2_and_name_the_option(self, run):
            result = run("print-port", "--nope")
            assert result.returncode == 2
            assert result.stderr == "print-port: unknown option: --nope\nSee 'print-port --help'\n"
```

- [ ] **Step 2: Remove the allowlist line and run**

Delete `print-port = "legacy: test when next touched"` from `tests/untested.toml`.

Run: `uv run --locked pytest tests/bin/test_print_port.py tests/test_conventions.py -q`
Expected: all pass, one skipped (the other platform's listing).

- [ ] **Step 3: Commit**

```bash
git add tests/bin/test_print_port.py tests/untested.toml
git commit -m "test(print-port): cover the listing, the port filter and the errors"
```

---

### Task 6: killport

**Files:**
- Create: `tests/bin/test_killport.py`
- Modify: `tests/untested.toml` (remove `killport`)

- [ ] **Step 1: Write the test**

```python
import signal
import subprocess


class TestKillport:
    def test_should_terminate_the_listener_and_report_the_freed_port(self, run, fake_bin, calls):
        with subprocess.Popen(["sleep", "100"]) as listener:
            fake_bin("sleep")
            fake_bin("lsof", script=listing_once(listener.pid))
            result = run("killport", "8080")
            assert listener.wait(timeout=5) == -signal.SIGTERM
        assert result.returncode == 0
        assert result.stdout == f"ℹ Killing 1 process(es) on port 8080: {listener.pid}\n✔ Port 8080 freed.\n"
        assert calls("lsof") == [["-t", "-iTCP:8080", "-sTCP:LISTEN"]] * 2

    class TestOnAListenerThatIgnoresSigterm:
        def test_should_escalate_to_sigkill(self, run, fake_bin):
            with subprocess.Popen(["sleep", "100"], preexec_fn=ignore_sigterm) as listener:
                fake_bin("sleep")
                fake_bin("lsof", stdout=f"{listener.pid}\n")
                result = run("killport", "8080")
                assert listener.wait(timeout=5) == -signal.SIGKILL
            assert result.returncode == 0
            assert result.stdout == (f"ℹ Killing 1 process(es) on port 8080: {listener.pid}\n"
                                     f"! Forcing SIGKILL on: {listener.pid}\n✔ Port 8080 freed.\n")

    class TestOnNoListener:
        def test_should_exit_1(self, run, fake_bin):
            fake_bin("lsof")
            result = run("killport", "8080")
            assert result.returncode == 1
            assert result.stderr == "✘ No process listening on port 8080.\n"

    class TestOnBadArguments:
        def test_should_reject_a_port_that_is_not_a_number(self, run):
            result = run("killport", "abc")
            assert result.returncode == 2
            assert result.stderr == "killport: not a port number: abc\nSee 'killport --help'\n"

        def test_should_reject_more_than_one_port(self, run):
            result = run("killport", "1", "2")
            assert result.returncode == 2
            assert result.stderr == "killport: expected exactly one <port>\nSee 'killport --help'\n"

        def test_should_print_the_help_to_stderr_without_arguments(self, run):
            result = run("killport")
            assert result.returncode == 2
            assert result.stderr.startswith("Purpose:")

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("killport", "--nope")
            assert result.returncode == 2
            assert result.stderr == "killport: unknown option: --nope\nSee 'killport --help'\n"


def listing_once(pid):
    return ('count=$(cat "$HOME/lsof.count" 2>/dev/null || echo 0)\n'
            'echo $((count + 1)) > "$HOME/lsof.count"\n'
            f'(( count == 0 )) && echo {pid}\n'
            'exit 0\n')


def ignore_sigterm():
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
```

The fake `sleep` returns at once, so the script's four 0.5 s polls cost nothing; `kill` is a bash builtin and reaches the real listener. `SIG_IGN` survives `exec`, so the second listener ignores SIGTERM from its first instruction and there is no race with the script's first `kill`. The `-15`/`-9` return codes are what `Popen.wait` reports for a process ended by that signal.

- [ ] **Step 2: Remove the allowlist line and run**

Delete `killport = "legacy: test when next touched"` from `tests/untested.toml`.

Run: `uv run --locked pytest tests/bin/test_killport.py tests/test_conventions.py -q`
Expected: all pass in well under a second.

- [ ] **Step 3: Commit**

```bash
git add tests/bin/test_killport.py tests/untested.toml
git commit -m "test(killport): cover SIGTERM, the SIGKILL escalation and the argument checks"
```

---

### Task 7: known-hosts-fix, with the `-f` fix

**Files:**
- Create: `tests/bin/test_known_hosts_fix.py`
- Modify: `home/dot_local/exact_bin/executable_known-hosts-fix:65,69`
- Modify: `tests/untested.toml` (remove `known-hosts-fix`)

**Interfaces:**
- Consumes: the `ssh-keygen` guard from Task 1; `fake_bin("ssh-keygen", script=...)` replaces it.

- [ ] **Step 1: Write the failing test**

Create `tests/bin/test_known_hosts_fix.py`. Every `ssh-keygen` in this step is a recording fake; the pass-through fake that runs the real tool is added in Step 5, after the script passes `-f`, so no run of the unfixed script can reach the real `~/.ssh/known_hosts`.

```python
class TestKnownHostsFix:
    class TestOnHost:
        def test_should_hand_ssh_keygen_the_known_hosts_under_home(self, run, fake_bin, calls, sandbox):
            fake_bin("ssh-keygen")
            result = run("known-hosts-fix", "a.test")
            assert result.returncode == 0
            assert calls("ssh-keygen") == [["-R", "a.test", "-f", str(sandbox.home / ".ssh/known_hosts")]]

    class TestOnLineNumber:
        def test_should_resolve_the_line_to_its_host(self, run, fake_bin, calls, sandbox):
            write_known_hosts(sandbox)
            fake_bin("ssh-keygen")
            result = run("known-hosts-fix", "2")
            assert result.returncode == 0
            assert result.stderr == "Line 2 → host b.test\n"
            assert calls("ssh-keygen") == [["-R", "b.test", "-f", str(sandbox.home / ".ssh/known_hosts")]]

        def test_should_delete_a_hashed_line_directly(self, run, fake_bin, calls, sandbox):
            known_hosts = write_known_hosts(sandbox)
            fake_bin("ssh-keygen")
            result = run("known-hosts-fix", "3")
            assert result.returncode == 0
            assert result.stderr == ("Hashed entry; deleting line 3 directly "
                                     "(twin entries, if any, will need separate handling).\n")
            assert known_hosts.read_text() == PLAIN_A + PLAIN_B
            assert calls("ssh-keygen") == []

        def test_should_reject_a_line_out_of_range(self, run, sandbox):
            write_known_hosts(sandbox)
            result = run("known-hosts-fix", "9")
            assert result.returncode == 1
            assert result.stderr == "known-hosts-fix: line 9 is out of range (1..3)\n"

        def test_should_fail_without_a_known_hosts_file(self, run, sandbox):
            result = run("known-hosts-fix", "1")
            assert result.returncode == 1
            assert result.stderr == f"known-hosts-fix: {sandbox.home}/.ssh/known_hosts does not exist\n"

    class TestOnBadArguments:
        def test_should_print_the_help_to_stderr_without_arguments(self, run):
            result = run("known-hosts-fix")
            assert result.returncode == 2
            assert result.stderr.startswith("Purpose:")

        def test_should_reject_two_arguments(self, run):
            result = run("known-hosts-fix", "a.test", "b.test")
            assert result.returncode == 2
            assert result.stderr == "known-hosts-fix: expected exactly one <host> or <line>\nSee 'known-hosts-fix --help'\n"

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("known-hosts-fix", "--nope")
            assert result.returncode == 2
            assert result.stderr == "known-hosts-fix: unknown option: --nope\nSee 'known-hosts-fix --help'\n"


KEY = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGRfYjWZcOhPaLmjKH3bTz3uY1H6Yk+3fBtYBgqd+8sW"
PLAIN_A = f"a.test {KEY}\n"
PLAIN_B = f"b.test,10.0.0.2 {KEY}\n"
HASHED = f"|1|abcdefghijklmnopqrstuvwxyz0=|abcdefghijklmnopqrstuvwxyz0= {KEY}\n"


def write_known_hosts(sandbox):
    ssh = sandbox.home / ".ssh"
    ssh.mkdir(mode=0o700)
    known_hosts = ssh / "known_hosts"
    known_hosts.write_text(PLAIN_A + PLAIN_B + HASHED)
    return known_hosts
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run --locked pytest tests/bin/test_known_hosts_fix.py -q`
Expected: `test_should_hand_ssh_keygen_the_known_hosts_under_home` and `test_should_resolve_the_line_to_its_host` fail: recorded `['-R', 'a.test']` (and `['-R', 'b.test']`) without `-f`. The rest pass.

- [ ] **Step 3: Pass the known_hosts path to ssh-keygen**

In `home/dot_local/exact_bin/executable_known-hosts-fix`:

Line 65: `  exec ssh-keygen -R "$host" -f "$known_hosts"`
Line 69: `exec ssh-keygen -R "$arg" -f "$known_hosts"`

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run --locked pytest tests/bin/test_known_hosts_fix.py -q && shellcheck home/dot_local/exact_bin/executable_known-hosts-fix`
Expected: all pass; shellcheck silent.

- [ ] **Step 5: Prove the removal with the real ssh-keygen**

Add to `TestOnHost`, after the first test:

```python
class TestKnownHostsFix:
    class TestOnHost:
        ...

        def test_should_remove_every_entry_of_the_host(self, run, fake_bin, sandbox):
            known_hosts = write_known_hosts(sandbox)
            fake_bin("ssh-keygen", script=REAL_SSH_KEYGEN)
            result = run("known-hosts-fix", "b.test")
            assert result.returncode == 0
            assert known_hosts.read_text() == PLAIN_A + HASHED
```

Add the constant next to the others at the bottom:

```python
REAL_SSH_KEYGEN = 'exec "$(command -pv ssh-keygen)" "$@"\n'
```

`command -pv` looks the real `ssh-keygen` up on the system default `PATH`, past the fake directory; with `-f` from Step 3 it edits the sandbox file (and leaves a `known_hosts.old` beside it). The `b.test,10.0.0.2` line goes as a whole because `-R` matches any name in the comma list.

Run: `uv run --locked pytest tests/bin/test_known_hosts_fix.py -q`
Expected: all pass.

- [ ] **Step 6: Remove the allowlist line, inspect, commit**

Delete `known-hosts-fix = "legacy: test when next touched"` from `tests/untested.toml`.

Run: `uv run --locked pytest tests/test_conventions.py -q`
Expected: pass.

```bash
git add home/dot_local/exact_bin/executable_known-hosts-fix tests/bin/test_known_hosts_fix.py tests/untested.toml
git commit -m "fix(known-hosts-fix): edit the known_hosts under HOME in both branches" -m "ssh-keygen -R without -f opens the known_hosts of the passwd-database home, while the <line> branch reads \$HOME/.ssh/known_hosts. Both now name the same file."
```

---

### Task 8: cert-get and cert-print

**Files:**
- Create: `tests/bin/test_cert_get.py`, `tests/bin/test_cert_print.py`
- Modify: `tests/untested.toml` (remove `cert-get`, `cert-print`)

**Interfaces:**
- Consumes: the `openssl` guard and the atomic recorder from Task 1 (both `openssl` processes of the pipeline record concurrently).

- [ ] **Step 1: Write the cert-get test**

```python
class TestCertGet:
    def test_should_print_the_leaf_certificate_as_pem(self, run, fake_bin, calls):
        fake_bin("openssl", script=OPENSSL)
        result = run("cert-get", "example.test")
        assert (result.returncode, result.stdout) == (0, "PEM:CERT\n")
        assert sorted(calls("openssl")) == [
            ["s_client", "-showcerts", "-servername", "example.test", "-connect", "example.test:443"],
            ["x509", "-outform", "PEM"]]

    def test_should_connect_to_the_given_port(self, run, fake_bin, calls):
        fake_bin("openssl", script=OPENSSL)
        run("cert-get", "mail.example.test", "993")
        assert ["s_client", "-showcerts", "-servername", "mail.example.test",
                "-connect", "mail.example.test:993"] in calls("openssl")

    class TestOnDownload:
        def test_should_write_domain_pem_and_print_its_name(self, run, fake_bin, sandbox):
            fake_bin("openssl", script=OPENSSL)
            result = run("cert-get", "--download", "example.test")
            assert (result.returncode, result.stdout) == (0, "example.test.pem\n")
            assert (sandbox.home / "example.test.pem").read_text() == "PEM:CERT\n"

    class TestOnBadArguments:
        def test_should_print_the_help_to_stderr_without_arguments(self, run):
            result = run("cert-get")
            assert result.returncode == 2
            assert result.stderr.startswith("Purpose:")

        def test_should_reject_a_third_argument(self, run):
            result = run("cert-get", "a", "1", "x")
            assert result.returncode == 2
            assert result.stderr == "cert-get: too many arguments\nSee 'cert-get --help'\n"

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("cert-get", "--nope")
            assert result.returncode == 2
            assert result.stderr == "cert-get: unknown option: --nope\nSee 'cert-get --help'\n"


OPENSSL = 'case $1 in s_client) printf "CERT\\n" ;; x509) printf "PEM:"; cat ;; esac\nexit 0\n'
```

The two `openssl` processes of the pipeline start together, so `calls` is compared sorted. `run` executes in the sandbox home, which is where `--download` writes.

- [ ] **Step 2: Write the cert-print test**

```python
class TestCertPrint:
    def test_should_print_the_leaf_certificate_as_text(self, run, fake_bin, calls):
        fake_bin("openssl", script=OPENSSL)
        result = run("cert-print", "example.test")
        assert (result.returncode, result.stdout) == (0, "TEXT:CERT\n")
        assert sorted(calls("openssl")) == [
            ["s_client", "-showcerts", "-servername", "example.test", "-connect", "example.test:443"],
            ["x509", "-inform", "pem", "-noout", "-text"]]

    def test_should_connect_to_the_given_port(self, run, fake_bin, calls):
        fake_bin("openssl", script=OPENSSL)
        run("cert-print", "example.test", "8443")
        assert ["s_client", "-showcerts", "-servername", "example.test",
                "-connect", "example.test:8443"] in calls("openssl")

    class TestOnBadArguments:
        def test_should_print_the_help_to_stderr_without_arguments(self, run):
            result = run("cert-print")
            assert result.returncode == 2
            assert result.stderr.startswith("Purpose:")

        def test_should_reject_a_third_argument(self, run):
            result = run("cert-print", "a", "1", "x")
            assert result.returncode == 2
            assert result.stderr == "cert-print: too many arguments\nSee 'cert-print --help'\n"

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("cert-print", "--nope")
            assert result.returncode == 2
            assert result.stderr == "cert-print: unknown option: --nope\nSee 'cert-print --help'\n"


OPENSSL = 'case $1 in s_client) printf "CERT\\n" ;; x509) printf "TEXT:"; cat ;; esac\nexit 0\n'
```

- [ ] **Step 3: Remove the allowlist lines and run**

Delete `cert-get = ...` and `cert-print = ...` from `tests/untested.toml`.

Run: `uv run --locked pytest tests/bin/test_cert_get.py tests/bin/test_cert_print.py tests/test_conventions.py -q`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add tests/bin/test_cert_get.py tests/bin/test_cert_print.py tests/untested.toml
git commit -m "test(cert): cover cert-get and cert-print with a fake openssl"
```

---

### Task 9: upgrade-all

**Files:**
- Create: `tests/bin/test_upgrade_all.py`
- Modify: `tests/untested.toml` (remove `upgrade-all`)

**Interfaces:**
- Consumes: guards for `brew`, `podman`, `mas`, `npm`, `gh`, `softwareupdate`, `gem` (all replaced by fakes here); `ruby` is not guarded and is faked so the gem step never runs the real one.

- [ ] **Step 1: Write the test**

```python
class TestUpgradeAll:
    def test_should_run_every_upgrader_and_report_success(self, run, fake_bin, calls):
        tooling(fake_bin)
        result = run("upgrade-all")
        assert result.returncode == 0
        assert result.stdout.endswith("⚙ Summary\n  ✔ all steps succeeded\n")
        assert calls("brew") == [["tap"], ["tap"], ["update"], ["upgrade"],
                                 ["outdated", "--formula", "--quiet"], ["cleanup"]]
        assert calls("mas") == [["upgrade"]]
        assert calls("npm") == [["update", "-g"]]
        assert calls("gh") == [["extension", "upgrade", "--all"]]
        assert calls("softwareupdate") == [["-l"]]

    class TestOnAFailingStep:
        def test_should_continue_and_exit_1_with_the_failures_listed(self, run, fake_bin, calls):
            tooling(fake_bin, brew='[[ $1 == upgrade ]] && exit 1\nexit 0\n', mas=1)
            result = run("upgrade-all")
            assert result.returncode == 1
            assert calls("npm") == [["update", "-g"]]
            assert result.stdout.endswith("⚙ Summary\n  ✘ brew upgrade\n  ✘ mas upgrade\n  ! 2 step(s) failed\n")

    class TestOnHomebrew:
        def test_should_untap_a_retired_tap(self, run, fake_bin, calls):
            tooling(fake_bin, brew='case $1 in tap) printf "homebrew/core\\nhomebrew/cask-fonts\\n" ;; esac\nexit 0\n')
            result = run("upgrade-all")
            assert "  ℹ untapping deprecated homebrew/cask-fonts\n" in result.stdout
            assert ["untap", "homebrew/cask-fonts"] in calls("brew")

        def test_should_rebuild_unbottled_formulae_from_source(self, run, fake_bin, calls):
            tooling(fake_bin, brew='case $1 in outdated) printf "foo\\nbar\\n" ;; esac\nexit 0\n')
            result = run("upgrade-all")
            assert "  ℹ rebuilding unbottled formulae from source: foo bar \n" in result.stdout
            assert ["upgrade", "--build-from-source", "foo", "bar"] in calls("brew")

    class TestOnPodmanMachine:
        def test_should_leave_a_machine_on_the_clients_version_alone(self, run, fake_bin, calls):
            tooling(fake_bin, podman=podman(client="5.6.1", server="5.6.0"))
            result = run("upgrade-all")
            assert "  ✔ machine already on podman 5.6.0 (client 5.6.1)\n" in result.stdout
            assert not any(call[:3] == ["machine", "os", "apply"] for call in calls("podman"))

        def test_should_rebase_a_machine_behind_the_client(self, run, fake_bin, calls):
            tooling(fake_bin, podman=podman(client="5.6.1", server="5.5.2"))
            result = run("upgrade-all")
            assert "  ℹ machine on podman 5.5.2, client on 5.6.1 — rebasing\n" in result.stdout
            assert "  ✔ machine rebased to podman 5.6\n" in result.stdout
            assert ["machine", "os", "apply", "quay.io/podman/machine-os:5.6", "--restart"] in calls("podman")

        def test_should_warn_when_the_machine_is_ahead(self, run, fake_bin, calls):
            tooling(fake_bin, podman=podman(client="5.5.1", server="5.6.2"))
            result = run("upgrade-all")
            assert "  ! machine (5.6.2) is ahead of the client (5.5.1) — upgrade the client first\n" in result.stdout
            assert not any(call[:3] == ["machine", "os", "apply"] for call in calls("podman"))

        def test_should_skip_without_a_machine(self, run, fake_bin):
            tooling(fake_bin, podman="exit 1\n")
            result = run("upgrade-all")
            assert "  ▪ no podman machine (create one with: podman machine init)\n" in result.stdout

    class TestOnRubyGems:
        def test_should_update_only_the_gems_outside_rubys_prefix(self, run, fake_bin, calls):
            tooling(fake_bin, gems="foo\nbar\n")
            run("upgrade-all")
            assert calls("gem") == [["update", "foo", "bar"]]

        def test_should_skip_when_only_shipped_gems_exist(self, run, fake_bin, calls):
            tooling(fake_bin, gems="")
            result = run("upgrade-all")
            assert "  ▪ no gems installed besides those shipped with Ruby\n" in result.stdout
            assert calls("gem") == []

    class TestOnAnyArgument:
        def test_should_exit_2(self, run):
            result = run("upgrade-all", "x")
            assert result.returncode == 2
            assert result.stderr == "upgrade-all: unknown argument: x\nSee 'upgrade-all --help'\n"


def tooling(fake_bin, *, brew="exit 0\n", podman="exit 1\n", mas=0, gems=""):
    fake_bin("brew", script=brew)
    fake_bin("podman", script=podman)
    fake_bin("mas", exit_code=mas)
    fake_bin("npm")
    fake_bin("gh")
    fake_bin("softwareupdate", stdout="No new software available.\n")
    fake_bin("gem")
    fake_bin("ruby", stdout=gems)


def podman(*, client, server):
    return "\n".join([
        'case "$*" in',
        '  "machine inspect --format {{.State}}") echo running ;;',
        '  "version --format {{.Client.Version}}") echo ' + client + ' ;;',
        '  "version --format {{.Server.Version}}") echo ' + server + ' ;;',
        "esac", "exit 0", ""])
```

The `brew tap` call appears twice because the script checks two retired taps. The "rebuilding" line ends in `foo bar ` with a trailing space because the script joins the names with `tr '\n' ' '`. A faked `gem` keeps `command -v gem` from resolving to `/usr/bin/gem`, which would take the "system Ruby" skip branch instead; the faked `ruby` returns the names the script treats as user gems.

- [ ] **Step 2: Remove the allowlist line and run**

Delete `upgrade-all = "legacy: test when next touched"` from `tests/untested.toml`.

Run: `uv run --locked pytest tests/bin/test_upgrade_all.py tests/test_conventions.py -q`
Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add tests/bin/test_upgrade_all.py tests/untested.toml
git commit -m "test(upgrade-all): cover the steps, the failure summary and the podman rebase"
```

---

### Task 10: cleanup

**Files:**
- Create: `tests/bin/test_cleanup.py`
- Modify: `tests/untested.toml` (remove `cleanup`)

**Interfaces:**
- Consumes: guards for `osascript`, `sudo`, `xcrun`, `brew`, `gem`, `npm`, `yarn`, `composer`, `uv` (all replaced by fakes); `getconf`, `plutil` and `docker` are faked for determinism.

- [ ] **Step 1: Write the test**

```python
import sys

import pytest

darwin = pytest.mark.skipif(sys.platform != "darwin", reason="cleanup is macOS only")


class TestCleanup:
    @darwin
    class TestOnDryRun:
        def test_should_delete_nothing_and_report_both_totals(self, run, fake_bin, calls, sandbox):
            safe, risky = xcode_leftovers(sandbox)
            quiet_tools(fake_bin, sandbox)
            result = run("cleanup", timeout=30)
            assert result.returncode == 0
            assert safe.exists() and risky.exists()
            assert "▪ DerivedData (dry-run)\n" in result.stdout
            assert "▪ Xcode Archives: would ask\n" in result.stdout
            assert "↗ Would reclaim: ~" in result.stdout
            assert calls("sudo") == []

        def test_should_delete_nothing_even_with_yes(self, run, fake_bin, sandbox):
            safe, risky = xcode_leftovers(sandbox)
            quiet_tools(fake_bin, sandbox)
            result = run("cleanup", "--yes", timeout=30)
            assert result.returncode == 0
            assert safe.exists() and risky.exists()

    @darwin
    class TestOnApply:
        def test_should_remove_safe_items_and_keep_risky_ones_without_a_terminal(self, run, fake_bin, sandbox):
            safe, risky = xcode_leftovers(sandbox)
            quiet_tools(fake_bin, sandbox)
            result = run("cleanup", "--apply", timeout=30)
            assert result.returncode == 0
            assert not safe.exists() and risky.exists()
            assert "✔ DerivedData cleaned\n" in result.stdout
            assert "ℹ non-interactive: keeping\n▪ Xcode Archives kept\n" in result.stdout

        def test_should_remove_risky_items_with_yes(self, run, fake_bin, sandbox):
            safe, risky = xcode_leftovers(sandbox)
            quiet_tools(fake_bin, sandbox)
            result = run("cleanup", "--apply", "--yes", timeout=30)
            assert result.returncode == 0
            assert not safe.exists() and not risky.exists()
            assert "ℹ auto-yes\n✔ Xcode Archives cleaned\n" in result.stdout

        def test_should_only_ever_hand_system_paths_to_sudo(self, run, fake_bin, calls, sandbox):
            quiet_tools(fake_bin, sandbox)
            run("cleanup", "--apply", timeout=30)
            assert calls("sudo")[0] == ["-v"]
            assert all(call[:3] == ["-n", "rm", "-rf"] for call in calls("sudo")[1:])

    @darwin
    class TestOnBadArguments:
        def test_should_exit_2_on_an_unknown_option(self, run):
            result = run("cleanup", "--nope")
            assert result.returncode == 2
            assert result.stderr == "cleanup: unknown option: --nope\nSee 'cleanup --help'\n"

        def test_should_reject_a_positional_argument(self, run):
            result = run("cleanup", "x")
            assert result.returncode == 2
            assert result.stderr == "cleanup: unexpected argument: x\nSee 'cleanup --help'\n"

        def test_should_reject_a_non_numeric_sim_unused(self, run):
            result = run("cleanup", "--sim-unused", "abc")
            assert result.returncode == 2
            assert result.stderr == "cleanup: --sim-unused: expected a number of days, got 'abc'\nSee 'cleanup --help'\n"

    @pytest.mark.skipif(sys.platform == "darwin", reason="the guard fires on other systems")
    class TestOnLinux:
        def test_should_refuse_to_run(self, run):
            result = run("cleanup")
            assert result.returncode == 1
            assert result.stderr == "cleanup: macOS only\n"


def xcode_leftovers(sandbox):
    safe = sandbox.home / "Library/Developer/Xcode/DerivedData/Foo"
    risky = sandbox.home / "Library/Developer/Xcode/Archives/Bar.xcarchive"
    for path in (safe, risky):
        path.mkdir(parents=True)
        (path / "blob").write_bytes(b"x" * 4096)
    return safe, risky


def quiet_tools(fake_bin, sandbox):
    fake_bin("osascript", stdout="0")
    fake_bin("sudo", exit_code=1)
    fake_bin("getconf", stdout=str(sandbox.home / "tmp/T"))
    fake_bin("xcrun", script=SIMCTL_EMPTY)
    fake_bin("brew", script='[[ $1 == --cache ]] && exit 1\nexit 0\n')
    for tool in ("composer", "gem", "npm", "yarn", "uv", "docker", "plutil"):
        fake_bin(tool, exit_code=1)


SIMCTL_EMPTY = "\n".join([
    'case "$*" in',
    '  "simctl list devices -j") printf \'{"devices":{}}\' ;;',
    '  "simctl runtime list -j") printf "[]" ;;',
    "esac", "exit 0", ""])
```

Why each fake: `osascript` answers the Finder trash count; `sudo -v` must fail or the script starts a `sleep 60` keepalive loop that keeps the test's pipes open for a minute; `getconf` moves the per-user temp dir into the sandbox so the leftover and code-sign-clone scans never see the real one; `xcrun` returns an empty simulator fleet so nothing is listed or deleted; `brew --cache` failing skips the cache size; the package tools exit 1 so `cleanup --apply` runs none of the real `gem cleanup`, `uv cache clean` or `npm cache clean`; `plutil` failing makes the JetBrains step report no installed IDE regardless of `/Applications`. The dry-run totals include real system log directories read with `du`, so the test checks for the line, not the number. The `sudo` calls in apply mode carry the real `/private/var/log` and `/Library/Logs` globs; the fake records and never runs them.

- [ ] **Step 2: Remove the allowlist line and run**

Delete `cleanup = "legacy: test when next touched"` from `tests/untested.toml`.

Run: `uv run --locked pytest tests/bin/test_cleanup.py tests/test_conventions.py -q`
Expected: all pass on this Mac (about 0.5 s per `cleanup` run), `TestOnLinux` skipped.

- [ ] **Step 3: Commit**

```bash
git add tests/bin/test_cleanup.py tests/untested.toml
git commit -m "test(cleanup): cover the dry run, apply, yes and the argument checks"
```

---

### Task 11: op-agent

**Files:**
- Create: `tests/bin/test_op_agent.py`
- Modify: `tests/untested.toml` (remove `op-agent`)

**Interfaces:**
- Consumes: the `op` guard (replaced by a fake) and the `pkill` guard (`stop` falls through to plain `kill`, which ends the daemon).

- [ ] **Step 1: Write the test**

```python
import os
import subprocess

import pytest


class TestOpAgent:
    class TestOnRead:
        def test_should_start_the_daemon_and_print_the_secret_byte_exact(self, run, fake_bin, calls, daemon):
            fake_bin("op", script=OP_SECRET)
            result = run("op-agent", "read", "op://Employee/item/password", timeout=30)
            assert result.returncode == 0
            assert result.stdout == " s3cr=t\n two\n"
            assert calls("op") == [["read", "--no-newline", "op://Employee/item/password"]]
            assert run("op-agent", "status").stdout.startswith("op-agent: running (pid ")

        def test_should_reuse_the_running_daemon(self, run, fake_bin, calls, daemon):
            fake_bin("op", script=OP_SECRET)
            run("op-agent", "read", "op://Employee/item/password", timeout=30)
            status = run("op-agent", "status").stdout
            run("op-agent", "read", "op://Employee/other/password", timeout=30)
            assert run("op-agent", "status").stdout == status
            assert [call[-1] for call in calls("op")] == ["op://Employee/item/password", "op://Employee/other/password"]

        def test_should_relay_an_op_error_and_exit_1(self, run, fake_bin, daemon):
            fake_bin("op", script='printf "[ERROR] no such item\\n" >&2\nexit 1\n')
            result = run("op-agent", "read", "op://Employee/missing/password", timeout=30)
            assert result.returncode == 1
            assert result.stderr == "op-agent: [ERROR] no such item\n"

        class TestOnAPidFileOfAForeignProcess:
            def test_should_give_up_after_the_write_timeout_and_drop_the_pid_file(self, run, sandbox):
                state = sandbox.home / "Library/Application Support/op-agent"
                state.mkdir(parents=True)
                os.mkfifo(state / "req", 0o600)
                with subprocess.Popen(["sleep", "60"]) as foreign:
                    (state / "pid").write_text(str(foreign.pid))
                    result = run("op-agent", "read", "op://Employee/item/password", timeout=30)
                    foreign.kill()
                assert result.returncode == 2
                assert result.stderr == "op-agent: daemon did not accept the request (stale pid file removed — retry)\n"
                assert not (state / "pid").exists()

    class TestOnStop:
        def test_should_end_the_daemon(self, run, fake_bin, daemon):
            fake_bin("op", script=OP_SECRET)
            run("op-agent", "read", "op://Employee/item/password", timeout=30)
            result = run("op-agent", "stop")
            assert result.returncode == 0
            status = run("op-agent", "status")
            assert (status.returncode, status.stdout) == (1, "op-agent: not running\n")

    class TestOnStatus:
        def test_should_exit_1_while_nothing_runs(self, run):
            result = run("op-agent", "status")
            assert (result.returncode, result.stdout) == (1, "op-agent: not running\n")

    class TestOnUnknownCommand:
        def test_should_exit_2(self, run):
            result = run("op-agent", "bogus")
            assert result.returncode == 2
            assert result.stderr == "op-agent: unknown command: bogus (see 'op-agent --help')\n"


OP_SECRET = '[[ $1 == read ]] && printf " s3cr=t\\n two\\n"\nexit 0\n'


@pytest.fixture
def daemon(run):
    yield
    run("op-agent", "stop")
```

The daemon is a real detached process (`nohup python3 … pty.spawn`) under the sandbox's `$HOME/Library/Application Support/op-agent`; the `daemon` fixture stops it after each test that may have started one. The secret has a leading space, an inner newline and a trailing newline on purpose: the base64 protocol must carry all three. The foreign-pid test needs the request FIFO to exist, as it would after an earlier daemon; without it the client's write would create a plain file and wait the full 90 s read timeout instead. That test takes the script's 5 s write timeout; the rest complete in well under a second each.

- [ ] **Step 2: Remove the allowlist line and run**

Delete `op-agent = "legacy: test when next touched"` from `tests/untested.toml`.

Run: `uv run --locked pytest tests/bin/test_op_agent.py tests/test_conventions.py -q; pgrep -fl op-agent || echo "no daemon left"`
Expected: all pass in about 7 s; `no daemon left`.

- [ ] **Step 3: Commit**

```bash
git add tests/bin/test_op_agent.py tests/untested.toml
git commit -m "test(op-agent): cover the daemon lifecycle, byte-exact secrets and the stale pid file"
```

---

### Task 12: gcloud-login, with the Chromium-install fix

**Files:**
- Create: `tests/bin/test_gcloud_login.py`
- Modify: `home/dot_local/exact_bin/executable_gcloud-login:114`
- Modify: `tests/untested.toml` (remove `gcloud-login`)

**Interfaces:**
- Consumes: guards for `gcloud`, `curl`, `npx`, `pkill` (the last stays guarded: the script runs it with `|| true`); fakes shadow the real `op-agent` and `gcloud-login-driver` scripts because fakes precede `bin_links` on `PATH`; `node` and `npx` are faked to satisfy `require_tools`; a fake Chromium binary is placed where `chromium_bin` globs.

- [ ] **Step 1: Write the tests of the existing behaviour**

Create `tests/bin/test_gcloud_login.py`:

```python
import pytest


class TestGcloudLogin:
    class TestOnOptions:
        def test_should_refuse_admin_and_adc_together(self, run):
            result = login(run, "--admin", "--adc")
            assert result.returncode == 1
            assert result.stderr == "✘ gcloud-login: --admin and --adc are mutually exclusive\n"

        @pytest.mark.parametrize("timeout", ["0", "abc"])
        def test_should_require_a_positive_timeout(self, run, timeout):
            result = login(run, f"--timeout={timeout}")
            assert result.returncode == 1
            assert result.stderr.startswith("✘ gcloud-login: --timeout must be a positive integer")

        def test_should_exit_2_on_an_unknown_option(self, run):
            result = login(run, "--nope")
            assert result.returncode == 2
            assert result.stderr == "✘ gcloud-login: unknown option --nope (see 'gcloud-login --help')\n"

    class TestOutsideTheIstaContext:
        def test_should_refuse_to_run(self, run):
            result = run("gcloud-login")
            assert result.returncode == 1
            assert result.stderr == "✘ gcloud-login: only available in the ista context\n"

    class TestOnStatus:
        def test_should_report_both_identities_and_exit_0_when_valid(self, run, fake_bin, calls):
            fake_bin("gcloud", script=GCLOUD_VALID)
            fake_bin("curl", stdout='{"email":"adc@ista-express.de"}')
            result = login(run, "--status")
            assert result.returncode == 0
            assert result.stdout == "CLI account:  me@ista-express.de (valid)\nADC identity: adc@ista-express.de (valid)\n"
            assert calls("curl") == [["-fsS", "https://oauth2.googleapis.com/tokeninfo?access_token=tok"]]

        def test_should_exit_1_when_a_login_is_needed(self, run, fake_bin):
            fake_bin("gcloud", exit_code=1)
            result = login(run, "--status")
            assert result.returncode == 1
            assert result.stdout == "CLI account:  none (needs login)\nADC identity: unknown (needs login)\n"

    class TestOnValidCredentials:
        @pytest.mark.parametrize("args,mode,command", [
            ((), "cli", ["auth", "login", NORMAL, "--quiet"]),
            (("--adc",), "adc", ["auth", "application-default", "login", NORMAL, "--quiet"]),
            (("--admin",), "admin", ["auth", "login", ADMIN, "--quiet"]),
        ], ids=["cli", "adc", "admin"])
        def test_should_do_nothing_and_say_so(self, run, fake_bin, calls, args, mode, command):
            fake_bin("gcloud")
            result = login(run, *args)
            assert result.returncode == 0
            assert result.stderr.endswith(f"✔ Credentials for {command[-2]} are still valid ({mode}); nothing to do\n")
            assert calls("gcloud") == [command]

    class TestOnGcloudFailingBeforeTheBrowser:
        def test_should_relay_its_output_and_exit_1(self, run, fake_bin):
            fake_bin("gcloud", script='echo "ERROR: boom" >&2\nexit 1\n')
            result = login(run)
            assert result.returncode == 1
            assert result.stderr.endswith("ERROR: boom\n✘ gcloud-login: gcloud failed before opening a browser\n")

        def test_should_exit_2_when_no_url_arrives_in_time(self, run, fake_bin):
            fake_bin("gcloud", script="sleep 5\n")
            result = login(run, "--timeout", "1")
            assert result.returncode == 2
            assert result.stderr.endswith("✘ gcloud-login: gcloud produced no auth url within 1s\n")

    class TestOnTheBrowserFlow:
        def test_should_drive_the_login_with_the_admin_password_from_op_agent(self, run, fake_bin, calls, sandbox):
            browser_tools(fake_bin, sandbox)
            fake_bin("op-agent", script='[[ $1 == status ]] && exit 1\nprintf hunter2\n')
            fake_bin("gcloud-login-driver", script='cat > "$HOME/driver.stdin"\ntouch "$HOME/callback"\nexit 0\n')
            result = login(run, "--admin", timeout=30)
            assert result.returncode == 0
            assert result.stderr.endswith(f"✔ Logged in (admin) as {ADMIN}\n")
            profile = sandbox.home / "Library/Application Support/gcloud-login/admin"
            [driver] = calls("gcloud-login-driver")
            assert driver[:3] == ["--port-file", str(profile / "DevToolsActivePort"), "--url-file"]
            assert driver[4:] == ["--email", ADMIN, "--timeout", "120"]
            assert (sandbox.home / "driver.stdin").read_text() == "hunter2"
            assert calls("op-agent") == [["status"], ["read", "op://Employee/p44thhnd5ylh6zrm6etwozs63a/password"]]
            assert (sandbox.home / "chromium.args").read_text().splitlines() == [
                f"--user-data-dir={profile}", "--remote-debugging-port=0", "--no-first-run",
                "--no-default-browser-check", "--no-startup-window"]

        def test_should_exit_2_when_the_driver_times_out_and_gcloud_never_finishes(self, run, fake_bin, sandbox):
            browser_tools(fake_bin, sandbox)
            fake_bin("gcloud-login-driver", exit_code=2)
            result = login(run, "--timeout", "1", timeout=30)
            assert result.returncode == 2
            assert ("! gcloud-login: automation stopped (driver exit 2); "
                    "finish the login in the Chromium window or press Ctrl-C\n") in result.stderr
            assert result.stderr.endswith("✘ gcloud-login: browser flow timed out\n")


NORMAL = "bjoern.kahlert@ista-express.de"
ADMIN = "bjoern.kahlert.admin@ista-express.de"

GCLOUD_VALID = "\n".join([
    'case "$*" in',
    '  "config get-value account") echo me@ista-express.de ;;',
    '  "auth print-access-token --quiet") exit 0 ;;',
    '  "auth application-default print-access-token") echo tok ;;',
    "esac", "exit 0", ""])

GCLOUD_BROWSER = "\n".join([
    'case "$*" in',
    '  "auth login "*|"auth application-default login "*)',
    "    printf 'https://accounts.google.com/o/oauth2/auth?x=1' > \"$GCLOUD_LOGIN_URL_FILE\"",
    '    for ((i = 0; i < 100; i++)); do [[ -e "$HOME/callback" ]] && exit 0; sleep 0.1; done',
    "    exit 1 ;;",
    "esac", "exit 0", ""])

CHROMIUM = "\n".join([
    "#!/usr/bin/env bash",
    'for arg in "$@"; do [[ $arg == --user-data-dir=* ]] && profile=${arg#*=}; done',
    'printf "%s\\n" "$@" > "$HOME/chromium.args"',
    'printf "9222\\n/devtools/browser/x\\n" > "$profile/DevToolsActivePort"',
    "exec sleep 30", ""])


def login(run, *args, **kwargs):
    return run("env", "DOTFILES_CONTEXT=ista", "gcloud-login", *args, **kwargs)


def browser_tools(fake_bin, sandbox):
    fake_bin("gcloud", script=GCLOUD_BROWSER)
    fake_bin("node")
    fake_bin("npx")
    chromium = sandbox.home / ".cache/gcloud-login/chromium/mac_arm-1702741/chrome-mac/Chromium.app/Contents/MacOS/Chromium"
    chromium.parent.mkdir(parents=True)
    chromium.write_text(CHROMIUM)
    chromium.chmod(0o755)
```

The fake `gcloud` plays the real one's part: it writes the OAuth URL to the file the script exports as `GCLOUD_LOGIN_URL_FILE`, then waits for the "callback" the fake driver signals with a file. The fake Chromium writes `DevToolsActivePort` into the profile the script passes and then sleeps until the script's EXIT trap kills it. `pkill` stays guarded; the script runs it with `|| true` and its stderr discarded.

- [ ] **Step 2: Remove the allowlist line and run**

Delete `gcloud-login = "legacy: test when next touched"` from `tests/untested.toml`.

Run: `uv run --locked pytest tests/bin/test_gcloud_login.py tests/test_conventions.py -q`
Expected: all pass in about 4 s (the two timeout tests wait their 1 s).

- [ ] **Step 3: Commit the characterization tests**

```bash
git add tests/bin/test_gcloud_login.py tests/untested.toml
git commit -m "test(gcloud-login): cover the modes, the status report and the browser flow with fakes"
```

- [ ] **Step 4: Write the failing test for the silent installation failure**

Add inside `TestOnTheBrowserFlow`:

```python
class TestGcloudLogin:
    class TestOnTheBrowserFlow:
        ...

        class TestOnAFailingChromiumInstall:
            def test_should_say_so_and_exit_1(self, run, fake_bin, calls, sandbox):
                fake_bin("gcloud", script=GCLOUD_BROWSER)
                fake_bin("node")
                fake_bin("npx", exit_code=1)
                result = login(run, timeout=30)
                assert result.returncode == 1
                assert result.stderr.endswith("✘ gcloud-login: Chromium install failed\n")
                assert calls("npx") == [["--yes", "@puppeteer/browsers", "install", "chromium@1702741",
                                         "--path", f"{sandbox.home}/.cache/gcloud-login"]]
```

- [ ] **Step 5: Run it to verify it fails**

Run: `uv run --locked pytest tests/bin/test_gcloud_login.py -q -k FailingChromiumInstall`
Expected: FAIL: stderr ends with `ℹ Installing Chromium 1702741 (plain build, immune to the managed-profile interception)\n`; `set -e` ended the script with npx's status before `die` could run.

- [ ] **Step 6: Report the failure**

`home/dot_local/exact_bin/executable_gcloud-login` line 114:

```bash
  npx --yes @puppeteer/browsers install "chromium@$CHROMIUM_BUILD" --path "$CACHE_DIR" >/dev/null \
    || die "gcloud-login: Chromium install failed"
```

Line 115 (`[[ -n "$(chromium_bin)" ]] || die ...`) stays for an installation that succeeds without producing the binary.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run --locked pytest tests/bin/test_gcloud_login.py -q && shellcheck home/dot_local/exact_bin/executable_gcloud-login`
Expected: all pass; shellcheck silent.

- [ ] **Step 8: Commit**

```bash
git add home/dot_local/exact_bin/executable_gcloud-login tests/bin/test_gcloud_login.py
git commit -m "fix(gcloud-login): report a failed Chromium install" -m "set -e ended the script with npx's status before the die line could print."
```

---

## Finish

- [ ] **Full verification**

Run: `make lint && uv run --locked pytest -m "not integration" -q`
Expected: lint clean; every test passes, three skipped (`print-port` on Linux, `cleanup` `TestOnLinux` on a Mac and the reverse elsewhere). Check `tests/untested.toml`: `[bin]` has lost `cert-get`, `cert-print`, `cleanup`, `gcloud-login`, `killport`, `known-hosts-fix`, `op-agent`, `pick-port`, `print-port`, `timeout`, `upgrade-all`; 18 legacy entries remain.

Run: `pgrep -fl 'op-agent|sleep 30' || echo clean`
Expected: `clean` (no daemon or fake Chromium survived the suite).

- [ ] **Ship (two offers, the AGENTS.md flow; ask before `git push` and again before the merge)**

PR title `test: unit tests for the scripts with logic`; body lists the three script changes (`known-hosts-fix -f`, `gcloud-login` install error, Brewfile `bash`) separately from the tests, and notes for existing machines: `brew install bash` by hand (the Brewfile runs once per machine) and that `chezmoi apply` removes `~/.claude/statusline-test` and `~/.claude/statusline-input.json` via `.chezmoiremove`. Then `gh pr checks <n> --watch --fail-fast`, squash-merge, delete the branch, `git fetch origin && git merge --ff-only origin/main` on `main` (plain `git pull` fails on this machine's `pull.rebase` with the unstaged scratch file).

## Follow-up: PR 3

The remaining `legacy` entries are wrappers (`box`, `docker`, `explain`, `flushdns`, `idea`, `idea-wait`, `mir`, `notify`, `omlx`, `pbcopy-dir`, `pbpaste-dir`, `serve`, `serve-live`, `gcloud-login-browser`), two with some logic (`ansi-test`, `dscleanup`, `grepr`, `intellij-workspace-fix`), and the eight `conf.d` modules. Each gets its test when its behaviour is next touched; wrappers around `open`, `osascript` or `pbcopy` get a permanent entry with that reason instead.
