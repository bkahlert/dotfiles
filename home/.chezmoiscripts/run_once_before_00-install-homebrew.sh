#!/usr/bin/env bash
# Purpose: Install Homebrew if not already installed.
# Usage:   Run automatically by chezmoi on first apply.

set -euo pipefail

[[ $(uname) == Darwin ]] || exit 0

if ! command -v brew &>/dev/null; then
  echo "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
