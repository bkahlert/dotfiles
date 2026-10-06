#!/usr/bin/env bash
# Purpose: Register user-scoped MCP servers when Claude Code is available.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

# Fresh Macs have no Homebrew bin directory on PATH yet.
PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"
command -v claude >/dev/null || exit 0

# Servers an earlier version of this script registered; removed wherever they are still registered.
for retired in context7 serena gcloud-observability; do
  claude mcp remove --scope user "$retired" 2>/dev/null || true
done

# idea — IntelliJ MCP server over HTTP; uses the currently active project.
# "idea" is the key IntelliJ's own auto-configure uses; "jetbrains" is its legacy key.
claude mcp remove --scope user jetbrains 2>/dev/null || true
claude mcp remove --scope user idea 2>/dev/null || true
claude mcp add --scope user --transport http idea http://127.0.0.1:64342/stream
