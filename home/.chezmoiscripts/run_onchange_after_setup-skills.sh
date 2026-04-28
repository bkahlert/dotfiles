#!/usr/bin/env bash
# Purpose: Install Claude Code skills.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

case "${DOTFILES_CONTEXT:-}" in
  bkahlert) agents=(claude-code) ;;
  ista)     agents=(claude-code gemini-cli github-copilot) ;;
  *)        exit 0 ;;
esac

# grill-me — Socratic quiz skill for learning topics interactively (mattpocock)
npx --yes skills@latest add mattpocock/skills/skills/grill-me --agent "${agents[@]}" -y
