# IDE Inspections

For routine or substantial changes to source files, call `mcp__ide__getDiagnostics` on the changed files and resolve reported errors and warnings before considering the task done. This surfaces IntelliJ/WebStorm inspections (e.g. SonarJS rules, deprecated API usage, type errors) that are not caught by the compiler or test suite alone.

Skip for trivial edits (typos, comment tweaks, formatting-only changes). If the MCP tool is unavailable when needed, note this explicitly rather than skipping silently.
