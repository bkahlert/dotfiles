# Open file types with IDE (macOS zsh suffix aliases)
if [[ $OSTYPE == darwin* ]]; then
  alias -s {kt,java,gradle,bat,txt,md,json,yaml,yml}=idea
fi

# Git shortcuts
alias alias-print='declare -f'
alias git+x='git update-index --chmod=+x'

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

if [[ $OSTYPE == darwin* ]]; then
  alias ip="dig +short myip.opendns.com @resolver1.opendns.com"
  alias localip="ipconfig getifaddr en0"
  alias browse="open -a /Applications/Google\ Chrome.app"
  alias serve="npx http-server -c-1 -p 80"
  alias live="npx live-server --port=80 --no-browser"
  alias ft="grep -rn -H -C 5 --exclude-dir={.git,.svn,CVS} --devices=skip -e"
  alias fix-spotlight='find . -type d \( -name "node_modules" -o -name ".git" \) -exec touch "{}/.metadata_never_index" \;'
fi
