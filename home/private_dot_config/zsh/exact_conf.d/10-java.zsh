[[ $OSTYPE == darwin* ]] || return 0

# Prefer Homebrew's openjdk; fall back to /usr/libexec/java_home.
if command -v brew &>/dev/null; then
  brew_jdk="$(brew --prefix)/opt/openjdk/libexec/openjdk.jdk"
  if [ -x "$brew_jdk/Contents/Home/bin/java" ]; then
    export JAVA_HOME="$brew_jdk/Contents/Home"
  fi
  unset brew_jdk
fi

if [ -z "${JAVA_HOME-}" ]; then
  JAVA_HOME=$(/usr/libexec/java_home 2>/dev/null) && export JAVA_HOME
fi
