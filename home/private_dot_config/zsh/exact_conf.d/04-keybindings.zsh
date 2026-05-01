# Use emacs keybindings (default, explicit)
bindkey -e

# Up/Down: prefix-based history search (via zsh-history-substring-search plugin).
# Highlights the matched prefix and is case-insensitive.
bindkey '^[[A' history-substring-search-up
bindkey '^[[B' history-substring-search-down
bindkey "${terminfo[kcuu1]}" history-substring-search-up
bindkey "${terminfo[kcud1]}" history-substring-search-down

# Home/End: beginning/end of line. Bind common sequences plus terminfo so this
# works across Ghostty, Terminal.app, iTerm2, tmux, and Linux ttys.
bindkey '^[[H'  beginning-of-line   # xterm
bindkey '^[[F'  end-of-line
bindkey '^[OH'  beginning-of-line   # application keypad mode
bindkey '^[OF'  end-of-line
bindkey '^[[1~' beginning-of-line   # legacy / linux console
bindkey '^[[4~' end-of-line
bindkey "${terminfo[khome]}" beginning-of-line
bindkey "${terminfo[kend]}"  end-of-line
