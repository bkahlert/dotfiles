# Statusline in Python Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `~/.claude/statusline` renders correctly when Claude Code starts from the Dock, where `#!/usr/bin/env bash` resolves to macOS's bash 3.2 and the bash ≥ 4.2 constructs (`$'\uXXXX'`, `${id,,}`) print literally or fail with "bad substitution". The script becomes stdlib-only Python 3.9, the version `/usr/bin/python3` has on every Mac, so nothing depends on `PATH` or Homebrew.

**Decision (2026-10-03, with the user):** rewrite in Python. Rejected: re-exec into Homebrew bash (a fix that still depends on Homebrew), failing fast plus a `launchctl setenv PATH` (environment state outside the repo), and rewriting for bash 3.2 (locale-dependent `printf '\u'`).

**Architecture:** one file, `home/private_dot_claude/executable_statusline`, `#!/usr/bin/env python3`. Same CLI (`--nerd-fonts`, `--no-nerd-fonts`, `--preview`, `-h/--help`, exit 2 with a hint on unknown options), same header, same output byte for byte. One pure function per part, taking the parsed session dict and a `nerd` flag; `main()` joins the non-empty parts with ` · `. No `jq`, `awk` or `date` calls.

**Tech Stack:** Python 3.9 stdlib, pytest via `uv run --locked`, chezmoi.

## Global Constraints

- Branch `fix/statusline-python`. Never commit on `main`. Never stage `home/private_dot_config/zsh/exact_conf.d/90-scratch.zsh`; `git add` explicit paths only.
- Test command: `uv run --locked pytest -m "not integration" -q`; `make lint` before the PR. Do not touch `tests/gcloud-login-driver.test.js`, `executable_gcloud-login-driver` or the Makefile's `node --test` line.
- The script must run on Python 3.9: no `match`, no `X | Y` annotations at runtime, no `zip(strict=)`.
- Preserved on purpose, not fixed here: unparsable stdin renders the defaults and exits 0.
- Tests follow `~/.config/agents/rules/testing.md`. Commits follow `~/.config/agents/rules/git.md`, no AI attribution trailers. PR title: `fix(claude): render the statusline without a modern bash`.
- JetBrains MCP is connected: `mcp__idea__get_file_problems` with `errorsOnly: false` on every changed file before each commit.

## Tasks

- [x] **1. Tests lose the clock fake.** The Python script reads `time.time()`, not `date`. `sample()` and the cases in `test_statusline.py` compute `resets_at` from the real time, aimed at the middle of each rounding bucket (`now + 65300` s renders `¹⁸·¹ʰ`, `now + 358400` s renders `⁴·¹ᵈ`; the offsets sit near the top of their bucket, so elapsed test time only moves them inward). The `clock` fixture and `FROZEN` go. Run against the bash script: still green.
- [x] **2. Pin the bug.** `TestOnGuiLaunch.test_should_render_with_only_the_system_path`: `run("env", "PATH=/usr/bin:/bin", "statusline", "--nerd-fonts", stdin=...)` renders `NERD`. Red against the bash script on a Mac (`/usr/bin/env bash` is 3.2 there); the Python script makes it green.
- [x] **3. Rewrite the script in Python.** Port every behaviour the tests pin plus the ones they do not: `%g` token sizes, `int(usd*100)` truncation, the `[0:8]` session id, superscript tables, 10-segment bar thresholds, the Nerd Font probe with cache and `NERD_FONTS` override, local-before-global settings model.
- [x] **4. Idiomatic pass.** A Python specialist agent refactors the working script for clarity and idiom with the suite as the guard; behaviour and output unchanged, Python 3.9 compatible.
- [x] **5. Packaging.** Homebrew `bash` stays in the Brewfile and the macOS CI job: `cleanup`, `op-agent`, `gcloud-login` and `known-hosts-fix` need bash ≥ 4.4 (empty arrays under `set -u`, job notices, FIFO reads), found in review after a first attempt to drop it. Only the Brewfile comment changes.
- [ ] **6. Verify and ship.** Suite, `make lint`, inspections, code review on `fable`, then the `chezmoi apply` offer for the one file.
