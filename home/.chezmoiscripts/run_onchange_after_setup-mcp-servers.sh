#!/usr/bin/env bash
# Purpose: Register user-scoped MCP servers in Claude Code.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

# claude is where run_once_before_03-install-claude put it, which is on no PATH yet on a fresh machine.
PATH="$HOME/.local/bin:$PATH"
command -v claude >/dev/null || { printf 'claude not found; run_once_before_03-install-claude installs it\n' >&2; exit 1; }

# Servers an earlier version of this script registered; removed wherever they are still registered.
for retired in context7 serena gcloud-observability; do
  claude mcp remove --scope user "$retired" 2>/dev/null || true
done

# idea — IntelliJ MCP server over HTTP; uses the currently active project.
# "idea" is the key IntelliJ's own auto-configure uses; "jetbrains" is its legacy key.
claude mcp remove --scope user jetbrains 2>/dev/null || true
claude mcp remove --scope user idea 2>/dev/null || true
claude mcp add --scope user --transport http idea http://127.0.0.1:64342/stream
