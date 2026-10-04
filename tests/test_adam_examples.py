"""Gradient, optimizer and selection checks for the separate example study."""

import math
import runpy
from pathlib import Path

import numpy as np
import pytest

study = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/study_adam_examples.py"))


@pytest.mark.parametrize("case", study["cases"](), ids=lambda c: c["id"])
def test_objective_gradient_and_known_minimum(case):
    evaluate = study["evaluate"]
    f, g = evaluate(np.array(case["target"]), case)
    assert f == pytest.approx(0, abs=1e-24)
    np.testing.assert_allclose(g, [0, 0], atol=1e-10)
    for point in (case["start"], [0.7, -0.3], [-0.4, 0.9]):
        point = np.array(point, dtype=float)
        numerical = []
        for axis in np.eye(2):
            numerical.append((evaluate(point+1e-5*axis, case)[0]
                              - evaluate(point-1e-5*axis, case)[0]) / 2e-5)
        np.testing.assert_allclose(evaluate(point, case)[1], numerical, rtol=2e-7, atol=2e-6)


@pytest.mark.parametrize("method", study["METHODS"])
def test_batch_matches_independent_scalar_updates(method):
    case = dict(family="quartic", scale=100, start=[-3, 2], target=[0, 0])
    configs = [dict(alpha=0.0002, beta=0.9), dict(alpha=0.001, beta=0.99)]
    paths, _, _ = study["trajectories"](case, method, configs, steps=40)
    for i, config in enumerate(configs):
        x, moments, squares = [-3., 2.], [0., 0.], [0., 0.]
        expected = [x[:]]
        for t in range(1, 41):
            for j, scale in enumerate((1, 100)):
                g = scale * (x[j] + x[j]**3)
                if method == "gd":
                    direction = g
                elif method == "momentum":
                    moments[j] = config["beta"] * moments[j] + g
                    direction = moments[j]
                else:
                    moments[j] = .9 * moments[j] + .1 * g
                    squares[j] = .999 * squares[j] + .001 * g*g
                    direction = (moments[j] / (1-.9**t)) / (
                        math.sqrt(squares[j] / (1-.999**t)) + 1e-8)
                x[j] -= config["alpha"] * direction
            expected.append(x[:])
        np.testing.assert_allclose(paths[:, i], expected, rtol=1e-12, atol=1e-13)


def test_selection_requires_staying_in_both_targets_and_keeps_failures():
    paths = np.zeros((5, 3, 2))
    f = np.array([[1, 1, 1], [1e-6, 1e-6, 1e-6], [.1, 1e-6, np.nan],
                  [1e-6, 1e-6, np.nan], [1e-6, 1e-6, np.nan]])
    d = np.array([[1, 1, 1], [.001, .1, .001], [.001, .1, np.nan],
                  [.001, .1, np.nan], [.001, .1, np.nan]])
    records = study["summarize"](paths, f, d, [{}, {}, {}])
    assert records[0]["settled"] == 3
    assert records[1]["settled"] is None  # Objective alone is insufficient.
    assert records[2]["settled"] is None and not records[2]["finite"]
    assert records[2]["final_relative_loss"] is None


def test_divergence_is_missing_not_a_fake_minimum():
    case = study["cases"]()[0]
    paths, f, d = study["trajectories"](case, "gd", [dict(alpha=1e5, beta=0)], steps=10)
    assert np.isnan(paths[-1]).all()
    assert not study["summarize"](paths, f, d, [{}])[0]["finite"]
