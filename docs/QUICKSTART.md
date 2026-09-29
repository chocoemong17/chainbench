# A complete first run

ChainBench is a local NumPy tool for small experiments, not a production solver. This walkthrough uses only public algorithms and an exact, deterministic quadratic.

For question-led bilingual pages, one-factor comparisons and saved-result replay,
see [the v0.4.0 workflow guide](LEARNING_WORKFLOWS.md). This page retains the
small hand-checkable Python example and the original fixed-check walkthrough.

## Install the released version

Download `chainbench-0.4.0-py3-none-any.whl` from the repository's `v0.4.0` GitHub prerelease into your working folder. With Python 3.10 or newer:

```bash
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS. On Windows PowerShell use `.venv\Scripts\Activate.ps1`. Alternatively, run `.venv\Scripts\python.exe` directly without changing your PowerShell execution policy.

```bash
python -m pip install ./chainbench-0.4.0-py3-none-any.whl
python -m pip check
python -m chainbench --version
python -m chainbench report --format html --output report.html
python -m chainbench check all
python -m chainbench report --format json --output results.json
```

Open `report.html` in your browser to see each selected result, its plotted evidence
and limitations. All content is local and static; links to sources are optional.

The default suite has seven `CONSISTENT` conditions and one `INFO` observation. `INFO` is not a failed test and not a proof of relative performance. Exit 0 means the suite's quantitative conditions passed; exit 1 means at least one was inconsistent; exit 2 reports invalid input, missing evidence or an output error. Existing output files require an explicit `--force` to overwrite.

Pip may download NumPy during installation. Once installed, running ChainBench itself requires neither a network connection nor an API key. The wheel and sdist are published here, not on PyPI.

## Reproduce a small calculation in Python

```python
import numpy as np
from chainbench import QuadraticProblem, conjugate_gradient

Q = np.array([[4.0, 1.0], [1.0, 3.0]])
x_star = np.array([1.0, 7.0]) / 11
problem = QuadraticProblem(Q, np.array([1.0, 2.0]), x_star)
trace = conjugate_gradient(problem, steps=8)
print(trace.iterates[-1])   # approximately [0.09090909, 0.63636364]
print(trace.termination)    # converged
print(trace.residual_norm)  # actual ||b - Q @ x||, close to zero
```

A returned `Trace` alone is not a promise that the requested tolerance was reached. In CG, `termination` is `converged` or `max_steps`; a zero/short iteration budget may produce the latter. Other fixed-budget methods leave this field as `None` because they do not implement a tolerance-based stopping rule.

CG uses `max(atol, rtol * ||b-Q*x0||)` as its stopping tolerance. The relative reference is the **initial residual**, not necessarily `||b||` for a nonzero initial guess. A small residual is not by itself a small forward error on an ill-conditioned problem. See [SOURCE_MAP.md](SOURCE_MAP.md) for the bound and numerical assumptions.

### Constructing a quadratic from a lower-precision reference

The three-argument `QuadraticProblem(Q, b, x_star)` treats `x_star` as an exact
reference for the stored float64 problem. It therefore checks `Q @ x_star == b`
at strict float64-relative precision. If `b` was first computed in float32,
rounding in that earlier matrix-vector product can make an otherwise sensible
input fail this exact-reference contract after promotion.

When `b` is *defined* by a reference point, use the explicit factory instead:

```python
Q32 = np.diag(np.geomspace(0.1, 1.0, 12).astype(np.float32))
x32 = np.linspace(-1, 1, 12, dtype=np.float32)
problem = QuadraticProblem.from_reference(Q32, x32)
```

The factory promotes `Q` and `x_star` to float64 first and then computes `b`,
so the stored reference remains stationary for the stored problem. It does not
silently relax the constructor's check. If an independently supplied `b` is part
of the data you intend to preserve, keep using the three-argument constructor and
treat a mismatch as input inconsistency rather than auto-correcting it.

## Inspect trajectories without cloning source

The installed wheel now includes the configurable experiment commands:

```bash
python -m chainbench preset quadratic --output config.json
python -m chainbench experiment --config config.json --output experiment.json
python -m chainbench experiment --config config.json --format markdown --output experiment.md
```

Open `config.json`, change `steps` or `problem.condition_number`, and rerun with a
new output filename. To try a different objective family:

```bash
python -m chainbench experiment --preset diagonal-lasso --format csv --output lasso.csv
python -m chainbench experiment --preset simplex --format markdown --output simplex.md
```

The JSON result embeds your resolved settings, Python/NumPy/ChainBench versions,
configuration/input fingerprints and every iterate's metrics. Coordinate vectors
can be included with `include_iterates: true` in the config. The CSV retains the
metadata with every row; termination is recorded only on each method's final row.

For quadratic experiments the stationarity metric is the true gradient norm; for
LASSO it is the proximal-gradient mapping norm; for simplex it is the Frank–Wolfe
gap. Do not compare these different quantities as if they were the same norm.
`budget_complete` is not a convergence certificate. CG may stop early or report
`max_steps`, both of which are valid observations rather than failures to run.

This is not a timing or equal-oracle-cost benchmark. See [EXPERIMENTS.md](EXPERIMENTS.md)
for a complete small config, allowed fields, limits and hash interpretation. The
older `examples/compare_quadratic.py` remains available in the source distribution
for readers who prefer a short standalone script.

## Troubleshooting

A `ModuleNotFoundError` usually means the interpreter used to run the program is not the one into which pip installed it; use `python -m pip` and `python -m chainbench` from the same virtual environment. An output-file error is intentional overwrite protection or an unavailable destination; choose a new file or explicitly use `--force`.

For an unexpected numerical failure, record the package version, Python/NumPy versions, exact inputs and complete error text in a bug report. Do not upload private data or unpublished work. Extreme scales outside floating-point representability remain unsupported; the new regression cases are not an arbitrary-precision guarantee.
