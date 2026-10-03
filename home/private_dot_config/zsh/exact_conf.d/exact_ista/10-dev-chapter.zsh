# Manages dev-chapter repository and adds tools to PATH
# Automatically clones repo if missing and keeps it updated (weekly)

# Guards the readonly declarations below against re-sourcing (e.g. `sc`),
# which would otherwise fail with "read-only variable".
[[ -n "$_DC_LOADED" ]] && return 0
typeset -g _DC_LOADED=1

readonly DEV_CHAPTER_REPO="$HOME/Development/istaexpress/dev-chapter"
readonly DEV_CHAPTER_TOOLS="$DEV_CHAPTER_REPO/tools"
readonly _DC_GIT_REMOTE="git@gitlab.com:ista-se/cas/ista-express/shared/dev-chapter-time/dev-chapter.git"
readonly _DC_CACHE_DIR="$HOME/.cache/dev-chapter"
readonly _DC_LAST_ATTEMPT_FILE="$_DC_CACHE_DIR/last_attempt"
readonly _DC_PULL_INTERVAL=$((7 * 24 * 60 * 60))

# Hard bounds for every network call below. This file runs on the interactive
# startup path, so a git operation that blocks blocks the terminal itself:
#   BatchMode        never prompt — a locked agent or unknown host key fails
#                    instead of silently waiting on the tty (which reads as a hang)
#   ConnectTimeout   cap the TCP connect to an unreachable host
#   ServerAlive*     cap a connection that stalls mid-transfer (~10 s)
readonly _DC_GIT_SSH='ssh -o BatchMode=yes -o ConnectTimeout=5 -o ServerAliveInterval=5 -o ServerAliveCountMax=2'

# Status lines in the style of the bin/ scripts: a glyph, coloured when the stream is a terminal.
# Warnings and errors go to stderr, so a clean start stays silent on both streams.
_dc_say() { # <fd> <tput colour> <glyph> <message>
  local on='' off=''
  [[ -t $1 ]] && { on=$(tput setaf $2); off=$(tput sgr0); }
  printf '%s%s%s %s\n' "$on" "$3" "$off" "$4" >&$1
}
_dc_ok()   { _dc_say 1 2 ✔ "$1"; }
_dc_warn() { _dc_say 2 3 '!' "$1"; }
_dc_err()  { _dc_say 2 1 ✘ "$1"; }

# Early exit if tools already in PATH
if [[ ":$PATH:" == *":$DEV_CHAPTER_TOOLS:"* ]]; then
  return 0
fi

# Clone repository if it doesn't exist
if [[ ! -d "$DEV_CHAPTER_REPO" ]]; then
  # The clone authenticates through the agent; without one a fresh machine stays quiet.
  [[ -n "$SSH_AUTH_SOCK" ]] || return 0
  echo "Cloning dev-chapter repository to $DEV_CHAPTER_REPO..."
  mkdir -p "$(dirname "$DEV_CHAPTER_REPO")"

  local _dc_out
  if _dc_out=$(GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="$_DC_GIT_SSH" \
    git clone "$_DC_GIT_REMOTE" "$DEV_CHAPTER_REPO" 2>&1); then
    _dc_ok "Repository cloned successfully"
    mkdir -p "$_DC_CACHE_DIR"
    date +%s > "$_DC_LAST_ATTEMPT_FILE"
  else
    # Surface the whole reason — a silent failure here is indistinguishable
    # from a hang, and git puts the actual cause on its *first* line.
    _dc_err "Failed to clone dev-chapter repository:"
    _dc_err "$_dc_out"
    return 1
  fi
fi

# Update repository if it's been more than a week
if [[ -d "$DEV_CHAPTER_REPO/.git" && -n "$SSH_AUTH_SOCK" ]]; then
  local should_pull=false

  if [[ ! -f "$_DC_LAST_ATTEMPT_FILE" ]]; then
    should_pull=true
  else
    local last_attempt=$(cat "$_DC_LAST_ATTEMPT_FILE")
    local now=$(date +%s)
    local age=$((now - last_attempt))

    if [[ $age -gt $_DC_PULL_INTERVAL ]]; then
      should_pull=true
    fi
  fi

  if [[ "$should_pull" == "true" ]]; then
    # Stamp before pulling, not after. This is what stops every new terminal
    # from retrying an unreachable remote and paying the full timeout again.
    mkdir -p "$_DC_CACHE_DIR"
    date +%s > "$_DC_LAST_ATTEMPT_FILE"

    local _dc_out
    if ! _dc_out=$(GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="$_DC_GIT_SSH" \
      git -C "$DEV_CHAPTER_REPO" pull --autostash 2>&1); then
      _dc_warn "Failed to update dev-chapter repository:"
      _dc_warn "$_dc_out"
    fi
  fi
fi

# Add tools to PATH if directory exists
if [[ -d "$DEV_CHAPTER_TOOLS" ]]; then
  export PATH="$DEV_CHAPTER_TOOLS:$PATH"
else
  _dc_warn "dev-chapter tools directory not found at $DEV_CHAPTER_TOOLS"
fi
