# idp: ista IDP CLI (https://gitlab.com/ista-se/cas/devops/shared/idp-cli).
# Writes one kubeconfig per reachable AKS cluster, switches KUBECONFIG between
# them, and activates eligible Azure PIM roles.
# Install: brew tap ista/tap git@gitlab.com:ista-se/cas/devops/shared/homebrew-tap.git
#          brew trust ista/tap && brew install idp-cli
#
# The generated script wraps `idp` in a function: `idp use` runs as a child
# process, so the wrapper evals its `export KUBECONFIG=...` line into this
# shell. It also registers tab completion via compdef, which needs compinit
# (08-completions.zsh) to have run first.
#
# The script is cached under $XDG_CACHE_HOME/zsh and regenerated when the idp
# binary is newer than the cache, so a shell start does not run idp.
command -v idp &>/dev/null || return 0

# Prefixed builtins only: plain mkdir/mv must stay the external commands in the user's session.
zmodload -Fm zsh/files 'b:zf_*'

_idp_cache="${XDG_CACHE_HOME:-$HOME/.cache}/zsh/idp-completion.zsh"
if [[ ! -s $_idp_cache || ${commands[idp]} -nt $_idp_cache ]]; then
  # Written aside and renamed into place, so a failed run keeps the old cache and a concurrent shell never reads half a file.
  { zf_mkdir -p "${_idp_cache:h}" &&
    idp completion zsh >| "$_idp_cache.$$" &&
    [[ -s $_idp_cache.$$ ]] &&
    zf_mv -f "$_idp_cache.$$" "$_idp_cache"; } || zf_rm -f "$_idp_cache.$$"
fi

[[ -r $_idp_cache ]] && source "$_idp_cache"
unset _idp_cache
