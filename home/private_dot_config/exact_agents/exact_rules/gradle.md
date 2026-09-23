# Gradle

## One build per project directory

Never run two Gradle builds against the same project directory at once: not the IDE's Gradle daemon next to a CLI build, and not a background `./gradlew`
left running by a subagent. Concurrent builds corrupt each other's outputs in two ways that both look like something else:

- **Test results.** `./gradlew test` fails with `NoSuchFileException: .../build/test-results/test/binary/in-progress-results-*.bin` after every test
  passed. The retry passes once the other build is gone; clearing `build/test-results` only appears to help because the retry runs alone.
- **Poisoned build cache.** Lock contention can leave a compile task with empty output that Gradle stores in the local build cache. Later builds restore it
  `FROM-CACHE`, report success and ship a jar without classes; downstream modules fail with `Unresolved reference` for every symbol of that module.
  `clean` does not help, a clean build recomputes the same key. Recover with `./gradlew <task> -Dorg.gradle.caching.debug=true | grep "Build cache key"`,
  delete that entry from `~/.gradle/caches/build-cache-1/`, rebuild, and verify by counting `.class` files in the module's build output.

Run Gradle in the foreground, keep the IDE's Gradle idle during long CLI builds, and give parallel agents separate git worktrees, since each has its own
`build/`.
