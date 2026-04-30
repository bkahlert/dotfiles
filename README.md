# dotfiles

Personal dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Quick start

**Fresh machine (one-liner):**

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply bkahlert --source ~/.local/share/chezmoi
```

**Existing machine:**

```sh
brew install chezmoi
chezmoi init --apply bkahlert
```

## How it works

- **[chezmoi](https://www.chezmoi.io/)** manages dotfiles — copies files to `$HOME` (no symlinks). Source state lives in `home/` (via `.chezmoiroot`).
- **[ZDOTDIR](https://zsh.sourceforge.io/Doc/Release/Files.html)** — zsh config lives in `~/.config/zsh/`, only `~/.zshenv` remains in `$HOME`.
- **[Sheldon](https://sheldon.cli.rs/)** — zsh plugin manager (TOML config, Rust-based).
- **[Starship](https://starship.rs/)** — cross-shell prompt (TOML config, Rust-based).
- **Autoloaded functions** — zsh-specific functions are files in `functions/`, loaded on first call.
- **Standalone scripts** — shell-agnostic utilities under `home/dot_local/exact_bin/` mirror `~/.local/bin` exactly: removing a script from the repo removes it from the target.
- **AI assistant configs** — `~/.claude/`, `~/.gemini/`, and `~/.config/agents/` are tracked so prompt rules and slash commands stay in sync across machines.

## Making changes

### Dotfiles (chezmoi)

```sh
chezmoi edit ~/.gitconfig         # edit a managed file
chezmoi diff                      # preview pending changes
chezmoi apply                     # apply changes to $HOME
chezmoi add ~/.config/foo/config  # start managing a new file
```

See [chezmoi daily operations](https://www.chezmoi.io/user-guide/daily-operations/).

### Zsh modules

Add a new module — create a numbered `.zsh` file in `conf.d/`:

```sh
chezmoi edit ~/.config/zsh/conf.d/10-mytool.zsh
```

Add a new function — create a file in `functions/` named after the function.
The file contains only the function body (no `funcname() {` wrapper):

```sh
chezmoi edit ~/.config/zsh/functions/myfunction
```

```zsh
# Example: functions/greet
echo "Hello, ${1:-world}!"
```

### Plugins (Sheldon)

Edit the plugin list:

```sh
chezmoi edit ~/.config/sheldon/plugins.toml
```

Add a plugin by adding a `[plugins.<name>]` section:

```toml
[plugins.my-plugin]
github = "author/repo"
```

Update all plugins:

```sh
sheldon lock --update
```

See [Sheldon documentation](https://sheldon.cli.rs/).

### Prompt (Starship)

Edit the prompt configuration:

```sh
chezmoi edit ~/.config/starship.toml
```

Changes take effect on the next prompt render (no restart needed).

See [Starship configuration](https://starship.rs/config/).

### Ghostty

Edit the terminal configuration:

```sh
chezmoi edit ~/.config/ghostty/config
```

Live reload: press **Cmd+Shift+,** (macOS) or **Ctrl+Shift+,** (Linux).

See [Ghostty configuration reference](https://ghostty.org/docs/config/reference).

## File layout

```
dotfiles/
├── .chezmoiroot                  # points chezmoi to home/
├── Containerfile                 # test container (Fedora + Ghostty + VNC)
├── Makefile                      # build/run/validate targets
│
└── home/                         # chezmoi source state
    ├── .chezmoi.toml.tmpl        # machine config (prompted on init)
    ├── .chezmoiscripts/          # install + setup scripts (homebrew, packages,
    │                             #   sheldon, nanorc, LaunchAgent, MCP, skills, .osx)
    ├── dot_zshenv                # sets ZDOTDIR → only file kept in $HOME
    ├── executable_dot_startup    # login script run via LaunchAgent (macOS)
    ├── Library/                  # LaunchAgents (macOS)
    │
    ├── dot_local/exact_bin/      # mirrors ~/.local/bin exactly (upgrade-all,
    │                             #   cleanup, cert-get, apply-macos-defaults, ...)
    │
    ├── private_dot_config/
    │   ├── zsh/
    │   │   ├── dot_zshrc         # thin loader
    │   │   ├── exact_conf.d/     # numbered zsh modules
    │   │   └── functions/        # autoloaded functions (zsh-specific only)
    │   ├── sheldon/              # plugin definitions
    │   ├── starship.toml         # prompt config
    │   ├── ghostty/              # terminal config
    │   └── exact_agents/         # shared AI agent rules (AGENTS.md)
    │
    ├── private_dot_claude/       # Claude Code config + skills
    ├── private_dot_gemini/       # Gemini CLI config
    ├── private_dot_ssh/          # SSH config (1Password agent on macOS)
    ├── dot_gitconfig.tmpl        # git (templated for name/email)
    ├── dot_npmrc.tmpl            # npm (templated for GitLab registry on business)
    ├── dot_curlrc                # curl defaults
    └── dot_tmux.conf             # tmux
```

## Zsh load order

```
~/.zshenv                          → sets ZDOTDIR=~/.config/zsh
~/.config/zsh/.zprofile            → Homebrew shellenv
~/.config/zsh/.zshrc               → autoloads functions, sources conf.d/*
  00-context.zsh.tmpl              → stamps $DOTFILES_CONTEXT (e.g. "ista" or empty)
  01–07                            → core: options, history, completions,
                                       keybindings, prompt, aliases, plugins
  08-print.zsh                     → printf_error/info/success/warning, die
  10-*.zsh                         → tool modules (homebrew, nvm, fzf, java, go,
                                       gradle, kubernetes, gcloud, glab, aws, …)
  20-claude.zsh                    → Claude CLI auto-install + completion
  conf.d/$DOTFILES_CONTEXT/*.zsh   → company-specific modules (sourced last)
```

## Testing in a container

Build and test with Podman:

```sh
make build      # build Fedora + Ghostty + VNC image
make validate   # apply dotfiles + verify zsh starts
make run        # start container with VNC on :5901
make vnc        # open VNC viewer
make stop       # stop the container
make clean      # remove the image
```

## Secrets

Secrets (GitLab tokens, npm auth tokens) are stored in [1Password](https://1password.com/) and fetched at `chezmoi apply` time via `onepasswordRead` in `.tmpl` files. Tokens never appear in the repo.

**Prerequisites:**
- 1Password desktop app installed and signed in
- 1Password CLI (`op`) installed (included in the Brewfile)
- CLI integration enabled in 1Password settings

**Required 1Password items** (business machines only):
- `op://Employee/GitLab Token/credential` — GitLab private token
- `op://Employee/GitLab NPM Token/credential` — npm registry auth token

## Repairing the startup LaunchAgent

The `~/.startup` script runs at login via a LaunchAgent. If it stops working:

```sh
# Re-run the chezmoi setup script
chezmoi apply --force
```

Or manually recreate:

```sh
launchctl unload ~/Library/LaunchAgents/com.user.startup.plist 2>/dev/null
chezmoi state delete-bucket --bucket=scriptState
chezmoi apply
```

## Design decisions

| Decision             | Choice                                    | Why                                                                          |
|----------------------|-------------------------------------------|------------------------------------------------------------------------------|
| Dotfiles manager     | chezmoi                                   | Real files (not symlinks), templating, multi-machine, can stop using anytime |
| Zsh layout           | ZDOTDIR                                   | Keeps `$HOME` clean — only `~/.zshenv`                                       |
| Plugin manager       | Sheldon                                   | TOML config, fast (Rust), actively maintained                                |
| Prompt               | Starship                                  | Actively maintained (p10k is on life support), cross-shell                   |
| Functions vs scripts | Scripts for POSIX, functions for zsh-only | Scripts work in any shell and from cron/other tools                          |
| exact_ on conf.d/    | yes                                       | Removing a module from the repo removes it from the target                   |
| exact_ on .config/   | no                                        | Other apps create dirs in .config/ freely                                    |
