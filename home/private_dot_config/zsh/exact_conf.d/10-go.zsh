if [ -z "$GOROOT" ] && [ -d /usr/local/go ]; then
  export GOROOT=/usr/local/go
fi

if [ -d "$GOROOT" ]; then
  export GOPATH=${GOPATH:-$HOME/go}
  export PATH=$PATH:$GOROOT/bin:$GOPATH/bin
fi
