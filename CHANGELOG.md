# Changelog

## 0.2.1 - 2026-09-29 (experimental alpha)

- Add `QuadraticProblem.from_reference(Q, x_star)` for the explicit case where the
  right-hand side is derived from a declared reference point. Inputs are promoted to
  float64 before `b` is computed, preserving strict stationary-reference semantics.
- Keep the three-argument `QuadraticProblem(Q, b, x_star)` constructor strict for
  independently supplied systems and make its precision-mismatch error actionable.
- Add a regression reproducing float32 matrix-vector rounding that previously caused
  a surprising constructor rejection, without weakening the exact-reference check.
- Add concrete workflows for implementation regression checks, condition-number
  sensitivity, trajectory inspection, cross-machine reproduction, and float32 input
  construction. These are documented workflows, not claims of external adoption.


## 0.2.0 - 2026-09-29 (experimental alpha)

- Add installed `preset` and `experiment` commands and the Python experiment API;
  support deterministic quadratic, diagonal-LASSO and simplex fixtures using existing methods.
- Validate versioned JSON configurations, reject ambiguous/unused fields and limit accidental work.
- Export full trajectories, method/termination semantics, normalized configs, input/configuration
  fingerprints and minimal environment metadata in JSON, CSV and Markdown.
- Exercise all presets and saved-config reruns after clean wheel AND sdist installation;
  bind that evidence to publication. Preserve the prior numerical regression/fault-injection suite.
- Add no-checkout onboarding, configuration reference, external-review protocol and feedback form.
- Keep old interfaces and prior releases; no new runtime dependency or external service is required.

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
