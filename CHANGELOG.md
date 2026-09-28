# Changelog

## Unreleased

- Add a Frank-Wolfe implementation and deterministic curvature-based `O(1/k)` simplex check.

- Add a conjugate-gradient implementation and deterministic check of its classical SPD A-norm convergence envelope.
- Add public-maintenance metadata, issue/PR templates, Dependabot configuration, and release guidance.

## 0.1.0

- Initial public release.
- Deterministic exact-solvable benchmark problems.
- Gradient descent and Nesterov acceleration checks.
- Polyak heavy-ball quadratic contraction check.
- ISTA/FISTA and a Beck--Teboulle FISTA bound check.
- CLI, tests, references, and CI.
