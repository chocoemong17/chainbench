# ChainBench

[![tests](https://github.com/chocoemong17/chainbench/actions/workflows/tests.yml/badge.svg)](https://github.com/chocoemong17/chainbench/actions/workflows/tests.yml)
![status](https://img.shields.io/badge/status-alpha-informational.svg)

**Small, auditable numerical experiments for published optimization and iterative-method results.**

ChainBench implements established methods on deterministic problems with exact reference solutions. It is useful for learning, checking an implementation, and spotting numerical regressions without a solver framework. NumPy is the only runtime dependency. All computation is local: no API key, telemetry, or paid service is required.

A numerical experiment can be **consistent with** a published result; it does not prove the theorem or reproduce every experiment in the original paper. This is an experimental alpha package, not a production solver or a worst-case certification tool.

## Help review the released version

For general use, install the latest **v0.2.1** maintenance release. The
[fixed v0.2.0 review kit](review/README.md) remains a deliberately frozen historical
baseline for cross-machine comparison; it is not the latest package. The helper
never uploads data. [Report an actual success, failure or confusing step in issue #28](https://github.com/chocoemong17/chainbench/issues/28).

v0.2.1 addresses the float32 exact-reference construction usability issue found
during evaluation without loosening the strict constructor. Internal reports and CI
are maintainer-assisted evidence, not outside users or endorsements. No star or
favorable review is requested.

## Install and run

Python 3.10 or newer is required. Use a fresh virtual environment:

```bash
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS, or run
`.venv\Scripts\python.exe` directly in Windows without changing execution policy.
The release wheel can be installed without Git:

```bash
python -m pip install https://github.com/chocoemong17/chainbench/releases/download/v0.2.1/chainbench-0.2.1-py3-none-any.whl
python -m chainbench --version
python -m chainbench check all
```

Alternatively, download the wheel from [GitHub Releases](https://github.com/chocoemong17/chainbench/releases)
and install its local filename. A source checkout also works: clone this repository,
enter its folder, and run `python -m pip install .`. The `chainbench` console command
and `python -m chainbench` address the same interface.

Do not assume a package named `chainbench` on an unrelated registry is this project;
no PyPI publication is configured. For a complete first run and a hand-checkable CG
example, see [the quickstart](docs/QUICKSTART.md).

## Change settings without editing Python

The installed package contains three configurable presets. No source checkout,
API key or remote service is needed after installation:

```bash
python -m chainbench experiment --preset quadratic --format markdown --output experiment.md
python -m chainbench experiment --preset diagonal-lasso --output lasso.json
python -m chainbench preset quadratic --output config.json
python -m chainbench experiment --config config.json --format csv --output trajectory.csv
```

Edit `config.json` to change dimensions, condition numbers, iteration budgets or
compatible methods. JSON, CSV and Markdown retain the resolved settings, input and
configuration hashes, software versions and trajectories. Each problem family uses
an explicitly named stationarity metric. `budget_complete` means the requested
updates ran, not convergence; CG separately reports `converged` or `max_steps`.
Equal iteration budgets are **not** equal computational work.

See [configurable experiments](docs/EXPERIMENTS.md) for valid fields, resource limits,
output schemas and reproducibility caveats. [Concrete use cases](docs/USE_CASES.md)
show how to use the same small fixtures for regression checks, conditioning
experiments, trajectory inspection and cross-machine reproduction. These are
workflows, not claims of existing external adoption. Experiments are observations;
the separate fixed suite below checks specific published inequalities.

## Bundled consistency checks

| CLI name | Algorithm / source | Interpretation |
|---|---|---|
| `gd-baseline` | Gradient descent, step 1/L | Smooth-convex objective-gap bound |
| `nesterov-1983` | Nesterov-style acceleration, implemented as smooth fixed-L FISTA | Historical slug; **not** a literal 1983 algorithm reproduction |
| `polyak-1964` | Polyak heavy-ball on an SPD quadratic | Empirical tail estimate; the 8% tolerance is not a theorem constant |
| `hestenes-stiefel-1952` | Conjugate gradient; standard bound in Shewchuk (1994), eq. (52) | Positive-iteration A-norm error envelope |
| `jaggi-2013` | Frank-Wolfe, Jaggi Algorithm 1 / Theorem 1 | Curvature-based bound for k >= 1 |
| `rockafellar-1976` | Exact proximal point on a quadratic | Direct strongly-convex resolvent specialization |
| `beck-teboulle-2009` | Fixed-L FISTA on diagonal LASSO | Composite objective-gap bound, exact soft-threshold optimum |
| `ista-vs-fista` | Same-budget comparison on one LASSO fixture | **INFO**, not a universal algorithm ranking |

The default suite contains **seven quantitative consistency conditions and one informational comparison**. Their assumptions, formulas, indexing, public sources, and numerical limitations are documented in [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md) and [REFERENCES.md](REFERENCES.md).

## Reports

```bash
chainbench check beck-teboulle-2009
chainbench check all --json
chainbench report --format markdown --output report.md
chainbench report --format csv --output report.csv
chainbench report --format json --output report.json
```

An existing output file is protected by default; add `--force` to replace it. Exit codes are `0` for satisfied conditions (INFO is allowed), `1` for an inconsistent quantitative condition, and `2` for invalid input or an output error.

The [benchmark snapshot](benchmarks/latest.md) is generated from the package, not entered as external validation. Its numeric regression test has explicit floating-point tolerances rather than brittle byte-for-byte numeric equality.

## Python API

```python
from chainbench import gradient_descent, strongly_convex_quadratic

problem = strongly_convex_quadratic(dim=20, mu=0.1, L=1.0)
trace = gradient_descent(problem, steps=30)
print(problem.gap(trace.iterates[-1]))
```

`problem.gap` evaluates the gap directly to avoid subtracting nearly equal objective values. Inputs must be finite real arrays of the documented dimension. Problem data are copied and made read-only. The strict `QuadraticProblem(Q, b, x_star)` constructor requires the declared reference to be stationary at float64-relative precision. If `b` is conceptually derived from `Q` and `x_star` (especially when the originals are float32), use `QuadraticProblem.from_reference(Q, x_star)`; it promotes first and computes a consistent stored `b` without weakening the strict constructor. Methods preserve the caller's starting array. CG additionally reports `trace.termination` and `trace.residual_norm`; exhaustion of the iteration budget is not reported as convergence. Method iteration budgets may be zero; quantitative check budgets must be positive.

## Development and validation

```bash
python -m pip install -e '.[dev]'
ruff check .
python -m pytest
python scripts/check_mutations.py
python -m build
python scripts/smoke_install.py
```

CI covers Python 3.10-3.12 on Ubuntu, Python 3.12 on Windows/macOS, and a Python 3.10 environment with NumPy 1.24.0, pytest 8.0.0 and Ruff 0.6.0. Tests include invalid inputs, deterministic rotated SPD problems, several condition numbers and regularization parameters, near-optimal gaps, CLI errors and report formats. The package job installs **both wheel and sdist in separate clean virtual environments outside the checkout** before running their CLIs, all three experiment presets, saved-config reruns and every export format.

For an actual external reproduction attempt, see [the reviewer guide](docs/REVIEWER_GUIDE.md) and use the reproducibility feedback issue form.

See [CONTRIBUTING.md](CONTRIBUTING.md), [methodology](docs/METHODOLOGY.md), [adding a check](docs/ADDING_A_CHECK.md) and [release procedure](RELEASING.md). Contributions should improve reproducibility, clarity, or correctness; adding more algorithms is not itself a quality measure.

## Scope and license

Only public, published methods and independent implementation code belong here. No private research notes, unpublished derivations, personal identities or private datasets are needed for this project. References credit the original authors; paper PDFs and third-party code are not redistributed as part of this package.

MIT; see [LICENSE](LICENSE). Maintained under the public handle **chocoemong17**.
