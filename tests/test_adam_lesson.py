"""Numerical correctness of the new lesson, independent of its video renderer."""

import json
import math
from pathlib import Path

import numpy as np
import pytest

from chainbench.adam_lesson import (
    METHODS,
    SCALE,
    START,
    STEPS,
    TARGET,
    experiment,
    gradient,
    iteration_at,
    objective,
    settled_step,
    time_at,
    trajectory,
)


@pytest.mark.parametrize("point", [[-1.5, 0.2], [0.3, 1.3], [0.0, 0.0], [1.0, -0.5]])
def test_quartic_gradient_matches_finite_difference(point):
    h = 1e-5
    numeric = []
    for j in range(2):
        a = list(point)
        b = list(point)
        a[j] += h
        b[j] -= h
        numeric.append((objective(a) - objective(b)) / (2 * h))
    np.testing.assert_allclose(gradient(point), numeric, rtol=2e-7, atol=2e-6)


def test_known_minimum_and_start():
    assert objective(TARGET) == 0
    assert gradient(TARGET) == [0, 0]
    assert objective(START) == 60024.75
    assert gradient(START) == [-30, 100000]
    assert math.dist(START, TARGET) == pytest.approx(math.sqrt(13))


@pytest.mark.parametrize("method", list(METHODS))
def test_every_update_matches_independent_numpy_recurrence(method):
    # Independent vector recurrence and direct polynomial derivative.
    trace = trajectory(method)
    x = np.array([-3., 2.])
    m = np.zeros(2)
    v = np.zeros(2)
    cfg = METHODS[method]
    expected = [x.copy()]
    for t in range(1, STEPS + 1):
        g = np.array([1., 10000.]) * (x + x**3)
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
    loss = (actual**2 / 2 + actual**4 / 4) @ np.array([1., SCALE])
    np.testing.assert_allclose([r["loss"] for r in trace["rows"]], loss, rtol=2e-7, atol=1e-13)
    np.testing.assert_allclose(
        [r["distance"] for r in trace["rows"]],
        np.linalg.norm(actual, axis=1),
        rtol=1e-9,
        atol=1e-12,
    )


def test_adam_first_update_has_bias_correction():
    trace = trajectory("adam", steps=1)
    g = np.array(gradient(trace["rows"][0]["point"]))
    # At t=1, corrected moments are exactly g and g squared.
    want = -0.14 * g / (np.abs(g) + 1e-8)
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
    for k in [0, 1, 10, 60, 61, 66, 67, 100, 611, 1200]:
        assert abs(iteration_at(time_at(k)) - k) <= 1


def test_approved_example_matches_archived_review_and_target_counts():
    path = Path(__file__).resolve().parents[1] / "docs/reviews/adam-example/proposal.json"
    approved = json.loads(path.read_text())["proposal"]
    record = experiment("0" * 40)
    assert record["target_test"]["settled"] == {"gd": None, "momentum": 611, "adam": 66}
    for method, data in approved["methods"].items():
        rows = record["traces"][method]["rows"]
        np.testing.assert_allclose([r["point"] for r in rows], data["path"], rtol=2e-8, atol=2e-9)
        assert settled_step(rows) == data["summary"]["settled"]


def test_early_clock_shows_every_step_and_holds_adam_arrival():
    early = {iteration_at(n / 24) for n in range(24 * 24 + 1)}
    assert early == set(range(67))
    assert all(iteration_at(n / 24) == 66 for n in range(24 * 24, 27 * 24 + 1))


def test_target_requires_both_metrics_and_remaining_budget():
    rows = [dict(loss=1, distance=1), dict(loss=1e-5, distance=1e-3),
            dict(loss=.1, distance=1e-3), dict(loss=1e-5, distance=1e-3)]
    assert settled_step(rows) == 3
    rows[-1]["distance"] = .1
    assert settled_step(rows) is None
