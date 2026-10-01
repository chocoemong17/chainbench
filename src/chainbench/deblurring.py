"""Bounded, noiseless ISTA/FISTA subset of Beck--Teboulle Figure 5."""

from __future__ import annotations

import hashlib
import platform

import numpy as np

from . import __version__, _regutools_image
from ._regutools_image import simple_image
from .methods import _proximal_iterates

SOURCE = "https://www.tau.ac.il/~becka/FISTA.pdf"


def blur_matrix(n: int = 64) -> tuple[np.ndarray, np.ndarray]:
    """Separable 9-tap sigma-4 Gaussian with edge-repeating symmetric extension."""
    offsets = np.arange(-4, 5)
    kernel = np.exp(-(offsets**2) / (2 * 4.0**2))
    kernel /= kernel.sum()
    matrix = np.zeros((n, n))
    for i in range(n):
        for offset, weight in zip(offsets, kernel):
            j = i + int(offset)
            j = -j - 1 if j < 0 else 2 * n - 1 - j if j >= n else j
            matrix[i, j] += weight
    return matrix, kernel


class DeblurLeastSquares:
    """F(u)=||B u B.T - observed||_F² in image coordinates, no penalty/no clipping."""

    def __init__(self, observed, matrix):
        self.observed, self.matrix = observed, matrix
        self.n = len(matrix)
        self.dim, self.L = self.n**2, 2.0

    def apply(self, x):
        return self.matrix @ x.reshape(self.n, self.n) @ self.matrix.T

    def smooth_grad(self, x):
        return (2 * self.apply((self.apply(x) - self.observed).ravel())).ravel()

    def prox_l1(self, x, step):
        # lambda=0: the soft-threshold map is the identity.
        return x.copy()

    def value(self, x):
        residual = self.apply(x) - self.observed
        return float(np.sum(residual * residual))


def _hash(array):
    return hashlib.sha256(np.asarray(array, dtype="<f8").tobytes(order="C")).hexdigest()


def run_deblurring(steps: int = 10000) -> dict:
    if type(steps) is not int or not 1 <= steps <= 10000:
        raise ValueError("steps must be an integer between 1 and 10000")
    truth = simple_image()
    matrix, kernel = blur_matrix()
    observed = matrix @ truth @ matrix.T
    problem = DeblurLeastSquares(observed, matrix)
    checkpoints = sorted(
        {0, 1, steps} | {k for k in (10, 100, 200, 1000, 5000, 10000) if k <= steps}
    )
    runs = {}
    for name in ("ista", "fista"):
        rows, snapshots = [], []
        for k, x in enumerate(
            _proximal_iterates(problem, steps, observed.ravel(), accelerated=name == "fista")
        ):
            objective = problem.value(x)
            rmse = float(np.sqrt(np.mean((x - truth.ravel()) ** 2)))
            if not np.isfinite(objective + rmse):
                raise FloatingPointError("non-finite deblurring observation")
            rows.append({"iteration": k, "objective": objective, "image_rmse": rmse})
            if k in checkpoints:
                snapshots.append(
                    {
                        "iteration": k,
                        "image": x.reshape(64, 64).tolist(),
                        "sha256": _hash(x),
                        "range": [float(x.min()), float(x.max())],
                    }
                )
        runs[name] = {
            "rows": rows,
            "snapshots": snapshots,
            "updates": steps,
            "termination": "fixed_budget",
        }
    return {
        "kind": "chainbench.fista-deblurring",
        "schema_version": 1,
        "evidence_level": "published-experiment-protocol-rerun",
        "source": {
            "url": SOURCE,
            "experiment": "Section 5.2, Figure 5; printed pp.199,201 / PDF pages17,19",
            "image_url": "https://www.netlib.org/numeralgo/na4-matlab7.tgz",
            "image_permission_notice": _regutools_image.__doc__,
            "image_version": "Regularization Tools 4.1 (March 2008), REGU/blur.m image subset",
            "archive_sha256": "07a8e8844a5593fc8ba739428b7637391342d8467be989bfb08681ee65f24b97",
            "image_source_sha256": "6ab03d347375aab26c847d924ff00cd1936d5324be53adcf4409a910f6890ac5",
        },
        "parameters": {
            "steps": steps,
            "paper_budget": 10000,
            "full_paper_budget": steps == 10000,
            "snapshot_iterations": checkpoints,
            "step_size": 0.5,
            "lambda": 0.0,
            "seed": None,
            "noise_std": 0.0,
        },
        "problem": {
            "shape": [64, 64],
            "dimension": 4096,
            "objective": "||B u B.T - b||_F^2",
            "L": 2.0,
            "f_star": 0.0,
            "optimizer": "the clean image is a minimizer, not necessarily the unique one",
            "initialization": "observed blurred image",
            "boundary": "symmetric edge-repeat: -1->0, n->n-1",
            "kernel_size": 9,
            "kernel_sigma": 4.0,
            "kernel_1d": kernel.tolist(),
            "blur_matrix_1d": matrix.tolist(),
            "clean_image": truth.tolist(),
            "observed_image": observed.tolist(),
            "clean_sha256": _hash(truth),
            "observed_sha256": _hash(observed),
            "matrix_sha256": _hash(matrix),
        },
        "runs": runs,
        "environment": {
            "chainbench": __version__,
            "numpy": np.__version__,
            "python": platform.python_version(),
        },
        "coordinate_equivalence": "At lambda=0, orthonormal Haar W gives u=W x. ISTA/FISTA and extrapolation commute with W; this run uses image coordinates with the same full squared loss and L=2.",
        "source_reported": {
            "iteration": 10000,
            "ista_order": 1e-3,
            "fista_order": 1e-7,
            "meaning": "Approximate magnitudes in the paper text, not exact reference values or pass thresholds.",
        },
        "differences": [
            "ISTA/FISTA subset; MTWIST omitted.",
            "Image generator pinned to the inspected 2008 v4.1 archive; the paper cites the 1994 toolbox article without a version hash.",
            "Image-coordinate implementation uses lambda=0 orthonormal-transform equivalence; no Haar coefficient path is claimed.",
            "NumPy float64 and explicit edge-repeat boundary replace MATLAB implementations.",
            "Snapshots, RMSE and input hashes are added; all objective observations are retained.",
        ],
        "limits": [
            "One published synthetic experiment, not representative image data or a universal method ranking.",
            "f_star=0 is known from the noiseless construction. Small objective error need not imply small reconstruction error.",
            "Display images use fixed [0,1] clipping only; iterates, RMSE and objectives are never clipped.",
        ],
    }
