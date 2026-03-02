# Homebrew Ruby (macOS)
if [[ -d /opt/homebrew/opt/ruby ]]; then
  export PATH="/opt/homebrew/lib/ruby/gems/3.3.0/bin:$PATH"
  export PATH="/opt/homebrew/opt/ruby/bin:$PATH"
  export LDFLAGS="-L/opt/homebrew/opt/ruby/lib"
  export CPPFLAGS="-I/opt/homebrew/opt/ruby/include"
fi
