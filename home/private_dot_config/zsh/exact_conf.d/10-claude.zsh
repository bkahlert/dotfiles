if command -v claude &>/dev/null; then
  zsh-defer source <(claude completion --shell zsh)
fi
