# Smart Gradle wrapper: prefers ./gradlew over system gradle
gw() {
  local gradle_cmd

  if [[ -x "./gradlew" ]]; then
    gradle_cmd="./gradlew"
  elif command -v gradle >/dev/null 2>&1; then
    gradle_cmd="gradle"
  else
    echo "Error: Could not find './gradlew' or a system-wide 'gradle' installation." >&2
    return 1
  fi

  command "$gradle_cmd" "$@"
}

# Runs Gradle dependency updates, rejecting non-stable versions
gw-updates() {
  local script_path="${(%):-%x}"
  local script_dir="${script_path:h}"
  local init_script="$script_dir/gradle-versions-plugin.init.gradle.kts"

  gw dependencyUpdates --init-script "$init_script" "$@"
}
