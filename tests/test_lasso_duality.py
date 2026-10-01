import copy

import numpy as np
import pytest
from test_wavelet_deblurring import load_validator

from chainbench._lasso_duality import SAFETY, residual_dual_bound
from chainbench.deblurring import blur_matrix
from chainbench.wavelet_deblurring import blur, haar, run_wavelet_deblurring
from chainbench.wavelet_views import wavelet_html


@pytest.mark.parametrize("point", [np.zeros(4), np.array([3.0, -1.0, 0.0, 2.0])])
def test_identity_design_exact_optimum_bracket_and_fenchel_identity(point):
    b = np.array([2.0, -1.0, 0.2, 0.0])
    lam = 0.6
    optimum = np.sign(b) * np.maximum(np.abs(b) - lam / 2, 0)
    fstar = np.sum((optimum - b) ** 2) + lam * np.sum(np.abs(optimum))
    d = residual_dual_bound(point - b, b, point, lambda v: v, lam)
    assert d["lower_bound"] <= fstar <= d["primal_objective"]
    assert d["suboptimality_upper_bound"] >= d["primal_objective"] - fstar
    assert abs(d["identity_residual"]) < 1e-14
    at_optimum = residual_dual_bound(optimum - b, b, optimum, lambda v: v, lam)
    assert at_optimum["suboptimality_upper_bound"] < 2e-12
    assert at_optimum["lower_bound"] == pytest.approx(fstar, abs=2e-12)


def test_zero_residual_and_zero_adjoint_do_not_divide_or_invent_gap():
    zero = np.zeros(3)
    d = residual_dual_bound(zero, zero, zero, lambda v: v, 0.1)
    assert d["scale"] == SAFETY
    assert d["suboptimality_upper_bound"] == d["lower_bound"] == 0
    # Zero operator, nonzero observation: residual need not be zero.
    d = residual_dual_bound(-np.ones(3), np.ones(3), zero, lambda v: zero, 0.1)
    assert d["dual_adjoint_inf"] == 0
    assert abs(d["identity_residual"]) < 1e-14
    assert d["lower_bound"] == pytest.approx(3.0)


def test_blurred_haar_dual_checked_against_explicit_dense_operator():
    matrix, kernel = blur_matrix(8)
    transform = np.column_stack([haar(e.reshape(8, 8)).ravel() for e in np.eye(64)])
    operator = np.kron(matrix, matrix) @ transform.T
    rng = np.random.default_rng(19)
    c, b = rng.normal(size=(2, 64))
    image = haar(c.reshape(8, 8), inverse=True)
    r = blur(image, kernel) - b.reshape(8, 8)
    d = residual_dual_bound(
        r, b.reshape(8, 8), c.reshape(8, 8), lambda v: haar(blur(v, kernel)), 0.07
    )
    nu = (2 * r * d["scale"]).ravel()
    assert np.linalg.norm(operator.T @ nu, np.inf) <= 0.07
    assert d["lower_bound"] == pytest.approx(-nu @ nu / 4 - b @ nu, abs=1e-14)
    assert abs(d["identity_residual"]) < 2e-14


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), 0.0, -1.0])
def test_invalid_lambda_rejected(bad):
    with pytest.raises(ValueError):
        residual_dual_bound(np.ones(2), np.zeros(2), np.ones(2), lambda v: v, bad)


def test_infeasible_or_nonfinite_adjoint_fails_closed():
    calls = []

    def broken(v):
        calls.append(1)
        return v if len(calls) == 1 else v * 100

    with pytest.raises(FloatingPointError, match="infeasible"):
        residual_dual_bound(np.ones(2), np.zeros(2), np.ones(2), broken, 0.1)
    with pytest.raises(FloatingPointError, match="adjoint"):
        residual_dual_bound(np.ones(2), np.zeros(2), np.ones(2), lambda v: v * np.nan, 0.1)


@pytest.fixture(scope="module")
def record():
    return run_wavelet_deblurring(1, seed=0)


def test_snapshot_diagnostic_and_old_records_remain_readable(record):
    validate = load_validator().validate_wavelet
    validate(record, require_duality=True)
    old = copy.deepcopy(record)
    del old["duality"]
    for run in old["runs"].values():
        for s in run["snapshots"]:
            del s["dual_bound"]
    validate(old)
    with pytest.raises(RuntimeError, match="lacks duality"):
        validate(old, require_duality=True)
    assert "data-wavelet-duality" not in wavelet_html(old)
    text = wavelet_html(record)
    assert 'data-dual-snapshot="1"' in text
    assert text.count("<tr data-dual-table-row>") == 4
    assert "F* = unknown" in text


@pytest.mark.parametrize("fault", ["sign", "half_loss", "scale", "infeasible", "missing", "nan"])
def test_independent_validator_rejects_dual_corruption(record, fault):
    r = copy.deepcopy(record)
    s = r["runs"]["fista"]["snapshots"][0]
    d = s["dual_bound"]
    if fault == "sign":
        d["lower_bound"] *= -1
    elif fault == "half_loss":
        d["dual_quadratic"] *= 2
    elif fault == "scale":
        d["scale"] *= 2
    elif fault == "infeasible":
        d["dual_adjoint_inf"] = 1.000000000001e-4
    elif fault == "missing":
        del s["dual_bound"]
    else:
        d["suboptimality_upper_bound"] = float("nan")
    with pytest.raises(RuntimeError):
        load_validator().validate_wavelet(r)
