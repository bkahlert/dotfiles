# Locale
export LANG=en_US.UTF-8
# macOS terminals inject LC_CTYPE=UTF-8, a pseudo-locale no Linux host has, and ssh forwards LC_*. LANG covers UTF-8.
unset LC_CTYPE

# Colors
autoload -U colors && colors
export CLICOLOR=1

# Word splitting compatible with sh
setopt shwordsplit

# Don't error on unmatched globs
unsetopt nomatch
