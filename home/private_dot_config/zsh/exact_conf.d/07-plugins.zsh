# Source zsh plugins managed by Sheldon (see ~/.config/sheldon/plugins.toml).
# Skipped if sheldon isn't installed yet (e.g. on a fresh machine).
if command -v sheldon &>/dev/null; then
  eval "$(sheldon source)"
fi
