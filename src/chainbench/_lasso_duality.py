"""Residual-based dual lower bound for a full-squared-loss LASSO.

Kim et al. (2007), Section III-B, Eq. (10)/(12). This conservative
residual scaling is an added diagnostic, not their interior-point solver.
"""

from __future__ import annotations

import numpy as np

SAFETY = 1.0 - 1e-12
SOURCE = {
    "url": "https://web.stanford.edu/~boyd/papers/pdf/l1_ls.pdf",
    "doi": "10.1109/JSTSP.2007.910971",
    "location": "Kim et al. (2007), Section III-B, Eqs. (10), (12), printed p.609 / PDF p.4",
    "operator": "A=R W; A^T=W^T R^T; full squared loss, no factor 1/2",
    "candidate": "r=A c-b; nu=2*s*r; s=(1-1e-12)*min(1,lambda/||2*A^T*r||_inf); norm=0 uses min term 1",
    "safety_factor": SAFETY,
    "scope": "Conservative residual-scaling variant derived from dual feasibility; not a transcription of Eq. (11) or an interior-point solver reproduction",
    "interpretation": "D<=F*<=F; F-D is an upper bound on unknown suboptimality, not F-F* or image RMSE",
    "numerics": "Float64 recomputed feasibility with a safety margin; not interval-arithmetic certification",
}


def residual_dual_bound(residual, observed, coefficients, adjoint, lam):
    """Reconstruct nu from retained residual inputs and the returned scale.

    The caller supplies r=A c-b and the true adjoint, with equal-shaped image
    residual/observation arrays. No known optimum or clean reference is used.
    """
    r, b, c = (np.asarray(a, dtype=float) for a in (residual, observed, coefficients))
    if (
        r.shape != b.shape
        or not r.size
        or not c.size
        or not all(np.isfinite(a).all() for a in (r, b, c))
        or not np.isfinite(lam)
        or lam <= 0
    ):
        raise ValueError("dual bound requires finite compatible arrays and positive lambda")
    raw_adjoint = np.asarray(adjoint(2 * r), dtype=float)
    if raw_adjoint.shape != c.shape or not np.isfinite(raw_adjoint).all():
        raise FloatingPointError("invalid residual adjoint")
    norm = float(np.max(np.abs(raw_adjoint)))
    scale = SAFETY * (min(1.0, lam / norm) if norm > 0 else 1.0)
    nu = (2 * r) * scale
    mapped = np.asarray(adjoint(nu), dtype=float)
    if mapped.shape != c.shape or not np.isfinite(mapped).all():
        raise FloatingPointError("invalid dual adjoint")
    feasible_norm = float(np.max(np.abs(mapped)))
    if feasible_norm > lam:
        raise FloatingPointError("dual candidate is numerically infeasible")
    quadratic = float(np.sum(nu * nu) / 4)
    linear = float(np.sum(b * nu))
    dual = -quadratic - linear
    primal = float(np.sum(r * r) + lam * np.sum(np.abs(c)))
    gap = primal - dual
    square_slack = float(np.sum((r - nu / 2) ** 2))
    l1_slack = float(lam * np.sum(np.abs(c)) + np.sum(mapped * c))
    values = dict(
        scale=scale,
        raw_adjoint_inf=norm,
        dual_adjoint_inf=feasible_norm,
        feasibility_margin=float(lam - feasible_norm),
        dual_quadratic=quadratic,
        dual_linear=linear,
        lower_bound=dual,
        primal_objective=primal,
        suboptimality_upper_bound=gap,
        square_slack=square_slack,
        l1_slack=l1_slack,
        identity_residual=float(gap - square_slack - l1_slack),
    )
    if not all(np.isfinite(v) for v in values.values()) or gap < 0:
        raise FloatingPointError("invalid dual objective bracket")
    return values
