from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ._validation import array, count, scalar, vector


def _freeze(x: np.ndarray) -> np.ndarray:
    result = x.copy()
    result.flags.writeable = False
    return result


@dataclass(frozen=True)
class QuadraticProblem:
    Q: np.ndarray
    b: np.ndarray
    x_star: np.ndarray
    _L: float = field(init=False, repr=False)
    _mu: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        q = array(self.Q, "Q")
        if q.ndim != 2 or q.shape[0] == 0 or q.shape[0] != q.shape[1]:
            raise ValueError("Q must be a nonempty square matrix")
        b = vector(self.b, q.shape[0], "b")
        xs = vector(self.x_star, q.shape[0], "x_star")
        scale = float(np.max(np.abs(q)))
        normalized = q / scale if scale else q.copy()
        if not np.allclose(normalized, normalized.T, rtol=0, atol=1e-12):
            raise ValueError("Q must be symmetric relative to its scale")
        # Preserve exactly symmetric/subnormal data; do not overflow Q+Q.T.
        if not np.array_equal(q, q.T):
            q = 0.5 * q + 0.5 * q.T
        with np.errstate(over="raise", invalid="raise"):
            eig = np.linalg.eigvalsh(q / scale) * scale if scale else np.zeros(q.shape[0])
            product = q @ xs
        if not np.all(np.isfinite(eig)) or eig[0] < 0:
            raise ValueError("Q must have finite nonnegative eigenvalues")
        # No absolute floor: otherwise tiny, nonstationary references pass as exact.
        magnitude = np.maximum(np.abs(product), np.abs(b))
        left = np.divide(product, magnitude, out=np.zeros_like(b), where=magnitude != 0)
        right = np.divide(b, magnitude, out=np.zeros_like(b), where=magnitude != 0)
        if np.any(np.abs(left - right) > 64 * np.finfo(float).eps * q.shape[0]):
            raise ValueError("x_star must satisfy Q @ x_star = b to relative floating precision")
        for name, value in (("Q", q), ("b", b), ("x_star", xs)):
            object.__setattr__(self, name, _freeze(value))
        object.__setattr__(self, "_L", float(eig[-1]))
        object.__setattr__(self, "_mu", float(eig[0]))

    @property
    def dim(self) -> int:
        return self.b.size

    @property
    def L(self) -> float:
        return self._L

    @property
    def mu(self) -> float:
        return self._mu

    def value(self, x: np.ndarray) -> float:
        x = vector(x, self.dim)
        return float(0.5 * x @ self.Q @ x - self.b @ x)

    def grad(self, x: np.ndarray) -> np.ndarray:
        return self.Q @ vector(x, self.dim) - self.b

    def gap(self, x: np.ndarray) -> float:
        """Avoid subtracting nearly equal objective values near the optimum."""
        e = vector(x, self.dim) - self.x_star
        return float(0.5 * e @ self.Q @ e)

    @property
    def f_star(self) -> float:
        return self.value(self.x_star)


@dataclass(frozen=True)
class SimplexQuadraticProblem:
    target: np.ndarray

    def __post_init__(self) -> None:
        target = array(self.target, "target")
        if target.ndim != 1 or target.size < 2:
            raise ValueError("target must be a vector with at least two entries")
        if np.any(target < 0) or not np.isclose(target.sum(), 1, rtol=0, atol=1e-12):
            raise ValueError("target must lie on the probability simplex")
        object.__setattr__(self, "target", _freeze(target))

    @property
    def dim(self) -> int:
        return self.target.size

    @property
    def x_star(self) -> np.ndarray:
        return self.target.copy()

    @property
    def f_star(self) -> float:
        return 0.0

    @property
    def curvature_upper_bound(self) -> float:
        return 2.0  # Hessian=I, squared Euclidean simplex diameter=2.

    def value(self, x: np.ndarray) -> float:
        e = vector(x, self.dim) - self.target
        return float(0.5 * e @ e)

    def gap(self, x: np.ndarray) -> float:
        return self.value(x)

    def grad(self, x: np.ndarray) -> np.ndarray:
        return vector(x, self.dim) - self.target

    def linear_minimizer(self, gradient: np.ndarray) -> np.ndarray:
        g = vector(gradient, self.dim, "gradient")
        vertex = np.zeros(self.dim)
        vertex[int(np.argmin(g))] = 1
        return vertex


@dataclass(frozen=True)
class DiagonalLassoProblem:
    a: np.ndarray
    b: np.ndarray
    lam: float

    def __post_init__(self) -> None:
        a = array(self.a, "a")
        if a.ndim != 1 or not a.size:
            raise ValueError("a must be a nonempty vector")
        b = vector(self.b, a.size, "b")
        if np.any(np.abs(a) < 1e-12):
            raise ValueError("all diagonal entries must be nonzero")
        object.__setattr__(self, "a", _freeze(a))
        object.__setattr__(self, "b", _freeze(b))
        object.__setattr__(self, "lam", scalar(self.lam, "lam"))

    @property
    def dim(self) -> int:
        return self.a.size

    @property
    def L(self) -> float:
        return float(np.max(self.a**2))

    def smooth_value(self, x: np.ndarray) -> float:
        residual = self.a * vector(x, self.dim) - self.b
        return float(0.5 * residual @ residual)

    def smooth_grad(self, x: np.ndarray) -> np.ndarray:
        return self.a * (self.a * vector(x, self.dim) - self.b)

    def value(self, x: np.ndarray) -> float:
        x = vector(x, self.dim)
        return self.smooth_value(x) + self.lam * float(np.abs(x).sum())

    def prox_l1(self, z: np.ndarray, step: float) -> np.ndarray:
        z = vector(z, self.dim, "z")
        threshold = scalar(step, "step") * self.lam
        return np.sign(z) * np.maximum(np.abs(z) - threshold, 0)

    @property
    def x_star(self) -> np.ndarray:
        ab = self.a * self.b
        return np.sign(ab) * np.maximum(np.abs(ab) - self.lam, 0) / self.a**2

    def gap(self, x: np.ndarray) -> float:
        """Quadratic error plus an l1 Bregman term, without F(x)-F(x*)."""
        x = vector(x, self.dim)
        error = self.a * (x - self.x_star)
        if self.lam == 0:
            return float(0.5 * error @ error)
        subgradient = np.clip(self.a * self.b / self.lam, -1, 1)
        return float(0.5 * error @ error + self.lam * np.sum(np.abs(x) - subgradient * x))

    @property
    def f_star(self) -> float:
        return self.value(self.x_star)


def smooth_convex_quadratic(dim: int = 80) -> QuadraticProblem:
    dim = count(dim, "dim", 4)
    q = np.diag(np.r_[0.0, np.geomspace(1e-5, 1, dim - 1)])
    xs = np.cos(np.arange(dim, dtype=float) * 0.37)
    xs[0] = 0
    return QuadraticProblem(q, q @ xs, xs)


def strongly_convex_quadratic(dim: int = 60, mu: float = 0.04, L: float = 1.0) -> QuadraticProblem:
    dim = count(dim, "dim", 2)
    mu, L = scalar(mu, "mu", positive=True), scalar(L, "L", positive=True)
    if mu >= L:
        raise ValueError("require 0 < mu < L")
    q = np.diag(np.geomspace(mu, L, dim))
    xs = np.sin(np.arange(dim, dtype=float) * 0.29) + 0.25
    return QuadraticProblem(q, q @ xs, xs)


def simplex_quadratic(dim: int = 50) -> SimplexQuadraticProblem:
    dim = count(dim, "dim", 2)
    return SimplexQuadraticProblem(np.full(dim, 1.0 / dim))


def diagonal_lasso(dim: int = 80, lam: float = 0.12) -> DiagonalLassoProblem:
    dim = count(dim, "dim", 2)
    a = np.linspace(0.35, 2.0, dim)
    idx = np.arange(dim, dtype=float)
    b = 0.8 * np.sin(idx * 0.41) + 0.35 * np.cos(idx * 0.13)
    return DiagonalLassoProblem(a, b, lam)
