"""Independent small exact examples distinguish methods, not just decreasing gaps."""
import numpy as np
import pytest

from chainbench import (
    DiagonalLassoProblem,
    QuadraticProblem,
    accelerated_gradient,
    conjugate_gradient,
    fista,
    gradient_descent,
    heavy_ball,
    ista,
    proximal_point,
)


def test_gradient_descent_hand_computed_iterates():
    p = QuadraticProblem(np.diag([1., 4.]), np.array([1., 8.]), np.array([1., 2.]))
    t = gradient_descent(p, 2)
    np.testing.assert_allclose(t.iterates, [[0., 0.], [.25, 2.], [.4375, 2.]], atol=0)


def test_cg_two_dimensional_exact_example_and_actual_residual():
    # First CG update is (1/4,1/2); the second solves Ax=b exactly in real arithmetic.
    q, b, xs = np.array([[4., 1.], [1., 3.]]), np.array([1., 2.]), np.array([1., 7.]) / 11
    p = QuadraticProblem(q, b, xs)
    t = conjugate_gradient(p, 3)
    np.testing.assert_allclose(t.iterates[1], [.25, .5], atol=1e-15)
    np.testing.assert_allclose(t.iterates[2], xs, atol=1e-15)
    assert t.termination == "converged"
    assert t.residual_norm == pytest.approx(float(np.hypot.reduce(b - q @ t.iterates[-1])))
    partial = conjugate_gradient(p, 1)
    assert partial.termination == "max_steps"
    assert partial.residual_norm > 1e-12
    assert conjugate_gradient(p, 0).termination == "max_steps"


def test_cg_absolute_tolerance_and_exact_start():
    p = QuadraticProblem(np.eye(2), np.ones(2), np.ones(2))
    assert conjugate_gradient(p, 3, p.x_star).termination == "converged"
    assert len(conjugate_gradient(p, 3, atol=2).iterates) == 1


def test_heavy_ball_hand_computed_momentum():
    p = QuadraticProblem(np.diag([1., 9.]), np.array([2., -9.]), np.array([2., -1.]))
    trace, alpha, beta = heavy_ball(p, 3)
    assert alpha == beta == .25
    np.testing.assert_allclose(trace.iterates, [[0, 0], [.5, -2.25], [1, 0], [1.375, -1.6875]])


def test_fista_third_iterate_contains_acceleration_and_l1_threshold():
    p = DiagonalLassoProblem(np.array([1., 2.]), np.array([2., -3.]), .5)
    trace = fista(p, 3)
    t1 = (1 + np.sqrt(5)) / 2
    t2 = (1 + np.sqrt(1 + 4*t1*t1)) / 2
    beta = (t1 - 1) / t2
    expected = .75 * (.65625 + beta * .28125) + .375
    np.testing.assert_allclose(trace.iterates[1], [.375, -1.375], atol=1e-15)
    np.testing.assert_allclose(trace.iterates[2], [.65625, -1.375], atol=1e-15)
    np.testing.assert_allclose(trace.iterates[3], [expected, -1.375], atol=1e-15)
    assert abs(trace.iterates[3][0] - ista(p, 3).iterates[3][0]) > .01


def test_smooth_fista_agrees_with_composite_zero_regularizer():
    q = np.diag([1., 4.])
    p = QuadraticProblem(q, np.array([2., -6.]), np.array([2., -1.5]))
    lasso = DiagonalLassoProblem(np.array([1., 2.]), np.array([2., -3.]), 0.)
    np.testing.assert_allclose(accelerated_gradient(p, 8).iterates, fista(lasso, 8).iterates)


@pytest.mark.parametrize("c", [.125, 1., 4.])
def test_proximal_point_matches_scalar_resolvents(c):
    diag, xs, start = np.array([1., 4.]), np.array([1., 2.]), np.array([3., -1.])
    p = QuadraticProblem(np.diag(diag), diag * xs, xs)
    actual = proximal_point(p, 1, c, start).iterates[1]
    np.testing.assert_allclose(actual, (start + c * diag * xs) / (1 + c * diag), atol=1e-15)
