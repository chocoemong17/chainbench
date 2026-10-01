"""Published noisy-image protocol with a declared, separately generated noise draw.

Beck--Teboulle (2009) Section 5.2 / Figure 4. The source does not publish its
noise samples; this is a protocol rerun, not a match to the original pixels.
"""

from __future__ import annotations

import hashlib
import json
import platform

import numpy as np

from . import __version__, _regutools_image
from ._lasso_duality import SOURCE as DUAL_SOURCE
from ._lasso_duality import residual_dual_bound
from .deblurring import SOURCE, blur_matrix
from .methods import _proximal_iterates


def haar(image: np.ndarray, inverse: bool = False) -> np.ndarray:
    """Three orthonormal separable Haar stages, recursing in the top-left block.

    Rows/columns pair even then odd samples; detail=(even-odd)/sqrt(2).
    The inverse applies the transposed stages in reverse order.
    """
    out = np.asarray(image, dtype=float).copy()
    if out.ndim != 2 or out.shape[0] != out.shape[1] or out.shape[0] < 8 or out.shape[0] % 8:
        raise ValueError("Haar input must be square with side divisible by eight")
    if not np.all(np.isfinite(out)):
        raise ValueError("Haar input must be finite")
    n = len(out)
    sizes = (n // 4, n // 2, n) if inverse else (n, n // 2, n // 4)
    scale = np.sqrt(2.0)
    for size in sizes:
        block = out[:size, :size].copy()
        half = size // 2
        if inverse:
            rows = np.empty_like(block)
            rows[::2] = (block[:half] + block[half:]) / scale
            rows[1::2] = (block[:half] - block[half:]) / scale
            out[:size, :size:2] = (rows[:, :half] + rows[:, half:]) / scale
            out[:size, 1:size:2] = (rows[:, :half] - rows[:, half:]) / scale
        else:
            cols = np.concatenate(
                (
                    (block[:, ::2] + block[:, 1::2]) / scale,
                    (block[:, ::2] - block[:, 1::2]) / scale,
                ),
                axis=1,
            )
            out[:size, :size] = np.concatenate(
                ((cols[::2] + cols[1::2]) / scale, (cols[::2] - cols[1::2]) / scale), axis=0
            )
    return out


def blur(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Nine-tap separable symmetric blur, without a dense 65536² matrix."""
    n = len(image)
    padded = np.pad(image, ((0, 0), (4, 4)), mode="symmetric")
    horizontal = sum(w * padded[:, j : j + n] for j, w in enumerate(kernel))
    padded = np.pad(horizontal, ((4, 4), (0, 0)), mode="symmetric")
    return sum(w * padded[j : j + n] for j, w in enumerate(kernel))


class WaveletLasso:
    """F(c)=||R W c-b||²+lambda||c||1, W orthonormal synthesis."""

    def __init__(self, observed, kernel, lam=1e-4):
        self.observed, self.kernel, self.lam = observed, kernel, lam
        self.n, self.dim, self.L = len(observed), observed.size, 2.0

    def synthesize(self, x):
        return haar(x.reshape(self.n, self.n), inverse=True)

    def smooth_grad(self, x):
        residual = blur(self.synthesize(x), self.kernel) - self.observed
        # The centered symmetric kernel and edge-repeat rule make R self-adjoint.
        return (2 * haar(blur(residual, self.kernel))).ravel()

    def prox_l1(self, x, step):
        return np.sign(x) * np.maximum(np.abs(x) - self.lam * step, 0.0)

    def value(self, x):
        residual = blur(self.synthesize(x), self.kernel) - self.observed
        return float(np.sum(residual**2) + self.lam * np.sum(np.abs(x)))


def array_hash(array):
    return hashlib.sha256(np.asarray(array, dtype="<f8").tobytes(order="C")).hexdigest()


def run_wavelet_deblurring(steps: int = 200, seed: int = 0) -> dict:
    if type(steps) is not int or not 1 <= steps <= 200:
        raise ValueError("steps must be an integer between 1 and 200")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("seed must be an integer between 0 and 2**32-1")
    clean = _regutools_image.simple_image(256)
    _, kernel = blur_matrix(8)
    noise = np.random.Generator(np.random.PCG64(seed)).normal(0.0, 1e-3, clean.shape)
    observed = blur(clean, kernel) + noise
    p = WaveletLasso(observed, kernel)
    initial = haar(observed).ravel()
    snapshots = sorted({0, 1, steps} | {k for k in (10, 100, 200) if k <= steps})
    runs = {}
    for method in ("ista", "fista"):
        rows, saved = [], []
        for k, x in enumerate(_proximal_iterates(p, steps, initial, accelerated=method == "fista")):
            image = p.synthesize(x)
            residual = blur(image, kernel) - observed
            smooth, penalty = float(np.sum(residual**2)), float(p.lam * np.sum(np.abs(x)))
            rmse = float(np.sqrt(np.mean((image - clean) ** 2)))
            if not np.isfinite(smooth + penalty + rmse):
                raise FloatingPointError("nonfinite wavelet observation")
            rows.append(
                dict(
                    iteration=k,
                    objective=smooth + penalty,
                    squared_residual=smooth,
                    penalty=penalty,
                    image_rmse=rmse,
                    zero_coefficients=int(np.count_nonzero(x == 0.0)),
                )
            )
            if k in snapshots:
                prox = p.prox_l1(x - p.smooth_grad(x) / p.L, 1 / p.L)
                saved.append(
                    dict(
                        iteration=k,
                        image=image.tolist(),
                        coefficients=x.reshape(256, 256).tolist(),
                        image_sha256=array_hash(image),
                        coefficients_sha256=array_hash(x),
                        proximal_gradient_norm=float(np.linalg.norm(p.L * (x - prox))),
                        image_range=[float(image.min()), float(image.max())],
                        dual_bound=residual_dual_bound(
                            residual,
                            observed,
                            x.reshape(256, 256),
                            lambda v: haar(blur(v, kernel)),
                            p.lam,
                        ),
                    )
                )
        runs[method] = dict(rows=rows, snapshots=saved, updates=steps, termination="fixed_budget")
    gradient = p.smooth_grad(initial)
    before = initial - gradient / 2
    after = p.prox_l1(before, 0.5)
    # Explicit categories illustrate shrinkage; full arrays remain recomputable.
    candidates = [
        int(np.argmin(np.abs(before))),
        int(np.argmax(np.abs(before))),
        int(np.argmin(np.abs(np.abs(before) - p.lam / 2))),
    ]
    first_step = [
        dict(
            index=i,
            coefficient=float(initial[i]),
            gradient=float(gradient[i]),
            before_threshold=float(before[i]),
            after_threshold=float(after[i]),
        )
        for i in candidates
    ]
    result = {
        "kind": "chainbench.wavelet-deblurring",
        "schema_version": 1,
        "evidence_level": "published-protocol-rerun-with-declared-noise",
        "source": {
            "url": SOURCE,
            "experiment": "Section 5.2 / Figure 4, printed pp.197,199-200 / PDF pages15,17-18",
            "image_version": "Regularization Tools 4.1 (March 2008), image subset of blur.m",
            "image_url": "https://www.netlib.org/numeralgo/na4-matlab7.tgz",
            "image_archive_sha256": "07a8e8844a5593fc8ba739428b7637391342d8467be989bfb08681ee65f24b97",
            "image_source_sha256": "6ab03d347375aab26c847d924ff00cd1936d5324be53adcf4409a910f6890ac5",
            "image_permission_notice": _regutools_image.__doc__,
        },
        "parameters": dict(
            steps=steps,
            paper_budget=200,
            full_paper_budget=steps == 200,
            seed=seed,
            rng="numpy.PCG64 + Generator.normal; exact noise array retained",
            noise_std=0.001,
            step_size=0.5,
            L=2.0,
            lam=0.0001,
            threshold=0.00005,
            haar_levels=3,
            snapshot_iterations=snapshots,
        ),
        "problem": dict(
            shape=[256, 256],
            dimension=65536,
            objective="||R W c-b||_F^2 + lambda*||c||_1",
            f_star=None,
            clean_image=clean.tolist(),
            observed_image=observed.tolist(),
            noise=noise.tolist(),
            kernel_1d=kernel.tolist(),
            initialization="c0=W^T b, y0=c0, t0=1",
            boundary="symmetric edge-repeat: -1->0, n->n-1",
            coefficient_layout="three separable stages, LL top-left, x detail top-right, y detail bottom-left, both detail bottom-right; even-minus-odd sign",
        ),
        "input_hashes": {
            name: array_hash(v)
            for name, v in [
                ("clean", clean),
                ("observed", observed),
                ("noise", noise),
                ("kernel", kernel),
            ]
        },
        "hash_encoding": "SHA-256 of row-major little-endian float64 array bytes",
        "first_step": first_step,
        "first_step_selection": [
            "smallest |z|",
            "largest |z|",
            "nearest |z| to threshold; first index breaks ties",
        ],
        "runs": runs,
        "duality": dict(DUAL_SOURCE),
        "environment": dict(
            chainbench=__version__,
            python=platform.python_version(),
            numpy=np.__version__,
            os=platform.system(),
        ),
        "differences": [
            "The paper does not supply its noise draw; the declared seeded draw is a ChainBench addition.",
            "The paper does not identify the image-generator version hash or all Haar implementation conventions.",
            "ISTA and FISTA only; MTWIST and Cameraman are omitted.",
            "Images, residual/penalty decomposition, coefficient counts and stationarity readouts are independently recomputed.",
        ],
        "limits": [
            "No match to Figure 4 pixels or reported endpoint values is asserted.",
            "The noisy penalized optimum is not supplied: F is an objective, not an optimality gap.",
            "One declared noise draw is not representative sampling or a universal method ranking.",
            "All coefficients, including coarse approximation coefficients, are penalized; images are never clipped during optimization.",
        ],
    }
    json.dumps(result, allow_nan=False)
    return result
