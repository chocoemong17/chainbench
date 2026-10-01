"""Exact-rational reference for the public sparsity construction; standard library only."""

from __future__ import annotations

import hashlib
import json
import math
from fractions import Fraction


def validate_fw_sparsity(record):
    def require(value, message):
        if not value:
            raise RuntimeError("FW sparsity evidence: " + message)

    def close(a, b):
        require(
            a is not None
            and math.isfinite(a)
            and math.isclose(a, float(b), rel_tol=2e-10, abs_tol=2e-12),
            "numerical value differs",
        )

    require(
        record["kind"] == "chainbench.fw-sparsity" and record["schema_version"] == 1,
        "schema differs",
    )
    steps = record["parameters"]["steps"]
    require(type(steps) is int and 1 <= steps <= 256, "budget differs")
    require(
        [c["dimension"] for c in record["cases"]] == [3, 8, 32, 128], "declared dimensions differ"
    )
    require(
        record["parameters"]["dimensions"] == [3, 8, 32, 128]
        and record["parameters"]["seed"] is None,
        "design differs",
    )
    for case in record["cases"]:
        n = case["dimension"]
        inputs = dict(
            dimension=n,
            start=[float(i == 0) for i in range(n)],
            optimizer=[1 / n] * n,
            objective="sum(x_i**2)",
            curvature=4.0,
            f_star=1 / n,
        )
        require(case["inputs"] == inputs, "source inputs differ")
        require(
            case["input_sha256"]
            == hashlib.sha256(
                json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "input hash differs",
        )
        require(
            case["updates"] == steps
            and case["termination"] == "fixed_budget"
            and len(case["rows"]) == steps + 1,
            "trace incomplete",
        )
        x = [Fraction(int(i == 0)) for i in range(n)]
        for k, row in enumerate(case["rows"]):
            require(
                row["iteration"] == k
                and len(row["x"]) == len(row["balanced"]) == len(row["gradient"]) == n,
                "row layout differs",
            )
            s = sum(v > 0 for v in x)
            require(row["support"] == s, "support differs")
            oracle = min(range(n), key=x.__getitem__)
            require(row["vertex_index"] == oracle, "oracle differs")
            objective = sum(v * v for v in x)
            balanced = [Fraction(int(v > 0), s) for v in x]
            for a, b, c, value, equal in zip(
                row["x"], row["gradient"], row["balanced"], x, balanced
            ):
                close(a, value)
                close(b, 2 * value)
                close(c, equal)
            for key, value in [
                ("objective", objective),
                ("primal_gap", objective - Fraction(1, n)),
                ("dual_gap", 2 * (objective - min(x))),
                ("support_floor", Fraction(1, s) - Fraction(1, n)),
                ("minimum_with_support", Fraction(1, s)),
                ("balanced_objective", Fraction(1, s)),
                ("balanced_primal_gap", Fraction(1, s) - Fraction(1, n)),
                ("balanced_dual_gap", Fraction(2, s) if s < n else 0),
                ("excess_over_support_minimum", objective - Fraction(1, s)),
            ]:
                close(row[key], value)
            if s < n:
                close(row["dual_support_floor"], Fraction(2, s))
                require(2 * (objective - min(x)) >= Fraction(2, s), "dual lower bound violated")
            else:
                require(row["dual_support_floor"] is None, "invented full-support dual floor")
            if k:
                close(row["iteration_upper"], Fraction(8, k + 2))
                require(
                    objective - Fraction(1, n) <= Fraction(8, k + 2), "iteration upper violated"
                )
            else:
                require(row["iteration_upper"] is None, "invented k=0 bound")
            require(objective >= Fraction(1, s), "support floor violated")
            if k < steps:
                gamma = Fraction(2, k + 2)
                close(row["gamma"], gamma)
                x = [(1 - gamma) * value + gamma * int(i == oracle) for i, value in enumerate(x)]
            else:
                require(row["gamma"] is None, "invented final update")
        require(len(case["construction"]) == n, "attaining construction incomplete")
        for s, point in enumerate(case["construction"], start=1):
            require(point["support"] == s and len(point["x"]) == n, "construction indexing differs")
            for i, value in enumerate(point["x"]):
                close(value, Fraction(1, s) if i < s else 0)
            for key, value in [
                ("objective", Fraction(1, s)),
                ("minimum", Fraction(1, s)),
                ("primal_gap", Fraction(1, s) - Fraction(1, n)),
                ("gap_floor", Fraction(1, s) - Fraction(1, n)),
                ("dual_gap", Fraction(2, s) if s < n else 0),
            ]:
                close(point[key], value)
            if s < n:
                close(point["dual_floor"], Fraction(2, s))
            else:
                require(point["dual_floor"] is None, "construction dual floor at full support")
