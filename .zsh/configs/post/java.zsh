# Link brew-installed JDK
if [ -r "$(brew --prefix)/opt/openjdk/libexec/openjdk.jdk" ] && [ ! -e '/Library/Java/JavaVirtualMachines/openjdk.jdk' ]; then
  ln -sfn "$(brew --prefix)/opt/openjdk/libexec/openjdk.jdk" '/Library/Java/JavaVirtualMachines/openjdk.jdk'
fi

# Use brew-installed JDK as JAVA_HOME by default
[ -e '/Library/Java/JavaVirtualMachines/openjdk.jdk' ] && JAVA_HOME='/Library/Java/JavaVirtualMachines/openjdk.jdk'

# Use OS default if no brew-installed JDK is available
[ -x "$JAVA_HOME/bin/java" ] || JAVA_HOME=$(/usr/libexec/java_home)

export JAVA_HOME
