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
| `quick-access/functions` | [home/private_dot_config/zsh/exact_functions/](../home/private_dot_config/zsh/exact_functions) | Autoloaded zsh functions, one file per function (none right now; `.keep` holds the directory) |
| `quick-access/completions` | [home/private_dot_config/zsh/exact_completions/](../home/private_dot_config/zsh/exact_completions) | Hand-written completions, for tools that ship none |
| `quick-access/conf.d` | [home/private_dot_config/zsh/exact_conf.d/](../home/private_dot_config/zsh/exact_conf.d) | Zsh modules — env setup, tool init, **and inline functions** |
| `quick-access/conf.d/exact_ista` | [.../exact_conf.d/exact_ista/](../home/private_dot_config/zsh/exact_conf.d/exact_ista) | Same, but only loaded when `$DOTFILES_CONTEXT` is set |
| `quick-access/aliases.zsh` | [.../06-aliases.zsh](../home/private_dot_config/zsh/exact_conf.d/06-aliases.zsh) | Most aliases, incl. suffix aliases (`alias -s md=idea`) |
| `quick-access/keybindings.zsh` | [.../04-keybindings.zsh](../home/private_dot_config/zsh/exact_conf.d/04-keybindings.zsh) | ZLE keybindings |
| `quick-access/scratch.zsh` | [.../90-scratch.zsh](../home/private_dot_config/zsh/exact_conf.d/90-scratch.zsh) | Not-yet-organized customizations; edit with `ec`, reload with `sc` (both defined in [.../89-scratch-workflow.zsh](../home/private_dot_config/zsh/exact_conf.d/89-scratch-workflow.zsh)) |
| `quick-access/plugins.toml` | [home/private_dot_config/sheldon/plugins.toml](../home/private_dot_config/sheldon/plugins.toml) | Sheldon plugins — they add commands and widgets too |
| `quick-access/zshrc` | [home/private_dot_config/zsh/dot_zshrc](../home/private_dot_config/zsh/dot_zshrc) | The loader: autoload + `conf.d` sourcing |
| `quick-access/zshenv` | [home/dot_zshenv](../home/dot_zshenv) | Runs for **every** zsh, including non-interactive ones |
| `quick-access/zprofile` | [home/private_dot_config/zsh/dot_zprofile](../home/private_dot_config/zsh/dot_zprofile) | Login shells only (Homebrew shellenv) |
| `quick-access/git-aliases` | [home/dot_gitconfig.tmpl](../home/dot_gitconfig.tmpl) | `[alias]` section — `git …` subcommands typed like shell commands |

Tests live beside the map: `bin` → `tests/bin/`, `functions` → `tests/functions/`, `conf.d` →
`tests/zsh/` (`conf.d/exact_ista` → `tests/zsh/ista/`); see [AGENTS.md](../AGENTS.md#testing).

Not symlinked, but worth knowing:

- `~/.config/zsh/.zshrc.local` — machine-local overrides, sourced last, deliberately unmanaged.
- [home/dot_bashrc](../home/dot_bashrc), [home/dot_bash_profile](../home/dot_bash_profile) — the bash side; only Ghostty integration and the prompt.
- [home/.chezmoiscripts/](../home/.chezmoiscripts) — runs at `chezmoi apply` time, not at shell time.
- **Agent skills** (Claude Code and friends) have one canonical copy in `~/.agents/skills/<name>/SKILL.md`,
  with a symlink `~/.claude/skills/<name> -> ../../.agents/skills/<name>` so each agent finds them.
  Two mechanisms produce that layout:
  - third-party skills: [run_onchange_after_setup-skills.sh](../home/.chezmoiscripts/run_onchange_after_setup-skills.sh)
    runs `skills add -g` (e.g. `grill-me`, `handoff`). The layout then depends on the agents requested: with a
    universal agent (Gemini CLI, GitHub Copilot) in the list, the CLI writes the canonical copy and the symlink;
    with `claude-code` alone (the `bkahlert` context) it copies straight into `~/.claude/skills/<name>`.
    Without `-g` the CLI treats the working directory as a project and leaves a `skills-lock.json` in `$HOME`,
    because chezmoi runs scripts there;
  - repo-owned skills: the SKILL.md sits in [home/dot_agents/skills/](../home/dot_agents/skills) and the
    symlink is a one-line `symlink_<name>` file in [home/private_dot_claude/skills/](../home/private_dot_claude/skills)
    (e.g. `gcloud-auth`). Chezmoi applies edits on the next apply; context-gating goes through `.chezmoiignore`.
  Don't install repo-owned skills through the CLI: from a local path it copies straight into
  `~/.claude/skills` without the canonical copy, and the copy goes stale on every edit.

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
6. **Whatever you add, its test goes with it**: `tests/bin/test_<name>.py` for a script,
   `tests/functions/test_<name>.py` for a function, `tests/zsh/test_<name>.py` for a module that
   defines functions. `make unit` tells you when one is missing; a file with no logic of its own is
   listed in `tests/untested.toml` with the reason instead. See [AGENTS.md](../AGENTS.md#testing).

Prefer `bin/` over a function when both would work: a script is testable on its
own, works from any shell, and can't be shadowed by accident.

## Why a command isn't where you expect

Zsh resolves a word in this order, first match wins:

```
alias → function → command on $PATH
```

`~/.local/bin` is prepended to `$PATH` ([09-path.zsh](../home/private_dot_config/zsh/exact_conf.d/09-path.zsh)),
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

## Completions

Most completions are **not** here. Homebrew formulae install theirs into
`$HOMEBREW_PREFIX/share/zsh/site-functions` (`_git`, `_kubectl`, `_op`, …),
plugins bring their own, and some tools generate one at startup — gcloud
sources `completion.zsh.inc` from [10-gcloud-sdk.zsh](../home/private_dot_config/zsh/exact_conf.d/10-gcloud-sdk.zsh),
idp the output of `idp completion zsh` from [10-idp.zsh](../home/private_dot_config/zsh/exact_conf.d/exact_ista/10-idp.zsh).

`completions/` is for the rest: a tool with no formula, or one of the scripts
in `bin/`. One file per command, named `_<command>`, starting with `#compdef
<command>`.

[`_killport`](../home/private_dot_config/zsh/exact_completions/_killport) is the
worked example — it offers the ports currently being listened on, described by
the process holding each. To check that the whole path works end to end:

```sh
python3 -m http.server 8765 >/dev/null 2>&1 &   # occupy a port
killport <TAB>                                  # → 8765  Python (pid 12345)
                                                # TAB again to walk the menu
killport 8765                                   # complete it, then free it
```

If a new completion doesn't show up, the dump is the usual suspect —
[08-completions.zsh](../home/private_dot_config/zsh/exact_conf.d/08-completions.zsh)
rebuilds `.zcompdump` when a file here is newer than it, so the file's mtime
has to be later than the dump's. `rm -f $ZDOTDIR/.zcompdump && exec zsh`
forces it.

## Load order

```
~/.zshenv                       → sets ZDOTDIR (every zsh, incl. non-interactive)
~/.config/zsh/.zprofile         → Homebrew shellenv (login shells)
~/.config/zsh/.zshrc            → autoloads functions, sources conf.d/*
  00-context.zsh                → stamps $DOTFILES_CONTEXT
  01–07                         → core (options, history, keybindings, prompt,
                                  aliases, plugins)
  08-completions.zsh            → compinit, after the plugins that extend $fpath
  09-path.zsh                   → $PATH, before anything resolves a command
  10-*.zsh                      → tool modules, one per tool
  20-claude.zsh                 → Claude CLI
  89-scratch-workflow.zsh       → `ec` / `sc`, the scratch workflow
  90-scratch.zsh                → drafts, loaded last
  conf.d/$DOTFILES_CONTEXT/     → context-specific modules (sourced last)
  .zshrc.local                  → machine-local, unmanaged
```
