# IntelliJ opens on the Mac's own screen, so a Linux shell or an SSH session gets a terminal editor.
if [[ $OSTYPE == darwin* && -z $SSH_CONNECTION ]]; then
  export VISUAL=idea-wait
else
  export VISUAL=nano
fi
export EDITOR=$VISUAL
