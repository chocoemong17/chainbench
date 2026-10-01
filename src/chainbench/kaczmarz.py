"""Strohmer–Vershynin's expectation-bound attainment, with every declared trial."""

from __future__ import annotations

import hashlib
import json
import platform

import numpy as np

from . import __version__
from ._kaczmarz_proof import conditional_projections

SOURCE = "https://arxiv.org/pdf/math/0702226v1"
# All rows are unit coordinate vectors, ordered in contiguous direction blocks.
CASES = (
    ("cube", (1, 1, 1), (1, 1, 1)),
    ("half", (1, 1), (1, 0)),
    ("one-in-eight", (1, 7), (1, 0)),
    ("one-in-thirty-two", (1, 31), (1, 0)),
    ("three-directions", (2, 5, 5), (1, 0, 0)),
    ("eight-directions", (2, 9, 9, 9, 9, 9, 9, 8), (1, 0, 0, 0, 0, 0, 0, 0)),
)


def run_kaczmarz(steps: int = 40, trials: int = 64) -> dict:
    if type(steps) is not int or not 1 <= steps <= 160:
        raise ValueError("steps must be an integer between 1 and 160")
    if type(trials) is not int or not 1 <= trials <= 128:
        raise ValueError("trials must be an integer between 1 and 128")
    cases = []
    for name, counts, initial in CASES:
        n, m = len(counts), sum(counts)
        a = np.repeat(np.eye(n), counts, axis=0)
        b, start = np.zeros(m), np.array(initial, dtype=float)
        norm2 = np.einsum("ij,ij->i", a, a)
        probabilities = norm2 / norm2.sum()
        inputs = dict(A=a.tolist(), b=b.tolist(), start=start.tolist(), solution=[0.] * n,
                      row_norm_squared=norm2.tolist(), row_probabilities=probabilities.tolist(),
                      direction_counts=list(counts), dimension=n, equations=m)
        runs = []
        for seed in range(trials):
            rng = np.random.Generator(np.random.PCG64(seed))
            choices = rng.choice(m, size=steps, replace=True, p=probabilities)
            points, x = [start.tolist()], start.copy()
            for index in choices:
                # Eq. (4), evaluated even after the solution is reached.
                x = x + (b[index] - a[index] @ x) / norm2[index] * a[index]
                if not np.all(np.isfinite(x)):
                    raise FloatingPointError("nonfinite randomized projection")
                points.append(x.tolist())
            errors = [float(np.dot(p, p)) for p in points]
            runs.append(dict(seed=seed, row_indices=choices.tolist(), iterates=points,
                             squared_errors=errors,
                             first_zero=next((k for k, v in enumerate(errors) if v == 0), None)))
        r = min(counts)
        initial_error = float(start @ start)
        # For these source constructions the bound is an exact expectation.
        exact = [initial_error * ((m - r) / m) ** k for k in range(steps + 1)]
        values = np.array([run["squared_errors"] for run in runs])
        histogram = [sum(run["first_zero"] == k for run in runs) for k in range(steps + 1)]
        cases.append(dict(
            id=name, inputs=inputs,
            input_sha256=hashlib.sha256(json.dumps(inputs, sort_keys=True,
                                                  separators=(",", ":")).encode()).hexdigest(),
            scaled_condition_squared=m / r, spectral_condition_squared=max(counts) / r,
            contraction_numerator=m-r, contraction_denominator=m,
            exact_expectation=exact, theorem_upper=exact.copy(), runs=runs,
            empirical_mean=values.mean(axis=0).tolist(),
            zero_counts=np.count_nonzero(values == 0, axis=0).tolist(),
            first_zero_counts=histogram,
            unresolved_trials=sum(run["first_zero"] is None for run in runs),
            updates=steps, termination="fixed_budget_including_after_zero",
            conditional_projection=conditional_projections(inputs, runs),
        ))
    return dict(
        kind="chainbench.kaczmarz-expectation", schema_version=1,
        parameters=dict(steps=steps, trials=trials, seeds=list(range(trials)),
                        generator="NumPy Generator(PCG64(seed)); choice with replacement and p",
                        coupling="same seeds across cases; do not pool cases as independent trials"),
        source=dict(url=SOURCE, doi="https://doi.org/10.1007/s00041-008-9030-4",
                    version="arXiv:math/0702226v1 (2007), journal issue 2009",
                    algorithm="Algorithm 1 / Eq. (4), printed/PDF page 4",
                    theorem="Theorem 2 / Eq. (5), printed/PDF page 4",
                    attainment="Section 3.2, printed/PDF page 9",
                    note="Section 3.2's last display prints x_0 on the left; use error to solution x=0, consistent with Theorem 2 and the preceding construction."),
        scope="Published expectation attainment, not a per-trajectory guarantee; sizes, seeds and visuals are added illustrations, not original experimental data.",
        environment=dict(chainbench=__version__, python=platform.python_version(), numpy=np.__version__),
        cases=cases,
    )
