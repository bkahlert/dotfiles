export NVM_DIR="$HOME/.nvm"

# Resolve nvm.sh from either install method:
#   - Official curl installer drops it at $NVM_DIR/nvm.sh
#   - Homebrew puts it at $(brew --prefix)/opt/nvm/nvm.sh and expects
#     $NVM_DIR to stay at ~/.nvm (pointing it at the cellar would wipe
#     installed Node versions on every brew upgrade — see brew's caveat).
_nvm_sh=
if [ -s "$NVM_DIR/nvm.sh" ]; then
  _nvm_sh="$NVM_DIR/nvm.sh"
elif command -v brew &>/dev/null && [ -s "$(brew --prefix)/opt/nvm/nvm.sh" ]; then
  _nvm_sh="$(brew --prefix)/opt/nvm/nvm.sh"
fi

# Lazy-load nvm only when actually installed; otherwise leave node/npm/npx
# alone so brew-installed binaries (or anything else on PATH) keep working.
#
# How it works: each stub replaces itself + its siblings the first time any of
# them is called. _nvm_lazy unfunctions them, sources nvm.sh (which redefines
# nvm + ensures node/npm/npx are on PATH), and the original call then dispatches
# to the real binary. This avoids the ~200ms nvm.sh load on every shell start.
if [ -n "$_nvm_sh" ]; then
  [ -d "$NVM_DIR" ] || mkdir -p "$NVM_DIR"
  _nvm_lazy() {
    unfunction nvm node npm npx 2>/dev/null
    source "$_nvm_sh"
  }
  nvm()  { _nvm_lazy; nvm  "$@"; }
  node() { _nvm_lazy; node "$@"; }
  npm()  { _nvm_lazy; npm  "$@"; }
  npx()  { _nvm_lazy; npx  "$@"; }
fi
