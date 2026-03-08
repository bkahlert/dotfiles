# Local bins
PATH="$HOME/.local/bin:/usr/local/sbin:$PATH"

# Kubernetes tools
PATH="$HOME/.krew/bin:$HOME/.arkade/bin:$PATH"

# Deduplicate PATH
export -U PATH
