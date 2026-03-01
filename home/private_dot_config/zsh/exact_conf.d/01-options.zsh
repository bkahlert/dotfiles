# Locale
export LANG=en_US.UTF-8

# Colors
autoload -U colors && colors
export CLICOLOR=1

# Word splitting compatible with sh
setopt shwordsplit

# Don't error on unmatched globs
unsetopt nomatch
