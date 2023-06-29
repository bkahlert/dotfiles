export NVM_DIR="$HOME/.nvm"
[ -e "$NVM_DIR" ] || mkdir "$NVM_DIR"
[ -s "$(brew --prefix)/opt/nvm/nvm.sh" ] && \. "$(brew --prefix)/opt/nvm/nvm.sh" # This loads nvm
[ "${INTELLIJ_ENVIRONMENT_READER-}" ] || {
  [ -s "$(brew --prefix)/opt/nvm/etc/bash_completion.d/nvm" ] && \. "$(brew --prefix)/opt/nvm/etc/bash_completion.d/nvm" # This loads nvm bash_completion
}
