"""Independently recomputed, precisely scoped public-paper examples.

Shewchuk (1994), Eq. (4), Figs. 8/30. The nine extra starts are our
controlled variations, not additional figures or representative sampling.
"""
from __future__ import annotations

import hashlib
import json
import platform

import numpy as np

from . import __version__
from ._conjugacy import add_metric_coordinates
from ._spectral import add_spectral_coordinates
from .methods import Trace, conjugate_gradient
from .problems import QuadraticProblem

SOURCE_URL = "https://www.cs.cmu.edu/~quake-papers/painless-conjugate-gradient.pdf"
SOURCE = {
    "author": "Jonathan Richard Shewchuk",
    "title": "An Introduction to the Conjugate Gradient Method Without the Agonizing Pain",
    "edition": "1 1/4, August 4, 1994",
    "url": SOURCE_URL,
    "pdf_sha256": "368110e5592d0d3e0b62884bcfffae00eb4a1ca9f850961ca1b594c3a32313e0",
    "setup": "Section 3, Eq. (4), printed p. 2 / PDF page 8",
    "sd": "Section 4, Eqs. (10)-(12), Figure 8, printed p. 8 / PDF page 14",
    "cg": "Section 8, Eqs. (45)-(49), Figure 30, printed p. 32 / PDF page 38",
    "envelope": "Section 9.2, Eq. (52), printed p. 36 / PDF page 42",
    "conjugacy": "Section 7.1, Figure 22, printed pp. 22-23 / PDF pages 28-29",
    "spectral": "Sections 9.1-9.2, Eq. (50), Figures 31(a-c)/33, printed pp. 33-36 / PDF pages 39-42",
}
METHOD_LABELS = {"sd": "Steepest descent (exact line search)", "cg": "Conjugate gradient"}
RTOL = 1e-12


def _steepest_descent(problem: QuadraticProblem, start: np.ndarray, steps: int) -> Trace:
    """Eqs. (10)-(12), deliberately separate from fixed-step GD.

    Only used on the bounded published SPD fixture. Recompute the residual;
    use the same true-residual stopping rule as the existing CG implementation.
    """
    x = start.copy()
    xs = [x.copy()]
    residual = problem.b - problem.Q @ x
    tolerance = RTOL * float(np.linalg.norm(residual))
    for _ in range(steps):
        if np.linalg.norm(residual) <= tolerance:
            break
        alpha = float(residual @ residual / (residual @ problem.Q @ residual))
        x = x + alpha * residual
        xs.append(x.copy())
        residual = problem.b - problem.Q @ x
    norm = float(np.linalg.norm(residual))
    return Trace(xs, np.array([problem.value(x) for x in xs]),
                 "converged" if norm <= tolerance else "max_steps", norm)


def input_digest(problem: dict, start: list[float]) -> str:
    """Hash actual float64 inputs in declared A, b, c, x0 order, little endian."""
    data = np.concatenate((np.asarray(problem["A"]).ravel(), problem["b"],
                           [problem["c"]], start)).astype("<f8")
    return hashlib.sha256(data.tobytes(order="C")).hexdigest()


def run_reproduction(steps: int = 12) -> dict:
    if isinstance(steps, bool) or not isinstance(steps, int) or not 2 <= steps <= 40:
        raise ValueError("steps must be an integer between 2 and 40")
    p = QuadraticProblem(np.array([[3., 2.], [2., 6.]]),
                         np.array([2., -8.]), np.array([2., -2.]))
    problem = {"A": p.Q.tolist(), "b": p.b.tolist(), "c": 0.,
               "x_star": p.x_star.tolist(), "f_star": p.value(p.x_star),
               "dimension": 2, "L": p.L, "mu": p.mu, "kappa": p.L / p.mu}
    starts = [("paper", [-2., -2.])] + [
        (f"start-{i + 1}", [float(x), float(y)])
        for i, (x, y) in enumerate((x, y) for x in (-3, 0, 3) for y in (-4, 0, 3))
    ]
    cases = []
    for case_id, start in starts:
        x0 = np.array(start)
        initial_energy = np.sqrt(2 * p.gap(x0))
        rho = (np.sqrt(p.L / p.mu) - 1) / (np.sqrt(p.L / p.mu) + 1)
        traces = {"sd": _steepest_descent(p, x0, steps),
                  "cg": conjugate_gradient(p, steps, x0=x0, rtol=RTOL, atol=0.)}
        runs = {}
        for method, trace in traces.items():
            rows = []
            for k, x in enumerate(trace.iterates):
                rows.append({"iteration": k, "x": x.tolist(),
                             "objective": p.value(x), "gap": p.gap(x),
                             "energy_error": float(np.sqrt(2 * p.gap(x))),
                             "residual_norm": float(np.linalg.norm(p.grad(x)))})
            runs[method] = {"label": METHOD_LABELS[method], "rows": rows,
                            "updates": len(rows) - 1, "termination": trace.termination}
        cases.append({"id": case_id,
                      "evidence_level": "published-example-reproduction" if case_id == "paper"
                      else "controlled-variation",
                      "start": start, "input_sha256": input_digest(problem, start),
                      "runs": runs,
                      "cg_envelope": [float(2 * rho ** k * initial_energy)
                                      for k in range(steps + 1)]})
    result = {
        "kind": "chainbench.reproduction", "schema_version": 1,
        "topic": "shewchuk-1994", "source": dict(SOURCE), "problem": problem,
        "parameters": {"steps": steps, "rtol": RTOL, "atol": 0.,
                       "stopping": "||b-Ax|| <= rtol * ||b-Ax0|| (recomputed residual)",
                       "sd_step": "alpha_k = (r_k^T r_k)/(r_k^T A r_k)",
                       "cg": "existing scaled-correction CG; exact-arithmetic equivalent",
                       "seed": None, "lambda": None},
        "variation_design": {"x1": [-3, 0, 3], "x2": [-4, 0, 3],
                             "selection": "complete Cartesian grid; no filtering",
                             "scope": "nine additional starts on ONE unchanged 2D matrix"},
        "input_hash_encoding": "SHA-256 of little-endian float64 A(row-major), b, c, x0",
        "cases": cases,
        "metric_geometry": add_metric_coordinates(problem, cases),
        "spectral_geometry": add_spectral_coordinates(problem, cases),
        "environment": {"chainbench": __version__, "numpy": np.__version__,
                        "python": platform.python_version()},
        "differences": [
            "Independent numerical redraw; no original pixels or digitized curve data.",
            "Iteration budget and residual tolerance are ChainBench choices.",
            "CG uses a scaled correction equation and true-residual stopping.",
            "Contours use our stated levels; 3D, energy plots and nine extra starts are additions.",
            "Figure 22's metric explanation is applied to our computed paths, not its original vectors.",
            "Figures 31(a-c)/33 comparison polynomials are redrawn; actual component ratios are added observations.",
        ],
        "limits": [
            "A pedagogical 2D example, not a dataset benchmark or whole-paper reproduction.",
            "Nine starts do not establish breadth across dimensions, spectra or problem families.",
            "The Eq. (52) envelope is an exact-arithmetic theorem, not a floating-point certificate.",
            "Iteration counts are not timing or equal-work measurements; no universal ranking.",
        ],
    }
    # Reject a broken computation before any JSON/HTML can present it as evidence.
    json.dumps(result, allow_nan=False)
    return result
