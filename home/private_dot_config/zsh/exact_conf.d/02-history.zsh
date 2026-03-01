HISTFILE="${XDG_STATE_HOME:-$HOME/.local/state}/zsh/history"
HISTSIZE=10000
SAVEHIST=10000

# Create history directory if needed
[[ -d ${HISTFILE:h} ]] || mkdir -p ${HISTFILE:h}

setopt hist_ignore_all_dups  # Remove older duplicate entries
setopt hist_reduce_blanks    # Remove superfluous blanks
setopt inc_append_history    # Write immediately, not on exit
setopt share_history         # Share history between sessions
