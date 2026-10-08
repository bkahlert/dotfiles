# Test Infrastructure Layout

## Goal

Make the repository root and `tests/` easier to scan by distinguishing real
test cases from reusable test infrastructure. Keep the existing subject-based
test organization and move the container test image out of the repository root.

## Current behavior

The dotfiles tests are organized by source subject: `bin`, `zsh`,
`chezmoiscripts`, `templates`, `modify`, and the provider-specific and
integration suites. This layout is documented in
[`AGENTS.md`](../../../AGENTS.md#where-a-test-lives), and several dotfiles
invoke test files by their current paths.

The root `tests/` directory also contains reusable helpers, sandbox fixtures,
shims, and a capability fixture alongside cross-cutting tests. At the
repository root, `Containerfile` and `entrypoint.sh` exist only to build and
run the test/integration container. The container build uses the repository
root as its context.

## Design

Keep all actual test cases at their current paths. Do not regroup them into
`unit/`, `system/`, or `browser/`: the subject-based layout matches this
repository's testing conventions and avoids changing paths used by scripts
and documentation.

Move shared testing infrastructure under `tests/harness/`:

```text
tests/
  harness/
    agent_integration.py
    agent_setup_cases.py
    repo.py
    fixtures/
      agent-capability.txt
    shims/
      keepassxc-cli
    container/
      Containerfile
      entrypoint.sh
  bin/
  chezmoiscripts/
  claude/
  copilot/
  integration/
  modify/
  templates/
  zsh/
  conftest.py
  test_*.py
```

Move `tests/agent_integration.py`, `tests/agent_setup_cases.py`,
`tests/repo.py`, `tests/shims/`, and
`tests/integration/fixtures/agent-capability.txt` to the corresponding
`tests/harness/` locations. Keep pytest `conftest.py` files where they are so
pytest continues to discover their hooks and scoped fixtures in the same
directories.

Move the root `Containerfile` and `entrypoint.sh` to
`tests/harness/container/`. Preserve the repository root as the image build
context. The Containerfile copies its entrypoint from
`tests/harness/container/entrypoint.sh`; Makefile targets and tests select the
Containerfile by its new path.

Add `tests/harness` to pytest's configured `pythonpath` while retaining
`tests` there. This keeps existing short imports such as `from repo import`
working and preserves imports of test modules from the integration suite.
Update helper constants and every tracked reference to moved assets, including
`AGENTS.md`.

## Scope boundaries

- Keep all `test_*.py` and `*.test.js` files at their current paths.
- Keep `tests/conftest.py` and the subject-local `conftest.py` files in place.
- Keep the image build context at the repository root; do not copy the
  dotfiles source tree into a smaller context.
- Do not reorganize unrelated root files or change test behavior.
- No file named `Dockerfile` exists; the repository uses `Containerfile`.

## Validation

Run the focused tests that assert the selected Containerfile path and inspect
its build instructions. Run `make unit` and `make lint` to verify test
collection, helper imports, shell syntax, and the relocated entrypoint. If a
container engine is available, run `make integration` to verify the image
build and apply flow end to end.

## Alternatives considered

1. **Add `tests/harness/` and retain subject-based test folders.**
   Recommended and approved. It creates an explicit home for infrastructure
   without changing the tests' documented paths.
2. **Move all test support to a top-level `test-support/`.**
   This separates helpers from pytest discovery, but adds another root
   directory and makes test imports and references less cohesive.
3. **Regroup tests into unit/system/browser categories.**
   This resembles the `netmon` test layout, but it does not match this
   repository's subject-based conventions and would change many test paths.
