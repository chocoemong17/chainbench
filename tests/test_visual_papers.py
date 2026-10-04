"""Independent arithmetic checks for the two explicitly scoped paper lessons."""

import math

import numpy as np
import pytest

from chainbench.visual_papers import (
    attention,
    depth_case,
    experiment,
    film_state,
    grid_case,
    query_case,
    residual_example,
)

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


@pytest.mark.parametrize("selected", [0, 1, 2])
@pytest.mark.parametrize("focus", [0, 1.28, 4])
def test_approved_query_case(selected, focus):
    result = query_case(selected, focus)
    logits = np.zeros(3)
    logits[selected] = focus
    expected = np.exp(logits) / np.exp(logits).sum()
    np.testing.assert_allclose(result["weights"], expected, rtol=1e-14)
    np.testing.assert_allclose(result["output"], expected, rtol=1e-14)
    if focus == 4:
        assert round(100 * result["weights"][selected]) == 96
    if focus == 0:
        np.testing.assert_allclose(result["weights"], 1 / 3)


@pytest.mark.parametrize("alpha", [0, 0.37, 1])
def test_scalar_forward_and_reverse_independent_differences(alpha):
    w = -0.1 * alpha
    b = 0.3 * alpha

    def loss(x, weight):
        y = max(0, x + weight * max(0, x) + b)
        return 0.5 * (y - 2.2) ** 2

    h = 1e-5
    row = residual_example(w2=w, b2=b)
    assert row["y"] == pytest.approx(2 + 0.1 * alpha)
    assert row["loss"] == pytest.approx(loss(2, w))
    assert row["dx"] == pytest.approx((loss(2 + h, w) - loss(2 - h, w)) / (2 * h), abs=1e-10)
    assert row["dw2"] == pytest.approx((loss(2, w + h) - loss(2, w - h)) / (2 * h), abs=1e-10)
    assert row["dx"] == pytest.approx(row["shortcut"] + row["branch"])


@pytest.mark.parametrize("depth", [0, 1, 2, 8, 16])
@pytest.mark.parametrize("shortcut", [False, True])
def test_depth_signed_chain_and_forward_point(depth, shortcut):
    def forward(x):
        for _ in range(depth):
            x = max(0, x - 0.1 * x + 0.1) if shortcut else max(0, -0.1 * x + 1.1)
        return x

    assert forward(1) == pytest.approx(1)
    actual = depth_case(depth, shortcut)[-1]
    expected = np.prod(np.full(depth, 0.9 if shortcut else -0.1))
    assert actual == pytest.approx(expected, rel=1e-13, abs=1e-25)
    h = 1e-3
    finite = (0.5 * forward(1 + h) ** 2 - 0.5 * forward(1 - h) ** 2) / (2 * h)
    assert actual == pytest.approx(finite, abs=1e-12)


def test_zero_and_inactive_controls_not_guaranteed():
    assert residual_example(w2=-1, b2=3)["dx"] == 0
    assert residual_example(x=-2, w2=0, b2=0)["y"] == 0
    assert residual_example(x=-2, w2=0, b2=0)["dx"] == 0
    assert depth_case(8, True, slope=-1)[-1] == 0
    assert abs(depth_case(8, False)[-1]) * 100 < 1
    assert round(abs(depth_case(8, True)[-1]) * 100) == 43


def test_grid_target_has_exactly_three_signed_changes():
    start = np.array(grid_case(0)["output"])
    end = np.array(grid_case(1)["output"])
    delta = end - start
    assert np.count_nonzero(delta == 1) == 2
    assert np.count_nonzero(delta == -1) == 1
    assert np.count_nonzero(delta) == 3
    np.testing.assert_allclose(grid_case(0.5)["output"], start + 0.5 * delta)


@pytest.mark.parametrize("slug", ["attention", "resnet"])
def test_record_and_film_chapters(slug):
    record = experiment(slug, SOURCE)
    assert record["source"] == SOURCE and record["kind"] == "chainbench.visual-paper.v2"
    assert record["chapters"] == [0, 12, 24, 36]
    assert [film_state(slug, k * 288)["scene"] for k in range(4)] == list(range(4))
    for frame in range(1152):
        row = film_state(slug, frame)
        assert 0 <= row["phase"] < 1
        assert row["scene"] == frame // 288
        if slug == "attention":
            np.testing.assert_allclose(
                row["weights"],
                np.exp(np.array(row["query"]) / np.sqrt(3))
                / np.exp(np.array(row["query"]) / np.sqrt(3)).sum(),
                atol=1e-14,
            )
        else:
            assert 0 <= row["depth"] <= 8
    if slug == "attention":
        np.testing.assert_allclose(film_state(slug, 33 * 24)["weights"], query_case(0)["weights"])
    else:
        assert len(record["blocks"]) == 101 and len(record["grids"]) == 101
        assert record["block"] == record["blocks"][-1]


@pytest.mark.parametrize(
    "call",
    [
        lambda: query_case(3),
        lambda: query_case(2, float("nan")),
        lambda: query_case(1, 5),
        lambda: depth_case(-1, True),
        lambda: depth_case(17, True),
        lambda: depth_case(2, True, float("inf")),
        lambda: grid_case(-0.1),
        lambda: grid_case(float("nan")),
        lambda: residual_example(float("inf")),
        lambda: film_state("attention", 1152),
        lambda: experiment("unknown", SOURCE),
        lambda: experiment("attention", "main"),
    ],
)
def test_rejects_invalid_fixture_requests(call):
    with pytest.raises(ValueError):
        call()
