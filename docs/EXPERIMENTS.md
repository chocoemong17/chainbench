# Configurable experiments (schema 1)

The installed `experiment` command runs the existing algorithms on small synthetic
problems. It is separate from `check all`: experiments report observations without
inventing a theorem pass/fail criterion for each new configuration.

## Run without a source checkout

After installing the release wheel or sdist:

```bash
python -m chainbench experiment --preset quadratic --format markdown --output quadratic.md
python -m chainbench experiment --preset diagonal-lasso --output lasso.json
python -m chainbench experiment --preset simplex --format csv --output simplex.csv
```

Preset definitions are part of the installed Python package, not files that require
cloning the repository. Running experiments makes no network requests. Pip may need
the network to install the package and NumPy initially.

## Choose parameters directly from the command line

You do not need to edit JSON for common changes:

```bash
python -m chainbench experiment --preset quadratic \
  --dimension 20 --condition-number 100 --L 2 --steps 50 \
  --methods gd smooth-fista cg --format html --output custom.html
```

Problem-specific options fail explicitly when used with the wrong family. The
quadratic preset accepts `--condition-number`, `--L`/ `--smoothness`, and
`--rotation householder|none`; diagonal LASSO accepts `--lam`. All families
accept `--dimension`, `--steps`, `--methods`, and `--include-iterates`.

For exploratory sampling of the **supported preset parameters**:

```bash
python -m chainbench preset quadratic --random-seed 17 --output sampled.json
python -m chainbench experiment --config sampled.json --format html --output sampled.html
```

The seed is a convenience for generating a config. The fully resolved JSON is the
reproducibility record, so save it. Random sampling chooses among the existing
synthetic parameterization; it does not load arbitrary data, generate a certified
worst case, or establish that a sampled instance is hard. Explicit CLI overrides
win over sampled values. To avoid ambiguous provenance, overrides cannot be mixed
with `--config`.

## Change a configuration and run it again

```bash
python -m chainbench preset quadratic --output config.json
```

Edit the generated JSON in a text editor. For example, this **complete** config runs
three methods on a six-dimensional diagonal quadratic:

```json
{
  "schema_version": 1,
  "problem": {
    "kind": "quadratic",
    "dimension": 6,
    "condition_number": 20,
    "L": 1,
    "rotation": "none"
  },
  "methods": ["gd", "smooth-fista", "cg"],
  "steps": 12,
  "include_iterates": true
}
```

Then:

```bash
python -m chainbench experiment --config config.json --output experiment.json
python -m chainbench experiment --config config.json --format csv --output trajectory.csv
```

When removing a method from a *generated* configuration, also remove its entry from
`method_options` (if present). Unused options are errors, not silently ignored.
Existing output files require `--force`; a configuration cannot be overwritten by
its own output, even with that option. Report files are **not** config files: the
JSON report's `config` member is the reusable configuration.

## Configuration fields

All configurations require `schema_version: 1` and a `problem` object with `kind`.
Unknown keys, duplicate JSON keys, NaN/Infinity, incompatible or duplicate methods,
and unused method options are rejected. The JSON file is limited to 16,384 UTF-8
bytes. There is no expression evaluation, module loading or URL/file-based dataset
loading. Arbitrary matrices are still available through the existing Python API;
this CLI does not pretend to be a general data-import format.

| Field | Default and allowed values |
|---|---|
| `problem.kind` | Required: `quadratic`, `diagonal-lasso`, or `simplex` |
| `problem.dimension` | 12; integer 2–256 |
| `steps` | 30; integer 0–2000, counting completed algorithm updates |
| `methods` | All compatible methods in the order listed below; a nonempty list |
| `include_iterates` | `false`; set `true` to retain the coordinate vectors too |
| `method_options` | Optional settings for selected CG/PPA methods only |

**Quadratic:** methods `gd`, `smooth-fista`, `heavy-ball`, `cg`, `proximal-point`.
`condition_number` defaults to 10 (range 1–1e6); `L` defaults to 1 (1e-6–1e6).
`rotation` is `householder` (default) or `none`. Eigenvalues are geometrically
spaced from L/condition_number to L, and the reference solution is evenly spaced
from -1 to 1. A fixed Householder reflection mixes the coordinates when selected;
it is not a randomly sampled rotation. The actual measured L and mu are reported,
so floating-point differences from the requested values are visible.

**Diagonal LASSO:** methods `ista`, `fista`. `lam` defaults to 0.12 (range 0–1000).
The design and response use the deterministic formulas in `diagonal_lasso`;
the reference is the coordinatewise soft-threshold solution. This is not a
real-world sparse regression or original image-deblurring dataset.

**Simplex:** method `frank-wolfe`. The target is the uniform probability vector;
the starting point is the first vertex. Other problem families start at zero.

CG options are `rtol` (default 1e-12, range 0–1) and `atol` (0, range 0–1e6).
PPA's `proximal_parameter` defaults to 1 (range 1e-6–1e6). For example:

```json
{"cg": {"rtol": 1e-10, "atol": 0}, "proximal-point": {"proximal_parameter": 2}}
```

This is the value of `method_options`, not an entire configuration. Parameters not
specified in a partial config are resolved in its exported `config`.

### Work limits

The interface rejects a conservative work proxy above 100 million before allocating
matrices: max(steps,1) times dimension-squared (quadratic) or dimension (other
families) times the number of methods, plus dimension-cubed setup for quadratics
and steps times dimension-cubed for PPA. These are safeguards against accidentally
large examples, **not** exact operation counts, time limits or a sandbox for
hostile workloads. The underlying Python methods are not subject to this UI limit.

## Reading the results

JSON is the full machine-readable envelope. CSV carries the normalized config,
configuration/input hashes and environment columns with each trajectory row;
Markdown contains the config, environment, final observations and every trajectory.
Only the final CSV row of each method has its run-level termination label.

| Quantity | Meaning |
|---|---|
| `gap` | Analytical objective error relative to the fixture's reference solution |
| `distance_to_reference` | Euclidean distance to that reference, not a residual |
| Quadratic stationarity | Norm of the true gradient Qx-b |
| LASSO stationarity | Norm of the proximal-gradient mapping L[x-prox(x-grad/L)] |
| Simplex stationarity | Frank–Wolfe dual gap grad(x)·(x-oracle(grad(x))) |

These stationarity quantities are **not interchangeable across problem families**.
Small floating roundoff (down to -1e-12) in the simplex dual gap is clamped to zero;
more negative values and all non-finite measurements cause an error. `gap` is not
clipped to conceal invalid values.

CG's `converged` means its recomputed residual met
`max(atol, rtol * initial_residual_norm)`; `max_steps` means it did not.
`budget_complete` for other methods means the requested updates ran, **not** that a
stopping tolerance or a theorem was satisfied. An experiment returns exit 0 if it
completed and serialized valid observations; it may correctly contain `max_steps`.
Invalid configs, numerical failures and output errors return exit 2. The existing
`check`/`report` commands retain their separate 0/1/2 consistency-check meanings.

Equal iteration budgets are not equal compute budgets. CG rechecks its residual
with an extra matrix-vector product, PPA solves a linear system per update, and
spectral/fixture setup occurs outside the iteration count. There is no speed
leaderboard, universal ranking or theorem certificate in these reports.

## Provenance and reproducibility

`config_sha256` hashes canonical, normalized JSON (sorted keys, compact separators,
UTF-8). Key ordering and equivalent default values do not change it. This is a
fingerprint of the settings, **not** a digital signature, a proof of execution or
protection against an author fabricating a report.

`fixture.input_sha256` hashes the actual generated inputs as little-endian float64
C-order arrays, prefixed by canonical name/shape headers. The fixture definition
identifier is `chainbench.deterministic.v1`. Different numerical-library builds can
produce different input bytes from the same formulas, especially after rotation.
The config hash lets you identify equivalent settings; the input-byte hash lets
you detect such representation differences. Neither promises bitwise identical
results on every platform. The report records ChainBench, Python and NumPy versions
and the OS name; it does not record a hostname, account name, home directory,
working directory, environment variables or credentials. It is not a full lockfile
or an exhaustive record of BLAS/compiler settings.

## Python entry point

```python
from chainbench.experiments import preset_config, run_experiment
from chainbench.experiment_reporting import render_experiment

config = preset_config("diagonal-lasso")
config["problem"]["lam"] = 0.2
config["steps"] = 50
result = run_experiment(config)
print(render_experiment(result, "markdown"))
```

The caller's config is not mutated. `run_experiment` returns fresh JSON-serializable
data; it validates observations before returning. Renderers are intended for this
returned object, not as validators for arbitrary untrusted third-party reports.
See [SOURCE_MAP.md](SOURCE_MAP.md) for the existing methods' references and formulas.
