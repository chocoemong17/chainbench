"""Scalar/Decimal verification of diagonal dual evidence; no ChainBench imports."""

import math
from decimal import Decimal, localcontext
from itertools import product


def validate_proximal_dual(result, *, required=False):
    def require(condition):
        if not condition:
            raise RuntimeError("proximal dual evidence differs")

    def close(actual, expected, atol=2e-13):
        require(
            math.isfinite(actual) and math.isclose(actual, expected, rel_tol=2e-12, abs_tol=atol)
        )

    present = "duality" in result
    require(present or not required)
    require(all(("dual_geometry" in case) == present for case in result["cases"]))
    if not present:
        return
    require(result["duality"]["kind"] == "diagonal-lasso-dual-geometry")
    require(result["duality"]["safety_factor"] == 1 - 1e-12)
    a, b = [1.0, 3.0], [1.4, -2.4]

    def value(nu):
        return -sum(v * v for v in nu) / 2 - sum(v * y for v, y in zip(nu, b))

    for case in result["cases"]:
        lam = case["lambda"]
        g = case["dual_geometry"]
        box = [lam / v for v in a]
        optimum = [max(-h, min(h, -v)) for h, v in zip(box, b)]
        for key, expected in (
            ("box_half_width", box),
            ("reference", optimum),
            ("reference_normalized", [v / h for v, h in zip(optimum, box)]),
        ):
            require(len(g[key]) == 2)
            for x, y in zip(g[key], expected):
                close(x, y)
        maximum = value(optimum)
        minimum = min(
            value([s * h for s, h in zip(signs, box)]) for signs in product((-1, 1), repeat=2)
        )
        for key, v in (
            ("reference_value", maximum),
            ("strong_duality_residual", case["f_star"] - maximum),
            ("surface_minimum", minimum),
            ("surface_maximum", maximum),
        ):
            close(g[key], v)
        require(len(g["contour_deficits"]) == 4 and set(g["runs"]) == {"ista", "fista"})
        for x, f in zip(g["contour_deficits"], (0.1, 0.3, 0.6, 0.9)):
            close(x, f * (maximum - minimum))
        for method, run in case["runs"].items():
            points = g["runs"][method]
            require(len(points) == len(run["rows"]))
            for row, d in zip(run["rows"], points):
                require(d["iteration"] == row["iteration"])
                r = [ai * xi - bi for ai, xi, bi in zip(a, row["x"], b)]
                norm = max(abs(ai * ri) for ai, ri in zip(a, r))
                scale = (1 - 1e-12) * (min(1, lam / norm) if norm else 1)
                nu = [scale * v for v in r]
                for key, expected in (
                    ("residual", r),
                    ("nu", nu),
                    ("normalized", [v / h for v, h in zip(nu, box)]),
                ):
                    require(len(d[key]) == 2)
                    for x, y in zip(d[key], expected):
                        close(x, y)
                feasible = max(abs(ai * vi) for ai, vi in zip(a, nu))
                require(feasible <= lam and d["dual_adjoint_inf"] <= lam)
                # High-precision direct subtraction of the dual quadratic,
                # independently of production's boundary-term expansion.
                with localcontext() as ctx:
                    ctx.prec = 60

                    def exact(v):
                        return -sum(Decimal(x) ** 2 for x in v) / 2 - sum(
                            Decimal(x) * Decimal(y) for x, y in zip(v, b)
                        )

                    deficit = float(exact(optimum) - exact(nu))
                upper = row["gap"] + deficit
                direct = row["objective"] - value(nu)
                for key, v in dict(
                    scale=scale,
                    raw_adjoint_inf=norm,
                    dual_adjoint_inf=feasible,
                    feasibility_margin=lam - feasible,
                    lower_bound=value(nu),
                    primal_gap=row["gap"],
                    dual_deficit=deficit,
                    suboptimality_upper_bound=upper,
                    direct_primal_minus_dual=direct,
                    gap_identity_residual=direct - upper,
                ).items():
                    close(d[key], v)
                require(
                    d["dual_deficit"] >= 0 and d["suboptimality_upper_bound"] >= d["primal_gap"]
                )
