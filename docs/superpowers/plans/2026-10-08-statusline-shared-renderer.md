# Shared Statusline Renderer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the generic statusline part-joining behavior into one shared Python module without changing Claude or Copilot output.

**Architecture:** Add `statusline_render.py` under chezmoi's `~/.local/share` target. Both statusline scripts import `render_parts` from that module and continue to own all provider-specific parsing and formatting.

**Tech Stack:** Python 3.9+ standard library, pytest, chezmoi.

**Spec:** [Shared Statusline Renderer Design](../specs/2026-10-08-statusline-shared-renderer-design.md)

## Global Constraints

- Use the Python standard library only.
- Install the module as `~/.local/share/statusline_render.py`.
- Expose `render_parts(parts, separator=" · ")`.
- Omit empty strings and return rendered text without printing or adding a newline.
- Keep provider-specific input parsing and formatting in the Claude and Copilot scripts.
- Use no subprocess boundary or fallback implementation.

## Review Focus

- Empty input returns `""` — covered by `test_should_return_empty_string_for_no_parts` in Task 1.
- Empty leading, interior, and trailing parts add no extra separators — covered by `test_should_omit_empty_parts_without_leaving_separators` in Task 1.
- Existing ANSI escapes and OSC hyperlink sequences remain unchanged — covered by `test_should_preserve_part_text_verbatim` in Task 1.
- A caller-supplied separator is used exactly — covered by `test_should_use_a_custom_separator` in Task 1.
- Both entry points still render their golden output, including the final newline — covered by the Claude and Copilot statusline suites in Task 2.

---

### Task 1: Add the shared renderer

**Files:**
- Create: `home/dot_local/share/statusline_render.py`
- Create: `tests/test_statusline_render.py`

**Interfaces:**
- Produces: `render_parts(parts, separator=" · ") -> str`, joining non-empty strings in order and returning an empty string when no non-empty parts remain.

- [ ] **Step 1: Write the renderer tests**

Create `TestStatuslineRender` with these cases:

```python
def test_should_join_parts_with_the_default_separator():
    assert render_parts(["model", "context"]) == "model · context"

def test_should_omit_empty_parts_without_leaving_separators():
    assert render_parts(["", "model", "", "context", ""]) == "model · context"

def test_should_use_a_custom_separator():
    assert render_parts(["model", "context"], " | ") == "model | context"

def test_should_return_empty_string_for_no_parts():
    assert render_parts([]) == ""

def test_should_preserve_part_text_verbatim():
    ansi = "\033[2mtext\033[0m"
    hyperlink = "\033]8;;file:///tmp/session\033\\session\033]8;;\033\\"
    assert render_parts([ansi, hyperlink]) == f"{ansi} · {hyperlink}"
```

Make the source module importable from the test by adding
`home/dot_local/share` to `sys.path` using `tests/repo.py`'s `ROOT`.

- [ ] **Step 2: Run the new tests and verify the expected failure**

Run: `uv run --locked pytest -q tests/test_statusline_render.py`

Expected: collection fails because `statusline_render` does not exist yet.

- [ ] **Step 3: Implement `render_parts`**

In `home/dot_local/share/statusline_render.py`, define the specified function.
Join only non-empty strings with the caller's separator; do not print, append a
newline, or transform part contents.

- [ ] **Step 4: Run the renderer tests**

Run: `uv run --locked pytest -q tests/test_statusline_render.py`

Expected: all five tests pass.

- [ ] **Step 5: Commit the shared renderer**

```bash
git add home/dot_local/share/statusline_render.py tests/test_statusline_render.py
git commit -m "feat(statusline): add shared part renderer"
```

### Task 2: Wire both statuslines to the shared renderer

**Files:**
- Modify: `home/private_dot_claude/executable_statusline`
- Modify: `home/private_dot_copilot/executable_statusline`
- Modify: `tests/conftest.py`
- Modify: `quick-access/README.md`
- Create symlink: `quick-access/statusline-render.py` -> `../home/dot_local/share/statusline_render.py`
- Test: `tests/claude/test_statusline.py`
- Test: `tests/copilot/test_statusline.py`

**Interfaces:**
- Consumes: `render_parts(parts, separator=" · ") -> str` from Task 1.
- Produces: Both statusline commands import the shared function from
  `~/.local/share/statusline_render.py`; their emitted output stays unchanged.

- [ ] **Step 1: Stage the shared module in the test sandbox**

Import `HOME_SOURCE` in `tests/conftest.py`. In `Sandbox.__init__`, create
`$HOME/.local/share` and symlink `statusline_render.py` there to
`HOME_SOURCE / "dot_local/share/statusline_render.py"`. This lets the real
scripts use the same source module under the isolated HOME.

- [ ] **Step 2: Import the helper from both entry points**

In each statusline script, add `~/.local/share` to `sys.path` using
`Path.home()`, then import `render_parts` from `statusline_render`. Replace
the local separator join at the output point with `print(render_parts(parts))`
and remove the now-unused local `SEPARATOR` constant. Leave part construction
and all other behavior untouched.

- [ ] **Step 3: Add the helper to quick access**

Create the `quick-access/statusline-render.py` symlink to the shared source
module and add it to the map in `quick-access/README.md`, describing it as the
shared Claude/Copilot statusline text renderer. Add the table row with source
`home/dot_local/share/statusline_render.py` and the symlink path above.

- [ ] **Step 4: Run both provider test suites**

Run:

```bash
uv run --locked pytest -q tests/claude/test_statusline.py tests/copilot/test_statusline.py
```

Expected: both suites pass, including their existing complete-output
assertions.

- [ ] **Step 5: Run the complete unit suite**

Run: `make unit`

Expected: pytest and the Node test command exit successfully; no Python test
fails.

- [ ] **Step 6: Commit the wiring**

```bash
git add home/private_dot_claude/executable_statusline \
  home/private_dot_copilot/executable_statusline tests/conftest.py \
  quick-access/README.md quick-access/statusline-render.py
git commit -m "refactor(statusline): share part rendering"
```
