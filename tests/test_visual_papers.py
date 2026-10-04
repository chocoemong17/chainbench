"""Independent arithmetic checks for the two explicitly scoped paper lessons."""

import math

import numpy as np
import pytest

from chainbench.visual_papers import attention, experiment, frame_steps, residual_block

SOURCE = "a" * 40


@pytest.mark.parametrize("angle", [0, 17, 45, 90, 133, 180])
def test_attention_equation_and_weighted_output(angle):
    q = 4 * np.array([math.cos(math.radians(angle)), math.sin(math.radians(angle))])
    keys = np.array([[1, 0], [0, 1], [-1, 0], [0, -1]])
    values = np.array(
        [[0.88, 0.25, 0.2], [0.22, 0.68, 0.47], [0.23, 0.45, 0.85], [0.89, 0.65, 0.22]]
    )
    actual = attention(q.tolist(), keys.tolist(), values.tolist())
    logits = q @ keys.T / np.sqrt(2)
    weights = np.exp(logits - logits.max())
    weights /= weights.sum()
    np.testing.assert_allclose(actual["scores"], logits, atol=1e-14)
    np.testing.assert_allclose(actual["weights"], weights, atol=1e-14)
    np.testing.assert_allclose(actual["output"], weights @ values, atol=1e-14)
    assert min(actual["weights"]) > 0
    assert sum(actual["weights"]) == pytest.approx(1)


def test_uniform_query_and_permutation_equivariance():
    k = [[1, 0], [0, 1], [-1, 0]]
    v = [[1, 0], [0, 1], [1, 1]]
    a = attention([0, 0], k, v)
    assert a["weights"] == pytest.approx([1 / 3] * 3)
    assert a["output"] == pytest.approx([2 / 3] * 2)
    a = attention([4, 1], k, v)
    b = attention([4, 1], k[::-1], v[::-1])
    assert a["output"] == pytest.approx(b["output"])
    assert a["weights"] == pytest.approx(b["weights"][::-1])


def test_stable_softmax_large_but_finite_logits():
    result = attention([1000], [[1], [2]], [[0], [1]])
    assert result["weights"] == [0, 1]
    assert result["output"] == [1]


@pytest.mark.parametrize(
    "q,k,v",
    [
        ([], [[1]], [[1]]),
        ([1], [], []),
        ([1, 2], [[1]], [[1]]),
        ([1], [[1], [2]], [[1], [1, 2]]),
        ([float("nan")], [[1]], [[1]]),
        ([1e308], [[1e308]], [[1]]),
    ],
)
def test_attention_rejects_invalid_inputs(q, k, v):
    with pytest.raises(ValueError):
        attention(q, k, v)


@pytest.mark.parametrize("x", [-2.0, 0.0, 0.25, 0.5, 0.75, 1.0])
@pytest.mark.parametrize("strength", [0.0, 0.4, 1.0])
def test_residual_two_layer_block_matches_matrix_calculation(x, strength):
    hidden = np.maximum(0, np.array([[1.0], [0.0]]) @ np.array([x]) + np.array([0.0, 1.0]))
    delta = (strength * np.array([0.8, -0.4])) @ hidden
    actual_delta, actual_output = residual_block(x, strength)
    assert actual_delta == pytest.approx(delta, abs=1e-15)
    assert actual_output == pytest.approx(max(0, x + delta), abs=1e-15)
    if strength == 0:
        assert actual_output == max(0, x)


@pytest.mark.parametrize("strength", [-0.1, 1.1, float("inf"), float("nan")])
def test_residual_rejects_invalid_strength(strength):
    with pytest.raises(ValueError):
        residual_block(0.5, strength)


@pytest.mark.parametrize("slug,steps", [("attention", 180), ("resnet", 100)])
def test_record_and_shared_clock(slug, steps):
    record = experiment(slug, SOURCE)
    assert record["source"] == SOURCE
    assert record["steps"] == steps
    assert len(record["rows"]) == steps + 1
    frames = frame_steps(steps)
    assert len(frames) == 48 * 24
    assert frames == sorted(frames)
    assert set(frames) == set(range(steps + 1))
    assert set(frames[: 4 * 24]) == {0}
    assert set(frames[22 * 24 : 25 * 24]) == {steps // 2}
    assert set(frames[41 * 24 :]) == {steps}


def test_full_residual_sweep_and_declared_target():
    record = experiment("resnet", SOURCE)
    original = np.array(record["input"])
    target = np.array(record["target"])
    assert set(original.flatten()) == {0.25, 0.75}
    np.testing.assert_allclose(np.unique(target), [0.05, 0.95], atol=1e-15)
    for row in record["rows"]:
        delta = row["strength"] * (0.8 * original - 0.4)
        expected = np.maximum(0, original + delta)
        np.testing.assert_allclose(row["delta"], delta, atol=1e-15)
        np.testing.assert_allclose(row["output"], expected, atol=1e-15)
        assert row["rmse"] == pytest.approx(np.sqrt(np.mean((expected - target) ** 2)), abs=1e-15)
    np.testing.assert_array_equal(record["rows"][0]["output"], original)
    np.testing.assert_allclose(record["rows"][-1]["output"], target, atol=1e-15)
    assert record["rows"][0]["rmse"] == pytest.approx(0.2)
    assert record["rows"][50]["rmse"] == pytest.approx(0.1)


@pytest.mark.parametrize("slug,source", [("unknown", SOURCE), ("attention", "main")])
def test_record_rejects_unbound_sources(slug, source):
    with pytest.raises(ValueError):
        experiment(slug, source)
