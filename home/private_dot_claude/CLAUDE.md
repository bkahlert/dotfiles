@~/.config/agents/AGENTS.md

# Skills

Skills are tools — invoke when one strongly matches the task, not by default. Match the ceremony to the stakes:

- **Conversational / read-only** (Q&A, explaining code, reading docs): no skill ceremony — just answer.
- **Trivial edits** (typo, single-line, well-scoped change): no mandatory skill. Invoke one only if it directly guides the change (e.g. `superpowers:systematic-debugging` for a real bug).
- **Routine implementation** (small features, ops/config changes, bounded refactors): use `grill-me` to pressure-test the design when the approach isn't obvious; otherwise plan in-context and proceed.
- **Substantial work** (multi-file features, architectural decisions): full superpowers flow — grill (or brainstorm if grill exposes architectural ambiguity), plan, implement, review.

Process skills (`grill-me`, `superpowers:systematic-debugging`) take precedence over implementation skills (`frontend-design`, `mcp-builder`) when both could apply. Ask which skill to use only when the choice is genuinely load-bearing.

Project-level `AGENTS.md` / `CLAUDE.md` may strengthen these defaults; honor them when they do.


# Context awareness

Your context window auto-compacts near its limit, so don't stop early due to token budget concerns. As the budget tightens, save progress and state to memory before refresh. Stay persistent and autonomous; complete tasks fully.


# Subagent orchestration

Use subagents when tasks can run in parallel, require isolated context, or involve independent workstreams that don't need to share state. For simple tasks, sequential operations, single-file edits, or tasks where you need to maintain context across steps, work directly rather than delegating.
