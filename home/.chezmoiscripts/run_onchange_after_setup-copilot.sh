#!/usr/bin/env bash
# Purpose: Set up GitHub Copilot CLI's MCP servers, plugins and third-party skills.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"
if command -v fnm >/dev/null; then
  fnm_env=$(fnm env --shell bash)
  eval "$fnm_env"
fi
command -v copilot >/dev/null || exit 0
command -v fnm >/dev/null || { printf 'fnm not found; run_once_before_01-install-packages installs it\n' >&2; exit 1; }

copilot mcp remove idea 2>/dev/null || true
copilot mcp add --transport http idea http://127.0.0.1:64342/stream
copilot mcp remove context7 2>/dev/null || true
copilot mcp add context7 -- npx --yes @upstash/context7-mcp@latest
copilot mcp remove chrome-devtools 2>/dev/null || true
copilot mcp add chrome-devtools -- npx --yes chrome-devtools-mcp@latest \
  --headless --isolated --no-usage-statistics

marketplaces=$(copilot plugin marketplace list --json)
registered=$(jq -r 'any(.[]; .name == "superpowers-marketplace")' <<<"$marketplaces")
if [[ $registered == false ]]; then
  copilot plugin marketplace add obra/superpowers-marketplace
fi
copilot plugin install superpowers@superpowers-marketplace

for skill in grill-me grilling handoff; do
  npx --yes skills add -g "mattpocock/skills/skills/productivity/$skill" --agent github-copilot -y
done
