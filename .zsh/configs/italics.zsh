# Fixes the local terminfo
# - support of italics for xterm-256color
_fix_terminfo() {
  [ ! "$(find ~/.terminfo -type f -name xterm-256color 2>/dev/null)" ] || return
  local tmp_terminfo && tmp_terminfo=$(mktemp) && cat <<TERMINFO >"$tmp_terminfo" && tic -o ~/.terminfo "$tmp_terminfo" && rm "$tmp_terminfo"
xterm-256color|xterm with 256 colors and italic,
  dim=\E[2m, sitm=\E[3m, ritm=\E[23m,
  use=xterm-256color,
TERMINFO
  if [ $? ]; then
    echo "terminfo fixed: $(tput dim)half-bright$(tput sgr0) $(tput sitm)italics$(tput ritm) $(tput smso)standout$(tput rmso)"
  else
    echo "$(tput setaf 1)Failed to terminfo$(tput sgr0)" >&2
  fi
}

[ "${INTELLIJ_ENVIRONMENT_READER-}" ] || _fix_terminfo
