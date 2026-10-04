#!/usr/bin/env bash
# Purpose: Install Claude Code skills.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

case "${DOTFILES_CONTEXT:-}" in
  bkahlert) agents=(claude-code) ;;
  ista)     agents=(claude-code gemini-cli github-copilot) ;;
  *)        exit 0 ;;
esac

command -v npx >/dev/null || { printf 'npx not available; skipping skills install\n' >&2; exit 0; }

# Both pins run third-party code on every apply; bump them together, which also re-runs this script.
skills_cli=skills@1.7.0
mattpocock_ref=d81f3a183412e71a5b1e84ca21bc1a35eea03a60

# grill-me — Socratic quiz skill for learning topics interactively (mattpocock)
npx --yes "${skills_cli}" add -g "mattpocock/skills/skills/productivity/grill-me#${mattpocock_ref}" --agent "${agents[@]}" -y

# handoff — compact the conversation into a document a fresh session can continue from (mattpocock)
npx --yes "${skills_cli}" add -g "mattpocock/skills/skills/productivity/handoff#${mattpocock_ref}" --agent "${agents[@]}" -y
