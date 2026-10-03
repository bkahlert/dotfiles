# dotfiles [![Buy Me A Coffee](https://img.shields.io/static/v1?label=&message=%E2%98%95%20Buy%20Me%20A%20Coffee&color=FFDD00)](https://www.buymeacoffee.com/bkahlert)

Personal dotfiles managed with [chezmoi](https://www.chezmoi.io/).

## Quick start

**Fresh machine (one-liner):**

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -- \
  init --apply bkahlert --source ~/.local/share/chezmoi
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
- **Shell features** — scripts, functions, aliases and keybindings are spread over several prefixed source paths. [quick-access/](quick-access/README.md) maps them with prefix-free symlinks and explains where a new one belongs.
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

### Shell features (scripts, functions, aliases)

See [quick-access/README.md](quick-access/README.md) — location map, which place a new
command belongs in, resolution order, and zsh load order.

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

## SSH keys (KeePassXC)

Personal SSH keys (github, etc.) live in iCloud Drive's Vault directory.
On `chezmoi apply`, `.chezmoiscripts/run_onchange_after_dump-ssh-from-kdbx.tmpl`
reads the vault (prompting for the master password via a macOS dialog) and
materializes `~/.ssh/conf.d/*.conf` + `*.pub` files; the actual private keys are
pushed live into the launchd ssh-agent (`SSH_AUTH_SOCK`) by KeePassXC's own SSH
Agent integration when the database is unlocked.

KeePassXC is installed via the Brewfile, but its SSH Agent integration is an
app preference chezmoi can't manage — set it up once per machine:

1. Open KeePassXC and unlock your `kdbx` file(s).
2. **Settings → SSH Agent → check "Enable SSH Agent integration"**, then fully
   quit and reopen KeePassXC (the per-entry tab below only appears after a
   restart).
3. For each key entry, edit it → **SSH Agent** tab → check **"Add key to agent
   when database is opened/unlocked"** (usually already set from the kdbx
   template).

## Testing

```sh
make lint                # shellcheck, zsh -n, workflow lint
make unit                # pytest unit tests + node driver test
make integration         # apply all three contexts in a Fedora container (needs Podman)
make integration-native  # same, natively into a temp HOME (macOS)
make ci                  # lint unit integration
make run                 # start the VNC inspection container on :5901
make vnc                 # open a VNC viewer
make stop                # stop it
make clean               # remove the images
```

CI runs the same targets on every pull request; `main` requires the `ci` check. Details in [AGENTS.md](AGENTS.md#testing).

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

