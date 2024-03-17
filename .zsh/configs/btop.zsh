top() {
  if command -v btop >/dev/null || brew install btop >/dev/null; then
    btop "$@"
  else
    command top "$@"
  fi
}
