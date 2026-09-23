# IDE Inspections

For routine or substantial changes to source files, call `mcp__ide__getDiagnostics` on the changed files and resolve reported errors and warnings before considering the task done. This surfaces IntelliJ/WebStorm inspections (e.g. SonarJS rules, deprecated API usage, type errors) that are not caught by the compiler or test suite alone.

Skip for trivial edits (typos, comment tweaks, formatting-only changes). If the MCP tool is unavailable when needed, note this explicitly rather than skipping silently.

## Gradle JVM

When IntelliJ reports "Incompatible Gradle JVM", or Gradle refuses to run on the JDK behind `JAVA_HOME`, pin the daemon JVM in the project instead of
changing the IDE's project SDK: a hand-written `gradle/gradle-daemon-jvm.properties` containing only `toolchainVersion=<major>` makes Gradle 8.8+ pick a
matching installed JDK, and IntelliJ 2025.1+ follows it for its Gradle JVM (needs Gradle 8.9+, so bump older wrappers first). `./gradlew updateDaemonJvm`
generates the same file but refuses without a toolchain download repository; the minimal file works through JDK auto-detection.
