#!/usr/bin/env bash
# Purpose: Install Homebrew if not already installed.
# Usage:   Run automatically by chezmoi on first apply.

set -euo pipefail

[[ $(uname) == Darwin ]] || exit 0

# A fresh Mac has no brew on PATH yet: dot_zprofile, which adds it, is applied only after the scripts run.
if ! command -v brew &>/dev/null; then
  for prefix in /opt/homebrew /usr/local; do
    if [[ -x $prefix/bin/brew ]]; then
      eval "$("$prefix/bin/brew" shellenv)"
      break
    fi
  done
fi

if ! command -v brew &>/dev/null; then
  echo "Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
