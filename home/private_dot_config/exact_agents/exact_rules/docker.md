# Docker / container builds

## HEALTHCHECK

Every authored `Dockerfile` **must** declare a `HEALTHCHECK` instruction.

Why: orchestrators (Docker, Compose, Swarm, Kubernetes via `livenessProbe`-equivalent tooling, CI smoke tests) rely on it to distinguish *running* from *ready*. Without it, a container that has crashed internally but kept its PID 1 alive will be treated as healthy and will silently absorb traffic.

The check should exercise the actual service contract — hit the HTTP endpoint, run the CLI's `--version`, query the DB socket — not just `true` or a presence check on a PID. If the upstream base image already declares an appropriate `HEALTHCHECK`, you may inherit it; state that explicitly in a comment so it isn't mistaken for an oversight.

If a image genuinely has no meaningful health signal (e.g. a one-shot job, a `scratch`-based static binary used only as a build artifact), write `HEALTHCHECK NONE` with a one-line comment explaining why. The directive is then present and intentional rather than forgotten.
