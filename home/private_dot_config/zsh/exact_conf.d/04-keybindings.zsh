# Use emacs keybindings (default, explicit)
bindkey -e

# A terminal without these keys (TERM=dumb) has empty terminfo entries, and bindkey
# rejects an empty sequence, so each terminfo binding is guarded.
#
# Up/Down: prefix-based history search (via zsh-history-substring-search plugin).
# Highlights the matched prefix and is case-insensitive.
bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down
[[ -n ${terminfo[kcuu1]} ]] && bindkey "${terminfo[kcuu1]}" history-substring-search-up
[[ -n ${terminfo[kcud1]} ]] && bindkey "${terminfo[kcud1]}" history-substring-search-down

# Home/End: beginning/end of line. Bind common sequences plus terminfo so this
# works across Ghostty, Terminal.app, iTerm2, tmux, and Linux ttys.
bindkey '^[[H'  beginning-of-line   # xterm
bindkey '^[[F'  end-of-line
bindkey '^[OH'  beginning-of-line   # application keypad mode
bindkey '^[OF'  end-of-line
bindkey '^[[1~' beginning-of-line   # legacy / linux console
bindkey '^[[4~' end-of-line
[[ -n ${terminfo[khome]} ]] && bindkey "${terminfo[khome]}" beginning-of-line
[[ -n ${terminfo[kend]} ]] && bindkey "${terminfo[kend]}"  end-of-line
