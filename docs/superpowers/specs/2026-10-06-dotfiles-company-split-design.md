# Company-specific dotfiles split

## Goal

Separate company-specific configuration from the public dotfiles repository's
current source tree while keeping a complete internal downstream checkout for
work machines. Each machine uses one chezmoi source: public for general use,
internal for work.

The local internal checkout is created before the public split is merged. The
public repository's existing history is preserved; company-specific files in
older public commits are not rewritten or removed from history.

## Approved architecture

Create `../dotfiles-ista` locally from the existing public repository history.
The internal checkout owns all company-specific configuration and supporting
tests and documentation. Work configuration is unconditional there; it is not
selected by a `.company` profile value.

The public checkout retains the general-purpose configuration and removes
company-specific behavior from its current tree. Shared behavior remains
available in both checkouts, with work-specific additions or variants present
only in the internal checkout. Genuinely shared files remain in both.

After the public split is squash-merged through the normal public flow, update
the internal checkout's public base and rebase its internal-only commits onto
the resulting public `main`. Resolve overlap by retaining the internal
work-specific behavior. Future public updates are merged inward so the
downstream history remains connected.

## Ownership boundary

The split covers all company-specific source state and the tests and documents
that describe or verify it. The source inventory includes, but is not limited
to:

- profile selection and ignore rules, including
  [`home/.chezmoi.toml.tmpl`](../../../home/.chezmoi.toml.tmpl) and
  [`home/.chezmoiignore`](../../../home/.chezmoiignore);
- work-only zsh modules and the
  [quick-access guide](../../../quick-access/README.md);
- company-specific scripts, skills, secrets, SSH, npm registry, package, and
  starship configuration;
- tests for those files, profile-specific test fixtures, and integration
  coverage.

Mixed files stay in the public checkout with company-specific branches removed;
the internal checkout has the work behavior without a runtime company switch.
Shared code, tests, and documentation stay public and are retained internally
where needed. The inventory is determined from the source tree during
implementation, so the examples above are not an exclusion list.

## Git and safety boundaries

- Keep public `main` unchanged during local implementation; make public changes
  on a local topic branch.
- Create the internal checkout and its work-specific commits locally, based on
  public history. Do not create or configure a hosted internal remote.
- Do not rewrite existing public commits, publish either checkout, or apply
  changes to `$HOME`.
- Verify the local migration before publication. The later internal rebase
  depends on the public split being squash-merged and is a follow-up outside
  this local-only authorization; do not simulate it or claim it is complete.
- Once the public split is merged and the user authorizes that follow-up,
  rebase the internal-only commits onto updated public `main`. Subsequent
  upstream changes flow inward by merge.

## Validation

Run the repository's lint and unit suites in both checkouts, updating the
tests and supporting documentation with their corresponding source changes.
Run the container integration target in each checkout where the required
container runtime is available; report any unavailable integration run rather
than treating it as passed.

Confirm that:

- the public current tree contains no active company-profile selector or
  company-only behavior;
- the internal current tree contains the complete work configuration without
  `.company` gating;
- both checkouts retain the expected Git ancestry and local branch/remote
  state, with no hosted internal remote or publication;
- no changes have been applied to `$HOME`.

## Alternatives considered

1. **Create the local downstream now and realign after the public split.**
   Recommended and approved. It starts the local migration now, preserves
   public history, and retains ancestry for future upstream merges.
2. **Wait for the public split to merge before creating the internal checkout.**
   This simplifies initial alignment but delays the requested local migration.
3. **Create an independent internal history.** This isolates the repositories
   but makes future public upstream integration harder and was not selected.
