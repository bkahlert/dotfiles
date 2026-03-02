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
| `.is_personal` | bool | `true` on personal machines; `false` on business machines |
| `.chezmoi.os` | string | `"darwin"` or `"linux"` (built-in) |

Use `{{ if not .is_personal }}` to gate business-only configs.
Use `{{ if eq .chezmoi.os "darwin" }}` to gate macOS-only configs.

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

Files in `exact_conf.d/` are sourced in alphabetical order by [dot_zshrc](home/private_dot_config/zsh/dot_zshrc). Only `*.zsh` files are sourced (non-zsh files like `.kts` are safe to colocate).

**Numbering convention:**
- `01`–`07`: Core zsh setup (options, history, completions, keybindings, prompt, aliases, plugins)
- `08`: Infrastructure utilities (`08-print.zsh` — print functions used by other modules)
- `10-*`: Tool-specific modules (one per tool: homebrew, nvm, gradle, etc.)

When adding a new tool, create `10-<toolname>.zsh` (or `.zsh.tmpl` if it needs template data).

The `exact_` prefix on `conf.d/` means **removing a file from the repo removes it from the target**. Always add new modules to the source state.

### Autoloaded Functions

Files in `functions/` are autoloaded by zsh. Each file is named after the function and contains only the function body (no `funcname() { ... }` wrapper). They are loaded on first call.

Use autoloaded functions for zsh-specific utilities. Use `~/.local/bin` scripts for shell-agnostic tools.

### Print Utilities

[08-print.zsh](home/private_dot_config/zsh/exact_conf.d/08-print.zsh) provides `printf_error`, `printf_info`, `printf_success`, `printf_warning`, and `die`. These are designed as a single sourceable file so they can be copy-pasted into standalone scripts. Other conf.d modules and autoloaded functions can use them freely since they're sourced first.

## Install Scripts

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
| `~/.osx` | [executable_dot_osx](home/executable_dot_osx) | macOS defaults |

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

**Add a business-only config:**
```sh
# Use .tmpl extension and wrap content in:
# {{ if not .is_personal -}}
# ...content...
# {{ end -}}
```

**Add a macOS-only config:**
```sh
# Option A: Runtime check in .zsh file
# if [[ "$OSTYPE" == darwin* ]]; then ... fi

# Option B: Chezmoi template (.tmpl)
# {{ if eq .chezmoi.os "darwin" -}}
# ...content...
# {{ end -}}
```

**Add a secret:**
1. Store in 1Password
2. Reference with `{{ onepasswordRead "op://vault/item/field" }}` in a `.tmpl` file

**Add a brew package:**
Edit [run_once_before_01-install-packages.sh.tmpl](home/.chezmoiscripts/run_once_before_01-install-packages.sh.tmpl) and add to the Brewfile.

## Testing

```sh
chezmoi diff          # preview changes
chezmoi apply -n      # dry run
chezmoi apply         # apply to $HOME
make build && make validate   # test in container
```
