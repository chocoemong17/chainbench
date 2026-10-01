# Changelog

## Unreleased

- Add `compare` for two to four saved experiment records, with exact provenance
  retention, pairwise setup/input/environment diagnostics, bounded strict imports
  and separate panels when objectives differ. Shared-method overlays use actual
  saved samples only. Include bilingual offline reading, installed wheel/sdist
  audits, browser checks and a cloud-generated PDF review packet.
  [Contract and examples](docs/SAVED_COMPARISON.md).

The development toolkit is now integrated into `main` through [PR #73](https://github.com/chocoemong17/chainbench/pull/73).
Its [final candidate CI](https://github.com/chocoemong17/chainbench/actions/runs/36880865578)
passed all eight jobs, including 1,288 tests in each of six compatibility configurations,
clean wheel/sdist installations and offline browser checks. The failed Windows
fixture-decoding run and its UTF-8 repair remain recorded in the PR.

The complete extended tour now has 25 HTML pages and 24 numerical records,
including the later Adam, ADMM and FISTA backtracking reports. Cloud generation
also produces a checked two-page FISTA PDF. The README and reading guide link
archived PDF/geometry previews that remain readable without Actions sign-in.
The entries below describe successive implementation stages; earlier 19- and
20-page counts describe those stages, not the complete current extended tour.
The frozen v0.5.0 release remains unchanged. Later commits retain their own CI.

- Keep the complete macOS Python 3.12 gate on the standard macOS 26 Intel runner
  after the ARM64 pool failed to allocate a runner. Preserve the cancelled attempt
  and distinguish Intel validation from earlier Apple Silicon results.
- Compare independent numerical reruns with the existing canonical trajectory
  tolerance after Intel macOS exposed exact-equality assumptions. Keep provenance,
  types, counts and inputs exact; preserve same-record serialization/preview checks
  and every independent scientific validator. Add corrupt-record rejection cases.
- Stabilize CG's three scalar inner-product quantities with compensated accumulation.
  A complete Intel audit found late trajectory drift up to 4.32e-4; single-thread
  execution did not fix it. The controlled scalar-reduction replacement removed
  discrepancies beyond the existing comparison tolerance. Preserve matrix-vector
  products, true-residual stopping, exact-start behavior and mathematical bounds.
  Add cancellation, nonfinite-arithmetic and repeated-seed regressions.
  [Diagnosis, numerical changes and limits](docs/CG_ARITHMETIC.md).
- Preserve the actual recorded next objective in Frank–Wolfe segment views after
  validating its direct evaluation. A minimum-version BLAS path exposed a
  last-bit difference from reevaluation. Keep the trajectory, independent Decimal
  audit and exact stored-record identity checks unchanged; add retention and
  invalid-value regressions.

- Explain randomized Kaczmarz's conditional expectation through actual orthogonal
  error triangles and all possible row choices from each recorded input point.
  Keep candidate projections separate from sampled history, synchronize the
  completed update and retain zero-error/degenerate states. Add independent
  rational checks and full browser-state coverage.

- Extend the optional tour to twenty HTML pages with the randomized Kaczmarz
  construction, actual coordinate preview and links comparing deterministic,
  support-constrained and expected-error attainment. Retain the seventeen-page
  base and all existing numeric records. Validate new metadata/standalone parity
  while accepting prior two-extension manifests.
- Require the randomized workflow's installation result at the release gate and
  check the actual smoke-summary contract against that gate, preventing key drift.

- Add six explicit members of Strohmer–Vershynin's expected-error bound attainment
  through `case-study kaczmarz-expectation`. Show actual 3D projections, row and
  direction probabilities, all seeds and the finite batch mean. Retain every
  update after zero and unresolved trials; never test single paths against an
  expectation bound. Add rational/state validators and offline browser checks.
  Source-version notation caveat is explicit.

- Explain the same quadratic PPA updates through their shifted subproblem and
  gradient balance. Synchronize completed solves with the existing landscape
  player, retain floating residuals and native tables, and omit the panel without
  PPA. Independent numerical and browser checks cover the added explanation.


- Connect the same nine ISTA/FISTA trajectories to the minimized upper model,
  actual update slices and the distinction between current and extrapolated
  descent references. Include every stage, L1 corner and numerical value.
- Add independent model expansion, rational reference and corrupt-record checks,
  synchronized browser validation, and native tables.

- Connect every atlas topic to its experiment/geometry/stress workflows through
  question-led cards. Bind direct tour links to included artifacts and declared
  commands, provide related-lesson links, and retain standalone command fallbacks.
  Preserve calculations and 17/19-page counts.

- Connect source finite-spectrum/interval comparison polynomials to actual CG
  eigenmode errors and weighted energy in the existing Shewchuk reproduction.
  Retain absent-mode ratios as null and measured roundoff. Correct the Eq. (52)
  page locator; preserve algorithms, starts and stopping.

- Add optional `tour --extended` with the 200-update noisy Haar protocol and
  40-update Frank–Wolfe sparsity construction. Connect their actual previews and
  related reports, retain base records, validate extension metadata and require
  both tour variants in distribution evidence. The base tour remains seventeen
  HTML pages; the extended tour has nineteen.

- Repair the existing landscape comparison: consistent method colors, equal
  contour coordinate scales, numeric 3D axes, visible actual inputs/settings and
  per-method iterate/termination readouts. Retain the original numerical paths,
  validate all five methods independently, and include the comparison in the tour.

- Connect Shewchuk's ellipse-to-circle explanation to the existing SD/CG paths.
  Show their actual transformed coordinates and adjacent displacement directions,
  with Euclidean/A inner products, undefined pairs and finite-precision limits.
  Validate all observations in installed distributions and every browser state.

- Recompute Lessard–Recht–Packard's public heavy-ball counterexample with the
  existing recurrence. Connect signed iterates, objective heights and two-state
  geometry; retain every added grid start, the exact source cycle and separate
  stationarity/repetition diagnostics. Add it to the tour, atlas and installed
  evidence gate without changing the eight fixed checks.

- Connect Frank–Wolfe's exact oracle to its affine lower model and optimal-value
  bracket. Show actual vertex values, both endpoints and the dual-gap width for
  all twelve controlled cases; retain final-row evidence and verify the displays
  independently from the existing recurrence.

- Lead the README with actual image evidence, scoped geometry previews and a
  question-to-workflow map. Add a pinned development review route; distinguish its
  commands and commit from the frozen v0.5.0 release. Generate the image preview
  from validated full-budget JSON, retaining source permission and input hashes.

- Recompute the noiseless 64×64 ISTA/FISTA subset of Beck–Teboulle Figure 5,
  using a permission-preserving port of the public procedural image. Retain every
  scalar observation, declared full-precision snapshots, source differences and
  both objective/image error; do not treat source magnitudes as exact targets.
- Link the full image experiment into the offline tour with an actual reconstruction
  preview and reciprocal, scope-labelled proximal geometry links.
- Stream the existing proximal recurrence for the 10,000-step experiment while
  preserving public Trace outputs. Independently check operators, coordinates,
  installs and displayed pixels; keep long final-axis labels inside SVG bounds.

- Resolve the narrow quadratic centre of the tight-GD construction with samples
  at its exact joins and a normalized inset. Inspect every actual GD point and
  its constant gradient; explain algebraic attainment separately from the bound.
- Verify the geometry at maximum horizon and extreme allowed scales, in installed
  distributions and offline browsers. Existing recurrence and bound values stay fixed.

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
