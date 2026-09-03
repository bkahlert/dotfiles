# Test Naming & Structure

## 1. Specificity via Nesting

Achieve test specificity through hierarchical nesting rather than long BDD descriptions. Each level should add a single layer of context.

- **Concise Strings**: Keep individual descriptions brief.
- **No Redundancy**: Do not repeat words from a parent block in a child block.
- **The "Full Path" Rule**: The test's intent should be clear when reading the nested breadcrumbs (e.g., Resource > Name > On missing technician > should be
  null).

## 2. Phrasing & Conditional Logic

- **Favor "on" over "if"**: Use "on [state/event]" for triggers (e.g., `on missing foo` instead of `if foo is missing`).
- **Time Dimension**: Only use "when" or "if" if the condition implies a temporal sequence or complex logic that "on" cannot represent.
- **Direct Outcomes**: The final leaf node should focus strictly on the result/assertion (e.g., `should be null`, `it returns 200`).

## 3. Assertion Structure

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

## 4. File Layout: tests first, helpers last

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
top-level and member functions can be referenced from anywhere in the file.

```kotlin
// ❌ Bad — fixtures before the first test
private fun technician(name: String = "Ada") = Technician(...)
private fun resourceFor(technician: Technician?) = Resource(...)

class ResourceTest : ShouldSpec({
    context("name") { ... }
})

// ✅ Good — tests first, fixtures below
class ResourceTest : ShouldSpec({
    context("name") { ... }
})

private fun technician(name: String = "Ada") = Technician(...)
private fun resourceFor(technician: Technician?) = Resource(...)
```

## 5. Framework Adaptability

Adapt the syntax to the project's specific framework while maintaining the hierarchical philosophy:

- **Kotest (ShouldSpec)**: Use `context(...)` for nesting and `should(...)` for assertions.
- **Jest/RSpec/Mocha**: Use `describe(...)` for subjects, `context(...)` for states, and `it(...)` for assertions.
- **JUnit 5**: Use `@Nested` classes with `@DisplayName`.

## 6. Examples

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
