# nvm comes from run_once_before_02-install-nvm, which leaves an nvm.sh already there alone: on machines set up
# before it, Homebrew's symlink, so uninstalling Homebrew's nvm needs that script rerun. node, npm and npx need no
# nvm.sh: .zshenv puts the default version's bin on PATH for every shell. Only nvm itself does, and its ~200 ms
# load waits for the first call.
export NVM_DIR="$HOME/.nvm"

# .zshenv put the default version's bin on PATH, but the login files after it (path_helper, brew shellenv) put
# their directories ahead, and with them any other node. nvm's goes back to the front.
path=(${(M)path:#$NVM_DIR/versions/node/*} ${path:#$NVM_DIR/versions/node/*})

[[ -s $NVM_DIR/nvm.sh ]] || return 0

nvm() {
  unfunction nvm
  source "$NVM_DIR/nvm.sh"
  nvm "$@"
}
