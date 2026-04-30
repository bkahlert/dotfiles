[[ -d $HOME/.krew/bin   ]] && PATH="$HOME/.krew/bin:$PATH"
[[ -d $HOME/.arkade/bin ]] && PATH="$HOME/.arkade/bin:$PATH"
export -U PATH

export KUBE_EDITOR="ideaw --wait"
