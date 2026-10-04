[[ $OSTYPE == darwin* ]] || return 0

# A JAVA_HOME that already points at a working JDK wins (direnv, a parent shell,
# a manual override). A stale one is dropped so it cannot block the fallback below.
[[ -n ${JAVA_HOME-} && -x $JAVA_HOME/bin/java ]] && return 0
unset JAVA_HOME

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
