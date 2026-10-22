#!/usr/bin/env bash
# Purpose: Install Codex's Superpowers plugin and third-party skills.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"
if command -v fnm >/dev/null; then
  fnm_env=$(fnm env --shell bash)
  eval "$fnm_env"
fi
command -v codex >/dev/null || exit 0
command -v fnm >/dev/null || { printf 'fnm not found; run_once_before_01-install-packages installs it\n' >&2; exit 1; }

# The upstream repository includes Codex's native marketplace and plugin manifests.
marketplaces=$(codex plugin marketplace list --json)
registered=$(jq -r 'any(.marketplaces[]; .name == "superpowers-dev")' <<<"$marketplaces")
if [[ $registered == false ]]; then
  codex plugin marketplace add obra/superpowers
fi
codex plugin add superpowers@superpowers-dev

npx --yes skills add -g "https://github.com/mattpocock/skills" \
  --skill grill-me \
  --skill grilling \
  --skill handoff \
  --skill improve-codebase-architecture \
  --skill codebase-design \
  --skill domain-modeling \
  --skill setup-matt-pocock-skills \
  --agent codex -y
