#!/usr/bin/env bash
# Purpose: Install core packages via Homebrew (macOS) or curl (Linux).
# Usage:   Run automatically by chezmoi on first apply.

set -euo pipefail

if [[ $(uname) == Darwin ]]; then
  brew bundle --file=/dev/stdin <<EOF
brew "sheldon"
brew "starship"
brew "zoxide"
brew "bat"
brew "jq"
brew "btop"
cask "1password-cli"
cask "font-jetbrains-mono-nerd-font"
EOF

else
  # Sheldon
  if ! command -v sheldon &>/dev/null; then
    curl --proto '=https' -fLsS https://rossmacarthur.github.io/install/crate.sh \
      | bash -s -- --repo rossmacarthur/sheldon --to ~/.local/bin
  fi

  # Starship
  if ! command -v starship &>/dev/null; then
    curl -sS https://starship.rs/install.sh | sh -s -- --yes
  fi

  # zoxide
  if ! command -v zoxide &>/dev/null; then
    curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh
  fi
fi
