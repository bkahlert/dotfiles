# fzf shell integration:
#   Ctrl-R  fuzzy history search (replaces zsh's default reverse-i-search)
#   Ctrl-T  fuzzy file picker (insert path into command line)
#   Alt-C   fuzzy directory picker + cd
#   Tab     fuzzy completion via **<TAB> trigger
#
# `fzf --zsh` (fzf 0.48+) emits all integrations in one shot.
if command -v fzf &>/dev/null; then
  if (( $+functions[zsh-defer] )); then
    zsh-defer eval "$(fzf --zsh)"
  else
    eval "$(fzf --zsh)"
  fi
fi
