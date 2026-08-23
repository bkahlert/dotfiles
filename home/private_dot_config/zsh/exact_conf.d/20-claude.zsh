# Auto-install Claude CLI wrapper
claude() {
  if ! (( $+commands[claude] )); then
    echo "Claude not found. Installing..." >&2
    curl -fsSL https://claude.ai/install.sh | bash
    rehash
  fi
  command claude "$@"
}

# No shell completion here on purpose: the CLI has no `completion` subcommand
# (`claude --help` lists none), so `claude completion --shell zsh` was parsed as
# a *prompt* plus an unknown option, printing "error: unknown option '--shell'"
# on every shell start. Re-add only if a completion subcommand ships.

alias clauded="claude --dangerously-skip-permissions"
