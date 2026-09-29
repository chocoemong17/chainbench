# Concrete use cases

ChainBench intentionally stays small: synthetic exact-reference problems make it
possible to inspect a method and its numerical evidence without introducing a
second solver as hidden ground truth. These examples describe useful workflows;
they are **not** claims that outside researchers already use the project.

## 1. Catch an implementation regression

Run the fixed public-source suite before and after changing optimization code:

```bash
python -m chainbench check all --json > before.json
# make and test your implementation change
python -m chainbench check all --json > after.json
```

A changed quantitative result is a prompt to inspect the recurrence, indexing,
fixture and cited formula. A green label is still only finite numerical evidence,
not a theorem proof.

## 2. Explore sensitivity to conditioning without editing Python

Create a deterministic quadratic config and change only the condition number:

```bash
python -m chainbench preset quadratic --output kappa10.json
python -m chainbench experiment --config kappa10.json --output kappa10-result.json
```

Duplicate the config, change `problem.condition_number` from `10` to `1000`,
choose a new output filename and rerun. Compare trajectories for GD, smooth FISTA,
heavy-ball, CG and proximal point. This is useful for seeing how a controlled
spectral change affects the recorded gaps and stationarity values.

Do **not** interpret equal iteration counts as equal computational work: CG performs
different operations from a gradient step, while proximal point solves a system.

## 3. Inspect a trajectory in a teaching or debugging session

Set `include_iterates` to `true` in a small config such as dimension 2 or 3:

```bash
python -m chainbench experiment --config tiny.json --format csv --output tiny.csv
```

The report retains the normalized config, input/configuration fingerprints,
method parameters, objective gap, stationarity measure and optional coordinates.
For a hand-checkable starting point, see the two-dimensional GD calculation in
`tests/test_experiments.py` and the recurrence tests.

## 4. Reproduce the same released experiment on another machine

Use the frozen v0.2.0 review helper rather than a development checkout:

```bash
python review.py collect --output my-review.json
python review.py summary my-review.json
```

The helper verifies that the installed code matches the published wheel and records
a fixed set of public synthetic observations. Two reports can be compared with the
documented finite tolerances. A portability or input-fingerprint difference is
reported explicitly instead of being rewritten as an unqualified match.

See `review/README.md` and issue #28 for the public feedback path. CI executions
are maintainer-controlled validation and are not counted as outside adoption.

## 5. Construct an exact-reference quadratic from float32 source arrays

The strict three-argument constructor preserves independently supplied `b` and
therefore rejects a reference that is not stationary to float64-relative precision.
If `b` is meant to be derived from a lower-precision `Q` and `x_star`, use:

```python
import numpy as np
from chainbench import QuadraticProblem

Q32 = np.diag(np.geomspace(0.1, 1.0, 12).astype(np.float32))
x32 = np.linspace(-1, 1, 12, dtype=np.float32)
problem = QuadraticProblem.from_reference(Q32, x32)
```

This promotes the inputs first and then computes the stored right-hand side. It
does not silently loosen the exact-reference check or rewrite an independently
supplied `b`.

## What these workflows do not establish

They do not show production-scale solver performance, real-dataset usefulness,
worst-case optimality, independent peer review, external adoption or universal
algorithm rankings. The project should widen its scope only when a concrete use
case can retain an independently verifiable reference quantity and a maintainable
input contract.
