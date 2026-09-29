# IDE Inspections

While the JetBrains MCP tools (`mcp__idea__*`) are connected, a change is done only once every error and warning on the files it touched is fixed or
explained — whatever their type: Markdown, YAML and shell scripts are inspected like code.

## Checking

Call `mcp__idea__get_file_problems` for each changed file with `errorsOnly: false` — the default reports errors only, so a file full of warnings comes back
as an empty list. Don't use `mcp__ide__getDiagnostics` for this: it answers only for the file active in the editor and times out for every other file.

Fix each error and warning, or name it in the reply with the reason it stays — a false positive, or a pre-existing finding whose fix would widen the change.
On prose, apply a grammar or style suggestion only when the rewording reads as well as the original. Skip the check only for trivial edits (typo, comment
tweak, formatting-only), and if a call fails, say so rather than skipping silently.

## Gradle JVM

When IntelliJ reports "Incompatible Gradle JVM", or Gradle refuses to run on the JDK behind `JAVA_HOME`, pin the daemon JVM in the project instead of
changing the IDE's project SDK: a handwritten `gradle/gradle-daemon-jvm.properties` containing only `toolchainVersion=<major>` makes Gradle 8.8+ pick a
matching installed JDK, and IntelliJ 2025.1+ follows it for its Gradle JVM (needs Gradle 8.9+, so bump older wrappers first). `./gradlew updateDaemonJvm`
generates the same file but refuses without a toolchain download repository; the minimal file works through JDK auto-detection.
