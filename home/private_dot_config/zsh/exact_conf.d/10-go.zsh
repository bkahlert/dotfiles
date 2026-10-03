# Add $GOPATH/bin (where `go install` puts binaries) to PATH.
if command -v go &>/dev/null; then
  export GOPATH=${GOPATH:-$HOME/go}
  PATH="$PATH:$GOPATH/bin"
  export -U PATH
fi
