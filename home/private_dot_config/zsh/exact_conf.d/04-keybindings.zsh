# Use emacs keybindings (default, explicit)
bindkey -e

# Up/Down: prefix-based history search.
# Type the start of a command, then Up/Down cycles through past entries that
# begin with that prefix. In multi-line buffers the cursor moves between lines
# first and only searches history when Up is pressed on the first line (Down
# on the last line) — that's the "or-beginning-search" half.
autoload -Uz up-line-or-beginning-search down-line-or-beginning-search
zle -N up-line-or-beginning-search
zle -N down-line-or-beginning-search

# Bind both raw escape sequences and terminfo entries so this works across
# terminals (Ghostty, iTerm2, tmux, ssh into Linux, ...).
bindkey '^[[A' up-line-or-beginning-search
bindkey '^[[B' down-line-or-beginning-search
bindkey "${terminfo[kcuu1]}" up-line-or-beginning-search
bindkey "${terminfo[kcud1]}" down-line-or-beginning-search

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
