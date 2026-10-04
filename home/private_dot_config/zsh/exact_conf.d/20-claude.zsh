# claude comes from run_once_before_03-install-claude, which puts it in ~/.local/bin, where it updates itself.

# No shell completion here on purpose: the CLI has no `completion` subcommand
# (`claude --help` lists none), so `claude completion --shell zsh` was parsed as
# a *prompt* plus an unknown option, printing "error: unknown option '--shell'"
# on every shell start. Re-add only if a completion subcommand ships.

alias clauded="claude --dangerously-skip-permissions"
