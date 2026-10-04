# Node.js versions come from fnm (run_once_before_02-install-node). Its env puts the default on PATH, and
# --use-on-cd switches to the version a .node-version or .nvmrc asks for.
(( $+commands[fnm] )) || return 0
eval "$(fnm env --use-on-cd --shell zsh)"
