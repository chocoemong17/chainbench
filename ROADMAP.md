## After v0.5.0: published examples before algorithm counts

- Tight-GD now resolves its shrinking quadratic centre, exposes every actual
  step and constant gradient, and explains the algebraic attainment separately
  from the class-wide bound. See [source and scope](docs/GD_TIGHT_CASE.md).

- The development-source `tour` command connects these reports through one offline
  reading path, with explicit evidence levels, all seeded cases and file hashes.
  See [the bounded bundle](docs/OFFLINE_TOUR.md).
- Implemented on the development branch: exact-setup numerical reproduction of
  Shewchuk Figures 8 and 30, linked geometry/energy views, and every start in a declared
  nine-point grid. See [the source and scope](docs/SHEWCHUK_REPRODUCTION.md).
- Implemented on the development branch: Frank–Wolfe simplex/oracle movement,
  explicitly tied to Jaggi Algorithm 1, with all twelve target/start cases. See the
  [geometry and certificate contract](docs/SIMPLEX_GEOMETRY.md).
- Implemented on the development branch: inspectable individual and nearest-rank
  cases, four dimensions, quadratic orientations/starts, actual input arrays, and
  explicit unresolved ratios. See [sampler v2](docs/STRESS_SAMPLING.md).
- Implemented on the development branch: ISTA/FISTA composite contours and 3D
  heights, extrapolation/gradient/shrinkage inspection, and all nine lambda/start
  cases. See [proximal geometry](docs/PROXIMAL_GEOMETRY.md).
- Implemented in development: the noiseless 64×64 ISTA/FISTA subset of Figure 5,
  using the attributed public procedural image, explicit operator and lambda=0
  coordinate equivalence. See [source differences](docs/FISTA_DEBLURRING.md).
  The noisy 256×256 experiment remains deferred; its exact noise draw is unspecified.
- Implemented on the development branch: symbolic update flows for all eight
  topics, an operation/state comparison and linked method relationships. Historical
  attribution is separated from mathematical specialization and measured evidence.
- The new commands are not yet a release; previous tags/assets remain unchanged.
- Canonical `learn`/`report`/`plot` views now retain their computation-derived
  inputs and settings too; see [the instance contract](docs/CANONICAL_CONTEXT.md).

## v0.5.0: evidence breadth and geometry

- Label the first paper plot as a canonical illustration rather than representative evidence.
- Run reproducible multi-instance stress for all eight bundled topics.
- Show five quadratic methods on the same contour map, 3D surface and convergence chart.
- Deepen the bilingual paper atlas with motivation, strengths, trade-offs and method relationships.
- Keep tight/worst-case language reserved for public extremal constructions.

# Roadmap and priorities

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
