from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class QuadraticProblem:
    Q: np.ndarray
    b: np.ndarray
    x_star: np.ndarray

    def __post_init__(self) -> None:
        q = np.asarray(self.Q, dtype=float)
        b = np.asarray(self.b, dtype=float)
        x_star = np.asarray(self.x_star, dtype=float)
        if q.ndim != 2 or q.shape[0] != q.shape[1]:
            raise ValueError("Q must be square")
        if b.shape != (q.shape[0],) or x_star.shape != (q.shape[0],):
            raise ValueError("b and x_star must match Q")
        if not np.allclose(q, q.T, atol=1e-12):
            raise ValueError("Q must be symmetric")
        eigvals = np.linalg.eigvalsh(q)
        if eigvals[0] < -1e-12:
            raise ValueError("Q must be positive semidefinite")
        if not np.allclose(q @ x_star, b, atol=1e-10):
            raise ValueError("x_star must satisfy Q @ x_star = b")
        object.__setattr__(self, "Q", q)
        object.__setattr__(self, "b", b)
        object.__setattr__(self, "x_star", x_star)

    @property
    def dim(self) -> int:
        return self.b.size

    @property
    def L(self) -> float:
        return float(np.linalg.eigvalsh(self.Q)[-1])

    @property
    def mu(self) -> float:
        return max(0.0, float(np.linalg.eigvalsh(self.Q)[0]))

    def value(self, x: np.ndarray) -> float:
        x = np.asarray(x, dtype=float)
        return float(0.5 * x @ self.Q @ x - self.b @ x)

    def grad(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        return self.Q @ x - self.b

    @property
    def f_star(self) -> float:
        return self.value(self.x_star)


@dataclass(frozen=True)
class DiagonalLassoProblem:
    a: np.ndarray
    b: np.ndarray
    lam: float

    def __post_init__(self) -> None:
        a = np.asarray(self.a, dtype=float)
        b = np.asarray(self.b, dtype=float)
        if a.ndim != 1 or b.shape != a.shape:
            raise ValueError("a and b must be one-dimensional arrays of equal length")
        if np.any(np.abs(a) < 1e-12):
            raise ValueError("all diagonal entries must be nonzero")
        if self.lam < 0:
            raise ValueError("lam must be nonnegative")
        object.__setattr__(self, "a", a)
        object.__setattr__(self, "b", b)

    @property
    def dim(self) -> int:
        return self.a.size

    @property
    def L(self) -> float:
        return float(np.max(self.a**2))

    def smooth_value(self, x: np.ndarray) -> float:
        residual = self.a * np.asarray(x, dtype=float) - self.b
        return float(0.5 * residual @ residual)

    def smooth_grad(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        return self.a * (self.a * x - self.b)

    def value(self, x: np.ndarray) -> float:
        x = np.asarray(x, dtype=float)
        return self.smooth_value(x) + self.lam * float(np.linalg.norm(x, ord=1))

    def prox_l1(self, z: np.ndarray, step: float) -> np.ndarray:
        threshold = step * self.lam
        return np.sign(z) * np.maximum(np.abs(z) - threshold, 0.0)

    @property
    def x_star(self) -> np.ndarray:
        numer = self.a * self.b
        return np.sign(numer) * np.maximum(np.abs(numer) - self.lam, 0.0) / (self.a**2)

    @property
    def f_star(self) -> float:
        return self.value(self.x_star)


def smooth_convex_quadratic(dim: int = 80) -> QuadraticProblem:
    if dim < 4:
        raise ValueError("dim must be at least 4")
    positive = np.geomspace(1e-5, 1.0, dim - 1)
    eigvals = np.concatenate(([0.0], positive))
    q = np.diag(eigvals)
    x_star = np.cos(np.arange(dim, dtype=float) * 0.37)
    x_star[0] = 0.0
    b = q @ x_star
    return QuadraticProblem(q, b, x_star)


def strongly_convex_quadratic(dim: int = 60, mu: float = 0.04, L: float = 1.0) -> QuadraticProblem:
    if dim < 2:
        raise ValueError("dim must be at least 2")
    if not 0 < mu < L:
        raise ValueError("require 0 < mu < L")
    eigvals = np.geomspace(mu, L, dim)
    q = np.diag(eigvals)
    x_star = np.sin(np.arange(dim, dtype=float) * 0.29) + 0.25
    b = q @ x_star
    return QuadraticProblem(q, b, x_star)


def diagonal_lasso(dim: int = 80, lam: float = 0.12) -> DiagonalLassoProblem:
    if dim < 2:
        raise ValueError("dim must be at least 2")
    a = np.linspace(0.35, 2.0, dim)
    b = 0.8 * np.sin(np.arange(dim, dtype=float) * 0.41) + 0.35 * np.cos(
        np.arange(dim, dtype=float) * 0.13
    )
    return DiagonalLassoProblem(a=a, b=b, lam=lam)
