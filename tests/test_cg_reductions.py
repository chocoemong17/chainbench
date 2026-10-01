"""Regressions for Intel CG rerun drift without loosening numerical gates."""
import numpy as np
import pytest
from _numeric_records import assert_recomputed_record

from chainbench.methods import _cg_dot, conjugate_gradient
from chainbench.problems import QuadraticProblem
from chainbench.stress import run_stress_case


@pytest.mark.parametrize("offset", range(8))
def test_cg_inner_product_retains_unit_between_cancelling_large_terms(offset):
    # Exact result is 1. Vary the allocation/view offset, not the mathematical input.
    storage = np.empty(offset + 3)
    values = storage[offset:]
    values[:] = [2.**54, 1., -2.**54]
    assert _cg_dot(values, np.ones(3)) == 1.


@pytest.mark.parametrize("left,right", [
    ([1e308, 1e308], [1., 1.]),  # finite products, unrepresentable sum
    ([1e308], [2.]),             # unrepresentable product
    ([float("nan")], [1.]),
    ([float("inf")], [1.]),
])
def test_cg_inner_product_rejects_nonfinite_arithmetic(left, right):
    with pytest.raises(FloatingPointError):
        _cg_dot(np.asarray(left), np.asarray(right))


@pytest.mark.parametrize("seed", [7, 19])
def test_cg_late_stress_iterates_repeat_at_unchanged_tolerance(seed):
    # Both dimension-40 inputs exhibited late drift in the Intel diagnostic run.
    first = run_stress_case("hestenes-stiefel-1952", seed)
    for _ in range(6):
        rerun = run_stress_case("hestenes-stiefel-1952", seed)
        assert_recomputed_record(rerun, first)


def test_cg_preserves_true_residual_and_exact_start_with_cancellation():
    # The API defines its true residual using b - Q @ x, including at x0.
    # A different accumulation there would change what counts as an exact start.
    q = np.ones((3, 3)) + np.diag([1., 2., 3.])
    reference = np.array([1e16, 1., -1e16])
    problem = QuadraticProblem.from_reference(q, reference)
    trace = conjugate_gradient(problem, 3, x0=problem.x_star)
    assert trace.termination == "converged"
    assert trace.residual_norm == 0.
    assert len(trace.iterates) == 1
    np.testing.assert_array_equal(trace.iterates[0], reference)
