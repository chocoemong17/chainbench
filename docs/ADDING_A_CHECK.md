# Adding a literature check

A literature check should be a small, reviewable unit that connects a public
reference to executable numerical evidence.

## Suggested workflow

1. Open a "Propose a literature check" issue and link the public reference.
2. State the exact formula, rate, residual, or qualitative prediction to test.
3. Choose a deterministic problem with an exact or independently verifiable
   reference quantity.
4. Implement the minimum algorithmic code needed for the reproduction.
5. Add a function returning a `CheckResult`.
6. Register a stable CLI slug in `CHECKS`.
7. Add focused unit tests and ensure `chainbench check all` stays green.
8. Add the bibliographic entry to `REFERENCES.md`.
9. Add a one-line description to the README table.
10. Open a pull request and explain what would make the numerical check fail.

## Naming

Paper-specific slugs normally use a recognizable author/year form, for example:

```text
nesterov-1983
beck-teboulle-2009
```

Use a descriptive baseline slug when a check is not tied to a single paper.

## Testing guidance

At minimum, test both the implementation and the literature-facing check. A
useful test suite usually contains:

- one basic algorithm-behavior test,
- one exact-solution or stationarity test for the problem fixture, and
- one assertion that the registered literature check is consistent.

Avoid tests that merely assert the current printed number. The test should
encode the mathematical relationship being reproduced.

## Pull-request notes

A good PR description names the public source, states the quantity compared,
and explains why the chosen reference value is trustworthy. Do not present a
finite experiment as a proof or add claims of novelty.
