autoload -Uz compinit

# Only regenerate .zcompdump once per day
if [[ -n $ZDOTDIR/.zcompdump(#qN.mh+24) ]]; then
  compinit
else
  compinit -C
fi
