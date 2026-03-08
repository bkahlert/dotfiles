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

## Template Data

Defined in [.chezmoi.toml.tmpl](home/.chezmoi.toml.tmpl), prompted on `chezmoi init`:

| Variable | Type | Usage |
|---|---|---|
| `.email` | string | Git config email |
| `.name` | string | Git config name |
| `.company` | string | Company name (empty on personal machines, e.g. `"ista"` on business) |
| `.chezmoi.os` | string | `"darwin"` or `"linux"` (built-in) |

**Never use `.is_personal`** — it has been replaced by `.company`.

### Runtime context: `$DOTFILES_CONTEXT`

`conf.d/00-context.zsh.tmpl` stamps `$DOTFILES_CONTEXT` at apply time (e.g. `ista`). On personal machines the file renders empty. All runtime code should branch on `$DOTFILES_CONTEXT` instead of template conditionals:

```zsh
[[ -n "$DOTFILES_CONTEXT" ]] && ...   # any business machine
[[ "$DOTFILES_CONTEXT" == ista ]] && ... # ista specifically
```

In shell scripts use the env var with a default:
```bash
[[ "${DOTFILES_CONTEXT:-}" == ista ]] && ...
```

### Avoid templates — prefer runtime checks

**Only use `.tmpl` when there is no runtime alternative.** Prefer:
- `[[ $OSTYPE == darwin* ]]` over `{{ if eq .chezmoi.os "darwin" }}`
- `[[ $(uname) == Darwin ]] || exit 0` in `.chezmoiscripts/` shell scripts
- `[[ -n "$DOTFILES_CONTEXT" ]]` over `{{ if .company }}`
- Directory structure (`conf.d/ista/`) over template conditionals

A template is justified when the value must be baked in at apply time and the target format has no runtime equivalent — e.g. secrets in static config files, interpolated identity fields, or chezmoi-specific change detection. When in doubt, ask whether a runtime check could replace it.

## Secrets

Secrets are fetched from 1Password at apply time using `onepasswordRead` in `.tmpl` files:

```
{{ onepasswordRead "op://vault/item/field" }}
```

**Never commit plain-text secrets.** Required 1Password items (business only):
- `op://Employee/GitLab Token/credential`
- `op://Employee/GitLab NPM Token/credential`

## Zsh Architecture

### ZDOTDIR

Zsh config lives in `~/.config/zsh/` (set by `~/.zshenv`). Only `~/.zshenv` remains in `$HOME`.

### conf.d Modules

Files in `exact_conf.d/` are sourced by [dot_zshrc](home/private_dot_config/zsh/dot_zshrc) in two passes:
1. Generic modules (`conf.d/*.zsh`) in alphabetical order
2. Company-specific modules (`conf.d/$DOTFILES_CONTEXT/*.zsh`) if `$DOTFILES_CONTEXT` is set

Only `*.zsh` files are sourced (non-zsh files like `.kts` are safe to colocate).

**Numbering convention:**
- `01`–`07`: Core zsh setup (options, history, completions, keybindings, prompt, aliases, plugins)
- `08`: Infrastructure utilities (`08-print.zsh` — print functions used by other modules)
- `10-*`: Tool-specific modules (one per tool: homebrew, nvm, gradle, etc.)

**For business-specific modules**, place them in `conf.d/ista/` as plain `.zsh` files — no template needed. The directory itself is the conditional.

When adding a new tool, create `10-<toolname>.zsh`. Only use `.zsh.tmpl` if the file embeds a secret or requires `sha256sum` change detection.

The `exact_` prefix on `conf.d/` means **removing a file from the repo removes it from the target**. Always add new modules to the source state.

### Autoloaded Functions

Files in `functions/` are autoloaded by zsh. Each file is named after the function and contains only the function body (no `funcname() { ... }` wrapper). They are loaded on first call.

Use autoloaded functions for zsh-specific utilities. Use `~/.local/bin` scripts for shell-agnostic tools.

### Print Utilities

[08-print.zsh](home/private_dot_config/zsh/exact_conf.d/08-print.zsh) provides `printf_error`, `printf_info`, `printf_success`, `printf_warning`, and `die`. These are designed as a single sourceable file so they can be copy-pasted into standalone scripts. Other conf.d modules and autoloaded functions can use them freely since they're sourced first.

## Install Scripts

Each package entry in install scripts must have an inline comment stating:
1. What the tool does (one phrase)
2. What requires it or why it's installed this way (e.g. "required by chezmoi secrets", "no distro package available")

Example: `brew "1password-cli" # 1Password CLI (op); required by chezmoi to read secrets at apply time`

[.chezmoiscripts/](home/.chezmoiscripts/) contains:
- `run_once_before_00-install-homebrew.sh.tmpl` — installs Homebrew (macOS)
- `run_once_before_01-install-packages.sh.tmpl` — installs core packages via Brewfile (macOS) or curl (Linux)
- `run_once_after_setup-startup-launchagent.sh.tmpl` — sets up `~/.startup` LaunchAgent (macOS)
- `run_onchange_after_sheldon-lock.sh.tmpl` — re-locks Sheldon plugins when config changes

## Key Files

| Target | Source | Notes |
|---|---|---|
| `~/.zshenv` | [dot_zshenv](home/dot_zshenv) | Sets ZDOTDIR |
| `~/.config/zsh/.zshrc` | [dot_zshrc](home/private_dot_config/zsh/dot_zshrc) | Thin loader |
| `~/.config/zsh/.zprofile` | [dot_zprofile.tmpl](home/private_dot_config/zsh/dot_zprofile.tmpl) | Homebrew shellenv |
| `~/.gitconfig` | [dot_gitconfig.tmpl](home/dot_gitconfig.tmpl) | Templated name/email |
| `~/.ssh/config` | [private_config.tmpl](home/private_dot_ssh/private_config.tmpl) | 1Password SSH agent (macOS) |
| `~/.claude/CLAUDE.md` | [CLAUDE.md](home/private_dot_claude/CLAUDE.md) | AI coding conventions |
| `~/.claude/settings.json` | [settings.json](home/private_dot_claude/settings.json) | Claude Code settings |
| `~/.npmrc` | [dot_npmrc.tmpl](home/dot_npmrc.tmpl) | Business: GitLab registry |
| `~/.startup` | [executable_dot_startup](home/executable_dot_startup) | Login script (macOS, run via LaunchAgent) |

## Common Tasks

**Add a new zsh module:**
```sh
# Create home/private_dot_config/zsh/exact_conf.d/10-<tool>.zsh
# Use .zsh.tmpl if it needs template variables
```

**Add a new autoloaded function:**
```sh
# Create home/private_dot_config/zsh/functions/<funcname>
# File contains only the function body
```

**Add a business-only zsh module:**
```sh
# Place it in conf.d/ista/ as a plain .zsh file — no template needed.
# Create home/private_dot_config/zsh/exact_conf.d/ista/10-<tool>.zsh
```

**Add a macOS-only config:**
```sh
# Prefer a runtime check — avoid .tmpl:
# In .zsh files:   [[ $OSTYPE == darwin* ]] || return 0
# In .sh scripts:  [[ $(uname) == Darwin ]] || exit 0
```

**Add a secret:**
1. Store in 1Password
2. Reference with `{{ onepasswordRead "op://vault/item/field" }}` in a `.tmpl` file

**Add a brew package:**
Edit [run_once_before_01-install-packages.sh.tmpl](home/.chezmoiscripts/run_once_before_01-install-packages.sh.tmpl) and add to the Brewfile.

## Git Commits

- Do **not** include `Co-Authored-By:` or any AI attribution lines in commit messages.

## Testing

```sh
chezmoi diff          # preview changes
chezmoi apply -n      # dry run
chezmoi apply         # apply to $HOME
make build && make validate   # test in container
```
