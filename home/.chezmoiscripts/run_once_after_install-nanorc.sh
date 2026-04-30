#!/usr/bin/env bash
# Purpose: Install scopatz/nanorc syntax highlighting bundle for nano.
# Usage:   Run automatically by chezmoi the first time this file is seen.

set -euo pipefail

[ -e "$HOME/.nano" ] && exit 0

command -v git >/dev/null || { printf 'git not available; skipping nanorc install\n' >&2; exit 0; }

git clone --depth=1 --quiet https://github.com/scopatz/nanorc.git "$HOME/.nano"
