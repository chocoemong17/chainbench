"""ChainBench: reproducible checks of classic optimization results."""

from .checks import CheckResult, run_all, run_check
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
    DiagonalLassoProblem,
    QuadraticProblem,
    SimplexQuadraticProblem,
    diagonal_lasso,
    simplex_quadratic,
    smooth_convex_quadratic,
    strongly_convex_quadratic,
)

__all__ = [
    "CheckResult",
    "DiagonalLassoProblem",
    "QuadraticProblem",
    "SimplexQuadraticProblem",
    "accelerated_gradient",
    "conjugate_gradient",
    "diagonal_lasso",
    "fista",
    "frank_wolfe",
    "gradient_descent",
    "heavy_ball",
    "ista",
    "proximal_point",
    "run_all",
    "run_check",
    "simplex_quadratic",
    "smooth_convex_quadratic",
    "strongly_convex_quadratic",
]

__version__ = "0.1.0"
