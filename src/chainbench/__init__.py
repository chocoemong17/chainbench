"""ChainBench: reproducible checks of classic optimization results."""

from .checks import CheckResult, run_all, run_check
from .methods import accelerated_gradient, conjugate_gradient, fista, gradient_descent, heavy_ball, ista
from .problems import (
    DiagonalLassoProblem,
    QuadraticProblem,
    diagonal_lasso,
    smooth_convex_quadratic,
    strongly_convex_quadratic,
)

__all__ = [
    "CheckResult",
    "DiagonalLassoProblem",
    "QuadraticProblem",
    "accelerated_gradient",
    "conjugate_gradient",
    "diagonal_lasso",
    "fista",
    "gradient_descent",
    "heavy_ball",
    "ista",
    "run_all",
    "run_check",
    "smooth_convex_quadratic",
    "strongly_convex_quadratic",
]

__version__ = "0.1.0"
