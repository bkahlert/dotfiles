# Lazy glab CLI: shadows `glab` with a function that brew-installs on first use.
glab() {
  if ! command -v glab &>/dev/null; then
    if command -v brew &>/dev/null; then
      echo "glab not found — installing via Homebrew..."
      brew install glab || return 1
    else
      echo "glab not found and Homebrew is not available. Please install glab manually."
      return 1
    fi
  fi
  command glab "$@"
}
