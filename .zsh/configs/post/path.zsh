# Ensure dotfiles bin directory is loaded first
PATH="$HOME/.local/bin:$HOME/bin:/usr/local/sbin:$PATH"
PATH="$HOME/Library/Python/3.11/bin:$PATH"
PATH="$HOME/.krew/bin:$HOME/.arkade/bin:$PATH"

# Try loading ASDF from the regular home dir location
#if [ -f "$HOME/.asdf/asdf.sh" ]; then
#  . "$HOME/.asdf/asdf.sh"
#elif which brew >/dev/null; then
#  . "$(brew --prefix asdf)/libexec/asdf.sh"
#fi

export -U PATH
