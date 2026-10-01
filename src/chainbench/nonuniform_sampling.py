"""Declared-input rerun of Strohmer--Vershynin's nonuniform sampling protocol.

arXiv:math/0702226v1, Section 4.1 / Eq. (18) / Figure 1. The paper does not
supply its nodes, signal coefficients, initial point or random stream.
"""

from __future__ import annotations

import hashlib
import json
import platform

import numpy as np

from . import __version__
from ._sampling_projection import projection_response

SOURCE = "https://arxiv.org/pdf/math/0702226v1"
METHODS = ("cyclic", "uniform", "weighted")


def complex_record(values):
    a = np.asarray(values, dtype=complex)
    return dict(real=a.real.tolist(), imag=a.imag.tolist())


def _hash(values):
    a = np.asarray(values)
    dtype = "<c16" if np.iscomplexobj(a) else "<f8"
    return hashlib.sha256(np.asarray(a, dtype=dtype).tobytes(order="C")).hexdigest()


def periodic_weights(nodes):
    t = np.asarray(nodes, dtype=float)
    if (
        t.ndim != 1
        or len(t) < 3
        or not np.isfinite(t).all()
        or t[0] < 0
        or t[-1] >= 1
        or np.any(np.diff(t) <= 0)
    ):
        raise ValueError("nodes must be distinct, sorted, finite points in [0,1)")
    previous = np.r_[t[-1] - 1, t[:-1]]
    following = np.r_[t[1:], t[0] + 1]
    weights = (following - previous) / 2
    if np.any(weights <= 0) or not np.isfinite(weights).all():
        raise FloatingPointError("invalid periodic sampling weights")
    return weights


def project_row(coefficients, row, value):
    """Complex orthogonal projection using the conjugate row direction."""
    denominator = float(np.vdot(row, row).real)
    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError("projection requires a finite nonzero row")
    return coefficients + (value - np.dot(row, coefficients)) / denominator * np.conjugate(row)


def _case(seed, steps, snapshots, grid):
    r, m = 50, 700
    n = 2 * r + 1

    def rng(stream):
        return np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, stream])))

    nodes = np.sort(rng(0).uniform(size=m))
    weights = periodic_weights(nodes)
    probabilities = weights / weights.sum()
    frequencies = np.arange(-r, r + 1)
    basis = np.exp(2j * np.pi * nodes[:, None] * frequencies)
    generator = rng(1)
    truth = np.zeros(n, dtype=complex)
    truth[r] = generator.normal()
    positive = (generator.normal(size=r) + 1j * generator.normal(size=r)) / np.sqrt(2)
    truth[r + 1 :], truth[:r] = positive, np.conjugate(positive[::-1])
    truth /= np.linalg.norm(truth)
    samples = basis @ truth
    draws = rng(2).uniform(size=steps)
    cumulative = np.cumsum(probabilities)
    cumulative[-1] = 1.0
    selections = {
        "cyclic": np.arange(steps) % m,
        "uniform": np.floor(draws * m).astype(int),
        "weighted": np.searchsorted(cumulative, draws, side="right"),
    }
    display_basis = np.exp(2j * np.pi * grid[:, None] * frequencies)
    singular = np.linalg.svd(np.sqrt(weights)[:, None] * basis, compute_uv=False)
    if not np.isfinite(singular).all() or singular[-1] <= 0:
        raise FloatingPointError("weighted sampling operator is not numerically full rank")
    gaps = np.diff(np.r_[nodes, nodes[0] + 1])
    delta = float(np.max(gaps))
    applicable = 2 * r * delta < 1
    condition_bound = (1 + 2 * r * delta) / (1 - 2 * r * delta) if applicable else None
    runs = {}
    for method, choices in selections.items():
        x = np.zeros(n, dtype=complex)
        errors, squared, saved = [], [], []
        projection = None
        for k in range(steps + 1):
            difference = x - truth
            error_squared = float(np.vdot(difference, difference).real)
            if not np.isfinite(error_squared) or error_squared < 0:
                raise FloatingPointError("invalid coefficient error")
            errors.append(float(np.sqrt(error_squared)))
            squared.append(error_squared)
            if k in snapshots:
                signal = display_basis @ x
                residual = np.sqrt(weights) * (basis @ x - samples)
                saved.append(
                    dict(
                        iteration=k,
                        coefficients=complex_record(x),
                        coefficients_sha256=_hash(x),
                        signal=complex_record(signal),
                        weighted_residual_l2=float(np.linalg.norm(residual)),
                        last_projection=projection,
                    )
                )
            if k == steps:
                break
            i = int(choices[k])
            row = basis[i]
            # All Fourier rows have squared norm n. Periodic positive row
            # weights cancel in this projection and only change sampling.
            nxt = project_row(x, row, samples[i])
            if k + 1 in snapshots:
                correction = nxt - x
                following_error = nxt - truth
                after = float(np.vdot(following_error, following_error).real)
                removed = float(np.vdot(correction, correction).real)
                projection = dict(
                    row=i,
                    node=float(nodes[i]),
                    probability=(
                        None
                        if method == "cyclic"
                        else float(1 / m if method == "uniform" else probabilities[i])
                    ),
                    prediction_before=complex_record(np.dot(row, x)),
                    prediction_after=complex_record(np.dot(row, nxt)),
                    observed=complex_record(samples[i]),
                    previous_error_squared=error_squared,
                    next_error_squared=after,
                    correction_squared=removed,
                    pythagorean_residual=error_squared - after - removed,
                    signal_update=projection_response(
                        x, nxt, row, samples[i], nodes[i], frequencies, grid
                    ),
                )
            x = nxt
        runs[method] = dict(
            rows=choices.tolist(),
            error_l2=errors,
            error_squared=squared,
            snapshots=saved,
            updates=steps,
            termination="fixed_budget",
        )
    return dict(
        id=f"seed-{seed}",
        seed=seed,
        nodes=nodes.tolist(),
        weights=weights.tolist(),
        probabilities=probabilities.tolist(),
        periodic_gaps=gaps.tolist(),
        frequencies=frequencies.tolist(),
        truth_coefficients=complex_record(truth),
        observed_samples=complex_record(samples),
        truth_signal=complex_record(display_basis @ truth),
        sampling_uniforms=draws.tolist(),
        input_hashes={
            key: _hash(value)
            for key, value in (
                ("nodes", nodes),
                ("weights", weights),
                ("truth_coefficients", truth),
                ("observed_samples", samples),
                ("sampling_uniforms", draws),
            )
        },
        conditioning=dict(
            singular_values=singular.tolist(),
            spectral_condition=float(singular[0] / singular[-1]),
            scaled_condition_squared=float(n * weights.sum() / singular[-1] ** 2),
            max_periodic_gap=delta,
            theorem4_applicable=applicable,
            theorem4_condition_upper=condition_bound,
            theorem4_bound_three_applicable=delta <= 1 / (4 * r),
        ),
        runs=runs,
    )


def run_nonuniform_sampling(steps: int = 15000) -> dict:
    if type(steps) is not int or not 1 <= steps <= 15000:
        raise ValueError("steps must be an integer between 1 and 15000")
    snapshots = sorted(
        {0, 1, steps} | {k for k in (10, 100, 1000, 5000, 10000, 15000) if k <= steps}
    )
    grid = np.linspace(0, 1, 513)
    result = dict(
        kind="chainbench.nonuniform-sampling",
        schema_version=1,
        evidence_level="published-protocol-rerun-with-declared-inputs",
        source=dict(
            url=SOURCE,
            version="arXiv:math/0702226v1 (2007), later journal publication 2009",
            locations="Section 4.1: Eq. (18), p.10; protocol and Theorem 4, p.11; Figure 1, p.12",
            journal_doi="10.1007/s00041-008-9030-4",
        ),
        parameters=dict(
            bandlimit=50,
            sample_count=700,
            dimension=101,
            steps=steps,
            paper_plot_budget=15000,
            full_paper_plot_budget=steps == 15000,
            seeds=[0, 1, 2],
            snapshot_iterations=snapshots,
        ),
        conventions=dict(
            operator="A_jk=sqrt(w_j)*exp(2*pi*i*k*t_j), k=-50,...,50; b_j=sqrt(w_j)*f(t_j)",
            weights="w_j=(t_next-t_previous)/2, with periodic neighbors on the unit torus; p=w/sum(w)",
            initialization="All three methods start at the zero coefficient vector",
            rng="Generator(PCG64(SeedSequence([seed,stream]))): streams 0 nodes, 1 real-signal coefficients, 2 shared uniform row-selection draws",
            truth="DC standard normal; positive-frequency coefficients (N(0,1)+i*N(0,1))/sqrt(2), negative frequencies conjugate-reflected; normalize coefficient L2 norm to 1",
            sampling="Cyclic ascending row order; uniform floor(m*u); weighted inverse CDF with side=right and final CDF endpoint 1. Same u couples randomized choices within each case",
            projection="x_next=x+(f_j-dot(v_j,x))/real(vdot(v_j,v_j))*conj(v_j); positive row weight cancels",
            metric="Figure 1 uses coefficient error ||x_k-x_true||_2, not its square or data residual",
            hash_encoding="SHA-256 of row-major little-endian float64 real arrays or complex128 (real/imag interleaved) complex arrays",
        ),
        display_grid=grid.tolist(),
        projection_geometry=dict(
            kind="chainbench.fourier-projection-response",
            schema_version=1,
            source="Derived from Section 4.1 Eq. (18)'s finite Fourier basis and Algorithm 1's row projection; not an original paper figure",
            identity="K_r(t-t_j)=sum_{q=-r}^r exp(2*pi*i*q*(t-t_j))/(2*r+1); ideal delta_f=(observed-v_j*x)*(2*r+1)/||v_j||^2*K_r",
            actual="Actual previous coefficients and rounded following-minus-previous correction are retained during execution",
            comparison="The kernel predicts the exact-arithmetic update. Raw differences from the actual floating-point correction are retained, including at roundoff",
            grid="The 513 display nodes plus the selected observation node, sorted and deduplicated; the kernel center is explicitly sampled",
        ),
        cases=[_case(seed, steps, snapshots, grid) for seed in (0, 1, 2)],
        differences=[
            "Original nodes, signal coefficients, initial point and random stream are unavailable; the declared inputs are additions, not a recovery of Figure 1 pixels or endpoints.",
            "All three declared seeds are retained; no selection based on convergence or Theorem 4's gap condition.",
            "The source prose says row norm, while Algorithm 1 and Eq. (18) give squared row norm n*w_j; this implementation uses p_j=w_j/sum(w).",
            "The plotted maximum of 15000 projections is the full default budget; smaller budgets are previews.",
        ],
        limits=[
            "Three declared instances are not representative sampling or an expectation estimate; no universal method ranking is asserted.",
            "Coefficient error includes both real and imaginary parts. Waveform plots show the real part; the full complex arrays remain in the evidence.",
            "Theorem 4's sufficient condition is checked separately; an inapplicable bound is null, not a replaced seed or a failed linear solve.",
            "Differences near floating-point roundoff are retained and are not evidence of a meaningful speed ranking.",
        ],
        environment=dict(
            chainbench=__version__, numpy=np.__version__, python=platform.python_version()
        ),
    )
    json.dumps(result, allow_nan=False)
    return result
