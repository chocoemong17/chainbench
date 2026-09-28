# Changelog

## 0.1.0 - 2026-09-28

- Initial public release of ChainBench.
- Add deterministic exact-solvable fixtures for smooth/strongly-convex quadratics, diagonal LASSO, and simplex quadratics.
- Add gradient-descent and Nesterov accelerated-gradient convergence checks.
- Add Polyak heavy-ball quadratic contraction check.
- Add Hestenes--Stiefel conjugate-gradient A-norm convergence check.
- Add Jaggi Frank-Wolfe curvature-based `O(1/k)` simplex check.
- Add Rockafellar proximal-point strongly-convex contraction check.
- Add Beck--Teboulle FISTA objective-gap check and an ISTA/FISTA same-budget comparison.
- Add deterministic Markdown, CSV, and JSON report export with a checked-in benchmark snapshot.
- Add public references, reproducibility methodology, contribution guidance, issue/PR templates, Dependabot, and release guidance.
- Test Python 3.10--3.12 in CI and build both wheel and source distributions.
