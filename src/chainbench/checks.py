from __future__ import annotations

from dataclasses import dataclass

import numpy as np

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
    return CheckResult(
        "nesterov-1983",
        "Nesterov acceleration",
        "Yu. E. Nesterov (1983), convergence rate O(1/k^2)",
        "Accelerated iterates stay below the standard O(1/k^2) gap bound on this instance.",
        "max_k gap_k / bound_k",
        worst,
        1.0,
        worst <= 1.0 + 1e-10,
        "Finite-instance consistency check; not a proof.",
    )


def check_gradient_descent(steps: int = 80) -> CheckResult:
    p = smooth_convex_quadratic()
    x0 = np.zeros(p.dim)
    trace = gradient_descent(p, steps=steps, x0=x0)
    gaps = _safe_gap(trace.values, p.f_star)
    d2 = float(np.linalg.norm(x0 - p.x_star) ** 2)
    ks = np.arange(1, steps + 1, dtype=float)
    bound = p.L * d2 / (2.0 * ks)
    worst = float(np.max(gaps[1:] / bound))
    return CheckResult(
        "gd-baseline",
        "Gradient-descent baseline",
        "Classical gradient descent with step 1/L",
        "Iterates stay below the standard O(1/k) gap bound on this instance.",
        "max_k gap_k / bound_k",
        worst,
        1.0,
        worst <= 1.0 + 1e-10,
        "Baseline for the accelerated checks.",
    )


def check_polyak(steps: int = 180) -> CheckResult:
    p = strongly_convex_quadratic()
    trace, alpha, beta = heavy_ball(p, steps=steps)
    errors = np.asarray([np.linalg.norm(x - p.x_star) for x in trace.iterates])
    ratios = errors[1:] / np.maximum(errors[:-1], 1e-300)
    valid = ratios[errors[:-1] > 1e-10]
    observed_ratio = float(np.median(valid[-20:]))
    rho = (np.sqrt(p.L) - np.sqrt(p.mu)) / (np.sqrt(p.L) + np.sqrt(p.mu))
    rel = abs(observed_ratio - rho) / rho
    return CheckResult(
        "polyak-1964",
        "Polyak heavy-ball",
        "B. T. Polyak (1964), Some methods of speeding up the convergence of iteration methods",
        "Observed tail contraction is compared with the quadratic spectral-radius prediction.",
        "relative error: observed tail ratio vs predicted rho",
        rel,
        0.08,
        rel <= 0.08,
        f"alpha={alpha:.6g}, beta={beta:.6g}, rho={rho:.6g}, observed={observed_ratio:.6g}.",
    )


def check_conjugate_gradient(steps: int = 20) -> CheckResult:
    p = strongly_convex_quadratic(dim=30, mu=0.1, L=1.0)
    x0 = np.zeros(p.dim)
    trace = conjugate_gradient(p, steps=steps, x0=x0)
    errors = np.asarray(
        [np.sqrt((x - p.x_star) @ p.Q @ (x - p.x_star)) for x in trace.iterates]
    )
    kappa = p.L / p.mu
    rho = (np.sqrt(kappa) - 1.0) / (np.sqrt(kappa) + 1.0)
    ks = np.arange(len(errors), dtype=float)
    bound = 2.0 * (rho**ks) * errors[0]
    worst = float(np.max(errors / bound))
    return CheckResult(
        "hestenes-stiefel-1952",
        "Conjugate gradient",
        "M. R. Hestenes and E. Stiefel (1952), Methods of Conjugate Gradients",
        "A-norm errors stay below the classical condition-number convergence envelope.",
        "max_k ||e_k||_Q / (2 rho^k ||e_0||_Q)",
        worst,
        1.0,
        worst <= 1.0 + 1e-10,
        f"kappa={kappa:.6g}, rho={rho:.6g}; checked {len(errors) - 1} iterations.",
    )


def check_frank_wolfe(steps: int = 80) -> CheckResult:
    p = simplex_quadratic(dim=50)
    trace = frank_wolfe(p, steps=steps)
    gaps = _safe_gap(trace.values, p.f_star)
    ks = np.arange(len(gaps), dtype=float)
    bound = 2.0 * p.curvature_upper_bound / (ks + 2.0)
    worst = float(np.max(gaps / bound))
    return CheckResult(
        "jaggi-2013",
        "Frank-Wolfe",
        "M. Jaggi (2013), Revisiting Frank-Wolfe: Projection-Free Sparse Convex Optimization",
        "Primal gaps stay below the standard curvature-based O(1/k) envelope.",
        "max_k gap_k / (2 C_f / (k+2))",
        worst,
        1.0,
        worst <= 1.0 + 1e-10,
        f"C_f upper bound={p.curvature_upper_bound:.6g}; deterministic simplex quadratic.",
    )


def check_proximal_point(steps: int = 30, proximal_parameter: float = 1.0) -> CheckResult:
    p = strongly_convex_quadratic(dim=40, mu=0.1, L=1.0)
    trace = proximal_point(p, steps=steps, proximal_parameter=proximal_parameter)
    errors = np.asarray([np.linalg.norm(x - p.x_star) for x in trace.iterates])
    contraction = 1.0 / (1.0 + proximal_parameter * p.mu)
    scaled_ratios = errors[1:] / np.maximum(contraction * errors[:-1], 1e-300)
    worst = float(np.max(scaled_ratios))
    return CheckResult(
        "rockafellar-1976",
        "Proximal point",
        "R. T. Rockafellar (1976), Monotone Operators and the Proximal Point Algorithm",
        "Successive errors respect the strongly-convex resolvent contraction on this quadratic.",
        "max_k ||e_(k+1)|| / (q ||e_k||)",
        worst,
        1.0,
        worst <= 1.0 + 1e-10,
        (
            f"proximal parameter={proximal_parameter:.6g}, mu={p.mu:.6g}, "
            f"q={contraction:.6g}."
        ),
    )


def check_fista(steps: int = 80) -> CheckResult:
    p = diagonal_lasso()
    x0 = np.zeros(p.dim)
    trace = fista(p, steps=steps, x0=x0)
    gaps = _safe_gap(trace.values, p.f_star)
    d2 = float(np.linalg.norm(x0 - p.x_star) ** 2)
    ks = np.arange(1, steps + 1, dtype=float)
    bound = 2.0 * p.L * d2 / (ks + 1.0) ** 2
    worst = float(np.max(gaps[1:] / bound))
    return CheckResult(
        "beck-teboulle-2009",
        "FISTA",
        "A. Beck and M. Teboulle (2009), FISTA",
        "FISTA stays below the standard O(1/k^2) composite objective-gap bound.",
        "max_k gap_k / bound_k",
        worst,
        1.0,
        worst <= 1.0 + 1e-10,
        "Diagonal LASSO has an exact coordinatewise optimum.",
    )


def check_ista_vs_fista(steps: int = 80) -> CheckResult:
    p = diagonal_lasso()
    i = ista(p, steps=steps)
    f = fista(p, steps=steps)
    gap_i = max(float(i.values[-1] - p.f_star), 1e-300)
    gap_f = max(float(f.values[-1] - p.f_star), 0.0)
    ratio = gap_f / gap_i
    return CheckResult(
        "ista-vs-fista",
        "ISTA vs FISTA",
        "Beck--Teboulle (2009)",
        "Compare final objective gaps after the same iteration budget.",
        "FISTA final gap / ISTA final gap",
        float(ratio),
        1.0,
        ratio <= 1.0,
        "Empirical comparison on one instance; not a universal dominance claim.",
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
    try:
        return CHECKS[slug]()
    except KeyError as exc:
        raise ValueError(f"unknown check: {slug}") from exc


def run_all() -> list[CheckResult]:
    return [fn() for fn in CHECKS.values()]
