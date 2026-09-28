from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .problems import DiagonalLassoProblem, QuadraticProblem


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


def heavy_ball(problem: QuadraticProblem, steps: int, x0: np.ndarray | None = None) -> tuple[Trace, float, float]:
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
