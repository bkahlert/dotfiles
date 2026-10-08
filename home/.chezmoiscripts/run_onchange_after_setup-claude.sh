#!/usr/bin/env bash
# Purpose: Set up Claude Code's MCP server and third-party skills.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"
if command -v fnm >/dev/null; then
  fnm_env=$(fnm env --shell bash)
  eval "$fnm_env"
fi
command -v claude >/dev/null || exit 0
command -v fnm >/dev/null || { printf 'fnm not found; run_once_before_01-install-packages installs it\n' >&2; exit 1; }

# Replace IntelliJ's legacy key and any earlier user-scoped registration.
claude mcp remove --scope user jetbrains 2>/dev/null || true
claude mcp remove --scope user idea 2>/dev/null || true
claude mcp add --scope user --transport http idea http://127.0.0.1:64342/stream

npx --yes skills add -g "https://github.com/mattpocock/skills" \
  --skill grill-me \
  --skill grilling \
  --skill handoff \
  --skill improve-codebase-architecture \
  --skill codebase-design \
  --skill domain-modeling \
  --skill setup-matt-pocock-skills \
  --agent claude-code -y
