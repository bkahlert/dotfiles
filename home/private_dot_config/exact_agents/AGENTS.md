# Dotfiles

- Most dotfiles located in the home directory are managed by chezmoi.
- To update dotfiles, e.g. `~/.config/agents/AGENTS.md`, the corresponding file, e.g. `$(chezmoi source-path)/private_dot_config/exact_agents/AGENTS.md`, needs
  to be updated first.

# Git

- Do never commit on the main/master branch.

# Documentation

Prefer the context7 MCP tool for any queries regarding external library documentation or up-to-date API specs to ensure accuracy over your internal training
data.

# Source location of dependencies

- When you need to know the actual source of a build dependency, chances are they are located in a sibling directory as I tend to keep projects / repos
  belonging together in the same parent directory.

- Reason about projects tightly coupled together (e.g. projects `technician-app-service` and `technician-app-web` are tightly coupled, with `-service` being a
  backend microservice and `-web` being its web (UI))

# Markdown

- When you reference a file, do so with a proper Markdown link
    - `[filename](path)`, or
    - `[path](path)`, or
    - `[title of the references file](path)`

# SVG

Whenever possible "relative" colors like `currentColor` (e.g. `fill="currentColor"`).

# Tailwind & Derivative Libraries (DaisyUI, etc.) Standards

- **Strict Rule: No Dynamic Class Construction**
    - **Never** use string concatenation or template literals to build class names for Tailwind CSS or any based library (DaisyUI, Flowbite, etc.).
    - **Reason**: The Tailwind compiler performs static analysis and only includes classes found as **complete, unbroken strings** in your source code.
      Constructed strings like `` `text-${color}-500` `` will be purged from the production build.
    - **❌ Bad**: `<div className={`alert alert-${type}`}>`
    - **❌ Bad**: `<button className={"btn-" + color}>`
    - **✅ Good**: Use a mapping object or a switch statement to return the **full class name** as a static string.

- **Implementation Pattern (Mapping)**:
  ```javascript
  // The compiler must see the full string (e.g., 'status-success') to include it
  const statusClasses = {
    success: 'status-success',
    error: 'status-error',
    warning: 'status-warning',
  };
  
  const className = `status ${statusClasses[status] || 'status-info'}`;
  ```

## Typing Guidelines

Avoid primitive obsession. Do not default to `string`, `number`, or `boolean` when a more descriptive general-purpose or domain-specific type exists.

- **General Purpose:** Use `Duration` or `Timestamp` instead of `numMilliseconds` or `epochSeconds`.
- **Business Domains:** Use semantic types like `InternationalBankAccountNumber` (IBAN), `VehicleIdentificationNumber` (VIN), or `CurrencyCode` instead of
  generic strings.
- **Validation:** Favor types that imply structural constraints or units of measure to improve clarity and reduce logic errors.

# Test Naming & Structure

## 1. Specificity via Nesting

Achieve test specificity through hierarchical nesting rather than long BDD descriptions. Each level should add a single layer of context.

- **Concise Strings**: Keep individual descriptions brief.
- **No Redundancy**: Do not repeat words from a parent block in a child block.
- **The "Full Path" Rule**: The test's intent should be clear when reading the nested breadcrumbs (e.g., Resource > Name > On missing technician > should be
  null).

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

```
context("resource") {
  context("name") {
    should("be technician's name")
      context("on missing technician") {
        should("be null")
      }
    }
  }
}
```

# Scripting

## Log messages

If the context implies prefixing log messages with an informative icon/symbol, use the following (if supported, apply color/format):

| Event       | Icon | Color               | Format |
|-------------|------|---------------------|--------|
| created     | `✱`  | Yellow              |        |
| added       | `✚`  | Green               |        |
| item        | `▪`  | Gray (Bright black) |        |
| link / file | `↗`  | Blue                |        |
| task        | `⚙`  | Yellow              |        |
| nested      | `❱`  | Yellow              |        |
| exit        | `↩`  | Red                 | Bold   |
| success     | `✔`  | Green               |        |
| info        | `ℹ`  | White               |        |
| warning     | `!`  | Yellow              | Bold   |
| error       | `✘`  | Red                 |        |
| failure     | `ϟ`  | Red                 | Bold   |

Apply color and format to the **icon only**, then reset.
Use whatever coloring mechanism is idiomatic for the runtime.
Avoid adding dependencies and avoid shell expansion pitfalls (e.g. use `printf` with single-quoted format strings in Bash).

## Shell/Bash scripts

### Files

- must follow the [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html), i.e. file header with purpose and usage
- must not contain hard coded escape sequences but use tput or a similar semantic approach
- shell script libraries must have a .bash extension
- shell scripts must
    - not have a file extension
    - be executable
    - use shebang `#!/usr/bin/env bash`

### Parameter handling

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

# Balancing autonomy and safety

Consider the reversibility and potential impact of your actions. You are encouraged to take local, reversible actions like editing files or running tests, but
for actions that are hard to reverse, affect shared systems, or could be destructive, ask the user before proceeding.

Examples of actions that warrant confirmation:

- Destructive operations: deleting files or branches, dropping database tables, rm -rf
- Hard to reverse operations: git push --force, git reset --hard, amending published commits
- Operations visible to others: pushing code, commenting on PRs/issues, sending messages, modifying shared infrastructure

When encountering obstacles, do not use destructive actions as a shortcut. For example, don't bypass safety checks (e.g. --no-verify) or discard unfamiliar
files that may be in-progress work.

# Research and information gathering

Search for this information in a structured way. As you gather data, develop several competing hypotheses. Track your confidence levels in your progress notes
to improve calibration. Regularly self-critique your approach and plan. Update a hypothesis tree or research notes file to persist information and provide
transparency. Break down this complex research task systematically.

# Overeagerness

Avoid over-engineering. Only make changes that are directly requested or clearly necessary. Keep solutions simple and focused:

- Scope: Don't add features, refactor code, or make "improvements" beyond what was asked. A bug fix doesn't need surrounding code cleaned up. A simple feature
  doesn't need extra configurability.

- Documentation: Don't add docstrings, comments, or type annotations to code you didn't change. Only add comments where the logic isn't self-evident.

- Defensive coding: Don't add error handling, fallbacks, or validation for scenarios that can't happen. Trust internal code and framework guarantees. Only
  validate at system boundaries (user input, external APIs).

- Abstractions: Don't create helpers, utilities, or abstractions for one-time operations. Don't design for hypothetical future requirements. The right amount of
  complexity is the minimum needed for the current task.

# Avoid focusing on passing tests and hard-coding

Please write a high-quality, general-purpose solution using the standard tools available. Do not create helper scripts or workarounds to accomplish the task
more efficiently. Implement a solution that works correctly for all valid inputs, not just the test cases. Do not hard-code values or create solutions that only
work for specific test inputs. Instead, implement the actual logic that solves the problem generally.

Focus on understanding the problem requirements and implementing the correct algorithm. Tests are there to verify correctness, not to define the solution.
Provide a principled implementation that follows best practices and software design principles.

If the task is unreasonable or infeasible, or if any of the tests are incorrect, please inform me rather than working around them. The solution should be
robust, maintainable, and extendable.

# Minimizing hallucinations in agentic coding

Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering. Make sure to investigate and
read relevant files BEFORE answering questions about the codebase. Never make any claims about code before investigating unless you are certain of the correct
answer - give grounded and hallucination-free answers.

# Keeping AI guidance files accurate

When writing or updating `AGENTS.md`, `CLAUDE.md`, or equivalent guidance files:

- **Prefer intent over enumeration.** Describe *why* a rule exists rather than listing every file or pattern it covers. A stated principle survives refactoring;
  a file list silently rots.

- **Anchor exceptions to their assumptions.** If you must list exceptions (e.g., "these files must stay as templates"), state the condition that makes each
  exception necessary — so it's clear when that condition no longer holds and the exception should be removed.

- **Review guidance after making code changes.** After any significant refactor, scan the guidance file for descriptions that no longer match the codebase.
  Stale guidance is worse than no guidance — it actively misleads future agents.

# Quality Assurance Gate

Before applying any code or config change, establish a **verification strategy** if none has been stated yet in this session:

- **What observable outcome confirms this change has its intended effect?**
- For code: TDD, test-after with rationale, or explicit manual steps
- For config/infra: what command output, log entry, or runtime behavior proves the change took effect (e.g. a pipeline cache tweak is only confirmed when a
  downstream job demonstrably skips the rebuild)

State this once, upfront, as: *"QA for this change: [method] — verified by [observable outcome]"*

For trivially non-functional changes (e.g. fixing a typo in a comment), say so explicitly — making the decision visible rather than silent.

# Codebase Invariants

When a session introduces or discovers a cross-cutting constraint that all code must comply with (e.g., adopting a code style, renaming convention,
architectural boundary), update the project's AI guidance file (`AGENTS.md`, `CLAUDE.md`, or equivalent) before the session ends.

Each invariant entry should include:

- The rule itself (actionable and specific)
- Why it was introduced (one sentence)
- A before/after example if the rule isn't self-evident
