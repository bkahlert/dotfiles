export NVM_DIR="$HOME/.nvm"

# Lazy-load nvm only when actually installed; otherwise leave node/npm/npx
# alone so brew-installed binaries (or anything else on PATH) keep working.
#
# How it works: each stub replaces itself + its siblings the first time any of
# them is called. _nvm_lazy unfunctions them, sources nvm.sh (which redefines
# nvm + ensures node/npm/npx are on PATH), and the original call then dispatches
# to the real binary. This avoids the ~200ms nvm.sh load on every shell start.
if [ -s "$NVM_DIR/nvm.sh" ]; then
  _nvm_lazy() {
    unfunction nvm node npm npx 2>/dev/null
    source "$NVM_DIR/nvm.sh"
  }
  nvm()  { _nvm_lazy; nvm  "$@"; }
  node() { _nvm_lazy; node "$@"; }
  npm()  { _nvm_lazy; npm  "$@"; }
  npx()  { _nvm_lazy; npx  "$@"; }
fi
