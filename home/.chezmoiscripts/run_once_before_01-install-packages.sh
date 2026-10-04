#!/usr/bin/env bash
# Purpose: Install core packages via Homebrew (macOS) or curl (Linux).
# Usage:   Run automatically by chezmoi on first apply.

set -euo pipefail

if [[ $(uname) == Darwin ]]; then
  # A fresh Mac has no brew on PATH yet: dot_zprofile, which adds it, is applied only after the scripts run.
  if ! command -v brew &>/dev/null; then
    for prefix in /opt/homebrew /usr/local; do
      if [[ -x $prefix/bin/brew ]]; then
        eval "$("$prefix/bin/brew" shellenv)"
        break
      fi
    done
  fi

  brew bundle --file=/dev/stdin <<EOF
brew "uv"                          # Python package/project manager (replaces pip + venv + pyenv)
brew "sheldon"                     # Zsh plugin manager; config in ~/.config/sheldon/plugins.toml
brew "starship"                    # Cross-shell prompt; config in ~/.config/starship.toml
brew "zoxide"                      # Smarter cd that learns frecency; aliased to z in conf.d
brew "bat"                         # cat replacement with syntax highlighting and git diff support
brew "jq"                          # Command-line JSON processor; used by scripts and aliases
brew "shellcheck"                  # Shell script linter; make lint runs it on every bash file
brew "actionlint"                  # GitHub Actions workflow linter; make lint runs it on .github/workflows
brew "btop"                        # Terminal resource monitor (CPU, memory, disk, network)
brew "coreutils"                   # GNU core utilities as g-prefixed binaries; macOS ships no timeout, ~/.local/bin/timeout forwards to gtimeout
brew "glab"                        # GitLab CLI (glab); merge requests and pipelines from the terminal, installed up front instead of on first use
brew "bash"                        # Bash 5; ~/.local/bin scripts need bash >= 4.4 (empty arrays under set -u, job notices, FIFO reads), macOS ships 3.2
brew "common-fate/granted/granted", trusted: true # granted (assume); AWS IAM Identity Center profile switcher, installed up front instead of on the first assume; trusted: Homebrew loads no third-party tap formula without it
cask "1password-cli"               # 1Password CLI (op); required by chezmoi to read secrets at apply time
cask "keepassxc"                   # KeePassXC; its KeeAgent feeds personal SSH keys into the launchd ssh-agent, and chezmoi reads personal secrets from its database at apply time
cask "font-jetbrains-mono-nerd-font" # Nerd Font variant of JetBrains Mono; required by Starship glyphs
EOF

else
  # An installer is downloaded in full before it runs, so a failed or truncated download aborts
  # the script instead of feeding a partial script to the shell.
  installer_dir=$(mktemp -d)
  trap 'rm -rf "$installer_dir"' EXIT

  # Usage: run_installer <shell> <url> [installer-args...]
  run_installer() {
    local shell=$1 url=$2 file
    shift 2
    file=$(mktemp "$installer_dir/installer.XXXXXX")
    curl --proto '=https' --tlsv1.2 -fsSL --output "$file" "$url"
    "$shell" "$file" "$@"
  }

  # Sheldon — zsh plugin manager; no package in most distros, installed via its own installer
  if ! command -v sheldon &>/dev/null; then
    run_installer bash https://rossmacarthur.github.io/install/crate.sh \
      --repo rossmacarthur/sheldon --to ~/.local/bin
  fi

  # Starship — cross-shell prompt; official installer handles version pinning and arch detection
  if ! command -v starship &>/dev/null; then
    run_installer sh https://starship.rs/install.sh --yes
  fi

  # zoxide — frecency-based cd replacement; aliased to z in conf.d
  # The installer script is pinned to a release tag; it still installs the latest release binary.
  if ! command -v zoxide &>/dev/null; then
    run_installer sh https://raw.githubusercontent.com/ajeetdsouza/zoxide/v0.10.0/install.sh
  fi
fi
