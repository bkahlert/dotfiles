# Dependencies

## Source location of dependencies

- When you need to know the actual source of a build dependency, chances are they are located in a sibling directory as I tend to keep projects / repos
  belonging together in the same parent directory.

- Reason about projects tightly coupled together (e.g. projects `technician-app-service` and `technician-app-web` are tightly coupled, with `-service` being a
  backend microservice and `-web` being its web (UI))

## Dependency Management

Before proposing any new dependency, BOM, or platform import, verify what is already provided. Many build systems include BOMs or platforms that transitively manage versions for a wide range of artifacts — adding a redundant one silently duplicates or conflicts with existing version governance.

- **Gradle:** `./gradlew dependencyInsight --dependency <artifact> --configuration compileClasspath` and inspect existing BOM POMs in the Gradle cache.
- **Maven:** `mvn dependency:tree` or check the effective POM (`mvn help:effective-pom`).

Only add a new BOM or version constraint if coverage is genuinely missing after this check.
