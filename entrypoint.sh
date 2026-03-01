#!/bin/bash
set -euo pipefail

# Apply dotfiles if repo is mounted
if [ -d /dotfiles/home ]; then
  # Provide default data for non-interactive container use
  mkdir -p ~/.config/chezmoi
  cat > ~/.config/chezmoi/chezmoi.toml <<'TOML'
[data]
    email = "test@example.com"
    name = "Test User"
    is_personal = true
TOML
  chezmoi init --apply --source /dotfiles/home
fi

# If "vnc" argument, start VNC + window manager + shell
if [ "${1:-}" = "vnc" ]; then
  vncserver :1 -geometry 1920x1080 -depth 24 -SecurityTypes None
  DISPLAY=:1 fluxbox &
  echo "VNC server started on port 5901"
  exec tail -f /root/.vnc/*:1.log
else
  exec zsh -li
fi
