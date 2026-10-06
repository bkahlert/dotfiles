#!/usr/bin/env bash
# Purpose: Set up Gemini CLI's third-party skills.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"
if command -v fnm >/dev/null; then
  fnm_env=$(fnm env --shell bash)
  eval "$fnm_env"
fi
command -v gemini >/dev/null || exit 0
command -v fnm >/dev/null || { printf 'fnm not found; run_once_before_01-install-packages installs it\n' >&2; exit 1; }

for skill in grill-me grilling handoff; do
  npx --yes skills add -g "mattpocock/skills/skills/productivity/$skill" --agent gemini-cli -y
done
