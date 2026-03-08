# Local bins
PATH="$HOME/.local/bin:/usr/local/sbin:$PATH"

# JetBrains Toolbox (macOS)
[[ -d "$HOME/Library/Application Support/JetBrains/Toolbox/scripts" ]] \
  && PATH="$PATH:$HOME/Library/Application Support/JetBrains/Toolbox/scripts"

# Python user install (macOS)
[[ -d "$HOME/Library/Python/3.11/bin" ]] \
  && PATH="$HOME/Library/Python/3.11/bin:$PATH"

# Kubernetes tools
PATH="$HOME/.krew/bin:$HOME/.arkade/bin:$PATH"

# Deduplicate PATH
export -U PATH
