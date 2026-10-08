# dotfiles [![CI](https://github.com/bkahlert/dotfiles/actions/workflows/ci.yml/badge.svg)](https://github.com/bkahlert/dotfiles/actions/workflows/ci.yml) [![License](https://img.shields.io/github/license/bkahlert/dotfiles?color=29ABE2&label=License)](https://github.com/bkahlert/dotfiles/blob/main/LICENSE) [![Buy Me A Coffee](https://img.shields.io/static/v1?label=&message=%E2%98%95%20Buy%20Me%20A%20Coffee&color=FFDD00)](https://www.buymeacoffee.com/bkahlert)

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
- **AI assistant configs** — `~/.claude/`, `~/.copilot/`, `~/.gemini/`, and `~/.config/agents/` are tracked so settings, prompt rules and slash commands stay in sync across machines.

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

### Agent status lines

[Claude's formatter](home/private_dot_claude/executable_statusline) and
[Copilot's formatter](home/private_dot_copilot/executable_statusline) share the
session, context and cost formatting. Claude also uses the shared model renderer;
Copilot omits the model from its custom status line.
[The shared component](home/dot_local/share/agent_statusline.py) owns semantic
CLI help and argument parsing, preview and input loading, input dumping, JSON
parsing, field lookup, numeric validation, severity colors, icons, context
gauges, hyperlinks and automatic Nerd Font detection. Both formatters use
its cache at `$XDG_CACHE_HOME/agent-statusline/nerd-font-support`, defaulting to
`~/.cache/agent-statusline/nerd-font-support`.
`--nerd-fonts` and `--no-nerd-fonts` override `NERD_FONTS=1`/`0`;
both override detection.
Each script supplies its own help header, preview fixture and input-dump filename.
Preview command failures preserve stderr and the failed command's exit status.

Session IDs and names render independently: only the shortened ID links to the
transcript, while the name appears in italics outside the link.
The shared `part_session` renderer accepts an optional ID, name and URL, and
selects its own session icon using the font override or automatic detection.
The shared `part_model` renderer also selects its icon and handles missing-model
text and optional configured-model highlighting; scripts only supply its arguments.
The shared `part_context` renderer owns gauge selection, percentage thresholds and
token formatting. Copilot supplies current context metrics, falling back to legacy fields.
The shared `part_cost` renderer formats dollar amounts with two decimals.
Each script supplies its own yellow/red thresholds, both set to 5/10 USD.
Copilot converts raw nano-AIU to an estimated dollar equivalent using
100 AIC per USD; this is a display estimate, not a verified billed amount.

Preview Claude's sample:

```sh
home/private_dot_claude/executable_statusline --preview --nerd-fonts
```

Preview Copilot's sample, with matching session, model and context values:

```sh
home/private_dot_copilot/executable_statusline --preview --nerd-fonts
```

Copilot shows the estimated session dollar cost in Claude's cost position.
Remote and allow-all indicators are omitted from the custom status line;
all native footer options remain enabled.
Its command input does not include
the plan allowance, active agent, reasoning effort or sandbox state. Those stay
in the native footer.

Both formatters save their latest raw input, including previews, as
`claude-statusline-input.json` and `copilot-statusline-input.json` in Python's
temporary directory (`TMPDIR` when set). Each file is replaced atomically with
owner-only permissions. The files contain session metadata and are overwritten
on the next render.

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

| Command | Coverage |
|---|---|
| `make lint` | shellcheck, zsh syntax, workflow lint |
| `make unit` | pytest unit tests and node driver test |
| `make integration` | Apply this checkout in a Fedora container; needs Podman |
| `make integration-native` | Apply into a temporary HOME on macOS; check Homebrew packages |
| `make ci` | Lint, unit and container integration; no agent login or model usage |
| `make integration-claude` | **Paid, opt-in:** effective Claude capabilities; needs Claude login |
| `make integration-copilot` | **Paid, opt-in:** effective Copilot capabilities; needs Copilot login |
| `make run` / `make vnc` | Start the inspection container / open its VNC viewer |
| `make stop` / `make clean` | Stop the inspection container / remove its images |

CI runs the same targets on every pull request; `main` requires the `ci` check. Details in [AGENTS.md](AGENTS.md#testing).

### Live agent capabilities

The authenticated targets test the **currently applied configuration**, not source
JSON or installer commands. They do not apply dotfiles or install missing tools.
Normal CLI sessions load user and project settings, plugins, skills and MCPs.
They are never part of `make ci`, `make unit`, or either apply integration target.
Running pytest directly skips them unless `--live-agent claude` or
`--live-agent copilot` is supplied.

| Capability | Required evidence |
|---|---|
| Context7 | Successful library resolution and a documentation query about Python's `len` |
| Chrome DevTools | Successful `list_pages` response from a real browser; no navigation or page changes |
| IntelliJ `idea` | Successful read of a tiny public fixture with a known marker |
| Superpowers | Successful `verification-before-completion` skill invocation, followed by a real `printf` check and evidence cited in the answer |

Assertions inspect structured tool calls and their results. An assistant's claim
that a capability works is insufficient. These smoke tests prove explicit skill
invocation, not automatic skill selection or consistent methodology adherence.
The browser check proves connection and page listing, not every browser tool.

Prerequisites: the chosen CLI must be installed and logged in; Node.js/npm must be
on PATH for stdio MCPs; Chrome must be installed; IntelliJ must have this repository
open and serve MCP at `http://127.0.0.1:64342/stream`. Start from your normal shell
so exported secrets, including `CONTEXT7_API_KEY`, are available. Missing,
disabled, unauthenticated or broken capabilities fail rather than silently skip.

Copilot provisioning runs on `chezmoi apply`: its
[agent setup](home/.chezmoiscripts/run_onchange_after_setup-copilot.sh) registers
Context7 and Chrome DevTools alongside `idea`, installs Superpowers from its
upstream marketplace, and installs third-party skills. The
[Claude setup](home/.chezmoiscripts/run_onchange_after_setup-claude.sh) registers
`idea` and installs skills; the
[Gemini setup](home/.chezmoiscripts/run_onchange_after_setup-gemini.sh) installs skills.
Each script runs only for its installed agent. Renaming these onchange scripts
makes their setup run again on the next apply. Copilot's
[source settings](home/private_dot_copilot/private_settings.json) also declare the
Superpowers marketplace and enabled plugin, so later applies keep it enabled
without rerunning setup. Chrome uses an isolated,
headless profile with usage statistics disabled; it does not attach to your
personal browser. Claude keeps its existing plugin configuration, so its live
check can expose the profile-picker failure recorded in the browser guidance.

Each target shares **one session across all probes**, has a 180-second timeout,
and performs no test-level retries. Claude uses Haiku, at most eight turns and a
$0.50 budget. Copilot uses Auto's efficiency tier and a 30-AI-credit soft cap,
the CLI's minimum. These are usage limits, not exact bill guarantees; an in-flight
response can exceed a soft cap. Normal startup hooks and CLI-level API retries can
also run. Only probe tools and `printf` receive explicit approval; file-write
tools are denied in Copilot. This is not an OS sandbox.
Copilot can read the shared agent guidance directory to follow its normal instructions.

For a cheaper focused check:

```sh
make integration-copilot AGENT_TEST_ARGS='--agent-capability idea'
```

The selector is repeatable and works for either authenticated target. Private
transcripts and stderr are saved under pytest's temporary directory, printed at
startup, rather than committed or dumped into failures. Copilot's final usage
statistics are saved alongside them as `usage.json`.

Shared IntelliJ configurations live in [.run/](.run): **ci (no AI usage)**,
**Claude capabilities (paid, opt-in)** and **Copilot capabilities (paid, opt-in)**.
If IntelliJ does not discover externally added configurations, reopen the project.
The CI target does not touch your real HOME or invoke paid agents, but still uses
network downloads and container resources; “no AI usage” is not “no side effects.”
