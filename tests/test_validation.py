import numpy as np
import pytest

from chainbench import (
    DiagonalLassoProblem,
    QuadraticProblem,
    SimplexQuadraticProblem,
    accelerated_gradient,
    conjugate_gradient,
    diagonal_lasso,
    fista,
    frank_wolfe,
    gradient_descent,
    heavy_ball,
    ista,
    proximal_point,
    simplex_quadratic,
    strongly_convex_quadratic,
)
from chainbench.checks import CHECKS, CheckResult

PAIRS = [
    (gradient_descent, strongly_convex_quadratic),
    (accelerated_gradient, strongly_convex_quadratic),
    (heavy_ball, strongly_convex_quadratic),
    (conjugate_gradient, strongly_convex_quadratic),
    (proximal_point, strongly_convex_quadratic),
    (ista, diagonal_lasso), (fista, diagonal_lasso), (frank_wolfe, simplex_quadratic),
]


@pytest.mark.parametrize("method,factory", PAIRS)
@pytest.mark.parametrize("steps", [-1, 1.5, True])
def test_invalid_steps_rejected(method, factory, steps):
    with pytest.raises(ValueError):
        method(factory(4), steps)


@pytest.mark.parametrize("method,factory", PAIRS)
@pytest.mark.parametrize("x", [np.zeros(3), np.zeros((4, 1)), np.full(4, np.nan)])
def test_invalid_initial_vector_rejected(method, factory, x):
    with pytest.raises(ValueError):
        method(factory(4), 1, x0=x)


@pytest.mark.parametrize("method,factory", PAIRS)
def test_zero_steps_preserve_caller_input(method, factory):
    x0 = np.full(4, 0.25)
    before = x0.copy()
    result = method(factory(4), 0, x0=x0)
    trace = result[0] if isinstance(result, tuple) else result
    assert len(trace.iterates) == 1
    np.testing.assert_array_equal(trace.iterates[0], before)
    np.testing.assert_array_equal(x0, before)


@pytest.mark.parametrize("value", [np.nan, np.inf, -1.0])
def test_invalid_regularizer_and_proximal_parameter(value):
    with pytest.raises(ValueError):
        diagonal_lasso(4, lam=value)
    with pytest.raises(ValueError):
        proximal_point(strongly_convex_quadratic(4), 1, value)


def test_float32_reference_factory_promotes_before_computing_rhs():
    q = np.diag(np.geomspace(0.1, 1.0, 12).astype(np.float32))
    x_star = np.linspace(-1, 1, 12, dtype=np.float32)
    b_float32 = q @ x_star

    with pytest.raises(ValueError, match="from_reference"):
        QuadraticProblem(q, b_float32, x_star)

    problem = QuadraticProblem.from_reference(q, x_star)
    assert problem.Q.dtype == np.float64
    assert problem.b.dtype == np.float64
    np.testing.assert_array_equal(problem.b, problem.Q @ problem.x_star)
    np.testing.assert_array_equal(problem.grad(problem.x_star), np.zeros(problem.dim))


def test_reference_factory_does_not_weaken_strict_constructor():
    with pytest.raises(ValueError, match="from_reference"):
        QuadraticProblem(np.eye(2), np.array([1.0, 1.001]), np.ones(2))


def test_problem_data_are_copied_and_readonly():
    q = np.eye(3)
    p = QuadraticProblem(q, np.ones(3), np.ones(3))
    q[0, 0] = 9
    assert p.L == 1
    assert p.Q[0, 0] == 1
    with pytest.raises(ValueError):
        p.Q[0, 0] = 9


def test_invalid_problem_arrays():
    for q in (np.empty((0, 0)), np.full((2, 2), np.nan), np.diag([-1, 1])):
        with pytest.raises(ValueError):
            QuadraticProblem(q, np.zeros(q.shape[0]), np.zeros(q.shape[0]))
    with pytest.raises(ValueError):
        DiagonalLassoProblem([], [], 1)
    with pytest.raises(ValueError):
        DiagonalLassoProblem([1, np.inf], [1, 1], 1)
    with pytest.raises(ValueError):
        SimplexQuadraticProblem(np.array([0.5, 0.500001]))


@pytest.mark.parametrize("fn", CHECKS.values(), ids=CHECKS.keys())
def test_checks_reject_zero_budget(fn):
    with pytest.raises(ValueError):
        fn(steps=0)


def test_nonfinite_result_is_never_a_pass():
    with pytest.raises(ValueError):
        CheckResult("x", "x", "x", "x", "x", np.nan, 1, True, "x")
    result = CheckResult("x", "x", "x", "x", "x", 2, 1, np.bool_(False), "x")
    assert result.consistent is False
