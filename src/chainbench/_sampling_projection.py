"""Actual recorded Fourier row updates and a separate exact-arithmetic kernel model."""

import numpy as np


def normalized_dirichlet(offsets, bandlimit):
    """Periodic sum of frequencies -r..r divided by 2r+1, stable at integer offsets."""
    if type(bandlimit) is not int or bandlimit < 0:
        raise ValueError("bandlimit must be a nonnegative integer")
    values = np.asarray(offsets, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("kernel offsets must be finite")
    wrapped = (values + 0.5) % 1 - 0.5
    return np.sinc((2 * bandlimit + 1) * wrapped) / np.sinc(wrapped)


def _complex(values):
    values = np.asarray(values, dtype=complex)
    return dict(real=values.real.tolist(), imag=values.imag.tolist())


def projection_response(previous, following, row, observed, node, frequencies, display_grid):
    """Retain the actual prior state; never recover it by reversing a rounded update."""
    n = len(frequencies)
    if n % 2 != 1 or not np.array_equal(frequencies, np.arange(-(n // 2), n // 2 + 1)):
        raise ValueError("a symmetric odd Fourier frequency set is required")
    grid = np.unique(np.r_[display_grid, node])
    operator = np.exp(2j * np.pi * grid[:, None] * frequencies)
    denominator = float(np.vdot(row, row).real)
    residual = observed - np.dot(row, previous)
    correction = following - previous
    ideal_coefficients = residual / denominator * np.conjugate(row)
    before, after = operator @ previous, operator @ following
    change = operator @ correction
    kernel = normalized_dirichlet(grid - node, n // 2)
    ideal_change = (residual * n / denominator) * kernel
    node_index = int(np.flatnonzero(grid == node)[0])
    return dict(
        previous_coefficients=_complex(previous),
        coefficient_correction=_complex(correction),
        grid=grid.tolist(),
        node_index=node_index,
        row_norm_squared=denominator,
        projection_residual=_complex(residual),
        previous_signal=_complex(before),
        next_signal=_complex(after),
        correction_signal=_complex(change),
        normalized_kernel=kernel.tolist(),
        ideal_signal_correction=_complex(ideal_change),
        coefficient_roundoff_inf=float(np.max(np.abs(correction - ideal_coefficients))),
        kernel_comparison_error_inf=float(np.max(np.abs(change - ideal_change))),
        linearity_residual_inf=float(np.max(np.abs(after - before - change))),
    )
