#!/usr/bin/env bash
# Purpose: Install the Claude Code CLI with Anthropic's native installer.
# Usage:   Run automatically by chezmoi on first apply.

set -euo pipefail

# The installer puts claude in ~/.local/bin (kept out of exact_bin by .chezmoiignore), where it updates itself.
[[ -x $HOME/.local/bin/claude ]] && exit 0

# Downloaded in full before it runs, so a failed or truncated download aborts instead of running half a script.
installer=$(mktemp)
trap 'rm -f "$installer"' EXIT
curl --proto '=https' --tlsv1.2 -fsSL --output "$installer" https://claude.ai/install.sh
bash "$installer"
