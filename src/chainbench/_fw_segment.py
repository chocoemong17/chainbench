"""Derived scalar geometry on an existing scheduled Frank–Wolfe step.

Jaggi (2013) Algorithm 3, PDF page 3 supplies the segment minimization.
This computes its local quadratic solution without advancing a second run.
"""

from __future__ import annotations

import numpy as np

from ._validation import scalar


def segment_metadata():
    return {
        "kind": "chainbench.frank-wolfe-segment-geometry",
        "schema_version": 1,
        "source": {
            "url": "https://proceedings.mlr.press/v28/jaggi13.pdf",
            "locator": "Algorithm 3, PDF page 3: minimize f(x+gamma(s-x)) on [0,1]",
        },
        "scope": "local segment diagnostic on the existing Algorithm 1 scheduled iterates",
        "curve": "65 uniform gamma samples union the scheduled gamma and analytic minimizer",
        "minimum": "clip(-slope/||s-x||^2,0,1); choose 0 for a zero direction",
        "equal_value_gamma": "unconstrained second root of phi(gamma)=phi(0); None for a zero direction",
        "limits": [
            "The alternative does not advance a second line-search trajectory.",
            "Derived quadratic geometry, not an original-paper experiment or a method ranking.",
            "Float64 values and raw quadratic-expansion discrepancies, not interval arithmetic.",
        ],
    }


def segment_profile(target, current, vertex, gamma, following, *, following_value=None):
    target, x, s, following = (
        np.asarray(v, dtype=float) for v in (target, current, vertex, following)
    )
    if any(v.shape != (3,) or not np.isfinite(v).all() for v in (target, x, s, following)):
        raise ValueError("segment geometry requires finite three-coordinate vectors")
    if not np.isfinite(gamma) or not 0 <= gamma <= 1:
        raise ValueError("scheduled gamma must be in [0,1]")
    direction = s - x
    q = float(direction @ direction)
    slope = float((x - target) @ direction)
    minimum_gamma = float(np.clip(-slope / q, 0, 1)) if q else 0.0
    parameter = np.unique(np.r_[np.linspace(0, 1, 65), gamma, minimum_gamma])
    # Use the same convex-combination operation as the actual recurrence, so the
    # scheduled sample is the actual computed next point, including rounding.
    points = (1 - parameter[:, None]) * x + parameter[:, None] * s
    scheduled_index = int(np.searchsorted(parameter, gamma))
    minimum_index = int(np.searchsorted(parameter, minimum_gamma))
    if not np.array_equal(points[scheduled_index], following):
        raise ValueError("the recorded next point differs from the scheduled convex combination")
    objective = np.array([float(0.5 * error @ error) for error in points - target])
    if following_value is not None:
        following_value = scalar(following_value, "recorded next objective")
        if not np.isclose(objective[scheduled_index], following_value, rtol=0, atol=3e-15):
            raise ValueError("the recorded next objective differs from the segment objective")
        # Repeated BLAS evaluation need not be bitwise identical. Retain the
        # actual row's value after checking the existing Decimal audit tolerance.
        objective[scheduled_index] = following_value
    error = x - target
    value = float(0.5 * error @ error)
    affine = value + parameter * slope
    quadratic = affine + 0.5 * parameter**2 * q
    return {
        "direction": direction.tolist(),
        "direction_norm_squared": q,
        "slope": slope,
        "minimum_gamma": minimum_gamma,
        "minimum_index": minimum_index,
        "minimum_point": points[minimum_index].tolist(),
        "minimum_value": float(objective[minimum_index]),
        "scheduled_index": scheduled_index,
        "equal_value_gamma": -2 * slope / q if q else None,
        "parameter": parameter.tolist(),
        "points": points.tolist(),
        "objective": objective.tolist(),
        "affine": affine.tolist(),
        "quadratic": quadratic.tolist(),
        "quadratic_roundoff_inf": float(np.max(np.abs(objective - quadratic))),
    }
