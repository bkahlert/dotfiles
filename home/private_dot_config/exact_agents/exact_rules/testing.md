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

## 4. Framework Adaptability

Adapt the syntax to the project's specific framework while maintaining the hierarchical philosophy:

- **Kotest (ShouldSpec)**: Use `context(...)` for nesting and `should(...)` for assertions.
- **Jest/RSpec/Mocha**: Use `describe(...)` for subjects, `context(...)` for states, and `it(...)` for assertions.
- **JUnit 5**: Use `@Nested` classes with `@DisplayName`.

## 5. Examples

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
