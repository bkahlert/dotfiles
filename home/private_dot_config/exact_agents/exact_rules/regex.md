# Regular Expression

- Avoid anonymous capturing groups.
    - Use named capture groups (e.g., `(?<name>...)`) for data you need.
    - Use non-capturing groups (e.g. `(?:...)`) for structural grouping.
    - This prevents index-based errors and makes the logic self-documenting.
