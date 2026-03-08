#!/usr/bin/env bash
# Purpose: Register user-scoped MCP servers in Claude Code.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

# context7 — up-to-date library documentation lookup (Upstash)
claude mcp remove --scope user context7 2>/dev/null || true
claude mcp add --scope user context7 -- npx -y @upstash/context7-mcp

# serena — codebase intelligence; detects project root from working directory
claude mcp remove --scope user serena 2>/dev/null || true
claude mcp add --scope user serena -- uvx \
  --from git+https://github.com/oraios/serena \
  serena start-mcp-server \
  --context ide-assistant \
  --project-from-cwd
