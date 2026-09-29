# Testing

## 1. Functional code ships with tests

Every functional aspect of a change — behaviour a caller or user can observe: a return value, a state change, an emitted event, an error path — is covered
by an automated test in the same change.

- **Only drafts and prototypes are exempt**, and only when the user has declared one (spike, proof of concept, "just try it", "quick draft").
- **Infeasible is said, not skipped.** If a behaviour cannot be tested with reasonable effort, name it in the reply with the reason and the manual check done
  instead.

## 2. Fast and lightweight — never at the expense of coverage

Keep each test as fast and small as the behaviour under test allows.

- **Test at the lowest level that exercises the behaviour.** Pure logic is tested without a framework, container or database around it; an integration
  test is for behaviour that *is* the integration: SQL, serialization, HTTP wiring, framework configuration.
- **Setup is proportional.** Build only the fixture the assertion needs, share expensive setup (containers, application contexts) across the class, and use
  the project's existing test stack — no new library for one matcher.
- **No waiting, no incidental I/O.** Replace `sleep` and polling with injected clocks, fakes or awaiting the actual signal; keep network, file system and
  wall-clock time out unless they are what is being tested.
- **Lightweight is not shallow.** Dropping an assertion or an error path, mocking the subject, or swapping an integration test for a unit test that cannot
  fail for the real defect is a quality cut, not an optimisation.

## 3. One Class per Subject

A test class is named after its subject plus `Test` or `IntegrationTest` — nothing else (`FooTest`, or `FooKtTest` for the top-level functions in
`Foo.kt`). No `FooLoggingTest`.

- **Aspects are contexts, not classes**: logging, metrics and tracing behaviour of `Foo` are `context` blocks inside `FooTest`.
- **A different class gets its own test**: if the would-be extra class actually exercises something else (a metrics helper, say), test that class directly
  under its own name.

## 4. Specificity via Nesting

Achieve test specificity through hierarchical nesting rather than long BDD descriptions. Each level should add a single layer of context.

- **Concise Strings**: Keep individual descriptions brief.
- **No Redundancy**: Do not repeat words from a parent block in a child block.
- **The "Full Path" Rule**: The test's intent should be clear when reading the nested breadcrumbs (e.g., Resource > Name > On missing technician > should be
  null).

## 5. Phrasing & Conditional Logic

- **Names are claims**: a stranger must be able to check the name against the subject, and read off the regression it guards against — e.g.
  `should("log the duration of an ended stream as text")`.
- **Favor "on" over "if"**: Use "on [state/event]" for triggers (e.g., `on missing foo` instead of `if foo is missing`).
- **Time Dimension**: Only use "when" or "if" if the condition implies a temporal sequence or complex logic that "on" cannot represent.
- **Direct Outcomes**: The final leaf node should focus strictly on the result/assertion (e.g., `should be null`, `it returns 200`).

## 6. Assertion Structure

Assertions must target the **immediate return value** of the action under test. Never chain the action call with assertions — store the result first.

- **Single assertion**: call the matcher directly on the result.
- **Multiple assertions**: use `result should { it ... ; it ... }` to group them.
- **Transformations** needed to express the assertion belong in the THEN, not in a separate intermediate variable that shadows the action step. A local variable for a long transformation chain is fine as long as it lives in the THEN section, after the result is captured.

```kotlin
// ❌ Bad — action and assertion chained, WHEN/THEN boundary invisible
myObject.transform().parse().has("key") shouldBe false

// ✅ Good — single assertion directly on result
val result = myObject.transform()
result.shouldNotContainJsonKey("key")

// ✅ Good — multiple assertions grouped
val result = myObject.transform()
result should {
    it shouldContain "\n"
    it shouldContain "  "
}

// ✅ Good — transformation is part of THEN, not a second WHEN
val result = myObject.transform()
val keys = result.parse().fieldNames().asSequence().toList()
keys shouldBe listOf("a", "b", "c")
```

Prefer expressive matchers over manual boolean extraction (`shouldNotContainJsonKey` over `.has("key") shouldBe false`).

## 7. File Layout: tests first, helpers last

A reader opens a test file to learn what the code does. The test cases answer that; fixtures, builders and custom matchers don't. Put the test cases at the
top and the infrastructure below them.

- **Tests first**: the top-level spec/class/`describe` starts right after imports and whatever declarations the language requires (package line, class
  header). No helper definitions above it.
- **Helpers last**: private helper functions, test data builders, fakes, custom matchers and constants go after the last test — at the bottom of the file, or
  as private members at the bottom of the test class.
- **Same rule inside a block**: a helper that only one `context`/`describe` needs lives at the end of that block, after its tests.
- **Extract when helpers dominate**: if the infrastructure grows larger than the tests, move it to a sibling fixtures file (e.g. `FooTestFixtures.kt`,
  `__fixtures__/foo.ts`) instead of letting it push the tests down.

Declaration order is about readability, not evaluation order. In JS/TS, helpers called from inside `it`/`beforeEach` callbacks can be `const` at the bottom
because the callbacks run later; anything evaluated while `describe` blocks are being registered must be a hoisted `function` or placed above. In Kotlin,
top-level and member functions can be referenced from anywhere in the file. Pick whichever declaration form the language or framework idiomatically offers
that lets the helper sit below its use.

```kotlin
// ❌ Bad — fixtures before the first test
private fun technician(name: String = "Ada") = Technician(/* ... */)
private fun resourceFor(technician: Technician?) = Resource(/* ... */)

class ResourceTest : ShouldSpec({
    context("name") { /* ... */ }
})

// ✅ Good — tests first, fixtures below
class ResourceTest : ShouldSpec({
    context("name") { /* ... */ }
})

private fun technician(name: String = "Ada") = Technician(/* ... */)
private fun resourceFor(technician: Technician?) = Resource(/* ... */)
```

## 8. Comments: exceptional

Tests typically carry no comments. Expressiveness lives in names, nesting and assertions; a test that needs a comment to be understood needs a more
readable implementation first. See [documentation.md](documentation.md) for the general rule.

- **No KDoc** on test classes or test helpers. A helper whose name cannot carry its meaning gets a better name first.
- **The rare exception** is knowledge the test itself cannot express: a corner case that is hard to see from the implementation, or the result of research
  worth keeping — e.g. the upstream bug a test works around.

## 9. Framework Adaptability

Adapt the syntax to the project's specific framework while maintaining the hierarchical philosophy:

- **Kotest (ShouldSpec)**: Use `context(...)` for nesting and `should(...)` for assertions.
- **Jest/RSpec/Mocha**: Use `describe(...)` for subjects, `context(...)` for states, and `it(...)` for assertions.
- **JUnit 5**: Use `@Nested` classes with `@DisplayName`.

## 10. Examples

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

## 11. Framework pitfalls

- **mockk and Kotlin value classes**: arguments arrive erased at the call boundary, so `firstArg<MyValueClass>()` throws `ClassCastException`. Read the
  underlying type and re-wrap: `MyValueClass(firstArg<UUID>())`.
