"""Small, declared teaching examples; independent of production lessons.

No trained classifier, performance benchmark, or original-paper dataset.
"""

from itertools import product


def forward(w1=1.0, w2=0.5, x=2.0, target=2.0):
    hidden = w1 * x
    output = w2 * hidden
    return hidden, output, 0.5 * (output - target) ** 2


def backward(w1=1.0, w2=0.5, x=2.0, target=2.0):
    hidden, output, _ = forward(w1, w2, x, target)
    signal = output - target
    return signal * w2 * x, signal * hidden


def update(rate=0.1):
    g1, g2 = backward()
    return 1.0 - rate * g1, 0.5 - rate * g2


VERTICAL = [[-1, 2, -1] for _ in range(3)]
HORIZONTAL = [list(row) for row in zip(*VERTICAL)]


def picture(shift=0):
    """Our own binary bars; shift 0 or 1 avoids cropped nonzero pixels."""
    if shift not in (0, 1):
        raise ValueError("Only the two declared, uncropped inputs are supported")
    data = [[0] * 9 for _ in range(7)]
    for row in range(1, 6):
        data[row][2 + shift] = 1
    for col in range(5, 8):
        data[4][col + shift] = 1
    return data


def correlate(data, kernel):
    """Valid stride-one 2D cross-correlation, followed by ReLU; no padding/bias."""
    height, width = len(data) - 2, len(data[0]) - 2
    return [[max(0, sum(data[r + i][c + j] * kernel[i][j]
                        for i in range(3) for j in range(3)))
             for c in range(width)] for r in range(height)]


FEATURES = (1.0, 2.0, 3.0, 4.0)
MASKS = tuple(product((0, 1), repeat=4))


def dropout(mask):
    """Original-paper convention: unscaled training activations, unit weights."""
    if len(mask) != 4 or any(v not in (0, 1) for v in mask):
        raise ValueError("Expected four binary gates")
    return sum(value * keep for value, keep in zip(FEATURES, mask))


def expected_dropout(p=0.5):
    if not 0 <= p <= 1:
        raise ValueError("Retention probability must lie in [0, 1]")
    return sum(dropout(m) * p ** sum(m) * (1 - p) ** (4 - sum(m)) for m in MASKS)


def verification():
    """Independent derivative/dot-product/enumeration checks before any drawing."""
    from math import isclose

    assert forward() == (2.0, 1.0, 0.5)
    assert backward() == (-1.0, -2.0)
    for weights in ((1.0, 0.5), (-0.3, 0.7), (0.0, 0.5), (1.0, 0.0)):
        gradients = backward(*weights)
        for i in range(2):
            plus, minus = list(weights), list(weights)
            plus[i] += 1e-6
            minus[i] -= 1e-6
            finite_difference = (forward(*plus)[2] - forward(*minus)[2]) / 2e-6
            assert isclose(gradients[i], finite_difference, abs_tol=1e-8)
    after = forward(*update())
    assert isclose(after[1], 1.54) and isclose(after[2], 0.1058)
    assert forward(*update(0.0)) == forward()
    assert forward(*update(2.0))[2] > forward()[2]  # Oversized steps can fail.
    vertical = correlate(picture(), VERTICAL)
    horizontal = correlate(picture(), HORIZONTAL)
    assert vertical[2][1] == 6 and horizontal[3][5] == 6
    assert horizontal[2][1] == 0 and vertical[3][5] == 0
    for kernel in (VERTICAL, HORIZONTAL):
        before = correlate(picture(), kernel)
        shifted = correlate(picture(1), kernel)
        assert all(b[1:] == a[:-1] for a, b in zip(before, shifted))
    assert 2 * 3 * 3 == 18 and 2 * 5 * 7 * 3 * 3 == 630
    assert dropout((1, 1, 0, 0)) == 3 and dropout((0, 0, 1, 1)) == 7
    assert dropout((0, 0, 0, 0)) == 0 and dropout((1, 1, 1, 1)) == 10
    for p in (0.0, 0.2, 0.5, 0.8, 1.0):
        assert isclose(expected_dropout(p), p * sum(FEATURES), abs_tol=1e-12)
    # Equality of the linear mean does not imply equality after a nonlinearity.
    nonlinear_mean = sum(max(0, dropout(m) - 6) for m in MASKS) / 16
    assert nonlinear_mean > max(0, expected_dropout() - 6)
    return {
        "scope": "constructed linear chain, hand-set filters, fixed-feature dropout; no accuracy claim",
        "backprop": {"gradients": list(backward()), "updated_weights": list(update()),
                     "before_loss": 0.5, "after_output": after[1], "after_loss": after[2],
                     "finite_difference_points": 4, "oversized_step_control": "passed"},
        "cnn": {"vertical_map": vertical, "horizontal_map": horizontal,
                "shared_weights": 18, "unshared_local_weights": 630,
                "translation_scope": "one-cell shift, common valid interior only"},
        "dropout": {"all_16_outputs": [dropout(m) for m in MASKS],
                    "linear_mean": expected_dropout(), "test_time_output": 5.0,
                    "nonlinear_counterexample_mean": nonlinear_mean,
                    "nonlinear_of_mean": 0.0},
    }
