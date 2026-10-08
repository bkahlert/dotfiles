#!/usr/bin/env bash
# Purpose: Apply the mounted dotfiles, then start zsh or the VNC inspection session.
# Usage:   entrypoint.sh [vnc | <zsh arguments>...]
#
# The apply's output goes to stdout so that stderr carries only what the zsh startup prints; the
# integration test asserts that it stays empty. Stdin is left untouched: chezmoi reads one line as
# the KeePassXC password when a template needs it. A keepassxc-cli shim is expected
# under /opt/shims.

set -euo pipefail

[[ -d /opt/shims ]] && export PATH="/opt/shims:$PATH"

if [[ -d /dotfiles/home ]]; then
  mkdir -p ~/.config/chezmoi
  cat > ~/.config/chezmoi/chezmoi.toml <<TOML
[data]
    email = "test@example.com"
    name = "Test User"
TOML
  chezmoi init --apply --no-tty --source /dotfiles/home 2>&1
fi

if [[ ${1:-} == vnc ]]; then
  vncserver :1 -geometry 1920x1080 -depth 24 -SecurityTypes None
  DISPLAY=:1 fluxbox &
  echo "VNC server started on port 5901"
  exec tail -f /root/.vnc/*:1.log
else
  exec zsh -li "$@"
fi
