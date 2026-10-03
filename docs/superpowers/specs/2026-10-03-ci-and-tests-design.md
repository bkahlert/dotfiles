# CI gate and test suite

Design for three asks: merges to `main` must pass tests, the tests must mean something, and future
changes must not go untested. Approved in conversation on 2026-10-03; the research behind the
tooling choices is summarised in [Decisions](#decisions).

## Goal

A green check on `main` guarantees:

1. `chezmoi apply` succeeds for every context (`company` = `""`, `bkahlert`, `ista`) on a fresh
   Linux machine and a fresh macOS machine, with the secret managers replaced by fakes.
2. Once applied, an interactive login zsh starts with exit code 0 and **no output on stderr**,
   within a time bound. This is the bug class behind #23, #34, #43 and #67.
3. The scripts in `bin/` and the autoloaded zsh functions behave as claimed, verified by unit tests
   that run the real script in an isolated environment with faked external commands.
4. Every script, function and function-defining zsh module either has a test or is listed with a
   reason. The list only shrinks.

## Out of scope

- A git-diff-aware check that enforces the "test when touched" ratchet mechanically.
- Per-context assertions on rendered files and `chezmoi verify`; the apply exit code covers apply
  correctness.
- `shfmt` formatting enforcement.
- Line coverage tooling (kcov, bashcov): fragile on macOS bash 3.2 and blind to zsh.
- Running the `run_once`/`run_onchange` scripts on macOS under test; they install Homebrew
  packages and register a LaunchAgent, which does not belong on a runner or in a temp home.

## Decisions

| Decision | Rationale |
|---|---|
| **pytest** for bash scripts, zsh functions and the integration legs | Honours the nesting rule in [testing.md](../../../home/private_dot_config/exact_agents/exact_rules/testing.md) fully (class = subject, nested class = context, method = claim), parametrizes over contexts in one line, best failure diagnostics, `uv` already on the machine. |
| Not bats-core | De-facto standard and alive (1.14, 2026-07), but flat test names and weaker diagnostics. Would have been the pick if a single toolchain mattered more than nesting. |
| Not ShellSpec, shunit2, zunit | Dormant or dead (no release since 2021, 2020, 2018). |
| Not bashunit | Active but pre-1.0 with releases every few weeks; API churn in a repo touched occasionally. |
| Not Go testscript | Excellent for golden-output checks (chezmoi tests itself with it) but no named cases, no exit-code assertion, no JUnit. |
| `node:test` stays for the Node driver only | Existing test; the subject is JavaScript. |
| Mocks are PATH shims, not function overrides | Subjects are separate processes (bash scripts, zsh); function mocks never reach them. Same primitive chezmoi uses to test its own `op`/`keepassxc-cli` integration. |
| One required check named `ci`, an aggregator job | Jobs can be renamed or split without touching the ruleset; a skipped upstream job counts as success for GitHub, so the aggregator checks results itself. |
| No `paths:` filter on the workflow | A filtered-out workflow leaves the required check pending and blocks the merge. |
| Weekly cron | The image and the macOS job install the latest chezmoi, sheldon, starship and zoxide; upstream can break the suite without a commit here. |
| `make` targets are the only thing CI runs | Local and CI are the same command. No `act`, no Dagger. |
| Container only by default on a developer Mac; native macOS leg opt-in | The container is the stronger sandbox. The native leg exists for CI's macOS coverage and for reproducing a macOS failure. |

## Test layers

| Target | Runs | Where |
|---|---|---|
| `make lint` | `shellcheck` on every file in the repo with a bash shebang or a `.sh`/`.bash` suffix, `.tmpl` files excluded; `zsh -n` on every `*.zsh` file (the one `.zsh.tmpl` does not parse raw and is covered by the integration legs); `actionlint` and `zizmor` on `.github/workflows` | locally, `checks` job |
| `make unit` | `uv run pytest -m "not integration"` and `node --test tests/` | locally, `checks` job, `macos` job |
| `make integration` | `uv run pytest tests/integration/test_apply_container.py` | locally (needs Podman), `integration` job |
| `make integration-native` | `uv run pytest tests/integration/test_apply_native.py` | `macos` job; locally on request |
| `make ci` | `lint unit integration` | convenience |

`make image` builds the test image (`--target base`). `make run`, `make vnc`, `make stop`, `make clean`
keep their current meaning; `make run` builds the `vnc` target. `make validate` is removed.
`CONTAINER_ENGINE ?= podman` in the Makefile and `CONTAINER_ENGINE` in the tests allow `docker`.

### Layout

```
pyproject.toml, uv.lock             # pytest as the only dev dependency; pytest config in pyproject
tests/
  conftest.py                       # fixtures: run, fake_bin, zsh, sandbox_env
  untested.toml                     # allowlist, see Enforcement
  test_conventions.py               # the allowlist test
  bin/test_<script>.py              # one module per bin/ script; hyphens become underscores
  functions/test_<fn>.py            # one per autoloaded zsh function
  zsh/test_<module>.py              # conf.d modules that define functions; numeric prefix dropped
  zsh/ista/test_<module>.py         # same for exact_ista/
  integration/
    test_apply_container.py
    test_apply_native.py
  shims/op                          # fake 1Password CLI
  shims/keepassxc-cli               # fake KeePassXC CLI
  gcloud-login-driver.test.js       # unchanged location, node:test
```

`tests/`, `docs/` and `pyproject.toml` are outside `home/` (`.chezmoiroot`), so chezmoi never sees
them; `tests/` is also in [.chezmoiignore](../../../home/.chezmoiignore) already.
`.venv/`, `.pytest_cache/` and `node_modules/` go into `.gitignore`.

### Unit tests

Fixtures in `tests/conftest.py`:

- `sandbox_env(tmp_path)`: a **minimal** environment, never the inherited one. `HOME`,
  `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME` and `TMPDIR` under
  `tmp_path`; `PATH` = the shim directory, then the system directories (`/usr/bin:/bin:/usr/sbin:/sbin`,
  plus Homebrew's bin on macOS so `jq` and friends resolve); `TERM=dumb`; `LANG=C.UTF-8`;
  `DOTFILES_CONTEXT` unset unless a test sets it.
- `fake_bin(name, *, stdout="", stderr="", exit_code=0, script=None)`: writes an executable shim
  into the shim directory that appends its arguments, one call per line, to
  `<shimdir>/.calls/<name>` and then prints the canned output or runs `script`.
  `fake_bin.calls(name)` returns the recorded argument lists.
- `run(name, *args, stdin=None, timeout=10)`: runs the script by its target name in `sandbox_env`,
  captures stdout and stderr as text, returns the `CompletedProcess`. A session-scoped directory of
  target-named symlinks into `home/dot_local/exact_bin/` sits on `PATH` after the shims, so
  `gh-latest` resolves and so does a sibling a script calls, such as `gcloud-login-driver`. No apply
  is needed to unit-test a script.
- `zsh(snippet, *, module=None, function=None)`: runs `zsh -f -c` in `sandbox_env` with `fpath`
  pointing at `exact_functions/` and the requested function autoloaded, or the requested
  `conf.d` module sourced first.

Conventions:

- Classes nest as the testing rule asks: `class TestGhLatest:`, inside it `class TestOnUnknownOption:`,
  inside that `def test_should_exit_2_and_name_the_option(...)`. Test cases first, helpers at the
  bottom of the module.
- Unit tests never reach the network or a secret manager; every external command the subject calls
  is a `fake_bin`. Coreutils, `awk`, `sed`, `jq` are real.
- A script whose only behaviour is delegating to a macOS tool (`open`, `osascript`, `pbcopy`) is
  listed in `untested.toml`, not tested by asserting that a fake was called.
- The driver test reads `CHROMIUM_BIN` first and falls back to today's cache lookup. When `CI` is
  set and no browser is found, the test fails instead of skipping.

### Integration: container

[Containerfile](../../../Containerfile) becomes two stages:

- `base`: Fedora, `zsh git curl jq findutils procps-ng`, chezmoi, sheldon, starship, zoxide,
  entrypoint. `HEALTHCHECK NONE` stays.
- `vnc` (`FROM base`): tigervnc, fluxbox, xterm, Ghostty from the COPR, VNC password.

[entrypoint.sh](../../../entrypoint.sh) contract:

- Reads `DOTFILES_COMPANY` (default empty) and writes `~/.config/chezmoi/chezmoi.toml` with
  `email`, `name`, `company` under `[data]`, as today.
- Prepends `/opt/shims` to `PATH` when that directory exists.
- Runs `chezmoi init --apply --no-tty --source /dotfiles/home` with **stderr redirected to
  stdout**, so everything the apply prints is informational. Stdin is left to the caller; the test
  supplies one dummy line, which chezmoi reads as the KeePassXC password under `--no-tty` and
  forwards to the fake `keepassxc-cli`.
- Then `exec zsh -li "$@"`; the `vnc` argument keeps its current branch.

`tests/integration/test_apply_container.py`:

- Session fixture: `<engine> build --target base -t dotfiles-test:base .` from the repo root. If
  the engine is missing, the fixture **fails** with a message naming `CONTAINER_ENGINE`; it does
  not skip.
- Parametrized over `company in ("", "bkahlert", "ista")`:
  `<engine> run --rm -i -e TERM=xterm-256color -e DOTFILES_COMPANY=<company>
  -v <repo>:/dotfiles:ro -v <repo>/tests/shims:/opt/shims:ro dotfiles-test:base -c true`
  with stdin `"dummy-password\n"`, stdout and stderr captured separately, `timeout=300`.
- Asserts `returncode == 0` and `stderr == ""`. On failure the assertion message includes both
  streams, so a failed apply and a noisy module are both readable.

### Integration: native macOS

`tests/integration/test_apply_native.py`, skipped with the reason "native apply targets macOS"
on every other OS:

- Preconditions, checked once and failing with a message if unmet: `chezmoi`, `sheldon`,
  `starship`, `zoxide` on `PATH`.
- Per `company`: a temp home; `sandbox_env` with the shims first on `PATH`, followed by Homebrew's
  bin and the system directories. **Preflight:** `chezmoi data --format json` in that environment
  must report `.chezmoi.homeDir` equal to the temp home, otherwise the test fails before applying.
- Writes the `[data]` config as the entrypoint does, then
  `chezmoi init --apply --exclude=scripts --no-tty --source <repo>/home` with the dummy password
  on stdin, then `zsh -li -c true </dev/null` in the same environment.
- Asserts the same as the container leg.

Isolation argument, documented in AGENTS.md: every path chezmoi and the shell startup touch
derives from `HOME`, `ZDOTDIR` or an `XDG_*` variable, all of which point into the temp home;
`--exclude=scripts` keeps `launchctl`, `defaults write`, `brew bundle` and `sheldon lock` out; the
shims shadow the real `op` and `keepassxc-cli`. A future module that writes to an absolute path at
startup would escape this sandbox; the container leg fails on such a module because the path does
not exist there.

### Fake secret CLIs

`tests/shims/op` (bash):

- `--version` prints `2.30.0`.
- `read <op://vault/item/field>` prints `fake:<item>/<field>` without a trailing newline when
  `--no-newline` is given, with one otherwise.
- Anything else exits 1 with `op: unsupported in tests: <args>` on stderr.

`tests/shims/keepassxc-cli` (bash):

- `--version` prints `2.7.9`.
- `show ... <entry>` prints `Title: <entry>`, `UserName: fake-user`, `Password: fake:<entry>`,
  `URL:`, `Notes:`; stdin (the password) is consumed and ignored.
- `attachment-export ...` prints `fake-attachment`.
- Anything else exits 1 with a message, as above.

Both shims are plain bash, executable, shellcheck-clean, and used identically by the container
and the native leg.

## CI workflow

`.github/workflows/ci.yml`, name `ci`:

- **Triggers:** `pull_request` (branches `main`), `push` (branches `main`),
  `schedule` weekly, `workflow_dispatch`. No `paths:`.
- **Top level:** `permissions: contents: read`; `concurrency` grouped by workflow and PR number
  or ref, `cancel-in-progress` only for `pull_request` events.
- **Job `checks`** (`ubuntu-24.04`, `timeout-minutes: 15`): checkout with
  `persist-credentials: false`; `apt-get install zsh`; `astral-sh/setup-uv`; actionlint via its
  pinned download script; `make lint unit` with `CHROMIUM_BIN=/usr/bin/google-chrome`.
- **Job `integration`** (`ubuntu-24.04`, `timeout-minutes: 30`): checkout; `setup-uv`;
  `make integration`. Podman is preinstalled on the image.
- **Job `macos`** (`macos-latest`, `timeout-minutes: 30`): checkout; `brew install chezmoi sheldon
  starship zoxide`; `setup-uv`; `make unit integration-native`.
- **Job `ci`** (`if: always()`, `needs: [checks, integration, macos]`, `timeout-minutes: 2`):
  fails unless every `needs.*.result` is `success`. The only required check.
- **`zizmor`** runs inside `make lint` as `uvx zizmor==1.30.1` so local and CI use one command;
  `actionlint` is a Homebrew formula locally and the pinned upstream download script on the runner.
- **Pins:** every `uses:` by full commit SHA with a `# vX.Y.Z` comment.
- **`.github/dependabot.yml`:** `github-actions` weekly and `uv` weekly, `cooldown` 3 days.

## Merge gate

Sequence: open the PR that adds the workflow, wait for its first green run, then change the ruleset
and repository settings, then merge.

Ruleset `main` (id 15788010) keeps `deletion` and `non_fast_forward` and gains:

```json
{"type":"pull_request","parameters":{
  "required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,
  "require_code_owner_review":false,"require_last_push_approval":false,
  "required_review_thread_resolution":false,"allowed_merge_methods":["squash"]}}
{"type":"required_status_checks","parameters":{
  "strict_required_status_checks_policy":false,"do_not_enforce_on_create":false,
  "required_status_checks":[{"context":"ci","integration_id":15368}]}}
```

Applied by reading the ruleset, appending the two rules, and `PUT`ting the whole object back
(the API's replace-versus-merge semantics for `rules` are undocumented; sending the full array is
correct either way). `integration_id` 15368 is the GitHub Actions app, so no other app can
satisfy the `ci` context.

Repository settings: default workflow token permission `read`
(`actions/permissions/workflow`: `default_workflow_permissions=read`,
`can_approve_pull_request_reviews=false`); `sha_pinning_required=true` after all actions are pinned.
Auto-merge stays disabled.

No bypass actor. If CI itself is broken, fix it through a PR; if that is impossible, set the
ruleset's `enforcement` to `disabled`, merge the fix, re-enable.

Ship flow in [AGENTS.md](../../../AGENTS.md), Offer 2: `gh pr checks --watch --fail-fast` runs
before `gh pr merge --squash --delete-branch`, because the merge is rejected while checks run.

## Enforcement

`tests/test_conventions.py` fails when:

1. A `home/dot_local/exact_bin/executable_<name>` has neither `tests/bin/test_<name>.py` (hyphens
   as underscores) nor an entry under `[bin]` in `tests/untested.toml`.
2. A `home/private_dot_config/zsh/exact_functions/<name>` has neither `tests/functions/test_<name>.py`
   nor an entry under `[functions]`.
3. A `conf.d` module (`exact_conf.d/**/*.zsh`, `*.zsh.tmpl`) that defines a function, detected by
   a line matching `^\s*(function\s+)?[A-Za-z_][A-Za-z0-9_-]*\s*\(\)\s*\{?` or
   `^\s*function\s+[A-Za-z_]`, has neither `tests/zsh/[ista/]test_<module>.py` (numeric prefix and
   dash dropped, hyphens as underscores, `.tmpl` ignored) nor an entry under `[conf_d]`.
4. An allowlist entry names a file that does not exist, or a file that has a test. Stale entries
   are errors, so the list cannot drift.

`tests/untested.toml`:

```toml
# Files without a test, each with the reason. "legacy" entries go when the file is next touched:
# that change adds the test and removes the line.
[bin]
flushdns = "legacy: test when next touched"
idea = "wraps `open -a`; no logic"

[functions]

[conf_d]
"ista/10-idp" = "legacy: test when next touched"
```

The baseline lists every currently untested file. The ratchet is a rule in AGENTS.md: a change to
a listed file adds its test and removes the entry in the same PR; permanent entries carry a reason
other than "legacy".

## Documentation changes

- [AGENTS.md](../../../AGENTS.md): a **Testing** section with the targets table, the layout, where
  a test for each kind of thing goes, the fixtures, the integration legs and the fake CLIs, the
  isolation argument for the native leg, the allowlist ratchet, and the rule that startup code
  writes only under `HOME`. The ship flow gains the `gh pr checks` step. The Testing block at the
  end is replaced by the targets.
- [quick-access/README.md](../../../quick-access/README.md): each location in the map gets its
  test folder; "Where does a new thing go?" says the test goes with it.
- [README.md](../../../README.md): "Testing in a container" becomes "Testing" with the targets.
- [testing.md](../../../home/private_dot_config/exact_agents/exact_rules/testing.md), Framework
  Adaptability: a pytest line, classes for subject and context, `test_should_*` for the claim.
- Brewfile in
  [run_once_before_01-install-packages.sh](../../../home/.chezmoiscripts/run_once_before_01-install-packages.sh):
  `shellcheck` and `actionlint` with the required purpose comments; `uv` is already listed.

## Delivery

**PR 1, `ci: gate merges on lint, unit and integration tests`:** pyproject and lockfile, conftest
and fixtures, `test_conventions.py` with the full baseline allowlist, both integration tests, the
shims, the Containerfile split and entrypoint contract, the Makefile, the `CHROMIUM_BIN` override
in the driver test, the workflow and Dependabot config, the documentation changes, and whatever
module fixes the first `ista` and `bkahlert` runs on a fresh home surface. Then the ruleset and
repository settings, then merge.

**PR 2, `test: unit tests for the scripts with logic`:** the statusline harness becomes
`tests/bin/test_statusline.py` with assertions on the three modes; unit tests for the scripts whose
behaviour is more than delegation, as the pattern for everything after; matching allowlist
removals.

### To verify during implementation

- Whether `--exclude=scripts` also skips rendering script templates. If it does not, the
  `dump-ssh-from-kdbx` template's `output "shasum"` call aborts the native leg on a runner without
  the iCloud file, and the template needs a `stat` guard. That guard is a real fix: a fresh Mac
  before iCloud sync hits the same path.
- Rootless `podman build` and `podman run` with a read-only bind mount on `ubuntu-24.04`.
- Google Chrome's sandbox on the current runner image; fallback is the documented
  `kernel.apparmor_restrict_unprivileged_userns=0` sysctl step.
- How much stderr the `ista` and `bkahlert` contexts produce today on a fresh home. Each line is a
  module to guard, which is the point of the gate.

## Research

Two reports informed the decisions and are kept out of the repository: a comparison of shell test
frameworks and zsh testing practice, and a survey of GitHub Actions gate mechanics and reference
dotfiles pipelines (twpayne/chezmoi, shunk031/dotfiles, zsltg/dot, kitos9112/dotfiles). The
load-bearing facts are restated above.
