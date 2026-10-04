#!/usr/bin/env bash
# Purpose: Install nvm and a default Node.js; .zshenv puts that node on PATH for every shell.
# Usage:   Run automatically by chezmoi on first apply.

set -euo pipefail

# Bump deliberately: the installer runs as published at this tag.
nvm_version=v0.40.8
export NVM_DIR="$HOME/.nvm"

if [[ ! -s $NVM_DIR/nvm.sh ]]; then
  # Downloaded in full before it runs, so a failed or truncated download aborts instead of running half a script.
  installer=$(mktemp)
  trap 'rm -f "$installer"' EXIT
  curl --proto '=https' --tlsv1.2 -fsSL --output "$installer" \
    "https://raw.githubusercontent.com/nvm-sh/nvm/$nvm_version/install.sh"
  mkdir -p "$NVM_DIR"
  # PROFILE=/dev/null: the installer would append its loader to a shell profile; .zshenv and conf.d/10-nvm.zsh cover that.
  PROFILE=/dev/null bash "$installer"
fi

# nvm.sh is not written for set -u.
set +u
# shellcheck source=/dev/null
source "$NVM_DIR/nvm.sh"

# A default chosen earlier (nvm alias default 22) stays and is installed if missing; otherwise the latest LTS
# becomes the default and follows each new LTS line.
if [[ -s $NVM_DIR/alias/default ]]; then
  nvm install "$(<"$NVM_DIR/alias/default")" --no-progress
else
  nvm install --lts --no-progress
  nvm alias default 'lts/*'
fi
