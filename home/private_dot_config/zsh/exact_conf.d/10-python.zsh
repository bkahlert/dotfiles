# Python user install (macOS) — highest installed version
[[ $OSTYPE == darwin* ]] || return 0

local -a python_bins=( "$HOME/Library/Python"/*/bin(Nn/) )
(( ${#python_bins} > 0 )) && PATH="${python_bins[-1]}:$PATH"
export -U PATH
