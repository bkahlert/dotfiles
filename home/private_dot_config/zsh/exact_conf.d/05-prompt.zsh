# Initialize the Starship prompt. Skipped if starship isn't installed yet
# (e.g. on a fresh machine before Brewfile has run).
if command -v starship &>/dev/null; then
  eval "$(starship init zsh)"
fi
