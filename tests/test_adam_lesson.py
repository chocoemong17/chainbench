"""Numerical correctness of the new lesson, independent of its video renderer."""

import math

import numpy as np
import pytest

from chainbench.adam_lesson import (
    ANGLE,
    METHODS,
    STEPS,
    gradient,
    iteration_at,
    objective,
    rotate,
    time_at,
    trajectory,
)


@pytest.mark.parametrize("point", [[-1.5, 0.2], [0.3, 1.3], [0.0, 0.0], [1.0, -0.5]])
def test_rotated_gradient_matches_finite_difference(point):
    h = 1e-6
    numeric = []
    for j in range(2):
        a = list(point)
        b = list(point)
        a[j] += h
        b[j] -= h
        numeric.append((objective(a) - objective(b)) / (2 * h))
    np.testing.assert_allclose(gradient(point), numeric, rtol=1e-7, atol=1e-7)


def test_known_minimum_and_rotation_preserve_distance():
    assert objective(rotate([1.0, 1.0])) < 1e-25
    np.testing.assert_allclose(gradient(rotate([1.0, 1.0])), 0, atol=1e-10)
    assert math.dist(rotate([-1.2, 1.0]), rotate([1.0, 1.0])) == pytest.approx(2.2)


@pytest.mark.parametrize("method", list(METHODS))
def test_every_update_matches_independent_numpy_recurrence(method):
    # Vectorized NumPy implementation, with an independently written chain rule.
    trace = trajectory(method)
    c, s = np.cos(ANGLE), np.sin(ANGLE)
    R = np.array([[c, -s], [s, c]])
    x = R @ [-1.2, 1.0]
    m = np.zeros(2)
    v = np.zeros(2)
    cfg = METHODS[method]
    expected = [x.copy()]
    for t in range(1, STEPS + 1):
        u, w = R.T @ x
        g = R @ np.array([2 * (u - 1) - 400 * u * (w - u * u), 200 * (w - u * u)])
        if method == "gd":
            update = cfg["alpha"] * g
        elif method == "momentum":
            m = cfg["beta"] * m + g
            update = cfg["alpha"] * m
        else:
            m = cfg["beta1"] * m + (1 - cfg["beta1"]) * g
            v = cfg["beta2"] * v + (1 - cfg["beta2"]) * g**2
            update = (
                cfg["alpha"]
                * (m / (1 - cfg["beta1"] ** t))
                / (np.sqrt(v / (1 - cfg["beta2"] ** t)) + cfg["epsilon"])
            )
        x = x - update
        expected.append(x.copy())
    actual = np.array([r["point"] for r in trace["rows"]])
    np.testing.assert_allclose(actual, expected, rtol=2e-9, atol=2e-10)
    uv = actual @ R
    loss = (1 - uv[:, 0]) ** 2 + 100 * (uv[:, 1] - uv[:, 0] ** 2) ** 2
    np.testing.assert_allclose([r["loss"] for r in trace["rows"]], loss, rtol=2e-7, atol=1e-13)
    np.testing.assert_allclose(
        [r["distance"] for r in trace["rows"]],
        np.linalg.norm(actual - R @ [1.0, 1.0], axis=1),
        rtol=1e-9,
        atol=1e-12,
    )


def test_adam_first_update_has_bias_correction():
    trace = trajectory("adam", steps=1)
    g = np.array(gradient(trace["rows"][0]["point"]))
    # At t=1, corrected moments are exactly g and g squared.
    want = -0.02 * g / (np.abs(g) + 1e-8)
    np.testing.assert_allclose(trace["rows"][1]["step"], want, rtol=1e-14, atol=1e-16)


def test_nonfinite_or_divergent_result_is_rejected():
    for alpha in [float("nan"), float("inf"), 0.0, -1.0]:
        with pytest.raises(ValueError):
            trajectory("adam", alpha=alpha)
    with pytest.raises(ValueError, match="Diverged"):
        trajectory("gd", alpha=10.0)


def test_film_mapping_selects_real_monotone_steps_with_both_endpoints():
    frames = [iteration_at(n / 24) for n in range(48 * 24)]
    assert frames[0] == 0 and frames[-1] == STEPS
    assert frames == sorted(frames)
    assert all(isinstance(k, int) and 0 <= k <= STEPS for k in frames)
    for k in [0, 1, 10, 60, 61, 1200, 2400]:
        assert abs(iteration_at(time_at(k)) - k) <= 1
