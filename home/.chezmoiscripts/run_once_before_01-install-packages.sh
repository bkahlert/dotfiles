#!/usr/bin/env bash
# Purpose: Install core packages via Homebrew (macOS) or curl (Linux).
# Usage:   Run automatically by chezmoi on first apply.

set -euo pipefail

if [[ $(uname) == Darwin ]]; then
  brew bundle --file=/dev/stdin <<EOF
brew "uv"                          # Python package/project manager (replaces pip + venv + pyenv)
brew "sheldon"                     # Zsh plugin manager; config in ~/.config/sheldon/plugins.toml
brew "starship"                    # Cross-shell prompt; config in ~/.config/starship.toml
brew "zoxide"                      # Smarter cd that learns frecency; aliased to z in conf.d
brew "bat"                         # cat replacement with syntax highlighting and git diff support
brew "jq"                          # Command-line JSON processor; used by scripts and aliases
brew "btop"                        # Terminal resource monitor (CPU, memory, disk, network)
cask "1password-cli"               # 1Password CLI (op); required by chezmoi to read secrets at apply time
cask "font-jetbrains-mono-nerd-font" # Nerd Font variant of JetBrains Mono; required by Starship glyphs
EOF

else
  # Sheldon — zsh plugin manager; no package in most distros, installed via its own installer
  if ! command -v sheldon &>/dev/null; then
    curl --proto '=https' -fLsS https://rossmacarthur.github.io/install/crate.sh \
      | bash -s -- --repo rossmacarthur/sheldon --to ~/.local/bin
  fi

  # Starship — cross-shell prompt; official installer handles version pinning and arch detection
  if ! command -v starship &>/dev/null; then
    curl -sS https://starship.rs/install.sh | sh -s -- --yes
  fi

  # zoxide — frecency-based cd replacement; aliased to z in conf.d
  if ! command -v zoxide &>/dev/null; then
    curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh
  fi
fi
