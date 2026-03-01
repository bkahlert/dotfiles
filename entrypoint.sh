#!/bin/bash
set -euo pipefail

# Apply dotfiles if repo is mounted
if [ -d /dotfiles/home ]; then
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
