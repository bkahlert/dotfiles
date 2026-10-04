#!/usr/bin/env bash
# Purpose: Install nvm and a default Node.js; .zshenv puts that node on PATH for every shell.
# Usage:   Run automatically by chezmoi on first apply.

set -euo pipefail

export NVM_DIR="$HOME/.nvm"

if [[ ! -s $NVM_DIR/nvm.sh ]]; then
  # master's installer installs the latest release. It is downloaded in full before it runs, so a failed or
  # truncated download aborts instead of running half a script.
  installer=$(mktemp)
  trap 'rm -f "$installer"' EXIT
  curl --proto '=https' --tlsv1.2 -fsSL --output "$installer" \
    https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh
  mkdir -p "$NVM_DIR"
  # PROFILE=/dev/null: the installer would append its loader to a shell profile; .zshenv and conf.d/10-nvm.zsh cover that.
  PROFILE=/dev/null bash "$installer"
fi

# nvm.sh is not written for set -u.
set +u
# shellcheck source=/dev/null
source "$NVM_DIR/nvm.sh"

# A default chosen earlier (nvm alias default 22) stays and is installed if missing; `system` needs nothing.
# Otherwise the latest LTS is installed and its major becomes the default: not lts/*, which resolves through an
# alias nvm rewrites to the newest remote release, so it stops matching once that release is not installed.
# nvm reads options only before the version.
if [[ -s $NVM_DIR/alias/default ]]; then
  default=$(<"$NVM_DIR/alias/default")
  [[ $default == system ]] || nvm install --no-progress "$default"
else
  nvm install --no-progress --lts
  lts=$(nvm version 'lts/*')
  lts=${lts#v}
  nvm alias default "${lts%%.*}"
fi
