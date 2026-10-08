# Shared Statusline Renderer Design

## Goal

Extract the smallest useful behavior shared by the Claude and Copilot
statusline scripts without merging their provider-specific logic. The initial
shared component only renders non-empty text parts separated by a separator.

## Current behavior

Both scripts construct a list of already-formatted strings, discard empty
strings, join the remaining parts with ` · `, and print the result. Their input
schemas and part formatting differ and are covered by separate golden-output
tests.

## Design

Add a small standard-library Python module at
`home/dot_local/share/statusline_render.py`, installed by chezmoi as
`~/.local/share/statusline_render.py`. It exposes one function:

```python
def render_parts(parts, separator=" · "):
    ...
```

The function joins the provided strings in order, omitting empty strings.
It returns the rendered string without printing or adding a newline. The
separator is configurable by the caller, with the existing middle dot as the
default.

Each statusline entry point adds `~/.local/share` to Python's import path and
calls `render_parts` with its own provider-specific parts. Input parsing,
formatting, ANSI styling, icon selection, font detection, and part ordering
remain in their current scripts. There is no subprocess boundary or fallback
implementation: a missing shared module should fail visibly rather than
silently diverge.

## Testing

- Unit-test `render_parts` for joining, empty-part omission, custom separators,
  and an empty input.
- Stage the shared module in the temporary HOME used by the script test
  harness, so both statusline commands exercise the same module as production.
- Keep both existing statusline golden-output suites passing to prove their
  visible output remains unchanged.
- Run the targeted Python tests and `make unit`.

## Scope boundaries

This first extraction does not unify JSON parsing, field lookup, formatting,
icons, thresholds, font detection, temporary input dumps, CLI options, or
preview behavior. Those can be considered separately if later duplication
justifies them.
