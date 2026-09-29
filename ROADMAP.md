# Roadmap and priorities

This is a small experimental alpha project. More algorithms, more commits or more
green tests are not substitutes for useful and independently reviewable behavior.

## Completed foundation

- Public-source mappings for the implemented recurrences and finite numerical checks.
- Versioned alpha distributions, cross-platform/minimum-dependency tests, clean
  installation of wheel and sdist, and artifact/commit verification before publication.
- Regressions for known false-convergence and missing-evidence counterexamples;
  four narrowly scoped fault injections, not exhaustive mutation coverage.
- Configurable installed experiments for quadratic, diagonal-LASSO and simplex
  fixtures, with portable trajectories, settings/input fingerprints and environment records.
- A no-checkout quickstart and a concrete protocol/form for external reproduction feedback.

## Next priorities after the configurable release

1. Collect and triage **actual** external installation and interpretation feedback.
   Do not substitute bot traffic or the maintainer's own tests for adoption.
2. Reduce and fix any reproducible defects before widening the supported scope.
3. Consider general dense/sparse user problems only when there is a clear use case,
   an independent reference quantity and a maintainable input/validation contract.
4. Evaluate optional trajectory plotting or report comparison after users identify
   a concrete need. Keep the runtime dependency footprint small.

No production-solver guarantee, original-paper dataset reproduction, independent
review, external adoption or support-program acceptance is implied by this roadmap.
