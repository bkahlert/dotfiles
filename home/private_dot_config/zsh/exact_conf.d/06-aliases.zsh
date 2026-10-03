# Open file types with IDE (suffix aliases — idea works cross-platform)
alias -s {kt,java,gradle,bat,txt,md,json,yaml,yml}=idea

# Git shortcuts
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

# Brew's python@X.Y kegs only link versioned names (python3, pip3) into PATH;
# bare `python`/`pip` stay in keg-only libexec. These aliases bridge that.
if command -v python3 &>/dev/null; then
  alias python=python3
fi
# Unguarded: pip3 may only reach PATH later (10-python adds the user bin dir).
alias pip=pip3

if [[ $OSTYPE == darwin* ]]; then
  # Drops .metadata_never_index in every node_modules/.git under the cwd
  # so Spotlight stops indexing them. Run e.g. in ~/Development to cover all projects at once.
  alias spotlight-skip-vendored='find . -type d \( -name "node_modules" -o -name ".git" \) -exec touch "{}/.metadata_never_index" \;'
fi
