autoload -Uz compinit

# Homebrew's completions live in its own site-functions dir, put on $fpath by
# `brew shellenv` — which .zprofile runs for login shells only. Add it here too,
# so non-login interactive shells (IDE terminals, containers, zsh started from a
# script) complete the same commands. Must happen before compinit.
for _brew_prefix in $HOMEBREW_PREFIX /opt/homebrew /home/linuxbrew/.linuxbrew; do
  [[ -n $_brew_prefix && -d $_brew_prefix/share/zsh/site-functions ]] || continue
  fpath=($_brew_prefix/share/zsh/site-functions $fpath)
  break
done
unset _brew_prefix

# compinit -C reuses the dump as-is: no $fpath rescan, no security check. That
# is the common case; rebuild only when the dump is missing, older than 24h, or
# older than a hand-written completion in completions/ (without that last test,
# a new completion would stay invisible until the dump ages out).
#
# Both tests glob into arrays first: zsh does not expand filename patterns
# inside [[ ]], where a glob would just be a non-empty literal string. Plain
# (N.mh-24) qualifiers, not (#qN.mh-24), which would need EXTENDED_GLOB.
_zcompdump=$ZDOTDIR/.zcompdump
_dump_fresh=($ZDOTDIR/.zcompdump(N.mh-24))
_newest_completion=($ZDOTDIR/completions/*(N.om[1]))

if (( $#_dump_fresh )) && [[ ! $_newest_completion -nt $_zcompdump ]]; then
  compinit -C
else
  compinit
  # compinit rewrites the dump only when its contents change, so editing a
  # completion it already knows leaves the dump older than that file — and
  # every later shell would rebuild again. Stamp it to end the cycle.
  [[ -s $_zcompdump ]] && touch $_zcompdump
fi

unset _zcompdump _dump_fresh _newest_completion

# Make the completion list a menu that arrow keys walk through. Without this
# the matches are only printed, and Up/Down stay bound to history search
# (04-keybindings.zsh) because no menuselect keymap is active. zsh/complist
# provides that keymap; press TAB a second time to enter the menu.
zmodload zsh/complist
zstyle ':completion:*' menu select
