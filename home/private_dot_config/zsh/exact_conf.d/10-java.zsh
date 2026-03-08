[[ $OSTYPE == darwin* ]] || return 0

if command -v brew &>/dev/null; then
  local brew_jdk="$(brew --prefix)/opt/openjdk/libexec/openjdk.jdk"
  local system_jdk='/Library/Java/JavaVirtualMachines/openjdk.jdk'

  if [ -r "$brew_jdk" ] && [ ! -e "$system_jdk" ]; then
    sudo ln -sfn "$brew_jdk" "$system_jdk" 2>/dev/null
  fi

  [ -e "$system_jdk" ] && JAVA_HOME="$system_jdk/Contents/Home"
  [ -x "$JAVA_HOME/bin/java" ] || JAVA_HOME=$(/usr/libexec/java_home 2>/dev/null)
  export JAVA_HOME
fi
