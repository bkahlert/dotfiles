# dotfiles

Personal dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Quick start

**Fresh machine (one-liner):**

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply bkahlert --source ~/.local/share/chezmoi
```

**Existing machine:**

```sh
chezmoi init --apply bkahlert
```

## How it works

- **[chezmoi](https://www.chezmoi.io/)** manages dotfiles — copies files to `$HOME` (no symlinks). Source state lives in `home/` (via `.chezmoiroot`).
- **[ZDOTDIR](https://zsh.sourceforge.io/Doc/Release/Files.html)** — zsh config lives in `~/.config/zsh/`, only `~/.zshenv` remains in `$HOME`.
- **[Sheldon](https://sheldon.cli.rs/)** — zsh plugin manager (TOML config, Rust-based).
- **[Starship](https://starship.rs/)** — cross-shell prompt (TOML config, Rust-based).
- **Autoloaded functions** — zsh-specific functions are files in `functions/`, loaded on first call.
- **Standalone scripts** — shell-agnostic utilities live in `~/.local/bin` (managed separately).

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
├── .chezmoiroot              # points chezmoi to home/
├── Containerfile              # test container (Fedora + Ghostty + VNC)
├── Makefile                   # build/run/validate targets
│
└── home/                      # chezmoi source state
    ├── .chezmoi.toml.tmpl     # machine config (prompted on init)
    ├── .chezmoiscripts/       # install scripts (homebrew, packages, sheldon)
    ├── dot_zshenv             # sets ZDOTDIR → only file in $HOME
    │
    ├── private_dot_config/
    │   ├── zsh/
    │   │   ├── dot_zshrc      # thin loader
    │   │   ├── exact_conf.d/  # numbered zsh modules
    │   │   └── functions/     # autoloaded functions (zsh-specific only)
    │   ├── sheldon/           # plugin definitions
    │   ├── starship.toml      # prompt config
    │   └── ghostty/           # terminal config
    │
    ├── dot_gitconfig.tmpl     # git (templated for name/email)
    └── dot_tmux.conf          # tmux
```

## Zsh load order

```
~/.zshenv                         → sets ZDOTDIR=~/.config/zsh
~/.config/zsh/.zprofile            → Homebrew shellenv
~/.config/zsh/.zshrc               → autoloads functions, sources conf.d/*
  01-options.zsh                   → locale, colors, setopt
  02-history.zsh                   → history size, dedup, append
  03-completions.zsh               → compinit (cached daily)
  04-keybindings.zsh               → bindkey
  05-prompt.zsh                    → starship init
  06-aliases.zsh                   → suffix aliases only
  07-plugins.zsh                   → sheldon source
  10-*.zsh                         → tool-specific (homebrew, nvm, java, go, ...)
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

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| Dotfiles manager | chezmoi | Real files (not symlinks), templating, multi-machine, can stop using anytime |
| Zsh layout | ZDOTDIR | Keeps `$HOME` clean — only `~/.zshenv` |
| Plugin manager | Sheldon | TOML config, fast (Rust), actively maintained |
| Prompt | Starship | Actively maintained (p10k is on life support), cross-shell |
| Functions vs scripts | Scripts for POSIX, functions for zsh-only | Scripts work in any shell and from cron/other tools |
| exact_ on conf.d/ | yes | Removing a module from the repo removes it from the target |
| exact_ on .config/ | no | Other apps create dirs in .config/ freely |
