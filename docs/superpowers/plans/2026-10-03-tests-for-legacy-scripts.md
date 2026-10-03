# Tests for the legacy-allowlisted scripts

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every `[bin]` entry in `tests/untested.toml` except `intellij-workspace-fix` gets a real test and loses its `legacy` line. Reading the scripts found three defects; each gets a failing test first, then a fix, one `fix(<script>)` commit per script.

**Decision (2026-10-03, with the user):** test all 18 scripts (no permanent entries); fix the defects in this PR; `conf.d` modules are out of scope (`08-print` was removed in its own PR; `90-scratch` is the user's work in progress).

## Defects

1. `explain` percent-encodes nothing but spaces: `+7`, `&`, `#`, `%` and quotes reach explainshell.com raw, so the example in its own help opens a wrong URL.
2. `${N?message}` makes bash print its own error with the script path and exit 1; `bash.md` wants the one-line `die` and exit 2. Scripts: `box` (`--image`), `notify` (`--title`, `--subtitle`, `--sound`), `gcloud-login-browser` (`url`), `cleanup` (`--sim-unused`), `gcloud-login` (`--timeout`), `op-agent` (`read`).
3. ~~`box` exits under `set -u` when `TERM` is unset.~~ Not a defect: bash defaults an unset `TERM` to `dumb`, even under `set -u`. A test pins it.

## Global Constraints

- Branch `test/legacy-script-tests`. Never commit on `main`. Never stage `home/private_dot_config/zsh/exact_conf.d/90-scratch.zsh`; `git add` explicit paths only.
- Test command `uv run --locked pytest -m "not integration" -q`; `make lint` before the PR. Do not touch `tests/gcloud-login-driver.test.js`, `executable_gcloud-login-driver` or the Makefile's `node --test` line.
- One test file per script: `tests/bin/test_<name>.py` (hyphens as underscores). The entry leaves `tests/untested.toml` in the same commit as its test.
- Characterization tests of untouched behaviour pass on first run; every defect fix has a RED run first.
- `idea` and `omlx` also probe absolute paths (`/Applications`, `/opt/homebrew/bin`); their "not found" tests skip where the tool is installed. No test-only seams.
- `intellij-workspace-fix` is left out (2026-10-03, user): it is being rewritten in Python elsewhere, which brings its own tests; its `legacy` entry stays and CI installs no `xmlstarlet`.
- Tests follow `~/.config/agents/rules/testing.md`, scripts `bash.md`, commits `git.md`. JetBrains inspections (`errorsOnly: false`) on every changed file before each commit.

## Tasks

- [x] **1. Wrappers and lookups:** `box` (+ defect 2), `docker`, `idea`, `idea-wait`, `omlx`.
- [x] **2. Filesystem tools:** `dscleanup`, `grepr`, `mir`, `pbcopy-dir`, `pbpaste-dir`.
- [x] **3. Notifiers and openers:** `explain` (+ defect 1), `flushdns`, `notify` (+ defect 2), `gcloud-login-browser` (+ defect 2).
- [x] **4. Servers and reference card:** `serve`, `serve-live`, `ansi-test`, `intellij-workspace-fix` (dropped, see constraints).
- [x] **5. Remaining `${N?}` sites:** `cleanup --sim-unused`, `gcloud-login --timeout`, `op-agent read`.
- [ ] **6. Verify and ship.** Suite, `make lint`, code review on `fable`, then the `chezmoi apply` offer.
