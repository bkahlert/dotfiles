# Git: branches and commit messages

Commit history is machine-read: commitlint gates it, and semantic-release, release-please, conventional-changelog and git-cliff turn it into version
bumps and changelogs. Every rule below exists so that a commit parses the same way in all of them.

## Branches

- Never commit on `main`/`master`. Every change starts on a branch and lands through a pull request.
- Name: `<type>/<TICKET-ID>-<slug>`, e.g. `feat/PROJ-123-oauth-login`, `fix/42-null-token`.
    - `<type>` is the commit type the branch mostly produces (see below), so branch and changelog share one vocabulary.
    - `<TICKET-ID>` as the tracker writes it (`PROJ-123`; the bare number for GitHub/GitLab issues). Omit the segment only when no ticket exists:
      `docs/git-rule`.
    - `<slug>`: two to five lowercase words, hyphen-separated, saying what the branch does — not the ticket title verbatim.
- One branch per ticket. Short-lived; delete after merge.

## Commit messages

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) with the Angular type set — the grammar every changelog tool parses by
default.

```
<type>(<scope>)!: <description>

<body>

<footer>
```

### Header

- `type` — lowercase, one of the following; anything else fails `@commitlint/config-conventional`:

  | Type | Use for | Release |
  |---|---|---|
  | `feat` | a user-visible capability | minor |
  | `fix` | a user-visible bug fix | patch |
  | `perf` | faster or leaner, behaviour unchanged | patch |
  | `revert` | undoing a commit | patch |
  | `refactor` | code change that is neither `feat` nor `fix` | none |
  | `docs`, `test`, `build`, `ci`, `style`, `chore` | as named; `chore` for what fits nowhere else | none |

  The type decides the version bump and the changelog section, so choose it by effect on the user, not by effort: a large internal rewrite is
  `refactor`, a one-line change users notice is `feat` or `fix`. Only `feat`, `fix`, `perf`, `revert` and breaking changes appear in a changelog
  by default.
- `scope` — the area of the code the change touches, as one lowercase noun: `parser`, `auth`, `zsh`. Letters, digits and hyphens. Reuse the
  scopes already in the history (`git log --format=%s | grep -oE '^\w+\([^)]+\)' | sort | uniq -c`): the changelog groups by scope, and `api`
  next to `apis` makes two groups. Omit the scope only when the change is cross-cutting.
- `description` — imperative present tense (`add`, not `added` or `adds`), lowercase first letter, no trailing period; it completes "this commit
  will …". Whole header at most 72 characters (commitlint allows 100, but `git log --oneline` and GitHub cut off past 72).

### Body

Blank line after the header, lines wrapped at 72. Say what changed and why — the motivation, the previous behaviour, the trade-off. Not how; the
diff shows that. Skip the body when the header says it all.

### Footers

Blank line after the body, one git trailer per line:

- `BREAKING CHANGE: <what breaks and how to migrate>`, plus `!` after the type/scope in the header. Use both: the `!` is visible in
  `git log --oneline`, the footer carries the migration text and is what older tooling reads. Either alone triggers a major release.
- `Closes #42` / `Fixes #42` closes the tracker issue; `Refs: PROJ-123` links without closing. Put the ticket here, not in the description: the
  tools render footer references as links and keep the changelog line clean.
- Reverts: header `revert: <original header>`, body `This reverts commit <sha>.` followed by the reason.

```
feat(auth)!: require PKCE for the authorization-code flow

Public clients could complete the flow without a code challenge, which
allowed authorization-code interception on mobile. Following RFC 7636,
the server now rejects requests without code_challenge.

BREAKING CHANGE: clients must send code_challenge and code_verifier;
the implicit-flow fallback was removed.
Refs: PROJ-123
```

### One change per commit

Each commit becomes one changelog line. A commit that fixes a bug and adds a feature reports only one of them; split it. Reformatting inside a
`feat` commit buries the feature in noise; make it a separate `style` commit.

### Pull requests

With squash-merge the PR title becomes the commit header on `main` and is all the changelog tools see. Write it as a header
(`type(scope): description`); GitHub appends `(#61)` itself. Put the footers (`BREAKING CHANGE:`, `Closes`) in the PR description so they end up
in the squash commit's body.
