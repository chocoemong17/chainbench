"""Shared validation; invalid numerical data must never appear to pass a check."""
from __future__ import annotations

from numbers import Integral, Real

import numpy as np


def count(value: int, name: str = "steps", minimum: int = 0) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer >= {minimum}")
    if value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


def scalar(value: float, name: str, *, positive: bool = False) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    value = float(value)
    if not np.isfinite(value) or value < 0 or (positive and value == 0):
        sign = "positive" if positive else "nonnegative"
        raise ValueError(f"{name} must be finite and {sign}")
    return value


def array(value: np.ndarray, name: str) -> np.ndarray:
    if np.iscomplexobj(value):
        raise ValueError(f"{name} must be real")
    out = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(out)):
        raise ValueError(f"{name} must contain only finite values")
    return out


def vector(value: np.ndarray, dim: int, name: str = "x") -> np.ndarray:
    out = array(value, name)
    if out.shape != (dim,):
        raise ValueError(f"{name} must have shape ({dim},)")
    return out


def initial(dim: int, x0: np.ndarray | None) -> np.ndarray:
    return np.zeros(dim) if x0 is None else vector(x0, dim, "x0").copy()
