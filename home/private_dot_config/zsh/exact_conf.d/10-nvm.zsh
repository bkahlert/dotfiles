# nvm comes from run_once_before_02-install-nvm. node, npm and npx need no nvm.sh: .zshenv puts the default
# version's bin on PATH for every shell. Only nvm itself does, and its ~200 ms load waits for the first call.
export NVM_DIR="$HOME/.nvm"

[[ -s $NVM_DIR/nvm.sh ]] || return 0

nvm() {
  unfunction nvm
  source "$NVM_DIR/nvm.sh"
  nvm "$@"
}
