"""Controlled spectral breadth for Shewchuk's CG polynomial explanation.

These declared 16-dimensional inputs extend the explanation in Section 9.1;
they are not the unspecified data behind Figure 31(d).
"""
from __future__ import annotations

import hashlib
import json
import math
import platform

import numpy as np

from . import __version__
from .methods import conjugate_gradient
from .problems import QuadraticProblem

SOURCE = "https://www.cs.cmu.edu/~quake-papers/painless-conjugate-gradient.pdf"


def hadamard_basis():
    h = np.ones((1, 1))
    for _ in range(4):
        h = np.block([[h, h], [h, -h]])
    return h / 4


def comparison_polynomials(degree):
    """Eq. (51)'s comparison polynomial, not a fitted actual CG polynomial."""
    grid = np.linspace(0, 8, 161)
    coefficients = [0.] * degree + [1.]
    denominator = float(np.polynomial.chebyshev.chebval(9/5, coefficients))
    values = np.polynomial.chebyshev.chebval((9-2*grid)/5, coefficients)/denominator
    rho = (math.sqrt(3.5)-1)/(math.sqrt(3.5)+1)
    return {
        "degree": degree, "abscissae": grid.tolist(), "values": values.tolist(),
        "interval_envelope": 1/denominator,
        "looser_envelope": 2*rho**degree,
    }


def run_cg_spectrum(steps: int = 32) -> dict:
    if type(steps) is not int or not 1 <= steps <= 64:
        raise ValueError("steps must be an integer between 1 and 64")
    spectra = {
        "two-values": np.array([2.]*8+[7.]*8),
        "two-clusters": np.r_[np.linspace(2, 2.1, 8), np.linspace(6.9, 7, 8)],
        "spread": np.linspace(2, 7, 16),
    }
    cases = []
    for spectrum_name, eigenvalues in spectra.items():
        for basis_name, basis in (("diagonal", np.eye(16)), ("hadamard", hadamard_basis())):
            matrix = (basis*eigenvalues) @ basis.T
            problem = QuadraticProblem(matrix, np.zeros(16), np.zeros(16))
            # Use exactly the matrix accepted by the shared solver, including its
            # symmetry normalization if construction rounded asymmetrically.
            matrix = problem.Q
            for profile in ("equal-coefficients", "equal-energy", "single-mode"):
                coefficients = (
                    np.ones(16) if profile == "equal-coefficients" else
                    1/np.sqrt(eigenvalues) if profile == "equal-energy" else np.eye(16)[0]
                )
                coefficients = coefficients / np.linalg.norm(coefficients)
                start = basis @ coefficients
                actual_initial = basis.T @ start
                initial_energy = float(2*problem.gap(start))
                initial_spectral_energy = float(np.sum(eigenvalues*actual_initial**2))
                initial_residual = float(np.hypot.reduce(problem.b-matrix@start))
                tolerance = 1e-12*initial_residual
                trace = conjugate_gradient(problem, steps, x0=start, rtol=1e-12, atol=0)
                rows = []
                for k, x in enumerate(trace.iterates):
                    modes = basis.T @ x
                    energies = eigenvalues*modes**2
                    spectral_energy = float(np.sum(energies))
                    direct_energy = float(2*problem.gap(x))
                    residual = problem.b-matrix@x
                    rows.append({
                        "iteration": k, "x": x.tolist(), "coefficients": modes.tolist(),
                        "component_ratios": [float(v/base) if base != 0 else None
                                             for v, base in zip(modes, actual_initial)],
                        "mode_energy": energies.tolist(),
                        "normalized_mode_energy": (energies/initial_spectral_energy).tolist(),
                        "direct_energy": direct_energy, "spectral_energy": spectral_energy,
                        "energy_identity_difference": direct_energy-spectral_energy,
                        "energy_ratio": math.sqrt(direct_energy/initial_energy),
                        "spectral_energy_ratio": math.sqrt(spectral_energy/initial_spectral_energy),
                        "euclidean_error": float(np.hypot.reduce(x)),
                        "objective": float(trace.values[k]),
                        "true_residual": residual.tolist(),
                        "true_residual_norm": float(np.hypot.reduce(residual)),
                    })
                # One declared quadratic witness: roots at the means of the first
                # and second halves of the sorted spectrum, without outcome selection.
                roots = [float(np.mean(eigenvalues[:8])), float(np.mean(eigenvalues[8:]))]
                grid = np.linspace(0, 8, 161)
                witness = (1-grid/roots[0])*(1-grid/roots[1])
                witness_nodes = (1-eigenvalues/roots[0])*(1-eigenvalues/roots[1])
                active = actual_initial != 0
                digest = hashlib.sha256(np.r_[matrix.ravel(), problem.b, start].astype('<f8').tobytes()).hexdigest()
                cases.append({
                    "id": f"{spectrum_name}-{basis_name}-{profile}",
                    "spectrum": spectrum_name, "basis_name": basis_name, "start_profile": profile,
                    "dimension": 16, "declared_eigenvalues": eigenvalues.tolist(),
                    "basis": basis.tolist(), "basis_layout": "columns are the declared construction modes",
                    "A": matrix.tolist(), "b": problem.b.tolist(), "x_star": problem.x_star.tolist(),
                    "start": start.tolist(), "declared_initial_coefficients": coefficients.tolist(),
                    "actual_initial_coefficients": actual_initial.tolist(),
                    "initial_energy": initial_energy, "initial_spectral_energy": initial_spectral_energy,
                    "initial_residual_norm": initial_residual, "residual_tolerance": tolerance,
                    "input_sha256": digest, "declared_condition_number": 3.5,
                    "realized_mu": problem.mu, "realized_L": problem.L,
                    "realized_condition_number": problem.L/problem.mu,
                    "distinct_declared_eigenvalues": len(set(eigenvalues)),
                    "active_declared_eigenvalues": sorted(set(eigenvalues[active])),
                    "basis_orthogonality_error_inf": float(np.max(np.abs(basis.T@basis-np.eye(16)))),
                    "eigen_equation_error_inf": float(np.max(np.abs(matrix@basis-basis*eigenvalues))),
                    "completed_updates": len(rows)-1, "termination": trace.termination,
                    "rows": rows,
                    "quadratic_witness": {
                        "degree": 2, "roots": roots, "abscissae": grid.tolist(),
                        "values": witness.tolist(), "at_eigenvalues": witness_nodes.tolist(),
                        "all_spectrum_factor": float(np.max(np.abs(witness_nodes))),
                        "active_spectrum_factor": float(np.max(np.abs(witness_nodes[active]))),
                        "weighted_energy_factor": math.sqrt(float(np.sum(
                            eigenvalues*actual_initial**2*witness_nodes**2))/initial_spectral_energy),
                        "rule": "roots at the arithmetic means of sorted modes 0:8 and 8:16",
                        "scope": "declared comparison polynomial, not an actual CG polynomial",
                    },
                })
    result = {
        "kind": "chainbench.cg-spectrum", "schema_version": 1,
        "evidence_level": "controlled-spectral-illustrations",
        "source": {
            "author": "Jonathan Richard Shewchuk", "year": 1994, "url": SOURCE,
            "polynomial": "Section 9.1, pp.33–35 / PDF 39–41, Eq. (50), Figure 31",
            "interval": "Section 9.2, p.36 / PDF 42, Eqs. (51)–(52), Figure 33",
            "scope": "new declared inputs illustrating the published spectral reasoning; not Figure 31(d)'s original data",
        },
        "parameters": {
            "steps": steps, "dimension": 16, "rtol": 1e-12, "atol": 0., "seed": None,
            "stopping": "true residual norm <= rtol times initial true residual norm, or budget exhausted",
            "recurrence": "existing scaled correction-equation CG; no new optimizer",
            "declared_interval": [2., 7.], "declared_condition_number": 3.5,
        },
        "design": "all 3 spectra x 2 orthogonal bases x 3 initial-error profiles, without performance filtering",
        "problem": "f(x)=0.5*x^T*A*x; b=0; x*=0; ||x0||_2=1",
        "input_hash_encoding": "SHA-256 little-endian float64 row-major A, then b, then x0",
        "comparisons": [comparison_polynomials(k) for k in range(max(c['completed_updates'] for c in cases)+1)],
        "cases": cases,
        "environment": {"chainbench": __version__, "numpy": np.__version__, "python": platform.python_version()},
        "limits": [
            "These are declared constructed inputs, not a reproduction of the unspecified Figure 31(d) data.",
            "Exact-arithmetic polynomial bounds and termination counts are not floating-point certificates.",
            "The stored matrix is rounded; construction-mode residuals and energy-identity differences are retained.",
            "Continuous comparison curves are not fitted actual CG polynomials; actual ratios occur only at declared modes.",
            "Component ratios are null when the initial mode coefficient is exactly zero; raw errors are never forced to zero.",
            "One dimension and interval do not establish representative performance or a universal method ranking.",
        ],
    }
    json.dumps(result, allow_nan=False)
    return result
