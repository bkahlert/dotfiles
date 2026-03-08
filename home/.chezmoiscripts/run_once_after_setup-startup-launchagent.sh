#!/usr/bin/env bash
# Purpose: Sets up a LaunchAgent that runs ~/.startup at login.
# Usage:   Run automatically by chezmoi on first apply. Re-run with: chezmoi apply --force

set -euo pipefail

[[ $(uname) == Darwin ]] || exit 0

plist_path="$HOME/Library/LaunchAgents/com.user.startup.plist"
startup_script="$HOME/.startup"

if [[ ! -f "$startup_script" ]]; then
  echo "Skipping LaunchAgent setup: $startup_script not found"
  exit 0
fi

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$plist_path" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.startup</string>
    <key>ProgramArguments</key>
    <array>
        <string>$startup_script</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.startup.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.startup.log</string>
</dict>
</plist>
EOF

launchctl unload "$plist_path" 2>/dev/null || true
launchctl load "$plist_path"

echo "LaunchAgent for ~/.startup configured"
