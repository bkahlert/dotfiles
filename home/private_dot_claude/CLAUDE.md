@~/.config/agents/AGENTS.md

# Skills

## Superpowers Framework
- You MUST follow the `superpowers:using-superpowers` protocol for every request.
- If any task has a matching skill (e.g., `superpowers:brainstorming`, `superpowers:systematic-debugging`), you must invoke it via the Skill tool before proceeding.
- If multiple skills apply, ask for clarification on which workflow to prioritize.
- For implementation please default to `Subagent-Driven`

If multiple skills can be used, ask which one to use.


# Context awareness and multi-window workflows

Your context window will be automatically compacted as it approaches its limit, allowing you to continue working indefinitely from where you left off. Therefore, do not stop tasks early due to token budget concerns. As you approach your token budget limit, save your current progress and state to memory before the context window refreshes. Always be as persistent and autonomous as possible and complete tasks fully, even if the end of your budget is approaching. Never artificially stop any task early regardless of the context remaining.


# Subagent orchestration

Use subagents when tasks can run in parallel, require isolated context, or involve independent workstreams that don't need to share state. For simple tasks, sequential operations, single-file edits, or tasks where you need to maintain context across steps, work directly rather than delegating.
