declare -r brew_jdk="$(brew --prefix)/opt/openjdk/libexec/openjdk.jdk"
declare -r system_jdk='/Library/Java/JavaVirtualMachines/openjdk.jdk'

# Link brew-installed JDK to system JDK
if [ -r "$brew_jdk" ] && [ ! -e "$system_jdk" ]; then
  ln -sfn "$brew_jdk" "$system_jdk"
fi

# Use system JDK as JAVA_HOME by default
[ -e "$system_jdk" ] && JAVA_HOME="$system_jdk/Contents/Home"

# Fall back to OS default
[ -x "$JAVA_HOME/bin/java" ] || JAVA_HOME=$(/usr/libexec/java_home)

export JAVA_HOME
