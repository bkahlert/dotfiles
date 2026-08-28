# Comments & Doc Comments

Code says *what*. A comment earns its place only by saying what the code cannot: why this way, what breaks otherwise.

Default to fewer, shorter comments. Verbosity is the common failure, not terseness.

## Delete rather than write

- **Restatement** of the signature or of the branches below it.
- **Advocacy.** State the fact once; skip the consequence, the counterfactual, and the moral.
- **Evidence** — measurements, dates, ticket history. Those belong in the commit message; they date, the constraint does not.
- **Stale rationale.** A comment defending changed behaviour misleads. When you change code, re-read its comment.

## Match the language's register

Write doc comments the way that language's own standard library does. In Kotlin/Java: open with `Returns …`, `Holds …`,
`Throws …`; one fact per sentence; let `[links]` do the describing. Prefer a single line.

## Prose discipline

Plain declarative sentences. Avoid absolute constructions (*"the events being in hand"* → *"the events are already
read"*), rhetorical inversion (*"[event] being the one that settled it"*), and em-dash chains.

```kotlin
// ❌ Restates the fold, argues its case, buries the fact in an absolute construction
/**
 * Folds these events into a [Projection], [create] and [transform] saying what each makes of the projection so far.
 *
 * Every event is applied, a [Projection.Failed] absorbing the rest rather than the iteration stopping: there is
 * nothing to save by stopping, the events being in hand already.
 */

// ✅ Leads with Returns, one fact per sentence
/**
 * Returns these events projected, [initialize] applying to the first and [evolve] to the rest.
 *
 * All are projected; a failure absorbs the rest. Stopping early saves nothing, since they are already read.
 */
```

## Where rationale lives

Put the reason on the declaration that would break — the field, function, or test someone is about to change. A
nullable type held nullable *on purpose* is the clearest case: without a note there, the next reader tightens it. A
design doc is no substitute; nobody consults it before deleting a constraint.
