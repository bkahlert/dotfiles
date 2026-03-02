import com.github.benmanes.gradle.versions.updates.DependencyUpdatesTask
import com.github.benmanes.gradle.versions.updates.resolutionstrategy.ComponentSelectionWithCurrent

initscript {
    repositories {
        gradlePluginPortal()
    }
    dependencies {
        // Use a dynamic version to always get the latest plugin
        classpath("com.github.ben-manes:gradle-versions-plugin:+")
    }
}

allprojects {
    apply<com.github.benmanes.gradle.versions.VersionsPlugin>()

    tasks.withType<DependencyUpdatesTask>().configureEach {
        // This logic rejects updates to unstable versions (e.g., RC, M)
        // if the current version is stable.
        resolutionStrategy {
            componentSelection {
                all(Action<ComponentSelectionWithCurrent> {
                    if (isNonStable(candidate.version) && !isNonStable(currentVersion)) {
                        reject("Non-stable update rejected: ${candidate.version}")
                    }
                })
            }
        }
    }
}

fun isNonStable(version: String): Boolean {
    val stableKeyword = listOf("RELEASE", "FINAL", "GA").any { version.uppercase().contains(it) }
    val stableRegex = "^[0-9,.v-]+(-r)?$".toRegex()
    val isStable = stableKeyword || stableRegex.matches(version)
    return isStable.not()
}
