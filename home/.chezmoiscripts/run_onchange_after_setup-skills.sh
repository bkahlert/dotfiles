#!/usr/bin/env bash
# Purpose: Install skills for every available Claude Code, Gemini CLI and GitHub Copilot CLI.
# Usage:   Run automatically by chezmoi when this file changes.

set -euo pipefail

# npx is that of fnm's default Node.js (run_once_before_02-install-node). fnm is Homebrew's on macOS, whose bin a
# fresh Mac has on no PATH yet, and in ~/.local/bin on Linux.
PATH="$PATH:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin"
if command -v fnm >/dev/null; then
  fnm_env=$(fnm env --shell bash)
  eval "$fnm_env"
fi

agents=()
if command -v claude >/dev/null; then agents+=(claude-code); fi
if command -v gemini >/dev/null; then agents+=(gemini-cli); fi
if command -v copilot >/dev/null; then agents+=(github-copilot); fi
if ((${#agents[@]} == 0)); then
  exit 0
fi

command -v fnm >/dev/null || { printf 'fnm not found; run_once_before_01-install-packages installs it\n' >&2; exit 1; }

# grill-me — Socratic quiz skill for learning topics interactively (mattpocock)
npx --yes skills add -g "mattpocock/skills/skills/productivity/grill-me" --agent "${agents[@]}" -y

# grilling — the interview itself; grill-me only tells the agent to call it, so grill-me does nothing without it (mattpocock)
npx --yes skills add -g "mattpocock/skills/skills/productivity/grilling" --agent "${agents[@]}" -y

# handoff — compact the conversation into a document a fresh session can continue from (mattpocock)
npx --yes skills add -g "mattpocock/skills/skills/productivity/handoff" --agent "${agents[@]}" -y
