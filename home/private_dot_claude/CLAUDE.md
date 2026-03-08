# Skills

## Superpowers Framework
- You MUST follow the `superpowers:using-superpowers` protocol for every request.
- If any task has a matching skill (e.g., `superpowers:brainstorming`, `superpowers:systematic-debugging`), you must invoke it via the Skill tool before proceeding.
- If multiple skills apply, ask for clarification on which workflow to prioritize.
- For implementation please default to `Subagent-Driven`

If multiple skills can be used, ask which one to use.


# Git

- Do never commit on the main/master branch.
- I use IntelliJ which has no support for `git worktree`.
  - Therefor don't use `git worktree`


# Source location of dependencies

- When you need to know the actual source of a build dependency, chances are they are located in a sibling directory as I tend to keep projects / repos belonging together in the same parent directory. 

- Reason about projects tightly coupled together (e.g. projects `technician-app-service` and `technician-app-web` are tightly coupled, with `-service` being a backend micro service and `-web` being its web (UI))


# Markdown

- When you reference a file, do so with a proper Markdown link
  - `[filename](path)`, or
  - `[path](path)`, or
  - `[title of the references file](path)`


# SVG

Whenever possible "relative" colors like `currentColor` (e.g. `fill="currentColor"`).


# Test Naming & Structure

## 1. Specificity via Nesting
Achieve test specificity through hierarchical nesting rather than long BDD descriptions. Each level should add a single layer of context.
- **Concise Strings**: Keep individual descriptions brief.
- **No Redundancy**: Do not repeat words from a parent block in a child block.
- **The "Full Path" Rule**: The test's intent should be clear when reading the nested breadcrumbs (e.g., Resource > Name > On missing technician > should be null).

## 2. Phrasing & Conditional Logic
- **Favor "on" over "if"**: Use "on [state/event]" for triggers (e.g., `on missing foo` instead of `if foo is missing`).
- **Time Dimension**: Only use "when" or "if" if the condition implies a temporal sequence or complex logic that "on" cannot represent.
- **Direct Outcomes**: The final leaf node should focus strictly on the result/assertion (e.g., `should be null`, `it returns 200`).

## 3. Framework Adaptability
Adapt the syntax to the project's specific framework while maintaining the hierarchical philosophy:
- **Kotest (ShouldSpec)**: Use `context(...)` for nesting and `should(...)` for assertions.
- **Jest/RSpec/Mocha**: Use `describe(...)` for subjects, `context(...)` for states, and `it(...)` for assertions.
- **JUnit 5**: Use `@Nested` classes with `@DisplayName`.

## Examples

**Bad (Flat & Verbose)**
"If the technician exists the name of the resource should equal the technician's name"
"If the technician does not exist the name of the resource should equal null"

**Good (Nested & Specific)**
context("resource") {
  context("name") {
    should("be technician's name")
    context("on missing technician") {
      should("be null")
    }
  }
}


# Shell/Bash scripts

## Files
- must follow the [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html), i.e. file header with purpose and usage
- must not contain hard coded escape sequences but use tput or a similar semantic approach
- shell script libraries must have a .bash extension
- shell scripts must
  - not have a file extension
  - be executable
  - use shebang `#!/usr/bin/env bash`

## Parameter handling
- prefer named parameters over positional arguments (unless those are actual files)
- adopt the following pattern for parse named parameters:
```
    local code=1
    while [ $# -gt 0 ]; do
        case $1 in
        --code) code=${2?$1: parameter value not set} && shift 2 ;;
        --code=*) code=${1#*=} && shift ;;
        *) break ;;
        esac
    done
```

- for boolean parameters you can use
```
  # Boolean flags
  local verbose=false
  case $1 in
      --verbose) verbose=true && shift ;;
```


# Context awareness and multi-window workflows

Your context window will be automatically compacted as it approaches its limit, allowing you to continue working indefinitely from where you left off. Therefore, do not stop tasks early due to token budget concerns. As you approach your token budget limit, save your current progress and state to memory before the context window refreshes. Always be as persistent and autonomous as possible and complete tasks fully, even if the end of your budget is approaching. Never artificially stop any task early regardless of the context remaining.


# Balancing autonomy and safety

Consider the reversibility and potential impact of your actions. You are encouraged to take local, reversible actions like editing files or running tests, but for actions that are hard to reverse, affect shared systems, or could be destructive, ask the user before proceeding.

Examples of actions that warrant confirmation:
- Destructive operations: deleting files or branches, dropping database tables, rm -rf
- Hard to reverse operations: git push --force, git reset --hard, amending published commits
- Operations visible to others: pushing code, commenting on PRs/issues, sending messages, modifying shared infrastructure

When encountering obstacles, do not use destructive actions as a shortcut. For example, don't bypass safety checks (e.g. --no-verify) or discard unfamiliar files that may be in-progress work.


# Research and information gathering

Search for this information in a structured way. As you gather data, develop several competing hypotheses. Track your confidence levels in your progress notes to improve calibration. Regularly self-critique your approach and plan. Update a hypothesis tree or research notes file to persist information and provide transparency. Break down this complex research task systematically.


# Subagent orchestration

Use subagents when tasks can run in parallel, require isolated context, or involve independent workstreams that don't need to share state. For simple tasks, sequential operations, single-file edits, or tasks where you need to maintain context across steps, work directly rather than delegating.


# Overeagerness

Avoid over-engineering. Only make changes that are directly requested or clearly necessary. Keep solutions simple and focused:

- Scope: Don't add features, refactor code, or make "improvements" beyond what was asked. A bug fix doesn't need surrounding code cleaned up. A simple feature doesn't need extra configurability.

- Documentation: Don't add docstrings, comments, or type annotations to code you didn't change. Only add comments where the logic isn't self-evident.

- Defensive coding: Don't add error handling, fallbacks, or validation for scenarios that can't happen. Trust internal code and framework guarantees. Only validate at system boundaries (user input, external APIs).

- Abstractions: Don't create helpers, utilities, or abstractions for one-time operations. Don't design for hypothetical future requirements. The right amount of complexity is the minimum needed for the current task.


# Avoid focusing on passing tests and hard-coding

Please write a high-quality, general-purpose solution using the standard tools available. Do not create helper scripts or workarounds to accomplish the task more efficiently. Implement a solution that works correctly for all valid inputs, not just the test cases. Do not hard-code values or create solutions that only work for specific test inputs. Instead, implement the actual logic that solves the problem generally.

Focus on understanding the problem requirements and implementing the correct algorithm. Tests are there to verify correctness, not to define the solution. Provide a principled implementation that follows best practices and software design principles.

If the task is unreasonable or infeasible, or if any of the tests are incorrect, please inform me rather than working around them. The solution should be robust, maintainable, and extendable.


# Minimizing hallucinations in agentic coding

Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering. Make sure to investigate and read relevant files BEFORE answering questions about the codebase. Never make any claims about code before investigating unless you are certain of the correct answer - give grounded and hallucination-free answers.
