# Roadmap: published examples before algorithm counts

## Current development main

[PR #73](https://github.com/chocoemong17/chainbench/pull/73) integrated the
implementation into `main` and links its actual cloud checks. The package version remains
0.5.0, but these development features are not in the frozen v0.5.0 release.
[Start with the reading guide](docs/REVIEW_GUIDE.md) for a pinned computation
snapshot, artifact downloads and specific questions to inspect.

The complete extended tour has 25 HTML pages and 24 numerical records. GitHub
Actions generates the bundle, audits its hashes and numerical evidence, and
renders a separate two-page FISTA review packet. Source stays in GitHub; full
tests, builds and browser checks run there too. The local task folder stays below
1 GB. [Cloud workflow and artifact lifetime](docs/CLOUD_WORKFLOW.md).

Implemented in the development source:

- **Published examples and their limits.** Shewchuk's original 2D CG/SD setup and
  declared added starts; Beck–Teboulle's noiseless image protocol and a separate
  noisy Haar protocol with a new noise draw; Strohmer–Vershynin's nonuniform
  Fourier sampling protocol with three new inputs. Each names its exact source,
  changed inputs and omitted scope. [Source map](docs/SOURCE_MAP.md).
- **Actual movement in space.** Linked contours, objective heights and iteration
  controls for quadratic methods, simplex oracle steps, proximal shrinkage and
  ADMM's solve/shrink/dual-memory stages. Local models, PPA subproblems and
  residuals explain computed steps. [Geometry comparison](docs/LANDSCAPE_CONTEXT.md).
- **FISTA step selection.** All 36 backtracking runs, every rejected proposal,
  carried curvature and signed objective/model difference; a guide compares them
  with the fixed-L report without equating iteration costs.
  [Exact recurrence and scope](docs/FISTA_BACKTRACKING.md).
- **Several inputs, including inconvenient ones.** All seeds 0–31 for each of
  eight stress topics, unresolved ratios, multiple starts and dimensions; all
  declared geometry cases and 18 same-condition-number CG spectral examples.
  [Sampling contract](docs/STRESS_SAMPLING.md), [CG spectra](docs/CG_SPECTRUM.md).
- **Counterexamples and sharp constructions.** Heavy-ball's published cycle,
  the source Adam/AMSGrad analysis variants and average regret, the public tight
  GD construction, sharp FW support floors and Kaczmarz expectation attainment.
  Finite paths, expectations and theorem statements remain separate.
  [Evidence levels](docs/OFFLINE_TOUR.md).
- **Connected paper explanations.** Eight bilingual atlas topics, symbolic
  process flows, operation/state comparisons and topic-specific report links.
  Return links and native tables preserve offline and no-script reading.
  [Learning paths](docs/LEARNING_WORKFLOWS.md).

The first consolidated remote run found 12 Windows UTF-8 fixture-read failures;
Linux/macOS, clean wheel/sdist installation and browser checks passed. The repair
and its follow-up run are recorded in [issue #74](https://github.com/chocoemong17/chainbench/issues/74).
The failure remains part of the record. The
[final consolidated candidate passed all eight CI jobs](https://github.com/chocoemong17/chainbench/actions/runs/36880865578),
including 1,288 tests in each of six compatibility configurations, clean wheel/sdist
installs and offline browser checks. Later commits have their own CI status.

The cloud PDF packet and updated reading route from
[issue #75](https://github.com/chocoemong17/chainbench/issues/75) are implemented.
Archived [PDF](https://github.com/chocoemong17/chainbench/blob/archive/local-reviews-20261001/cloud/33b6243/ChainBench_FISTA_review.pdf)
and [geometry previews](https://github.com/chocoemong17/chainbench/tree/archive/local-reviews-20261001/cloud/33b6243/browser-gallery)
are directly readable without installation or Actions sign-in.

## Next work, in priority order

1. Repair concrete correctness, portability or usability defects found in the
   current source; preserve all declared examples and existing validation.
2. Improve the reading route where actual use reveals a confusing step, missing
   input explanation or inaccessible comparison.
3. Use actual reader feedback to choose the next explanation or public experiment.
   Add a paper only with a precise source-to-recurrence mapping, explicit input
   differences, multiple meaningful examples and independent numerical checks.

Main, prior tags and historical review packets remain available. No acceptance,
independent review or production performance is inferred from CI results.

## v0.5.0: evidence breadth and geometry

- Label the first paper plot as a canonical illustration rather than representative evidence.
- Run reproducible multi-instance stress for all eight bundled topics.
- Show five quadratic methods on the same contour map, 3D surface and convergence chart.
- Deepen the bilingual paper atlas with motivation, strengths, trade-offs and method relationships.
- Keep tight/worst-case language reserved for public extremal constructions.

# Roadmap and priorities

The existing landscape comparison now exposes its actual input, method settings
and stopped states, uses consistent colors/equal contour scales, and is included
in the tour. [Scope and verification](docs/LANDSCAPE_CONTEXT.md).

The development Shewchuk view now explains A-conjugacy with the same computed
steps in x and square-root-metric coordinates. This extends understanding of the
existing reproduction; it does not add a method or claim preconditioner speedups.

ChainBench remains a small experimental alpha project. Useful and reviewable
behavior matters more than algorithm counts, commit counts or green test counts.

## v0.4.0: implemented in priority order

1. **Understand the selected result.** Bilingual question-led learning pages connect
   assumptions, the actual recurrence, public formulas, observed curves and limits.
   Six bound-based topics have normalized ratio plots; empirical/INFO topics do not
   masquerade as pointwise theorems.
2. **Change one condition.** Bounded one-factor sweeps retain all resolved configs,
   inputs and observations. A shared preflight work cap limits accidental large jobs.
3. **Recompute the evidence.** Saved schema-1 experiments can be replayed, with
   numerical mismatches, input fingerprints and environment changes distinguished.
4. **Show one public extremal construction.** The separate Drori--Teboulle GD case
   illustrates a matching bound and horizon-dependent Huber function under explicit
   h<=1 assumptions. It is not arbitrary-method worst-case search.

All four workflows must pass independent installed-wheel AND installed-sdist smoke
checks before publication. The existing eight checks, cross-platform/minimum-version
CI, targeted fault injections and distribution/commit integrity gates are preserved.

## Feedback that motivated this scope

The maintainer relayed seven outside reproduction/use attempts in issue #28, with
five graph requests and additional requests for clearer purpose and instance choice.
This is relayed feedback, not seven independently archived environment/run reports.
The next useful review is whether the new pages and controlled experiments address
those specific comprehension problems. Do not substitute CI or bot activity for it.

## Next decisions, not implemented claims

- Resolve concrete reproducible defects and accessibility/interpretation feedback first.
- Consider arbitrary matrix imports, sparse datasets or a local server only after a
  clear use case and safe, independently verifiable input contract are specified.
- Add another worst-case class only with an exact public theorem-to-code mapping.
- Keep honest limitations: no production guarantee, original-paper dataset benchmark,
  exhaustive testing, theorem-prover status or support-program acceptance claim.

The v0.2.0 reviewer kit remains a frozen historical comparison baseline, not the
recommended new package. All prior tags and release assets are left unchanged.
