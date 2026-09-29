import numpy as np
import pytest

from chainbench import (
    QuadraticProblem,
    accelerated_gradient,
    conjugate_gradient,
    diagonal_lasso,
    fista,
    frank_wolfe,
    gradient_descent,
    proximal_point,
    simplex_quadratic,
    strongly_convex_quadratic,
)


@pytest.mark.parametrize("dim", [4, 12])
@pytest.mark.parametrize("condition", [2.0, 10.0, 100.0])
def test_rotated_quadratic_bounds(dim, condition):
    # Fixed Householder rotation: exercises off-diagonal matrix products without randomness.
    u = np.arange(1, dim + 1, dtype=float)
    u /= np.linalg.norm(u)
    rotation = np.eye(dim) - 2 * np.outer(u, u)
    q = rotation @ np.diag(np.geomspace(1 / condition, 1, dim)) @ rotation.T
    xs = np.linspace(-1, 1, dim)
    p = QuadraticProblem(q, q @ xs, xs)
    gd, ag = gradient_descent(p, 20), accelerated_gradient(p, 20)
    d2 = xs @ xs
    for k in range(1, 21):
        assert p.gap(gd.iterates[k]) <= p.L * d2 / (2 * k) + 1e-12
        assert p.gap(ag.iterates[k]) <= 2 * p.L * d2 / (k + 1)**2 + 1e-12
    cg = conjugate_gradient(p, 8)
    rho = (np.sqrt(p.L / p.mu) - 1) / (np.sqrt(p.L / p.mu) + 1)
    e0 = np.sqrt(2 * p.gap(cg.iterates[0]))
    for k, x in enumerate(cg.iterates[1:], 1):
        assert np.sqrt(2 * p.gap(x)) <= 2 * rho**k * e0 + 1e-11


@pytest.mark.parametrize("lam", [0.0, 0.12, 10.0])
def test_lasso_exact_solution_and_gap(lam):
    p = diagonal_lasso(12, lam)
    for x in (np.zeros(p.dim), np.ones(p.dim), p.x_star):
        assert p.gap(x) == pytest.approx(p.value(x) - p.f_star, abs=1e-12)
    trace = fista(p, 20)
    for k, x in enumerate(trace.iterates[1:], 1):
        assert p.gap(x) <= 2 * p.L * np.linalg.norm(p.x_star)**2 / (k + 1)**2 + 1e-12


def test_stable_gap_does_not_round_a_near_optimal_point_to_zero():
    p = strongly_convex_quadratic(8)
    assert p.gap(p.x_star + 1e-9) > 0
    p = diagonal_lasso(8)
    assert p.gap(p.x_star + 1e-9) > 0


@pytest.mark.parametrize("c", [0.1, 1.0, 10.0])
def test_proximal_optimality_equation(c):
    p = strongly_convex_quadratic(6)
    trace = proximal_point(p, 5, c)
    for before, after in zip(trace.iterates, trace.iterates[1:]):
        np.testing.assert_allclose(after - before + c * p.grad(after), 0, atol=1e-12)


def test_cg_handles_tiny_scaled_system_and_exact_start():
    p = strongly_convex_quadratic(6, mu=1e-10, L=1e-9)
    trace = conjugate_gradient(p, 10)
    assert np.linalg.norm(trace.iterates[-1] - p.x_star) < 1e-8
    exact = conjugate_gradient(p, 6, p.x_star)
    assert len(exact.iterates) == 1


def test_frank_wolfe_oracle_and_bound():
    p = simplex_quadratic(8)
    g = np.linspace(-2, 1, p.dim)
    assert g @ p.linear_minimizer(g) == g.min()
    trace = frank_wolfe(p, 20)
    for k, x in enumerate(trace.iterates[1:], 1):
        assert x.min() >= 0
        assert x.sum() == pytest.approx(1)
        assert p.gap(x) <= 4 / (k + 2) + 1e-12
