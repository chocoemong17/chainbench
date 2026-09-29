from __future__ import annotations

from dataclasses import dataclass
from numbers import Real

import numpy as np

from ._validation import array, count
from .methods import (
    accelerated_gradient,
    conjugate_gradient,
    fista,
    frank_wolfe,
    gradient_descent,
    heavy_ball,
    ista,
    proximal_point,
)
from .problems import (
    diagonal_lasso,
    simplex_quadratic,
    smooth_convex_quadratic,
    strongly_convex_quadratic,
)


@dataclass(frozen=True)
class CheckResult:
    slug: str
    title: str
    reference: str
    statement: str
    metric: str
    observed: float
    threshold: float | None
    consistent: bool | None
    note: str

    def __post_init__(self) -> None:
        if self.observed is None:
            raise ValueError("observed is required; missing evidence is not a result")
        for name in ("observed", "threshold"):
            value = getattr(self, name)
            if value is not None:
                if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
                    raise ValueError(f"{name} must be a finite real number")
                value = float(value)
                if not np.isfinite(value):
                    raise ValueError(f"{name} must be finite; a non-finite check is invalid")
                object.__setattr__(self, name, value)
        if self.consistent is not None:
            if not isinstance(self.consistent, (bool, np.bool_)):
                raise ValueError("consistent must be bool or None")
            object.__setattr__(self, "consistent", bool(self.consistent))
        if (self.consistent is None) != (self.threshold is None):
            raise ValueError("INFO requires no threshold; a quantitative result requires one")


def _gaps(problem, trace) -> np.ndarray:
    gaps = np.asarray([problem.gap(x) for x in trace.iterates])
    if not np.all(np.isfinite(gaps)) or np.any(gaps < 0):
        raise FloatingPointError("invalid objective gap")
    return gaps


def _bound_result(slug, title, reference, statement, metric, ratios, note) -> CheckResult:
    ratios = array(ratios, "ratios")
    if ratios.ndim != 1 or not ratios.size or np.any(ratios < 0):
        raise ValueError("ratios must be a nonempty vector of finite nonnegative samples")
    worst = float(np.max(ratios))
    return CheckResult(slug, title, reference, statement, metric, worst, 1.0,
                       worst <= 1.0 + 1e-10, note)


def check_gradient_descent(steps: int = 80) -> CheckResult:
    steps = count(steps, minimum=1)
    p = smooth_convex_quadratic()
    trace = gradient_descent(p, steps)
    ks = np.arange(1, steps + 1, dtype=float)
    bound = p.L * float(p.x_star @ p.x_star) / (2 * ks)
    return _bound_result(
        "gd-baseline", "Gradient-descent baseline", "Beck--Teboulle (2009), ISTA with g=0",
        "Smooth-convex GD objective-gap bound on the bundled quadratic.",
        "max_k gap_k / bound_k", _gaps(p, trace)[1:] / bound,
        "Step=1/L; positive iterations only. This is not a universal numerical proof.",
    )


def check_nesterov(steps: int = 80) -> CheckResult:
    steps = count(steps, minimum=1)
    p = smooth_convex_quadratic()
    trace = accelerated_gradient(p, steps)
    ks = np.arange(1, steps + 1, dtype=float)
    bound = 2 * p.L * float(p.x_star @ p.x_star) / (ks + 1)**2
    return _bound_result(
        "nesterov-1983", "Nesterov-style acceleration (smooth FISTA)",
        "Beck--Teboulle (2009), fixed-L FISTA with g=0; Nesterov (1983) historical origin",
        "Smooth FISTA iterates satisfy the O(1/k^2) objective-gap bound on this quadratic.",
        "max_k gap_k / bound_k", _gaps(p, trace)[1:] / bound,
        "Historical CLI slug retained; not a literal reproduction of the 1983 algorithm.",
    )


def check_polyak(steps: int = 180) -> CheckResult:
    steps = count(steps, minimum=1)
    p = strongly_convex_quadratic()
    trace, alpha, beta = heavy_ball(p, steps)
    errors = np.asarray([np.linalg.norm(x - p.x_star) for x in trace.iterates])
    valid = errors[:-1] > 1e-10
    observed = float(np.median((errors[1:][valid] / errors[:-1][valid])[-20:]))
    rho = (np.sqrt(p.L) - np.sqrt(p.mu)) / (np.sqrt(p.L) + np.sqrt(p.mu))
    relative_error = abs(observed - rho) / rho
    return CheckResult(
        "polyak-1964", "Polyak heavy-ball (empirical tail)", "Polyak (1964), quadratic tuning",
        "Compare a finite tail contraction estimate with the spectral-radius prediction.",
        "relative error: observed tail ratio vs predicted rho", relative_error, 0.08,
        relative_error <= 0.08,
        f"alpha={alpha:.6g}, beta={beta:.6g}, rho={rho:.6g}; 8% is an empirical tolerance, "
        "not a theorem constant. Last up to 20 ratios above error=1e-10 are used.",
    )


def check_conjugate_gradient(steps: int = 20) -> CheckResult:
    steps = count(steps, minimum=1)
    p = strongly_convex_quadratic(30, 0.1, 1.0)
    trace = conjugate_gradient(p, steps)
    errors = np.sqrt(2 * _gaps(p, trace))
    rho = (np.sqrt(p.L / p.mu) - 1) / (np.sqrt(p.L / p.mu) + 1)
    ks = np.arange(1, len(errors), dtype=float)
    return _bound_result(
        "hestenes-stiefel-1952", "Conjugate gradient",
        "Hestenes--Stiefel (1952); bound: Shewchuk (1994), equation (52)",
        "Positive-iteration A-norm errors satisfy the classical condition-number envelope.",
        "max_k ||e_k||_Q / (2 rho^k ||e_0||_Q)", errors[1:] / (2 * rho**ks * errors[0]),
        f"kappa={p.L/p.mu:.6g}; k=0 excluded to avoid its fixed ratio of 0.5.",
    )


def check_frank_wolfe(steps: int = 80) -> CheckResult:
    steps = count(steps, minimum=1)
    p = simplex_quadratic(50)
    trace = frank_wolfe(p, steps)
    ks = np.arange(1, steps + 1, dtype=float)
    return _bound_result(
        "jaggi-2013", "Frank-Wolfe", "Jaggi (2013), Algorithm 1 and Theorem 1, delta=0",
        "Primal gaps satisfy the curvature-based envelope for k>=1.",
        "max_k gap_k / (2 C_f / (k+2))",
        _gaps(p, trace)[1:] / (2 * p.curvature_upper_bound / (ks + 2)),
        "C_f=2 for this simplex quadratic; exact linear minimization oracle.",
    )


def check_proximal_point(steps: int = 30, proximal_parameter: float = 1.0) -> CheckResult:
    steps = count(steps, minimum=1)
    p = strongly_convex_quadratic(40, 0.1, 1.0)
    trace = proximal_point(p, steps, proximal_parameter)
    errors = np.asarray([np.linalg.norm(x - p.x_star) for x in trace.iterates])
    q = 1 / (1 + proximal_parameter * p.mu)
    valid = errors[:-1] > 1e-12
    if not np.any(valid):
        raise ValueError("no error ratios above the numerical floor")
    return _bound_result(
        "rockafellar-1976", "Proximal point", "Rockafellar (1976); quadratic resolvent specialization",
        "Successive Euclidean errors satisfy the strongly-convex resolvent contraction.",
        "max_k error_(k+1) / (q * error_k)", errors[1:][valid] / (q * errors[:-1][valid]),
        f"q={q:.6g}; exact quadratic linear solves, not a general inexact PPA experiment.",
    )


def check_fista(steps: int = 80) -> CheckResult:
    steps = count(steps, minimum=1)
    p = diagonal_lasso()
    trace = fista(p, steps)
    ks = np.arange(1, steps + 1, dtype=float)
    bound = 2 * p.L * float(p.x_star @ p.x_star) / (ks + 1)**2
    return _bound_result(
        "beck-teboulle-2009", "FISTA", "Beck--Teboulle (2009), fixed-L FISTA",
        "Composite objective gaps satisfy the O(1/k^2) bound on diagonal LASSO.",
        "max_k gap_k / bound_k", _gaps(p, trace)[1:] / bound,
        "Exact soft-threshold optimum; stable gap evaluation avoids objective cancellation.",
    )


def check_ista_vs_fista(steps: int = 80) -> CheckResult:
    steps = count(steps, minimum=1)
    p = diagonal_lasso()
    gi = p.gap(ista(p, steps).iterates[-1])
    gf = p.gap(fista(p, steps).iterates[-1])
    if gi <= 1e-28:
        raise ValueError("ISTA comparison gap is below the numerical comparison floor")
    return CheckResult(
        "ista-vs-fista", "ISTA vs FISTA (observation)", "Beck--Teboulle (2009)",
        "Compare final objective gaps at the same iteration budget on one fixture.",
        "FISTA final gap / ISTA final gap", gf / gi, None, None,
        "Informational, not pass/fail: FISTA is not guaranteed to beat ISTA at every iteration.",
    )


CHECKS = {
    "gd-baseline": check_gradient_descent,
    "nesterov-1983": check_nesterov,
    "polyak-1964": check_polyak,
    "hestenes-stiefel-1952": check_conjugate_gradient,
    "jaggi-2013": check_frank_wolfe,
    "rockafellar-1976": check_proximal_point,
    "beck-teboulle-2009": check_fista,
    "ista-vs-fista": check_ista_vs_fista,
}


def run_check(slug: str) -> CheckResult:
    if slug not in CHECKS:
        raise ValueError(f"unknown check: {slug}")
    return CHECKS[slug]()


def run_all() -> list[CheckResult]:
    return [check() for check in CHECKS.values()]
