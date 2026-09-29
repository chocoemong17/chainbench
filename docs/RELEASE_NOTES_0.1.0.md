# ChainBench v0.1.0 — experimental alpha

A small, independently implemented toolkit for numerical consistency experiments from public optimization literature. This release is for reproducibility and education, not production optimization or theorem certification.

## What is included

Seven quantitative conditions cover gradient descent, smooth fixed-L FISTA/Nesterov-style acceleration, heavy-ball's empirical quadratic tail, conjugate gradient, Frank-Wolfe, quadratic proximal point and composite FISTA. An eighth experiment reports ISTA versus FISTA as informational data, not a universal dominance claim.

Deterministic fixtures have exact reference solutions. Stable gap formulas, finite-input validation, read-only problem data and scale-aware CG stopping make failures easier to diagnose. The CLI supports Markdown, CSV and JSON reports, `python -m chainbench`, version output and overwrite protection.

## Validation and artifacts

The release workflow gates publication on the cross-platform and minimum-runtime-dependency test matrix, then independently installs both distribution formats in clean environments outside the source checkout. See the attached `verification.json`, `build-environment.txt` and `SHA256SUMS` for the actual install/check results, environment and file digests. Uploaded assets are downloaded and hash-compared before publishing.

Install the attached wheel with:

```bash
python -m pip install ./chainbench-0.1.0-py3-none-any.whl
chainbench check all
```

The sdist can be installed with pip too. No PyPI release or API key is required.

## Important interpretation notes

The `nesterov-1983` CLI name is historical; the implementation is smooth fixed-L FISTA. Heavy-ball's 8% finite-tail tolerance is empirical, not a theorem constant. CG's bound is explicitly sourced to Shewchuk equation (52). PPA is a direct quadratic specialization. FISTA is demonstrated on diagonal LASSO, not on an original paper's full dataset. See `docs/SOURCE_MAP.md` for assumptions and formulas.

Only public published research and independent implementation code are included. Maintainer: `chocoemong17`. License: MIT.
