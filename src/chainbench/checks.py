from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .methods import accelerated_gradient, fista, gradient_descent, heavy_ball, ista
from .problems import diagonal_lasso, smooth_convex_quadratic, strongly_convex_quadratic


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


def _safe_gap(values: np.ndarray, f_star: float) -> np.ndarray:
    return np.maximum(values - f_star, 0.0)


def check_nesterov(steps: int = 80) -> CheckResult:
    p = smooth_convex_quadratic()
    x0 = np.zeros(p.dim)
    trace = accelerated_gradient(p, steps=steps, x0=x0)
    gaps = _safe_gap(trace.values, p.f_star)
    d2 = float(np.linalg.norm(x0 - p.x_star) ** 2)
    ks = np.arange(1, steps + 1, dtype=float)
    bound = 2.0 * p.L * d2 / (ks + 1.0) ** 2
    worst = float(np.max(gaps[1:] / bound))
    return CheckResult("nesterov-1983", "Nesterov acceleration",
        "Yu. E. Nesterov (1983), convergence rate O(1/k^2)",
        "Accelerated iterates stay below the standard O(1/k^2) gap bound on this instance.",
        "max_k gap_k / bound_k", worst, 1.0, worst <= 1.0 + 1e-10,
        "Finite-instance consistency check; not a proof.")


def check_gradient_descent(steps: int = 80) -> CheckResult:
    p = smooth_convex_quadratic()
    x0 = np.zeros(p.dim)
    trace = gradient_descent(p, steps=steps, x0=x0)
    gaps = _safe_gap(trace.values, p.f_star)
    d2 = float(np.linalg.norm(x0 - p.x_star) ** 2)
    ks = np.arange(1, steps + 1, dtype=float)
    bound = p.L * d2 / (2.0 * ks)
    worst = float(np.max(gaps[1:] / bound))
    return CheckResult("gd-baseline", "Gradient-descent baseline",
        "Classical gradient descent with step 1/L",
        "Iterates stay below the standard O(1/k) gap bound on this instance.",
        "max_k gap_k / bound_k", worst, 1.0, worst <= 1.0 + 1e-10,
        "Baseline for the accelerated checks.")


def check_polyak(steps: int = 180) -> CheckResult:
    p = strongly_convex_quadratic()
    trace, alpha, beta = heavy_ball(p, steps=steps)
    errors = np.asarray([np.linalg.norm(x - p.x_star) for x in trace.iterates])
    ratios = errors[1:] / np.maximum(errors[:-1], 1e-300)
    valid = ratios[errors[:-1] > 1e-10]
    observed_ratio = float(np.median(valid[-20:]))
    rho = (np.sqrt(p.L) - np.sqrt(p.mu)) / (np.sqrt(p.L) + np.sqrt(p.mu))
    rel = abs(observed_ratio - rho) / rho
    return CheckResult("polyak-1964", "Polyak heavy-ball",
        "B. T. Polyak (1964), Some methods of speeding up the convergence of iteration methods",
        "Observed tail contraction is compared with the quadratic spectral-radius prediction.",
        "relative error: observed tail ratio vs predicted rho", rel, 0.08, rel <= 0.08,
        f"alpha={alpha:.6g}, beta={beta:.6g}, rho={rho:.6g}, observed={observed_ratio:.6g}.")


def check_fista(steps: int = 80) -> CheckResult:
    p = diagonal_lasso()
    x0 = np.zeros(p.dim)
    trace = fista(p, steps=steps, x0=x0)
    gaps = _safe_gap(trace.values, p.f_star)
    d2 = float(np.linalg.norm(x0 - p.x_star) ** 2)
    ks = np.arange(1, steps + 1, dtype=float)
    bound = 2.0 * p.L * d2 / (ks + 1.0) ** 2
    worst = float(np.max(gaps[1:] / bound))
    return CheckResult("beck-teboulle-2009", "FISTA",
        "A. Beck and M. Teboulle (2009), FISTA",
        "FISTA stays below the standard O(1/k^2) composite objective-gap bound.",
        "max_k gap_k / bound_k", worst, 1.0, worst <= 1.0 + 1e-10,
        "Diagonal LASSO has an exact coordinatewise optimum.")


def check_ista_vs_fista(steps: int = 80) -> CheckResult:
    p = diagonal_lasso()
    i = ista(p, steps=steps)
    f = fista(p, steps=steps)
    gap_i = max(float(i.values[-1] - p.f_star), 1e-300)
    gap_f = max(float(f.values[-1] - p.f_star), 0.0)
    ratio = gap_f / gap_i
    return CheckResult("ista-vs-fista", "ISTA vs FISTA", "Beck--Teboulle (2009)",
        "Compare final objective gaps after the same iteration budget.",
        "FISTA final gap / ISTA final gap", float(ratio), 1.0, ratio <= 1.0,
        "Empirical comparison on one instance; not a universal dominance claim.")


CHECKS = {
    "gd-baseline": check_gradient_descent,
    "nesterov-1983": check_nesterov,
    "polyak-1964": check_polyak,
    "beck-teboulle-2009": check_fista,
    "ista-vs-fista": check_ista_vs_fista,
}


def run_check(slug: str) -> CheckResult:
    try:
        return CHECKS[slug]()
    except KeyError as exc:
        raise ValueError(f"unknown check: {slug}") from exc


def run_all() -> list[CheckResult]:
    return [fn() for fn in CHECKS.values()]
