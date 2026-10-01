from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ._validation import count, initial, scalar
from .problems import DiagonalLassoProblem, QuadraticProblem, SimplexQuadraticProblem


@dataclass(frozen=True)
class Trace:
    iterates: list[np.ndarray]
    values: np.ndarray
    termination: str | None = None
    residual_norm: float | None = None


def _trace(problem, xs: list[np.ndarray], **metadata) -> Trace:
    values = np.asarray([problem.value(x) for x in xs], dtype=float)
    if not np.all(np.isfinite(values)):
        raise FloatingPointError("non-finite objective; reduce problem scale")
    return Trace(xs, values, **metadata)


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


def _norm(x: np.ndarray) -> float:
    """Euclidean norm without directly squaring the unscaled coordinates."""
    if not np.all(np.isfinite(x)):
        raise FloatingPointError("non-finite residual; reduce problem scale")
    with np.errstate(over="raise", invalid="raise"):
        return float(np.hypot.reduce(x))


def _cg_dot(left: np.ndarray, right: np.ndarray) -> float:
    """Accumulate rounded products independently of BLAS reduction dispatch."""
    with np.errstate(over="raise", invalid="raise"):
        products = np.multiply(left, right)
    try:
        result = math.fsum(products)
    except (OverflowError, ValueError) as exc:
        raise FloatingPointError("non-finite CG inner product") from exc
    if not math.isfinite(result):
        raise FloatingPointError("non-finite CG inner product")
    return result


def _cg_matvec(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    """Use the same explicit accumulation for every small dense CG row."""
    return np.asarray([_cg_dot(row, vector) for row in matrix], dtype=float)


def conjugate_gradient(
    problem: QuadraticProblem, steps: int | None = None, x0: np.ndarray | None = None,
    *, rtol: float = 1e-12, atol: float = 0.0,
) -> Trace:
    """CG on a scaled correction equation, with true-residual stopping.

    Stop when ||b-Qx|| <= max(atol, rtol*||b-Qx0||). This relative-to-initial
    convention is retained from 0.1.0 (it is not SciPy's relative-to-b rule).
    ``termination`` distinguishes convergence from exhaustion of ``steps``.
    """
    steps = count(problem.dim if steps is None else steps)
    rtol, atol = scalar(rtol, "rtol"), scalar(atol, "atol")
    if problem.mu <= 0:
        raise ValueError("conjugate gradient requires a positive-definite quadratic")
    x = initial(problem.dim, x0)
    start, xs = x.copy(), [x.copy()]
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        raw = problem.b - problem.Q @ x
        initial_norm = _norm(raw)
        tolerance = max(atol, rtol * initial_norm)
        if initial_norm <= tolerance or steps == 0:
            return _trace(problem, xs, residual_norm=initial_norm,
                          termination="converged" if initial_norm <= tolerance else "max_steps")

        # Solve (Q/L) z = (b-Q*x0)/(L*scale), then x=x0+scale*z.
        # Normalize in two divisions, avoiding overflow in L*scale.
        operator = problem.Q / problem.L
        residual = raw / problem.L
        scale = float(np.max(np.abs(residual)))
        if not np.isfinite(scale) or scale == 0:
            raise FloatingPointError("CG correction cannot be represented at this scale")
        residual = residual / scale
        direction = residual.copy()
        rr = _cg_dot(residual, residual)
        correction = np.zeros(problem.dim)
        residual_norm = initial_norm
        termination = "max_steps"
        for _ in range(steps):
            qd = _cg_matvec(operator, direction)
            denominator = _cg_dot(direction, qd)
            if not np.isfinite(denominator) or denominator <= 0 or rr <= 0:
                raise FloatingPointError("CG encountered nonpositive or non-finite curvature")
            alpha = rr / denominator
            correction = correction + alpha * direction
            x = start + scale * correction
            xs.append(x.copy())
            # Never declare convergence from the recursively updated residual alone.
            raw = problem.b - problem.Q @ x
            residual_norm = _norm(raw)
            if residual_norm <= tolerance:
                termination = "converged"
                break
            residual = residual - alpha * qd
            rr_next = _cg_dot(residual, residual)
            if rr_next == 0:
                # A recurrence can round to zero while the true residual remains nonzero.
                residual = (raw / problem.L) / scale
                rr_next = _cg_dot(residual, residual)
                direction = residual.copy()
            else:
                direction = residual + (rr_next / rr) * direction
            if not np.isfinite(rr_next) or rr_next <= 0:
                raise FloatingPointError("CG residual lost numerical resolution before convergence")
            rr = rr_next
    return _trace(problem, xs, termination=termination, residual_norm=residual_norm)


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


def _proximal_iterates(problem, steps: int, x0: np.ndarray | None = None, *, accelerated: bool):
    """Stream the fixed-L recurrence; yielded copies cannot mutate future steps."""
    steps = count(steps)
    x = initial(problem.dim, x0)
    step = 1.0 / scalar(problem.L, "L", positive=True)
    y, t = x.copy(), 1.0
    yield x.copy()
    for _ in range(steps):
        base = y if accelerated else x
        xn = problem.prox_l1(base - step * problem.smooth_grad(base), step)
        if accelerated:
            tn = 0.5 * (1 + np.sqrt(1 + 4 * t * t))
            y = xn + ((t - 1) / tn) * (xn - x)
            t = tn
        x = xn
        yield x.copy()


def ista(problem: DiagonalLassoProblem, steps: int, x0: np.ndarray | None = None) -> Trace:
    return _trace(problem, list(_proximal_iterates(problem, steps, x0, accelerated=False)))


def fista(problem: DiagonalLassoProblem, steps: int, x0: np.ndarray | None = None) -> Trace:
    return _trace(problem, list(_proximal_iterates(problem, steps, x0, accelerated=True)))
