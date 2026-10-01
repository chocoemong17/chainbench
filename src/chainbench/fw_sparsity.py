"""Jaggi's published support-constrained construction, with actual FW trajectories."""

from __future__ import annotations

import hashlib
import json
import platform

import numpy as np

from . import __version__
from .methods import frank_wolfe
from .problems import SimplexQuadraticProblem

DIMENSIONS = (3, 8, 32, 128)
SOURCE = "https://proceedings.mlr.press/v28/jaggi13-supp.pdf"


def _dual_gap(x):
    # On the unit simplex this equals 2*(x@x-min(x)); termwise evaluation
    # avoids subtracting equal totals at the full-support optimum.
    return 2 * float(x @ (x - x.min()))


class _SquaredNormSimplex(SimplexQuadraticProblem):
    """Keep the existing exact simplex oracle, with the source's full scaling."""

    def value(self, x):
        return float(x @ x)

    def grad(self, x):
        return 2 * x

    def gap(self, x):
        return float(np.sum((x - self.target) ** 2))

    @property
    def f_star(self):
        return 1 / self.dim

    @property
    def curvature_upper_bound(self):
        return 4.0


def run_fw_sparsity(steps: int = 40) -> dict:
    if type(steps) is not int or not 1 <= steps <= 256:
        raise ValueError("steps must be an integer between 1 and 256")
    cases = []
    for n in DIMENSIONS:
        p = _SquaredNormSimplex(np.full(n, 1 / n))
        start = np.zeros(n)
        start[0] = 1
        trace = frank_wolfe(p, steps, start)
        rows = []
        for k, x in enumerate(trace.iterates):
            active = x > 0
            support = int(np.count_nonzero(active))
            balanced = active.astype(float) / support
            gradient = p.grad(x)
            oracle = p.linear_minimizer(gradient)
            row = dict(
                iteration=k,
                x=x.tolist(),
                support=support,
                objective=p.value(x),
                primal_gap=p.gap(x),
                gradient=gradient.tolist(),
                vertex_index=int(np.argmax(oracle)),
                dual_gap=_dual_gap(x),
                gamma=2 / (k + 2) if k < steps else None,
                support_floor=1 / support - 1 / n,
                minimum_with_support=1 / support,
                dual_support_floor=2 / support if support < n else None,
                iteration_upper=8 / (k + 2) if k >= 1 else None,
                balanced=balanced.tolist(),
                balanced_objective=p.value(balanced),
                balanced_primal_gap=p.gap(balanced),
                balanced_dual_gap=_dual_gap(balanced),
                excess_over_support_minimum=float(np.sum((x - balanced) ** 2)),
            )
            if (
                not np.all(np.isfinite(x))
                or np.any(x < 0)
                or not np.isclose(x.sum(), 1, rtol=0, atol=2e-14)
            ):
                raise FloatingPointError("invalid simplex observation")
            rows.append(row)
        construction = []
        for s in range(1, n + 1):
            x = np.zeros(n)
            x[:s] = 1 / s
            construction.append(
                dict(
                    support=s,
                    x=x.tolist(),
                    objective=p.value(x),
                    primal_gap=p.gap(x),
                    minimum=1 / s,
                    gap_floor=1 / s - 1 / n,
                    dual_gap=_dual_gap(x),
                    dual_floor=2 / s if s < n else None,
                )
            )
        inputs = dict(
            dimension=n,
            start=start.tolist(),
            optimizer=p.x_star.tolist(),
            objective="sum(x_i**2)",
            curvature=4.0,
            f_star=1 / n,
        )
        cases.append(
            dict(
                dimension=n,
                inputs=inputs,
                rows=rows,
                construction=construction,
                input_sha256=hashlib.sha256(
                    json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
                updates=steps,
                termination="fixed_budget",
            )
        )
    result = dict(
        kind="chainbench.fw-sparsity",
        schema_version=1,
        evidence_level="published-support-constrained-tight-construction",
        source=dict(
            url=SOURCE,
            location="Section 3 Lemmas 3–4, PDF p5; Appendix C, PDF p12",
            recurrence="Algorithm 1, PDF p1",
            bound="Theorem 1, PDF p4 in supplement",
            sha256="26446809e3770656d1fea7a2105f203d058b299033043e30f31ba524d8875600",
        ),
        parameters=dict(
            steps=steps,
            dimensions=list(DIMENSIONS),
            step_rule="2/(k+2)",
            oracle="basis vector at first minimum gradient coordinate",
            seed=None,
            stopping="fixed budget",
        ),
        construction="For every s=1..n, uniform weights on s coordinates attain f=1/s.",
        cases=cases,
        design="All dimensions 3,8,32,128; these dimensions and UI examples are added, not paper experiments.",
        support_definition="Exact count of positive computed coordinates; no threshold or truncation.",
        proof_identity="sum_i_on_support (x_i-1/s)^2 = sum_i x_i^2 - 1/s for sum_i x_i=1",
        limits=[
            "The public theorem supplies support-constrained extremality; finite checks are not its proof.",
            "Actual FW iterates need not attain the support floor or the iteration upper bound.",
            "Lemma 4 requires support<n; the lower-bound field is null at full support.",
            "Gamma_0=1 replaces the initial atom; iteration and support are distinct quantities.",
            "This source uses f=||x||² and Cf=4, unlike the half-loss simplex illustration.",
            "No new claim of exact worst-case FW iteration constants, representative sampling or runtime ranking.",
        ],
        environment=dict(
            chainbench=__version__, numpy=np.__version__, python=platform.python_version()
        ),
    )
    json.dumps(result, allow_nan=False)
    return result
