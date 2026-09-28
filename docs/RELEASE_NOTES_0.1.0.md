# ChainBench v0.1.0

ChainBench v0.1.0 is the first public release of a small reproducibility toolkit
for classic optimization and iterative-method results.

## Included checks

- Gradient descent: standard smooth-convex `O(1/k)` objective-gap envelope.
- Nesterov acceleration (1983): smooth-convex `O(1/k^2)` objective-gap envelope.
- Polyak heavy-ball (1964): quadratic tail contraction.
- Hestenes--Stiefel conjugate gradient (1952): SPD A-norm convergence envelope.
- Frank-Wolfe / conditional gradient (Jaggi 2013): curvature-based `O(1/k)` gap envelope.
- Rockafellar proximal point (1976): strongly-convex resolvent contraction.
- Beck--Teboulle FISTA (2009): composite `O(1/k^2)` objective-gap envelope.
- ISTA/FISTA same-budget comparison on the bundled exact-solvable LASSO fixture.

## Reproducibility

The package uses deterministic, dependency-light fixtures with exact or
independently verifiable reference quantities. `chainbench check all` runs the
entire suite, while `chainbench report` exports Markdown, CSV, or JSON reports.

The checked-in `benchmarks/latest.md` snapshot is intentionally timestamp-free
so numerical changes are visible in normal source review.

## Scope

These are finite numerical consistency checks of public, published results.
They are not mathematical proofs, novelty claims, or validations of private or
unpublished research.
