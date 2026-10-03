# Initialize zoxide (`z` command). Defer to post-startup when available.
# zsh-defer -c, not `zsh-defer eval "$(...)"`: the latter expands $(...) right away,
# so the tool would still run during startup and only its eval would be deferred.
if command -v zoxide &>/dev/null; then
  if (( $+functions[zsh-defer] )); then
    zsh-defer -c 'eval "$(zoxide init zsh)"'
  else
    eval "$(zoxide init zsh)"
  fi
fi
