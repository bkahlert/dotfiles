# intellij-workspace-fix: really select all file types

**Goal:** after the Go plugin is installed, every project's Tools > Actions on Save shows "Reformat code" and "Optimize imports" for **Files: Go files**. `intellij-workspace-fix` must put them back to **All file types** in every `workspace.xml` below the current directory, and nothing else may change in those files.

**Why the current script does not work (found 2026-10-03):** the Go plugin registers a `formatOnSaveOptions.defaultsProvider`. With it, a project without a stored entry defaults to `myRunOnSave=true`, `myAllFileTypesSelected=false`, `mySelectedFileTypes={Go}`. IntelliJ stores only values that differ from the defaults. The script writes only `myRunOnSave=true`, which equals the Go default, so `myAllFileTypesSelected` is still read as `false` and the Go restriction stays. The earlier handoff blamed the script for deleting sibling options; that deletion was harmless, but the missing `myAllFileTypesSelected` is the defect.

**Target state, per component (`FormatOnSaveOptions`, `OptimizeOnSaveOptions`):** what the IDE itself wrote after switching the dropdown to "All file types" in `netmon`, plus an explicit `myRunOnSave` so the entry does not depend on which IDE or plugins open the project:

```xml
<component name="FormatOnSaveOptions">
  <option name="myAllFileTypesSelected" value="true" />
  <option name="myRunOnSave" value="true" />
  <option name="mySelectedFileTypes">
    <set />
  </option>
</component>
```

Every other option of the component (for example `myFormatOnlyChangedLines`) and every other component stays byte for byte.

**Sources:** `FormatOnSaveOptionsBase.java` in intellij-community (defaults and storage); YouTrack IJPL-173810, IJPL-173808, GO-12541, GO-12238 (no global switch exists; new projects only via Settings for New Projects).

**Decision (2026-10-03):** rewrite in stdlib-only Python 3.9, as `statusline` was. The edit is a targeted text edit, not an `ElementTree` round trip, so whitespace, quoting and `<x />` style survive. The result is parsed with `ElementTree` before it is written; a file whose result is not well-formed or does not hold the target state is reported and left alone. `xmlstarlet` goes: its CI installs, the skip marker and the missing-`xmlstarlet` test go with it.

**Preserved:** CLI (`[-n|--dry-run]`, `-h/--help`, exit 2 with a hint), output lines `✔ fixed:`, `▪ already fixed:`, `ℹ would fix:`, timestamped backup next to the file, skipped `.git`, `build`, `cache`, `node_modules`. Added: `✖ failed:` and exit 1 for a file the script cannot edit safely. The help text says: close the project first, the IDE rewrites `workspace.xml` when it exits.

## Global Constraints

- Branch `fix/intellij-workspace-fix-all-file-types`, based on `test/legacy-script-tests` until that PR lands, then rebase onto `main`. Never commit on `main`. `git add` explicit paths only; never stage `90-scratch.zsh`.
- Python 3.9: no `match`, no `X | Y` at runtime.
- Test command `uv run --locked pytest -m "not integration" -q`; `make lint` before the PR; inspections on every changed file.

## Tasks

- [ ] **1. RED.** Fixtures from the real IDE shapes: Go-restricted entries (`myAllFileTypesSelected=false`, `mySelectedFileTypes` holding `Go`), the all-file-types entry `netmon` has, an entry with a sibling `myFormatOnlyChangedLines`, absent components. Expected output per the target state above. Fails against the bash script.
- [ ] **2. Rewrite** `executable_intellij-workspace-fix` in Python; delete the missing-`xmlstarlet` test and `needs_xmlstarlet`.
- [ ] **3. CI.** Remove `xmlstarlet` from the `checks` (apt) and `macos` (brew) jobs in `.github/workflows/ci.yml`.
- [ ] **4. Verify and ship.** Suite, `make lint`, inspections, code review on `fable`. Then the user's check: run `intellij-workspace-fix` on a project closed in the IDE, reopen it, confirm Actions on Save shows All file types, restart the IDE, confirm again.
