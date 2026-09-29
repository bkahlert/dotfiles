# Code documentation

Doc comments (KDoc, Javadoc, JSDoc, docstrings), inline comments, and code samples wherever they appear. Markdown prose
follows [markdown.md](markdown.md).

The bar is the language's standard library: `kotlin.collections`, `java.util`. Their docs state the contract, short and
complete, in a fixed register. Chatty, partial or missing docs fail that bar.

Two kinds of text, two rules. Public API gets the full contract. Everything else gets a comment only for what the code
cannot say.

## Public API: the contract, complete

Public API is what other code calls without reading the body: a library's surface, a module boundary, anything another
team consumes. Every such declaration you add or change has a doc comment, because its readers cannot see the body. Test
code has none ([testing.md](testing.md)).

The doc comment answers, in this order and only as far as they apply:

- **What it returns or does.** One sentence, first. `Returns the size of the collection.`
- **Edge cases.** Empty input, `null`, bounds. ``Returns the first element, or `null` if the collection is empty.``
- **Failures.** Each exception and its condition. KDoc: `@throws IndexOutOfBoundsException if [index] is out of bounds of this list.`
- **Guarantees a caller relies on.** Ordering, mutability, thread-safety, complexity when it is not the obvious one.

Leave out what the signature already says, how the body does it, and when to use it. A maintainer's reason for a
constraint is not contract either; it goes in a `//` comment (see [Where rationale lives](#where-rationale-lives)).

Even an obvious public member gets its one line, as `size` does above. Anywhere else, a doc that only rewords the name
(`getName` → "Gets the name") is noise. Write none.

```kotlin
// ❌ Tutorial voice, no contract
/**
 * This helper function can be used to safely get the first element of a collection.
 * It is very useful when you are not sure if the collection has elements, because it
 * never throws. Instead, it simply returns null.
 */

// ✅ kotlin.collections, verbatim
/** Returns the first element, or `null` if the collection is empty. */
```

## Register

Third person, present tense, indicative. Functions and properties open with the verb: `Returns`, `Creates`, `Appends`,
`Throws`. Never `This function returns`, `Will return`, `you`, `we`. Classes and interfaces are noun phrases:
`A generic ordered collection of elements.` One fact per sentence. One line when the contract fits on one.

Tags follow the language. KDoc names parameters inline as `[index]` and uses `@param` only for what the sentence cannot
carry. Javadoc lists `@param` and `@return` for every parameter and return value, by convention. Python docstrings are
imperative (`Return the …`, PEP 257). For any other language, read how its standard library does it.

## Code samples

A sample, in a doc comment or a Markdown fence, parses as written. Cut the rest with `/* ... */`, or with `// ...`
inside Javadoc or JSDoc, where `*/` ends the doc comment. A placeholder the language accepts also works: `TODO()` in
Kotlin, `...` in Python. Bare `...` in Kotlin or Java is a syntax error.

## Inline comments: only the why

Code says *what*. A comment earns its place only by saying what the code cannot: why this way, what breaks otherwise.
Default to fewer, shorter comments. Verbosity is the common failure, not terseness.

Delete rather than write:

- **Restatement** of the signature or of the branches below it.
- **Advocacy.** State the fact once; skip the consequence, the counterfactual, and the moral.
- **Evidence** — measurements, dates, ticket history. Those belong in the commit message; they date, the constraint does not.
- **Stale rationale.** A comment defending changed behaviour misleads. When you change code, re-read its comment.

## Prose discipline

Plain declarative sentences. Avoid absolute constructions (*"the events being in hand"* → *"the events are already
read"*), rhetorical inversion (*"[event] being the one that settled it"*), and em-dash chains.

```kotlin
// ❌ Restates the fold, argues its case, buries the fact in an absolute construction
/**
 * Folds these events into a [Projection], [initialize] and [evolve] saying what each makes of the projection so far.
 *
 * Every event is applied, a [Projection.Failed] absorbing the rest rather than the iteration stopping: there is
 * nothing to save by stopping, the events being in hand already.
 */

// ✅ Leads with Returns, one fact per sentence, contract only
/**
 * Returns these events projected: [initialize] applies to the first, [evolve] to each later one.
 *
 * Projection does not stop at a failure; a [Projection.Failed] absorbs the remaining events.
 */
```

## Where rationale lives

Put the reason on the declaration that would break — the field, function, or test someone is about to change. A
nullable type held nullable *on purpose* is the clearest case: without a note there, the next reader tightens it. A
design doc is no substitute; nobody consults it before deleting a constraint.
