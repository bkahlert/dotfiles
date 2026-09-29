# Git: branches and commit messages

Commit history is machine-read — commitlint gates it; semantic-release, release-please and conventional-changelog turn it into version bumps and
changelogs — so every commit must parse the same way in all of them.

## Branches

Never commit on `main`/`master`; every change starts on a branch and lands through a pull request. One branch per ticket, deleted after merge.

Name: `<type>/<TICKET-ID>-<slug>`, e.g. `feat/PROJ-123-oauth-login`. The type is a commit type from below. The ticket ID is written as the tracker
writes it (`PROJ-123`, or `42` for a GitHub issue) and omitted only when there is no ticket (`docs/git-rule`). The slug is two to five lowercase
hyphenated words saying what the branch does.

## Commits

[Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) with the Angular types — the grammar every changelog tool parses by
default:

```
<type>(<scope>): <description>

<body>

<footers>
```

**Type** — lowercase, from this table. It decides the version bump and whether the change is listed at all, so choose by effect on the user, not
by effort: a large internal rewrite is `refactor`, a one-line change users notice is `feat` or `fix`.

| Type | Use for | Release |
|---|---|---|
| `feat` | a user-visible capability | minor |
| `fix` | a user-visible bug fix | patch |
| `perf` | faster or leaner, behaviour unchanged | patch |
| `revert` | `revert: <original header>`, body `This reverts commit <sha>.` | patch |
| `refactor`, `docs`, `test`, `build`, `ci`, `style`, `chore` | as named, unlisted in changelogs; `chore` for what fits nowhere else | none |

**Scope** — one lowercase noun for the area touched (`parser`, `auth`, `zsh`). Reuse existing scopes, since the changelog groups by them:
`git log --format=%s | grep -oE '^\w+\([^)]+\)' | sort | uniq -c`. Omit only for cross-cutting changes.

**Description** — imperative present (`add`, not `added`), lowercase, no trailing period; whole header at most 72 characters.

**Body** — after a blank line, wrapped at 72: what changed and why, not how. Omit when the header says it all.

**Footers** — after a blank line, one git trailer per line:

- Breaking change: `!` before the colon *and* `BREAKING CHANGE: <what breaks, how to migrate>`. The `!` shows in one-line logs; the footer is what
  older tooling reads.
- Ticket: `Closes #42` / `Fixes #42` closes it, `Refs: PROJ-123` links it. Here, not in the description — tools link footer references.
- No AI-attribution trailers (`Co-Authored-By: Claude …`, `Generated with …`), in commits or PR descriptions.

```
feat(auth)!: require PKCE for the authorization-code flow

Public clients could complete the flow without a code challenge, which
allowed code interception on mobile. Requests without code_challenge
are now rejected (RFC 7636).

BREAKING CHANGE: clients must send code_challenge and code_verifier.
Refs: PROJ-123
```

**One change per commit** — each commit is one changelog line; a commit that fixes and adds reports only one. Split it, and keep reformatting in
its own `style` commit.

**Pull requests** — under squash-merge the PR title becomes the commit header, so write it as a header; GitHub appends `(#61)` itself. Footers in
the PR description reach the squash commit only if the repository's squash message is set to "title and description" — otherwise add them in the
merge dialog.
