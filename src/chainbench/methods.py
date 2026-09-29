from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ._validation import count, initial, scalar
from .problems import DiagonalLassoProblem, QuadraticProblem, SimplexQuadraticProblem


@dataclass(frozen=True)
class Trace:
    iterates: list[np.ndarray]
    values: np.ndarray


def _trace(problem, xs: list[np.ndarray]) -> Trace:
    values = np.asarray([problem.value(x) for x in xs], dtype=float)
    if not np.all(np.isfinite(values)):
        raise FloatingPointError("non-finite objective; reduce problem scale")
    return Trace(xs, values)


def gradient_descent(problem: QuadraticProblem, steps: int, x0: np.ndarray | None = None) -> Trace:
    steps = count(steps)
    x = initial(problem.dim, x0)
    L = scalar(problem.L, "L", positive=True)
    xs = [x.copy()]
    for _ in range(steps):
        x = x - problem.grad(x) / L
        xs.append(x.copy())
    return _trace(problem, xs)


def accelerated_gradient(problem: QuadraticProblem, steps: int, x0: np.ndarray | None = None) -> Trace:
    """Smooth specialization of Beck--Teboulle's fixed-L FISTA recurrence.

    Nesterov-style acceleration; not a line-by-line implementation of the 1983 paper.
    """
    steps = count(steps)
    x = initial(problem.dim, x0)
    L = scalar(problem.L, "L", positive=True)
    y, t, xs = x.copy(), 1.0, [x.copy()]
    for _ in range(steps):
        xn = y - problem.grad(y) / L
        tn = 0.5 * (1 + np.sqrt(1 + 4 * t * t))
        y = xn + ((t - 1) / tn) * (xn - x)
        x, t = xn, tn
        xs.append(x.copy())
    return _trace(problem, xs)


def heavy_ball(
    problem: QuadraticProblem, steps: int, x0: np.ndarray | None = None
) -> tuple[Trace, float, float]:
    steps = count(steps)
    if problem.mu <= 0:
        raise ValueError("heavy-ball classical tuning requires mu > 0")
    x = initial(problem.dim, x0)
    previous, xs = x.copy(), [x.copy()]
    root_L, root_mu = np.sqrt(problem.L), np.sqrt(problem.mu)
    alpha = 4.0 / (root_L + root_mu) ** 2
    beta = ((root_L - root_mu) / (root_L + root_mu)) ** 2
    for _ in range(steps):
        xn = x - alpha * problem.grad(x) + beta * (x - previous)
        previous, x = x, xn
        xs.append(x.copy())
    return _trace(problem, xs), float(alpha), float(beta)


def conjugate_gradient(
    problem: QuadraticProblem, steps: int | None = None, x0: np.ndarray | None = None,
    *, rtol: float = 1e-12, atol: float = 0.0,
) -> Trace:
    """Linear CG, with a scale-aware residual stopping rule."""
    steps = count(problem.dim if steps is None else steps)
    rtol, atol = scalar(rtol, "rtol"), scalar(atol, "atol")
    if problem.mu <= 0:
        raise ValueError("conjugate gradient requires a positive-definite quadratic")
    x = initial(problem.dim, x0)
    r = problem.b - problem.Q @ x
    direction, rr, xs = r.copy(), float(r @ r), [x.copy()]
    tolerance = max(atol, rtol * float(np.linalg.norm(r)))
    for _ in range(steps):
        if np.linalg.norm(r) <= tolerance:
            break
        qd = problem.Q @ direction
        denominator = float(direction @ qd)
        if not np.isfinite(denominator) or denominator <= 0:
            raise FloatingPointError("CG encountered nonpositive or non-finite curvature")
        alpha = rr / denominator
        x, r = x + alpha * direction, r - alpha * qd
        rr_next = float(r @ r)
        xs.append(x.copy())
        if np.linalg.norm(r) <= tolerance:
            break
        direction = r + (rr_next / rr) * direction
        rr = rr_next
    return _trace(problem, xs)


def frank_wolfe(
    problem: SimplexQuadraticProblem, steps: int, x0: np.ndarray | None = None
) -> Trace:
    steps = count(steps)
    x = initial(problem.dim, x0)
    if x0 is None:
        x[0] = 1
    if np.any(x < 0) or not np.isclose(x.sum(), 1, rtol=0, atol=1e-12):
        raise ValueError("x0 must lie on the probability simplex")
    xs = [x.copy()]
    for k in range(steps):
        vertex = problem.linear_minimizer(problem.grad(x))
        gamma = 2.0 / (k + 2.0)
        x = (1 - gamma) * x + gamma * vertex
        xs.append(x.copy())
    return _trace(problem, xs)


def proximal_point(
    problem: QuadraticProblem, steps: int, proximal_parameter: float = 1.0,
    x0: np.ndarray | None = None,
) -> Trace:
    steps = count(steps)
    c = scalar(proximal_parameter, "proximal_parameter", positive=True)
    x = initial(problem.dim, x0)
    system, xs = np.eye(problem.dim) + c * problem.Q, [x.copy()]
    for _ in range(steps):
        x = np.linalg.solve(system, x + c * problem.b)
        xs.append(x.copy())
    return _trace(problem, xs)


def ista(problem: DiagonalLassoProblem, steps: int, x0: np.ndarray | None = None) -> Trace:
    steps = count(steps)
    x = initial(problem.dim, x0)
    step = 1.0 / scalar(problem.L, "L", positive=True)
    xs = [x.copy()]
    for _ in range(steps):
        x = problem.prox_l1(x - step * problem.smooth_grad(x), step)
        xs.append(x.copy())
    return _trace(problem, xs)


def fista(problem: DiagonalLassoProblem, steps: int, x0: np.ndarray | None = None) -> Trace:
    steps = count(steps)
    x = initial(problem.dim, x0)
    step = 1.0 / scalar(problem.L, "L", positive=True)
    y, t, xs = x.copy(), 1.0, [x.copy()]
    for _ in range(steps):
        xn = problem.prox_l1(y - step * problem.smooth_grad(y), step)
        tn = 0.5 * (1 + np.sqrt(1 + 4 * t * t))
        y = xn + ((t - 1) / tn) * (xn - x)
        x, t = xn, tn
        xs.append(x.copy())
    return _trace(problem, xs)
