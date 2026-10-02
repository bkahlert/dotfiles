# idp: ista IDP CLI (https://gitlab.com/ista-se/cas/devops/shared/idp-cli).
# Writes one kubeconfig per reachable AKS cluster, switches KUBECONFIG between
# them, and activates eligible Azure PIM roles.
# Install: brew tap ista/tap git@gitlab.com:ista-se/cas/devops/shared/homebrew-tap.git
#          brew trust ista/tap && brew install idp-cli
#
# The generated script wraps `idp` in a function: `idp use` runs as a child
# process, so the wrapper evals its `export KUBECONFIG=...` line into this
# shell. It also registers tab completion via compdef, which needs compinit
# (03-completions.zsh) to have run first.
command -v idp &>/dev/null || return 0
source <(idp completion zsh)
