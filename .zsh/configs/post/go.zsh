if [ "$GOROOT" ]; then
  # if GOROOT is set, verify it points to a valid directory
  [ -d "$GOROOT" ] || echo "WARNING: GOROOT is set to a non-existent directory: $GOROOT" >&2
else
  # otherwise, try to find a valid GOROOT directory
  if [ -d /usr/local/go ]; then
      export GOROOT=/usr/local/go
  fi
fi

if [ -d "$GOROOT" ]; then
  # if GOROOT is valid, set GOPATH and extend PATH
  export GOPATH=${GOPATH:-$HOME/go}
  export PATH=$PATH:$GOROOT/bin:$GOPATH/bin
fi
