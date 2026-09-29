# A complete first run

ChainBench is a local NumPy tool for small experiments, not a production solver. This walkthrough uses only public algorithms and an exact, deterministic quadratic.

## Install the released version

Download `chainbench-0.1.1-py3-none-any.whl` from the repository's `v0.1.1` GitHub prerelease into your working folder. With Python 3.10 or newer:

```bash
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS. On Windows PowerShell use `.venv\Scripts\Activate.ps1`. Alternatively, run `.venv\Scripts\python.exe` directly without changing your PowerShell execution policy.

```bash
python -m pip install ./chainbench-0.1.1-py3-none-any.whl
python -m pip check
python -m chainbench --version
python -m chainbench check all
python -m chainbench report --format json --output results.json
```

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

## Inspect trajectories, not just pass/fail

For the example script, obtain a source checkout (examples are included in the sdist but not in the runtime wheel):

```bash
git clone --branch v0.1.1 --depth 1 https://github.com/chocoemong17/chainbench.git
cd chainbench
python -m pip install .
python examples/compare_quadratic.py --dim 12 --condition 10 --steps 20
```

The example writes CSV to standard output, with method, iteration, analytical gap, true residual norm and CG termination. The termination label is populated only on the final row of that run; earlier iterates are not labeled as converged. Change `--condition` or `--steps` to inspect a different deterministic experiment. It uses a fixed Householder rotation, so it exercises non-diagonal matrix products without randomness.

This is not a timing benchmark or an equal-oracle-cost competition: CG may terminate early and its stopping check uses an additional matrix-vector product. Equal iteration budgets do not imply equal computation costs. Do not interpret one CSV as a universal algorithm ranking.

## Troubleshooting

A `ModuleNotFoundError` usually means the interpreter used to run the program is not the one into which pip installed it; use `python -m pip` and `python -m chainbench` from the same virtual environment. An output-file error is intentional overwrite protection or an unavailable destination; choose a new file or explicitly use `--force`.

For an unexpected numerical failure, record the package version, Python/NumPy versions, exact inputs and complete error text in a bug report. Do not upload private data or unpublished work. Extreme scales outside floating-point representability remain unsupported; the new regression cases are not an arbitrary-precision guarantee.
