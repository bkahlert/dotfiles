alias kube_configs='echo "$(find ~/.kube -type f -regex '"'"'.*\.ya\{0,1\}ml'"'"' | tr '"'"'\n'"'"' ':')$HOME/.kube/config"'
export KUBECONFIG="$(kube_configs)"
alias kubectx='export KUBECONFIG="$(kube_configs)"; command kubectx'

export KUBE_EDITOR="idea --wait"

alias kc.current-cluster-url="kubectl config view --minify -o jsonpath='{.clusters[].cluster.server}'"
alias kc.current-cluster-hostname="kc.current-cluster-url | awk -F[/:] '{print \$4}'"
#alias microk8s="ssh "$(kc.current-cluster-hostname)" microk8s $*"
