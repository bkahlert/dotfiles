# No 'export LANG=C.UTF-8' as that would require C locales
export LC_CTYPE=UTF-8 # UTF-8 for string functions

# Enable word splitting as in `sh`
setopt shwordsplit

# No need to escape globbing characters
unsetopt nomatch
