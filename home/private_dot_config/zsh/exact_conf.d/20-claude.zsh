# Auto-install Claude CLI wrapper
claude() {
  if ! (( $+commands[claude] )); then
    echo "Claude not found. Installing..." >&2
    curl -fsSL https://claude.ai/install.sh | bash
    rehash
  fi
  command claude "$@"
}

if (( $+commands[claude] )); then
  zsh-defer source <(command claude completion --shell zsh)
fi

alias clauded="claude --dangerously-skip-permissions"
