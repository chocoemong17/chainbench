"""Counterexamples found after v0.1.0; do not replace with loose gap-only tests."""
import numpy as np
import pytest

from chainbench import QuadraticProblem, conjugate_gradient
from chainbench.checks import CheckResult, _bound_result
from chainbench.cli import _exit_code


@pytest.mark.parametrize("scale", [1e-200, 1e-100, 1., 1e100, 1e200])
def test_cg_is_invariant_to_global_system_scale(scale):
    q = scale * np.array([[4., 1.], [1., 3.]])
    xs = np.array([1., 2.])
    p = QuadraticProblem(q, q @ xs, xs)
    trace = conjugate_gradient(p, 4)
    assert len(trace.iterates) > 1
    np.testing.assert_allclose(trace.iterates[-1], xs, rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize("scale", [1e-200, 1., 1e200])
def test_nonstationary_reference_cannot_hide_under_absolute_tolerance(scale):
    with pytest.raises(ValueError, match="x_star"):
        QuadraticProblem(scale * np.eye(2), scale * np.array([1e-13, 0.]), np.zeros(2))


@pytest.mark.parametrize("value", [None, True, "0.5", np.nan, np.inf])
def test_missing_or_invalid_observation_is_not_a_result(value):
    with pytest.raises(ValueError):
        CheckResult("bad", "test", "test", "test", "test", value, 1., True, "")


@pytest.mark.parametrize("ratios", [[], [-np.inf, .5], [np.nan, .5], [-.1, .5], [[.5]]])
def test_bound_reduction_validates_every_sample(ratios):
    with pytest.raises((ValueError, FloatingPointError)):
        _bound_result("bad", "test", "test", "test", "test", np.asarray(ratios), "")


def test_empty_suite_does_not_exit_successfully():
    with pytest.raises(ValueError, match="empty"):
        _exit_code([])


@pytest.mark.parametrize("scale", [1e-200, 1., 1e200])
def test_asymmetric_matrices_are_rejected_relative_to_scale(scale):
    with pytest.raises(ValueError, match="symmetric"):
        QuadraticProblem(scale * np.array([[1., .01], [0., 1.]]), np.zeros(2), np.zeros(2))


def test_large_symmetric_matrix_does_not_overflow_when_symmetrized():
    p = QuadraticProblem(np.diag([1e308, 1e307]), np.zeros(2), np.zeros(2))
    assert np.isfinite(p.L)
    assert p.L == 1e308


@pytest.mark.parametrize("consistent,threshold", [(True, None), (False, None), (None, 1.)])
def test_info_and_quantitative_thresholds_are_not_confused(consistent, threshold):
    with pytest.raises(ValueError, match="threshold"):
        CheckResult("bad", "test", "test", "test", "test", .5, threshold, consistent, "")


def test_empty_cli_suite_is_an_error_without_writing_output(tmp_path, monkeypatch):
    from chainbench import cli
    monkeypatch.setattr(cli, "run_all", lambda: [])
    target = tmp_path / "empty.json"
    with pytest.raises(SystemExit) as exc:
        cli.main(["report", "--format", "json", "--output", str(target)])
    assert exc.value.code == 2
    assert not target.exists()
