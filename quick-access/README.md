# Where shell features live

Everything typed at a prompt — a command, a function, an alias, a keybinding —
is defined in one of the places below. The chezmoi source paths carry
`dot_`/`private_`/`exact_` prefixes that hide them in a file tree, so this
directory holds prefix-free symlinks pointing at the real locations.

The symlinks are for navigation only: they live outside `home/`, which is the
chezmoi source root (`.chezmoiroot`), so chezmoi never sees them.

## Map

| Symlink | Source | Holds |
|---|---|---|
| `quick-access/bin` | [home/dot_local/exact_bin/](../home/dot_local/exact_bin) | Shell-agnostic executables, mirrored to `~/.local/bin` |
| `quick-access/functions` | [home/private_dot_config/zsh/exact_functions/](../home/private_dot_config/zsh/exact_functions) | Autoloaded zsh functions, one file per function |
| `quick-access/conf.d` | [home/private_dot_config/zsh/exact_conf.d/](../home/private_dot_config/zsh/exact_conf.d) | Zsh modules — env setup, tool init, **and inline functions** |
| `quick-access/conf.d/exact_ista` | [.../exact_conf.d/exact_ista/](../home/private_dot_config/zsh/exact_conf.d/exact_ista) | Same, but only loaded when `$DOTFILES_CONTEXT` is set |
| `quick-access/aliases.zsh` | [.../06-aliases.zsh](../home/private_dot_config/zsh/exact_conf.d/06-aliases.zsh) | Most aliases, incl. suffix aliases (`alias -s md=idea`) |
| `quick-access/keybindings.zsh` | [.../04-keybindings.zsh](../home/private_dot_config/zsh/exact_conf.d/04-keybindings.zsh) | ZLE keybindings |
| `quick-access/scratch.zsh` | [.../90-scratch.zsh](../home/private_dot_config/zsh/exact_conf.d/90-scratch.zsh) | Not-yet-organized customizations; edit with `ec`, reload with `sc` |
| `quick-access/plugins.toml` | [home/private_dot_config/sheldon/plugins.toml](../home/private_dot_config/sheldon/plugins.toml) | Sheldon plugins — they add commands and widgets too |
| `quick-access/zshrc` | [home/private_dot_config/zsh/dot_zshrc](../home/private_dot_config/zsh/dot_zshrc) | The loader: autoload + `conf.d` sourcing |
| `quick-access/zshenv` | [home/dot_zshenv](../home/dot_zshenv) | Runs for **every** zsh, including non-interactive ones |
| `quick-access/zprofile` | [home/private_dot_config/zsh/dot_zprofile](../home/private_dot_config/zsh/dot_zprofile) | Login shells only (Homebrew shellenv) |
| `quick-access/startup` | [home/executable_dot_startup](../home/executable_dot_startup) | Runs at login via LaunchAgent, not at shell start |
| `quick-access/git-aliases` | [home/dot_gitconfig.tmpl](../home/dot_gitconfig.tmpl) | `[alias]` section — `git …` subcommands typed like shell commands |

Not symlinked, but worth knowing:

- `~/.config/zsh/.zshrc.local` — machine-local overrides, sourced last, deliberately unmanaged.
- [home/dot_bashrc](../home/dot_bashrc), [home/dot_bash_profile](../home/dot_bash_profile) — the bash side; only Ghostty integration and the prompt.
- [home/.chezmoiscripts/](../home/.chezmoiscripts) — runs at `chezmoi apply` time, not at shell time.

## Where does a new thing go?

1. **Does it need to run outside interactive zsh** — from a script, a Makefile,
   cron, a GUI app, or bash? → `bin/`, as `executable_<name>` with a shebang.
   This is the default; reach for it unless something below applies.
2. **Must it change the current shell** (`cd`, `export`, `setopt`, `bindkey`) or
   use zsh-only syntax? → a function.
   - Self-contained command → `functions/<name>`, autoloaded on first call,
     zero startup cost. The file holds only the body, no `name() { … }` wrapper.
   - Needs setup at shell startup, or belongs next to a tool's config →
     define it inside `conf.d/10-<tool>.zsh`.
3. **Is it pure shorthand** for an existing command? → an alias in `aliases.zsh`,
   or next to its tool's module if it only makes sense there.
4. **Work machine only?** → same rules, but under `conf.d/exact_ista/`. The
   directory is the conditional; no template needed.
5. **Not sure yet?** → `scratch.zsh`, then promote it once it proves useful.

Prefer `bin/` over a function when both would work: a script is testable on its
own, works from any shell, and can't be shadowed by accident.

## Why a command isn't where you expect

Zsh resolves a word in this order, first match wins:

```
alias → function → command on $PATH
```

`~/.local/bin` is prepended to `$PATH` ([10-path.zsh](../home/private_dot_config/zsh/exact_conf.d/10-path.zsh)),
so scripts here shadow Homebrew and system binaries of the same name — that is
deliberate for wrappers, and a trap otherwise.

To find out which layer answered:

```sh
whence -v foo                        # alias / function / file
functions foo                        # print a function's body and origin
chezmoi source-path "$(whence -p foo)"   # map a script back to its source file
```

## Gotchas

- `exact_` on `bin/`, `conf.d/`, and `functions/` means **deleting a file from
  the repo deletes it from `$HOME`** on the next apply. Conversely, a file
  created directly in the target is removed. Always edit the source.
- Editing through these symlinks edits the real source file, so `chezmoi apply`
  is still required. For `.tmpl` files use `chezmoi edit` instead.
- `conf.d` sources `*.zsh` only, so non-zsh files can be colocated safely
  (e.g. `gradle-versions-plugin.init.gradle.kts`).
- `$ZDOTDIR/completions` is on `fpath` but does not exist yet — create it in
  source state if you add completion functions.

## Load order

```
~/.zshenv                       → sets ZDOTDIR (every zsh, incl. non-interactive)
~/.config/zsh/.zprofile         → Homebrew shellenv (login shells)
~/.config/zsh/.zshrc            → autoloads functions, sources conf.d/*
  00-context.zsh                → stamps $DOTFILES_CONTEXT
  01–07                         → core (options, history, completions,
                                  keybindings, prompt, aliases, plugins)
                                  08 = infrastructure, 10-* = one per tool
  08-print.zsh                  → printf_* helpers and die
  10-*.zsh                      → tool modules
  20-claude.zsh                 → Claude CLI
  conf.d/$DOTFILES_CONTEXT/     → context-specific modules (sourced last)
  .zshrc.local                  → machine-local, unmanaged
```
