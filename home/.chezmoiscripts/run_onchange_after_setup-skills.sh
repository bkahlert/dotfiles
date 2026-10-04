#!/usr/bin/env bash
# Purpose: Install Claude Code skills.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

case "${DOTFILES_CONTEXT:-}" in
  bkahlert) agents=(claude-code) ;;
  ista)     agents=(claude-code gemini-cli github-copilot) ;;
  *)        exit 0 ;;
esac

# npx is the default node's, which run_once_before_02-install-nvm installed and nvm.sh puts on PATH.
export NVM_DIR="$HOME/.nvm"
[[ -s $NVM_DIR/nvm.sh ]] || { printf 'nvm not found in %s; run_once_before_02-install-nvm installs it\n' "$NVM_DIR" >&2; exit 1; }
# nvm.sh is not written for set -u.
set +u
# shellcheck source=/dev/null
source "$NVM_DIR/nvm.sh"
set -u

# Both pins run third-party code on every apply; bump them together, which also re-runs this script.
skills_cli=skills@1.7.0
mattpocock_ref=d81f3a183412e71a5b1e84ca21bc1a35eea03a60

# grill-me — Socratic quiz skill for learning topics interactively (mattpocock)
npx --yes "${skills_cli}" add -g "mattpocock/skills/skills/productivity/grill-me#${mattpocock_ref}" --agent "${agents[@]}" -y

# handoff — compact the conversation into a document a fresh session can continue from (mattpocock)
npx --yes "${skills_cli}" add -g "mattpocock/skills/skills/productivity/handoff#${mattpocock_ref}" --agent "${agents[@]}" -y
