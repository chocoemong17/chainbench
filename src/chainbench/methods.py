from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .problems import DiagonalLassoProblem, QuadraticProblem, SimplexQuadraticProblem


@dataclass(frozen=True)
class Trace:
    iterates: list[np.ndarray]
    values: np.ndarray


def _values(problem, xs: list[np.ndarray]) -> np.ndarray:
    return np.asarray([problem.value(x) for x in xs], dtype=float)


def gradient_descent(problem: QuadraticProblem, steps: int, x0: np.ndarray | None = None) -> Trace:
    if steps < 0:
        raise ValueError("steps must be nonnegative")
    x = np.zeros(problem.dim) if x0 is None else np.asarray(x0, dtype=float).copy()
    xs = [x.copy()]
    alpha = 1.0 / problem.L
    for _ in range(steps):
        x = x - alpha * problem.grad(x)
        xs.append(x.copy())
    return Trace(xs, _values(problem, xs))


def accelerated_gradient(problem: QuadraticProblem, steps: int, x0: np.ndarray | None = None) -> Trace:
    if steps < 0:
        raise ValueError("steps must be nonnegative")
    x = np.zeros(problem.dim) if x0 is None else np.asarray(x0, dtype=float).copy()
    y = x.copy()
    t = 1.0
    xs = [x.copy()]
    for _ in range(steps):
        x_next = y - problem.grad(y) / problem.L
        t_next = 0.5 * (1.0 + np.sqrt(1.0 + 4.0 * t * t))
        y = x_next + ((t - 1.0) / t_next) * (x_next - x)
        x = x_next
        t = t_next
        xs.append(x.copy())
    return Trace(xs, _values(problem, xs))


def heavy_ball(
    problem: QuadraticProblem, steps: int, x0: np.ndarray | None = None
) -> tuple[Trace, float, float]:
    if problem.mu <= 0:
        raise ValueError("heavy-ball classical tuning requires mu > 0")
    x = np.zeros(problem.dim) if x0 is None else np.asarray(x0, dtype=float).copy()
    x_prev = x.copy()
    sqrt_L = np.sqrt(problem.L)
    sqrt_mu = np.sqrt(problem.mu)
    alpha = 4.0 / (sqrt_L + sqrt_mu) ** 2
    beta = ((sqrt_L - sqrt_mu) / (sqrt_L + sqrt_mu)) ** 2
    xs = [x.copy()]
    for _ in range(steps):
        x_next = x - alpha * problem.grad(x) + beta * (x - x_prev)
        x_prev, x = x, x_next
        xs.append(x.copy())
    return Trace(xs, _values(problem, xs)), alpha, beta


def conjugate_gradient(
    problem: QuadraticProblem, steps: int | None = None, x0: np.ndarray | None = None
) -> Trace:
    """Run linear conjugate gradient on an SPD quadratic.

    The quadratic stationarity equation is Q x = b. This implementation is
    intentionally small and dependency-free so the literature check is easy to audit.
    """
    if problem.mu <= 0:
        raise ValueError("conjugate gradient requires a positive-definite quadratic")
    max_steps = problem.dim if steps is None else steps
    if max_steps < 0:
        raise ValueError("steps must be nonnegative")

    x = np.zeros(problem.dim) if x0 is None else np.asarray(x0, dtype=float).copy()
    r = problem.b - problem.Q @ x
    direction = r.copy()
    residual_sq = float(r @ r)
    xs = [x.copy()]

    for _ in range(max_steps):
        if residual_sq <= np.finfo(float).eps**2:
            break
        q_direction = problem.Q @ direction
        denom = float(direction @ q_direction)
        if denom <= 0.0:
            raise ValueError("conjugate gradient encountered a non-positive curvature direction")
        alpha = residual_sq / denom
        x = x + alpha * direction
        r = r - alpha * q_direction
        next_residual_sq = float(r @ r)
        xs.append(x.copy())
        if next_residual_sq <= np.finfo(float).eps**2:
            break
        beta = next_residual_sq / residual_sq
        direction = r + beta * direction
        residual_sq = next_residual_sq

    return Trace(xs, _values(problem, xs))


def frank_wolfe(
    problem: SimplexQuadraticProblem, steps: int, x0: np.ndarray | None = None
) -> Trace:
    """Run the classical Frank-Wolfe update on a simplex quadratic."""
    if steps < 0:
        raise ValueError("steps must be nonnegative")
    if x0 is None:
        x = np.zeros(problem.dim)
        x[0] = 1.0
    else:
        x = np.asarray(x0, dtype=float).copy()
    if x.shape != (problem.dim,):
        raise ValueError("x0 shape must match the simplex dimension")
    if np.any(x < -1e-12) or not np.isclose(np.sum(x), 1.0, atol=1e-12):
        raise ValueError("x0 must lie on the probability simplex")

    xs = [x.copy()]
    for k in range(steps):
        vertex = problem.linear_minimizer(problem.grad(x))
        gamma = 2.0 / (k + 2.0)
        x = (1.0 - gamma) * x + gamma * vertex
        xs.append(x.copy())
    return Trace(xs, _values(problem, xs))


def proximal_point(
    problem: QuadraticProblem,
    steps: int,
    proximal_parameter: float = 1.0,
    x0: np.ndarray | None = None,
) -> Trace:
    """Run exact proximal-point iterations on a convex quadratic."""
    if steps < 0:
        raise ValueError("steps must be nonnegative")
    if proximal_parameter <= 0.0:
        raise ValueError("proximal_parameter must be positive")

    x = np.zeros(problem.dim) if x0 is None else np.asarray(x0, dtype=float).copy()
    system = np.eye(problem.dim) + proximal_parameter * problem.Q
    xs = [x.copy()]
    for _ in range(steps):
        rhs = x + proximal_parameter * problem.b
        x = np.linalg.solve(system, rhs)
        xs.append(x.copy())
    return Trace(xs, _values(problem, xs))


def ista(problem: DiagonalLassoProblem, steps: int, x0: np.ndarray | None = None) -> Trace:
    x = np.zeros(problem.dim) if x0 is None else np.asarray(x0, dtype=float).copy()
    step = 1.0 / problem.L
    xs = [x.copy()]
    for _ in range(steps):
        x = problem.prox_l1(x - step * problem.smooth_grad(x), step)
        xs.append(x.copy())
    return Trace(xs, _values(problem, xs))


def fista(problem: DiagonalLassoProblem, steps: int, x0: np.ndarray | None = None) -> Trace:
    x = np.zeros(problem.dim) if x0 is None else np.asarray(x0, dtype=float).copy()
    y = x.copy()
    t = 1.0
    step = 1.0 / problem.L
    xs = [x.copy()]
    for _ in range(steps):
        x_next = problem.prox_l1(y - step * problem.smooth_grad(y), step)
        t_next = 0.5 * (1.0 + np.sqrt(1.0 + 4.0 * t * t))
        y = x_next + ((t - 1.0) / t_next) * (x_next - x)
        x = x_next
        t = t_next
        xs.append(x.copy())
    return Trace(xs, _values(problem, xs))
