#!/usr/bin/env bash
# Purpose: Register the user-scoped IntelliJ MCP server for available Claude Code and Copilot CLIs.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

# Fresh Macs have no Homebrew bin directory on PATH yet.
PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"
# idea — IntelliJ MCP server over HTTP; uses the currently active project.
# "idea" is the key IntelliJ's own auto-configure uses; "jetbrains" is its legacy key.
if command -v claude >/dev/null; then
  claude mcp remove --scope user jetbrains 2>/dev/null || true
  claude mcp remove --scope user idea 2>/dev/null || true
  claude mcp add --scope user --transport http idea http://127.0.0.1:64342/stream
fi

if command -v copilot >/dev/null; then
  copilot mcp remove idea 2>/dev/null || true
  copilot mcp add --transport http idea http://127.0.0.1:64342/stream
fi
