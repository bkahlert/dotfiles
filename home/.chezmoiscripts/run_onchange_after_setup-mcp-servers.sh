#!/usr/bin/env bash
# Purpose: Register user-scoped MCP servers in Claude Code.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

command -v claude >/dev/null || { printf 'claude not available; skipping MCP server setup\n' >&2; exit 0; }

# context7 — up-to-date library documentation lookup (Upstash)
claude mcp remove --scope user context7 2>/dev/null || true
#claude mcp add --scope user context7 -- npx -y @upstash/context7-mcp

# idea — IntelliJ MCP server over HTTP; uses the currently active project.
# "idea" is the key IntelliJ's own auto-configure uses; "jetbrains" is its legacy key.
claude mcp remove --scope user jetbrains 2>/dev/null || true
claude mcp remove --scope user idea 2>/dev/null || true
claude mcp add --scope user --transport http idea http://127.0.0.1:64342/stream

# serena — codebase intelligence fallback when IntelliJ is not running
claude mcp remove --scope user serena 2>/dev/null || true
#claude mcp add --scope user serena -- uvx \
#  --from git+https://github.com/oraios/serena \
#  serena start-mcp-server \
#  --context ide-assistant \
#  --project-from-cwd \
#  --enable-web-dashboard false

# gcloud-observability — GCP logs/traces. The server is work-only, so
# re-enabling the add needs a `[[ "$DOTFILES_CONTEXT" == ista ]]` guard; the
# removal runs everywhere, like the others above.
claude mcp remove --scope user gcloud-observability 2>/dev/null || true
#claude mcp add --scope user gcloud-observability -- npx -y @google-cloud/observability-mcp
