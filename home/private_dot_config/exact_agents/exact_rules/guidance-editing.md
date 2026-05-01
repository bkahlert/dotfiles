# Editing AI guidance files

## Keeping AI guidance files accurate

When writing or updating `AGENTS.md`, `CLAUDE.md`, or equivalent guidance files:

- **Prefer intent over enumeration.** Describe *why* a rule exists rather than listing every file or pattern it covers. A stated principle survives refactoring;
  a file list silently rots.

- **Anchor exceptions to their assumptions.** If you must list exceptions (e.g., "these files must stay as templates"), state the condition that makes each
  exception necessary — so it's clear when that condition no longer holds and the exception should be removed.

- **Review guidance after making code changes.** After any significant refactor, scan the guidance file for descriptions that no longer match the codebase.
  Stale guidance is worse than no guidance — it actively misleads future agents.

## Codebase Invariants

When a session introduces or discovers a cross-cutting constraint that all code must comply with (e.g., adopting a code style, renaming convention,
architectural boundary), update the project's AI guidance file (`AGENTS.md`, `CLAUDE.md`, or equivalent) before the session ends.

Each invariant entry should include:

- The rule itself (actionable and specific)
- Why it was introduced (one sentence)
- A before/after example if the rule isn't self-evident
