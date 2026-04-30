# Open file types with IDE (suffix aliases — ideaw works cross-platform)
alias -s {kt,java,gradle,bat,txt,md,json,yaml,yml}=ideaw

# Git shortcuts
alias alias-print='declare -f'
alias git+x='git update-index --chmod=+x'

# ls sorted by ctime: lsl = newest first, lsr = oldest first
alias lsl='ls -1lAFhct'
alias lsr='ls -1lAFhcrt'

# bat as cat (auto-detects dark/light mode on macOS)
if command -v bat &>/dev/null; then
  if [[ $OSTYPE == darwin* ]]; then
    alias cat="bat --theme=\$(defaults read -globalDomain AppleInterfaceStyle &> /dev/null && echo default || echo GitHub)"
  else
    alias cat="bat"
  fi
fi

# tldr aliases
if command -v tldr &>/dev/null; then
  alias samples="tldr"
  alias examples="tldr"
fi

# Picks the first bindable port from 80, 8080, or any free port.
# Bind-test uses python so EACCES (port 80 without sudo) is caught too.
_pick_port() {
  python3 -c '
import socket
for p in [80, 8080, 0]:
    s = socket.socket()
    try:
        s.bind(("0.0.0.0", p))
        print(s.getsockname()[1])
        s.close()
        break
    except OSError:
        pass
'
}

# Serve current directory (static).
serve() {
  local port; port=$(_pick_port) || { printf "serve: no port available\n" >&2; return 1; }
  printf "serve: http://localhost:%s\n" "$port" >&2
  npx http-server -c-1 -p "$port" "$@"
}

# Serve current directory with live-reload.
serve-live() {
  local port; port=$(_pick_port) || { printf "serve-live: no port available\n" >&2; return 1; }
  printf "serve-live: http://localhost:%s\n" "$port" >&2
  npx live-server --port="$port" --no-browser "$@"
}

if [[ $OSTYPE == darwin* ]]; then
  # Recursive full-text search with 5 lines of context, skipping VCS dirs.
  alias ft="grep -rn -H -C 5 --exclude-dir={.git,.svn,CVS} --devices=skip -e"
  alias full-text-search="ft"
  # Drops .metadata_never_index in every node_modules/.git under the cwd
  # so Spotlight stops indexing them. Run e.g. in ~/Development to cover all projects at once.
  alias spotlight-skip-vendored='find . -type d \( -name "node_modules" -o -name ".git" \) -exec touch "{}/.metadata_never_index" \;'
fi
