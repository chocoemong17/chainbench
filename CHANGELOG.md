# Changelog

## Unreleased

- Add `tour --output NEW_DIRECTORY`: a guided offline index with actual SVG previews,
  the learning atlas, published example, both geometry views, all eight stress topics
  at seeds 0–31 and the public tight-GD case. Keep all raw records and return links.
- Stage the reports, refuse existing destinations, retain file/settings hashes in
  a manifest, and clean failed writes. Require installed tour evidence and offline
  navigation checks before publication; no browser-side solver or server is added.

- Attach computation-derived instance context to every canonical learning/report
  chart and standalone SVG: exact inputs/hash, dimension, constants, actual start,
  method parameters, budget, completed updates and stopping. Keep singular
  quadratic conditioning explicitly undefined instead of inventing a finite value.
- Recompute all canonical observations from retained inputs in tests; independently
  verify input fingerprints, first updates and reference curves in wheel/sdist smoke.

- Add bilingual symbolic update flows and a two-method operation/state comparison
  to the learning atlas. Related-method navigation clears filters; focused exports
  provide runnable commands for omitted topics. Clarify Frank–Wolfe's 1956 origin
  versus Jaggi's 2013 analysis. Symbolic maps remain separate from numeric evidence.
- Exercise comparison, keyboard navigation, filtered links, focused pages, JSON,
  narrow layouts and the no-JavaScript fallback in offline browser CI.

- Add `geometry ista-fista`: linked composite contours, 3D heights and actual
  extrapolation/gradient/soft-threshold stages over nine lambda/start combinations.
  Explain zero coordinates, the half-squared-loss convention and nonmonotone FISTA.
- Independently verify proximal stages and geometry; require installed-distribution
  evidence and exercise every case/method in offline browser CI.

- Expand stress to a versioned dimension/orientation/start design with full input
  arrays and trajectories; add per-case curves, nearest-rank cards and `stress-case`.
- Correct undefined ISTA/FISTA ratios previously replaced with zero and zero-radius
  FISTA trials previously resampled. Retain unresolved rows without success counts.
- Stress schema/sampler v2 changes the input associated with an old seed; historical
  releases and ordinary schema-1 experiment/replay data remain unchanged.

- Add `geometry frank-wolfe`: triangle, projected 3D surface, chosen oracle vertex,
  convex-combination update and gap/certificate curves for all 12 declared cases.
  Explain scheduled-step nonmonotonicity and separate objective bounds from dual gaps.
- Validate geometry samples independently in tests and installed distributions;
  exercise all case controls and JSON downloads in the offline browser CI job.

- Recompute the published 2D setup in Shewchuk (1994), Figures 8 and 30, using exact
  line-search steepest descent and existing CG. New `reproduce shewchuk-1994` exports
  bilingual offline HTML or full JSON with inputs, metrics, termination and hashes.
- Connect equal-aspect contours, projected 3D heights, energy errors and iteration
  inspection; expose all nine declared extra starts as separate controlled variations.
- Add rational/geometry/CLI regression checks and optional offline browser inspection.
  Require installed reproduction evidence for both wheel and sdist before publication.

## 0.5.0 - 2026-09-29 (experimental alpha)

- Separate four evidence layers: public literature claim, one canonical illustration,
  seeded multi-instance stress, and a published tight case when one exists.
- Add `stress` for every bundled topic. Quantitative theorem-linked checks retain their
  selected threshold, heavy-ball stays explicitly empirical, and ISTA/FISTA stays INFO-only.
- Add `landscape` for the five quadratic methods: the same numerical trajectories are
  shown on a contour map, an oblique 3D objective surface, method-specific contour panels
  and a convergence plot. The teaching problem is labelled as an illustration, not ranking evidence.
- Deepen the bilingual learning atlas with research motivation, strengths, trade-offs,
  neighboring-method comparisons, an algorithm timeline and explicit evidence labels.
- Refresh the offline visual design and keep machine-readable evidence embedded in every
  new page. No CDN, telemetry, API key or new runtime dependency is added.
- Extend wheel/sdist smoke and publication evidence to the stress and landscape workflows.


## 0.4.0 - 2026-09-29 (experimental alpha)

- Add bilingual offline learning pages and normalized bound interpretations.
- Add one-factor parameter sweeps with a shared validated work budget.
- Add strict saved-experiment replay with numeric/input/environment comparisons.
- Add the public Drori--Teboulle tight GD Huber case, with explicit scope and source.
- Extend installed wheel/sdist evidence and release gates to all four workflows.
- Preserve old releases, the eight-item suite and the historical v0.2.0 review kit.

## 0.3.0 - 2026-09-29 (experimental alpha)

- Make HTML the default fixed-suite report: overview previews, selected paper messages,
  observed/reference SVG plots, measured outcomes, limitations and linked public sources.
- Add standalone `plot <check>` SVG and configurable experiment HTML. Preserve full
  raw samples, settings and environment in expandable, machine-readable evidence.
- Add no-argument onboarding and direct preset controls for dimension, methods,
  budget and supported parameters. `--random-seed` samples supported config knobs;
  it is neither arbitrary random-data generation nor worst-case certification.
- Fix clipped five-method legends, long chart headings and valid all-zero plots.
  Logarithmic zeros are explicit baseline markers, never silently positive epsilon values.
- Bind fixed-report verdicts to the plotted samples; reject inconsistent/duplicate results.
  Distinguish finite curve shape, rate guarantees and empirical heavy-ball ratios.
- Extend clean wheel/sdist installation gates to HTML/SVG, exact visual evidence,
  direct instance controls and repeatable seeded configuration generation.
- Retain the frozen v0.2.0 review helper as a historical baseline. Previous releases
  are not overwritten. No new runtime dependency, private research or paid service.

Migration: use `report --format markdown` for the previous report default. The
`experiment` command still defaults to JSON. Public Python method APIs are unchanged.

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
