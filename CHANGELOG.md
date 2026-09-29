# Changelog

## 0.1.1 - 2026-09-29

- Fix false CG stopping at extreme global scales; expose true residual and termination reason.
- Enforce scale-relative quadratic references and safe symmetrization.
- Reject missing observations, invalid bound samples and empty evidence suites.
- Bind published artifacts to their actual install hashes and source commit; guard pre-existing tags and failure responses.
- Add independent recurrence, negative-path and four targeted mutation checks.
- Add a tested, configurable trajectory example and end-to-end quickstart.

## 0.1.0 - initial alpha

- Independent implementations of gradient descent, smooth FISTA/Nesterov-style acceleration, Polyak heavy-ball, conjugate gradient, Frank-Wolfe, exact quadratic proximal point, ISTA and FISTA.
- Seven quantitative consistency conditions and one informational same-budget comparison on exact-solvable deterministic fixtures.
- Correct source-to-recurrence mapping, including the historical Nesterov CLI name, Shewchuk's explicit CG bound, and the scope of quadratic PPA and empirical heavy-ball checks.
- Finite-input, dimension, iteration-budget and parameter validation; read-only copied problem data; cached quadratic spectrum; scale-aware CG stopping.
- Stable objective-gap formulas and explicit rejection of non-finite check results.
- Markdown, CSV and strict JSON export, module execution, version output, protected output files and clean error exit codes.
- Regression tests for invalid inputs, rotated SPD matrices, condition numbers, regularizers, proximal optimality equations and near-optimal gaps.
- Ubuntu Python 3.10-3.12, Windows/macOS Python 3.12 and minimum NumPy/pytest/Ruff validation; separate clean wheel and sdist installation.
- Main-only gated GitHub prerelease workflow with verified distribution uploads and SHA256SUMS. No external registry publication or paid API usage.
- Public contribution, methodology, source mapping, issue/PR, security and release documentation; complete MIT license.
