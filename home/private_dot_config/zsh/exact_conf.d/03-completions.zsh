autoload -Uz compinit

# Glob qualifier (#qN.mh+24): regular file, modified >24h ago, no error if missing.
# Match (old/missing dump) → full compinit (rescan $fpath + security check).
# No match (fresh dump)    → compinit -C (fast path, skip security check).
if [[ -n $ZDOTDIR/.zcompdump(#qN.mh+24) ]]; then
  compinit
else
  compinit -C
fi
