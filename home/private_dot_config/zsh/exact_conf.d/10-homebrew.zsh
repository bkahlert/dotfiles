# Disable analytics
export HOMEBREW_NO_ANALYTICS=1

# Update once a week
export HOMEBREW_AUTO_UPDATE_SECS=604800

# Silence the recurring "Some casks with auto_updates true may still require
# --greedy..." footer printed after every `brew upgrade`. Not interested in
# greedy cask upgrades, so the hint is just noise.
export HOMEBREW_NO_ENV_HINTS=1
