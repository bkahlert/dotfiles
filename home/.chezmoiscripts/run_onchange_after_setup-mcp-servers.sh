#!/usr/bin/env bash
# Purpose: Register user-scoped MCP servers in Claude Code.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

# context7 — up-to-date library documentation lookup (Upstash)
claude mcp remove --scope user context7 2>/dev/null || true
#claude mcp add --scope user context7 -- npx -y @upstash/context7-mcp

# jetbrains — IntelliJ MCP server over HTTP; uses the currently active project.
# IntelliJ's own "auto-configure" writes the same server as "idea"; drop it to avoid duplicate tools.
claude mcp remove --scope user idea 2>/dev/null || true
claude mcp remove --scope user jetbrains 2>/dev/null || true
claude mcp add --scope user --transport http jetbrains http://127.0.0.1:64342/stream

# serena — codebase intelligence fallback when IntelliJ is not running
claude mcp remove --scope user serena 2>/dev/null || true
#claude mcp add --scope user serena -- uvx \
#  --from git+https://github.com/oraios/serena \
#  serena start-mcp-server \
#  --context ide-assistant \
#  --project-from-cwd \
#  --enable-web-dashboard false

if [[ -n "${DOTFILES_CONTEXT:-}" ]]; then
  # gcloud-observability — GCP logs/traces (work machines only)
  claude mcp remove --scope user gcloud-observability 2>/dev/null || true
  #claude mcp add --scope user gcloud-observability -- npx -y @google-cloud/observability-mcp
fi
