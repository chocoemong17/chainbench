"""Feasible residual candidates for the existing half-squared diagonal LASSO."""

from itertools import product

import numpy as np

from ._lasso_duality import SAFETY

CONTRACT = {
    "kind": "diagonal-lasso-dual-geometry",
    "source": "https://web.stanford.edu/~boyd/papers/pdf/l1_ls.pdf",
    "location": "Kim et al. (2007), Section III-B, Eqs. (10), (12), p.609 / PDF 4",
    "scaling": "Divide the source full-loss objective with penalty 2*lambda by 2; nu_source=2*nu gives D=-0.5||nu||^2-b^T nu",
    "candidate": "r=diag(a)*x-b; h=||diag(a)*r||_inf; s=(1-1e-12)*min(1,lambda/h); h=0 uses min term 1; nu=s*r",
    "safety_factor": SAFETY,
    "coordinates": "w_i=nu_i/(lambda/abs(a_i)); feasible box [-1,1]^2; unequal original-coordinate scales are explicit",
    "reference": "nu_star=clip(-b,-lambda/abs(a),lambda/abs(a)); analytic reference for this diagonal fixture only",
    "indexing": "stage k->k+1 displays the dual candidate from the completed next iterate x[k+1], with previous candidate at x[k]",
    "scope": "Added controlled geometry; no dual optimization algorithm or source MRI reproduction; candidates are diagnostics of retained primal iterates",
}


def dual_geometry(problem, runs):
    a, b, lam = problem.a, problem.b, problem.lam
    box = lam / np.abs(a)
    optimum = np.clip(-b, -box, box)

    def value(nu):
        return float(-0.5 * (nu @ nu) - b @ nu)

    maximum = value(optimum)
    minimum = min(value(box * np.array(signs)) for signs in product((-1, 1), repeat=2))
    records = {}
    for method, run in runs.items():
        points = []
        for row in run["rows"]:
            x = np.asarray(row["x"])
            residual = a * x - b
            norm = float(np.max(np.abs(a * residual)))
            scale = SAFETY * (min(1.0, lam / norm) if norm else 1.0)
            nu = scale * residual
            mapped = a * nu
            feasible_norm = float(np.max(np.abs(mapped)))
            if not np.isfinite(nu).all() or feasible_norm > lam:
                raise FloatingPointError("infeasible proximal dual candidate")
            lower = value(nu)
            delta = nu - optimum
            # Stable D(nu*)-D(nu), including the active-box boundary term.
            deficit = float(0.5 * (delta @ delta) + (optimum + b) @ delta)
            upper = row["gap"] + deficit
            direct_gap = row["objective"] - lower
            if not np.isfinite(deficit + upper + direct_gap) or min(deficit, upper) < 0:
                raise FloatingPointError("invalid proximal dual objective bound")
            points.append(
                dict(
                    iteration=row["iteration"],
                    residual=residual.tolist(),
                    scale=scale,
                    raw_adjoint_inf=norm,
                    nu=nu.tolist(),
                    normalized=(nu / box).tolist(),
                    dual_adjoint_inf=feasible_norm,
                    feasibility_margin=lam - feasible_norm,
                    lower_bound=lower,
                    primal_gap=row["gap"],
                    dual_deficit=deficit,
                    suboptimality_upper_bound=upper,
                    direct_primal_minus_dual=direct_gap,
                    gap_identity_residual=direct_gap - upper,
                )
            )
        records[method] = points
    return dict(
        box_half_width=box.tolist(),
        reference=optimum.tolist(),
        reference_normalized=(optimum / box).tolist(),
        reference_value=maximum,
        strong_duality_residual=float(problem.f_star - maximum),
        surface_minimum=minimum,
        surface_maximum=maximum,
        contour_deficits=[fraction * (maximum - minimum) for fraction in (0.1, 0.3, 0.6, 0.9)],
        runs=records,
    )
