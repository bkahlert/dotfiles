# Dotfiles Repository — Agent Guide

This repo manages dotfiles with [chezmoi](https://www.chezmoi.io/). Source state lives in `home/` (set by `.chezmoiroot`). Chezmoi copies files to `$HOME` — no symlinks.

## Chezmoi Naming Conventions

Source files in `home/` use chezmoi prefixes that control target name, permissions, and behavior:

| Prefix/Suffix | Meaning | Example |
|---|---|---|
| `dot_` | Target name starts with `.` | `dot_gitconfig` → `~/.gitconfig` |
| `private_` | File mode `0600` / dir mode `0700` | `private_dot_ssh/` → `~/.ssh/` (0700) |
| `exact_` | Dir is exact: files not in source are **removed** from target | `exact_conf.d/` |
| `empty_` | Create empty file if it doesn't exist | `empty_dot_hushlogin` → `~/.hushlogin` |
| `executable_` | File mode `0755` | `executable_dot_osx` → `~/.osx` |
| `.tmpl` suffix | File is a Go template, rendered at apply time | `dot_gitconfig.tmpl` |
| `run_once_before_` | Script runs once before file changes | install scripts |
| `run_once_after_` | Script runs once after file changes | setup scripts |
| `run_onchange_after_` | Script runs when its content hash changes | plugin lock |
| `modify_` | Script receives the current target on stdin and prints the new content; use to own a few keys in an app-managed file | `modify_private_claude_desktop_config.json` |

## Template Data

Defined in [.chezmoi.toml.tmpl](home/.chezmoi.toml.tmpl), prompted on `chezmoi init`:

| Variable | Type | Usage |
|---|---|---|
| `.email` | string | Git config email |
| `.name` | string | Git config name |
| `.company` | string | Context name — `"bkahlert"` personal, `"ista"` business, empty for none (the test container). An identifier, not a business flag. |
| `.chezmoi.os` | string | `"darwin"` or `"linux"` (built-in) |

**Never use `.is_personal`** — it has been replaced by `.company`.

### Runtime context: `$DOTFILES_CONTEXT`

`conf.d/00-context.zsh.tmpl` stamps `$DOTFILES_CONTEXT` at apply time (`bkahlert`, `ista`). All runtime code should branch on `$DOTFILES_CONTEXT` instead of template conditionals:

- Any known context, personal included: `[[ -n "$DOTFILES_CONTEXT" ]] && ...`
- Business only; use this for work-only behaviour: `[[ "$DOTFILES_CONTEXT" == ista ]] && ...`

In shell scripts use the env var with a default:
```bash
[[ "${DOTFILES_CONTEXT:-}" == ista ]] && ...
```

### Avoid templates — prefer runtime checks

**Only use `.tmpl` when there is no runtime alternative.** Prefer:
- `[[ $OSTYPE == darwin* ]]` over `{{ if eq .chezmoi.os "darwin" }}`
- `[[ $(uname) == Darwin ]] || exit 0` in `.chezmoiscripts/` shell scripts
- `[[ -n "$DOTFILES_CONTEXT" ]]` over `{{ if .company }}`
- Directory structure (`exact_conf.d/exact_ista/`) over template conditionals

A template is justified when the value must be baked in at apply time and the target format has no runtime equivalent — e.g. secrets in static config files, interpolated identity fields, or chezmoi-specific change detection. When in doubt, ask whether a runtime check could replace it.

## Secrets

Secrets are baked in at apply time by `.tmpl` files. The template is the record of where a secret lives; there is no separate registry. The backend follows the context:

- `ista`: 1Password — `{{ onepasswordRead "op://Employee/<item>/credential" }}`
- otherwise: KeePassXC — `{{ (keepassxc "<item>").Password }}`, database set in [.chezmoi.toml.tmpl](home/.chezmoi.toml.tmpl). chezmoi asks for the master password once per run, and only when a template reads from it.

An item needed in both contexts keeps the same title in both vaults, so one template can branch on `.company`. A secret file that makes no sense in a context is dropped via [.chezmoiignore](home/.chezmoiignore), not rendered empty. Secrets a shell needs land as files under `~/.local/share/secrets/` ([dot_local/share/private_secrets](home/dot_local/share/private_secrets)) and are exported by a `conf.d` module; `chezmoi apply` is the rotation step.

**Never commit plain-text secrets.** Inventory: `grep -rn 'op://\|keepassxc "' home/`.

## Zsh Architecture

Zsh config lives in `~/.config/zsh/` (set by `~/.zshenv`); only `~/.zshenv` remains in `$HOME`.

**[quick-access/README.md](quick-access/README.md) is the map** of every place a shell feature can live — `~/.local/bin` scripts, autoloaded functions, `conf.d` modules, aliases, keybindings, context-specific modules — plus the rule for choosing between them and the load order. Read it before adding or moving a command, and update it whenever a location is added, removed, or renamed.

Invariants that bite when editing source state:

- `exact_` on `exact_bin/`, `exact_conf.d/` and `exact_functions/` means **removing a file from the repo removes it from the target**, and a file created directly in `$HOME` is deleted on the next apply. Always edit source state.
- Exception: `~/.local/bin/claude` is owned by the Claude installer (`https://claude.ai/install.sh`) and survives `exact_bin` via `.chezmoiignore`. Other installer-owned entries need the same treatment.
- Only use `.zsh.tmpl` when the file embeds a secret or needs `sha256sum` change detection — a module that merely differs per machine should branch on `$DOTFILES_CONTEXT` at runtime.
- Context-specific modules go in `exact_conf.d/exact_ista/` as plain `.zsh`; the directory is the conditional, so no template is needed.

## Install Scripts

Each package entry in install scripts must have an inline comment stating:
1. What the tool does (one phrase)
2. What requires it or why it's installed this way (e.g. "required by chezmoi secrets", "no distro package available")

Example: `brew "1password-cli" # 1Password CLI (op); required by chezmoi to read secrets at apply time`

[.chezmoiscripts/](home/.chezmoiscripts) holds the apply-time scripts; the `run_once_before_`/`run_once_after_`/`run_onchange_after_` prefix and the name say when each runs and what it sets up. `00`/`01` prefixes order the install scripts (Homebrew before packages). Only add `.tmpl` where the script itself needs a template value.

## Key Files

| Target | Source | Notes |
|---|---|---|
| `~/.zshenv` | [dot_zshenv](home/dot_zshenv) | Sets ZDOTDIR |
| `~/.config/zsh/.zshrc` | [dot_zshrc](home/private_dot_config/zsh/dot_zshrc) | Thin loader |
| `~/.config/zsh/.zprofile` | [dot_zprofile](home/private_dot_config/zsh/dot_zprofile) | Homebrew shellenv |
| `~/.gitconfig` | [dot_gitconfig.tmpl](home/dot_gitconfig.tmpl) | Templated name/email |
| `~/.ssh/config` | [private_config](home/private_dot_ssh/private_config) | 1Password SSH agent (macOS) |
| `~/.claude/CLAUDE.md` | [CLAUDE.md](home/private_dot_claude/CLAUDE.md) | AI coding conventions |
| `~/.claude/settings.json` | [claude-settings.json](home/.chezmoitemplates/claude-settings.json) via [modify_settings.json](home/private_dot_claude/modify_settings.json) | Claude Code settings; `model` and `effortLevel` stay as set on the machine |
| `~/.npmrc` | [private_dot_npmrc.tmpl](home/private_dot_npmrc.tmpl) | Business only (mode 0600, ignored elsewhere): GitLab and Artifactory registry tokens |
| `~/.agents/skills/*`, `~/.claude/skills/*` | [dot_agents/skills](home/dot_agents/skills), [private_dot_claude/skills](home/private_dot_claude/skills) | Repo-owned agent skills + their symlinks; third-party ones via [setup-skills](home/.chezmoiscripts/run_onchange_after_setup-skills.sh). See [quick-access/README.md](quick-access/README.md) |
| `~/.local/bin/gcloud-login` | [executable_gcloud-login](home/dot_local/exact_bin/executable_gcloud-login) | Unattended gcloud/ADC login (ista); design notes in git history (`git show 64f5401:docs/superpowers/plans/2026-09-22-gcloud-login-findings.md`) |

## Common Tasks

**Add a script, function, alias or zsh module:**
See [quick-access/README.md](quick-access/README.md) — it decides which of the locations applies and documents the conventions for each.

**Add a macOS-only config:**
Prefer a runtime check; avoid `.tmpl`.

- In `.zsh` files: `[[ $OSTYPE == darwin* ]] || return 0`
- In `.sh` scripts: `[[ $(uname) == Darwin ]] || exit 0`

**Add a secret:**
1. Store it in the vault of the context that needs it (1Password `Employee` on ista, KeePassXC otherwise); same title in both if both need it.
2. Reference it from a `.tmpl` file as shown under [Secrets](#secrets). If a shell needs it, add a file under `dot_local/share/private_secrets/` and export it from a `conf.d` module.

**Add a brew package:**
Edit [run_once_before_01-install-packages.sh](home/.chezmoiscripts/run_once_before_01-install-packages.sh) and add to the Brewfile.

## Shipping Changes

This repo is solo-maintained and uses GitHub PRs as the merge mechanism (not as a review gate). The ship flow comes in **two offers**, in order: first apply the change locally so the user can test it, then ship it. Don't bundle both into one prompt — the user needs a chance to verify between them.

### Offer 1 — Apply locally

Once a change is committed on a topic branch and the user has confirmed it's ready, **proactively offer to apply and verify**:

> "Want me to run `chezmoi apply` (dry run first) so you can test it?"

Default flow when accepted:
1. `chezmoi diff` — show the pending changes.
2. `chezmoi apply -n` — dry run.
3. **Resolve target-side conflicts semantically when easy.** If the dry run shows drift in files outside the current change (e.g. unrelated reordering in `~/.claude/settings.json`), reason about whether the live state is meaningful or stale; if the resolution is obvious and low-risk, apply it (e.g. re-add the live value to source state, or accept the source overwrite). If the conflict is non-trivial, ambiguous, or touches secrets / `.chezmoi.toml.tmpl` / `run_once_*` scripts, stop and surface it to the user.
4. `chezmoi apply` — apply to `$HOME`.
5. Hand back to the user to test.

### Offer 2 — Ship it

After the user confirms the applied change works, **then** offer the GitHub ship flow:

> "Want me to push, open a PR, squash-merge it, and delete the branch?"

Default flow when accepted:
1. `git push -u origin <branch>`
2. `gh pr create` with a concise title and bulleted summary
3. `gh pr checks <n> --watch --fail-fast` — the `ci` check is required; the merge is rejected while it runs
4. `gh pr merge <n> --squash --delete-branch`
5. `git checkout main && git pull --ff-only`

### When *not* to offer

- Change is incomplete or under active iteration → skip both offers.
- User has signaled they want to review on GitHub first ("let me look at the PR") → skip Offer 2; still safe to make Offer 1.
- Change touches secrets, `.chezmoi.toml.tmpl`, or `run_once_*` install scripts that warrant a container test (`make integration`) before applying to `$HOME` → mention this with Offer 1 so the user can pick container-test instead.

Don't stack offers on follow-up turns; ask each one once, then drop it.

## Testing

| What | How |
|---|---|
| shellcheck, `zsh -n`, actionlint + zizmor | `make lint` |
| pytest (tests/bin, tests/functions, tests/zsh, conventions, shims) + node driver test | `make unit` |
| Apply all three contexts in a Fedora container, require a silent zsh (needs Podman) | `make integration` |
| Same, into a temp HOME on this Mac, plus a check that every Brewfile package exists in Homebrew (network); what CI's macOS job runs. Opt-in locally | `make integration-native` |
| Lint, unit and integration | `make ci` |
| Preview changes to `$HOME` | `chezmoi diff` |
| Dry run | `chezmoi apply -n` |

CI runs the same targets on every pull request and on `main`; the `ci` check is required to merge.

### Where a test lives

| Subject | Test |
|---|---|
| `bin/executable_<name>` | `tests/bin/test_<name>.py` (hyphens as underscores) |
| `private_dot_claude/executable_<name>` (`~/.claude/<name>`) | `tests/claude/test_<name>.py`, same sandbox; `run("<name>")` resolves it |
| `functions/<name>` | `tests/functions/test_<name>.py` |
| `conf.d/NN-<name>.zsh` that defines a function | `tests/zsh/test_<name>.py`; `conf.d/exact_ista/...` under `tests/zsh/ista/` |
| `.chezmoiscripts/run_*_<name>` | `tests/chezmoiscripts/test_<name>.py`: the name without the `run_…` prefix, ordering digits and extension (`01-install-packages.sh` → `test_install_packages.py`) |
| `modify_<name>` (anywhere under `home/`) | `tests/modify/test_<name>.py`, dots as underscores (`modify_settings.json` → `test_settings_json.py`) |
| a `.tmpl` outside `.chezmoiscripts/`, and `.chezmoiignore` | `tests/templates/test_<name>.py`: the prefixes `modify_`, `executable_`, `private_`, `exact_`, `empty_` and `dot_`, ordering digits and `.tmpl` dropped, other non-alphanumerics as underscores (`private_conf.d/20-ista-1password.conf.tmpl` → `test_ista_1password_conf.py`, `.chezmoiignore` → `test_chezmoiignore.py`) |
| every `conf.d` module | loaded by the integration legs; a module that prints on a fresh machine fails them |

`tests/test_conventions.py` fails when a script, function, function-defining module, `modify_` script or template has neither a test nor an entry in `tests/untested.toml`, and when an entry is stale. A `"legacy: ..."` entry goes when the file's **behaviour** is next changed: that change adds the test and removes the line. Lint or formatting edits do not trigger it. A file with no logic of its own (a wrapper around `open`, `osascript`, `pbcopy`) keeps a permanent entry with that reason.

### Writing a unit test

Fixtures in [tests/conftest.py](tests/conftest.py) run the real script or function:

- `run("name", *args)` runs a `bin/` or `~/.claude` script by its target name in a sandbox: temp `HOME`, `XDG_*` and `TMPDIR`; `PATH` is fakes first, then the other `bin/` scripts, then symlinks to the real tools listed in `REAL_TOOLS` ([conftest.py](tests/conftest.py): shells, coreutils, `awk`, `sed`, `jq`, `python3`, ...) and nothing else. They come from fixed system and Homebrew directories, not the caller's `PATH`; a missing one aborts the run. A subject that needs another real tool adds it there.
- `fake_bin("tool", stdout=..., exit_code=..., script=...)` puts a fake on `PATH`; `calls("tool")` returns its recorded argument lists.
- `zsh("snippet", function="name")` or `zsh("snippet", modules=["ista/10-dev-chapter.zsh"])` runs `zsh -f` with the source tree's functions and modules.
- `script("name", *args, uname="Darwin", env={...})` (in `tests/chezmoiscripts/`) runs a `.chezmoiscripts/` script by its key under the same sandbox, with a fake `uname` so either OS branch can be taken.
- `chezmoi.render("private_dot_npmrc.tmpl", company="ista", os="darwin")`, `chezmoi.config(company)` and `chezmoi.ignored(company)` (in `tests/templates/`) run the real `chezmoi` against the source tree with the `op` and `keepassxc-cli` shims as vaults, so a secret renders as a placeholder that names its backend. They skip where `chezmoi` is not installed (the lint-and-unit CI job); the macOS job runs them.
- `modify(script, current, **env)` (in `tests/modify/`) runs a `modify_` script the way chezmoi does: the current target on stdin, the new content on stdout.
- Network, vault, system-state and user-state tools (`op`, `gh`, `gcloud`, `curl`, `openssl`, `ssh-keygen`, `brew`, `git`, `chezmoi`, `podman`, `xcrun`, `open`, `osascript`, `launchctl`, `defaults`, `sudo`, `pbcopy`, `lsof`, `pkill`, ...) are guarded: calling one unfaked fails with exit 127. Any other tool outside `REAL_TOOLS` is not on `PATH` and fails as not found, installed or not. Fake what the subject needs; the `REAL_TOOLS` are real.
  `PATH` is the only barrier: a subject that calls a tool by absolute path (`/usr/bin/curl`), or that runs through a real interpreter (`python3`, `zsh`, `bash`), can still reach host programs. It stops accidents, not a script that means to escape.

Classes nest as [testing.md](home/private_dot_config/exact_agents/exact_rules/testing.md) asks: `TestGhLatest` > `TestOnUnknownOption` > `test_should_exit_2_and_name_the_option`.

### Integration legs

Both legs write a chezmoi config with the context's `company`, apply the source tree with `tests/shims/op` and `tests/shims/keepassxc-cli` first on `PATH` and `--no-tty` with a dummy password on stdin, then run `zsh -li -c true` and require exit 0 and an empty stderr.

- Container ([Containerfile](Containerfile) stage `base`, [entrypoint.sh](entrypoint.sh)): Fedora with chezmoi, sheldon, starship, zoxide. `make run` builds the `vnc` stage for manual inspection.
- Native macOS: a temp home, `--exclude=scripts` (no `brew bundle`, no `defaults write`), `sheldon lock` by hand, and a preflight that `chezmoi data` reports the temp home. Every path chezmoi and the startup files touch derives from `HOME`, `ZDOTDIR` or an `XDG_*` variable, which is why this is safe to run on a developer Mac. **Startup code must keep it that way: write only under those directories, and stay silent when a tool you wrap is absent.**
