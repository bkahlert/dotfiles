#!/usr/bin/env bash
# Purpose: Install Claude Code skills.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

case "${DOTFILES_CONTEXT:-}" in
  bkahlert) agents=(claude-code) ;;
  ista)     agents=(claude-code gemini-cli github-copilot) ;;
  *)        exit 0 ;;
esac

# npx is the default node's, which run_once_before_02-install-nvm installed. --no-use and an explicit `nvm use`:
# loading alone would pick the version of an ~/.nvmrc (the script runs in $HOME) and, should that one not be
# installed, fail without a word.
export NVM_DIR="$HOME/.nvm"
[[ -s $NVM_DIR/nvm.sh ]] || { printf 'nvm not found in %s; run_once_before_02-install-nvm installs it\n' "$NVM_DIR" >&2; exit 1; }
# nvm.sh is not written for set -u.
set +u
# shellcheck source=/dev/null
source "$NVM_DIR/nvm.sh" --no-use
nvm use default >/dev/null
set -u

# grill-me — Socratic quiz skill for learning topics interactively (mattpocock)
npx --yes skills add -g "mattpocock/skills/skills/productivity/grill-me" --agent "${agents[@]}" -y

# handoff — compact the conversation into a document a fresh session can continue from (mattpocock)
npx --yes skills add -g "mattpocock/skills/skills/productivity/handoff" --agent "${agents[@]}" -y
