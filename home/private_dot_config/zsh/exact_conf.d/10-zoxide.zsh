# Initialize zoxide (`z` command). Defer to post-startup when available.
if command -v zoxide &>/dev/null; then
  if (( $+functions[zsh-defer] )); then
    zsh-defer eval "$(zoxide init zsh)"
  else
    eval "$(zoxide init zsh)"
  fi
fi
