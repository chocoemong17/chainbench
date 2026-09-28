import numpy as np

from chainbench.problems import diagonal_lasso, smooth_convex_quadratic


def test_quadratic_exact_optimizer():
    p = smooth_convex_quadratic(20)
    assert np.linalg.norm(p.grad(p.x_star)) < 1e-12


def test_diagonal_lasso_exact_optimizer_is_stationary_coordinatewise():
    p = diagonal_lasso(30)
    x = p.x_star
    g = p.smooth_grad(x)
    active = np.abs(x) > 1e-12
    assert np.allclose(g[active] + p.lam * np.sign(x[active]), 0.0, atol=1e-10)
    assert np.all(np.abs(g[~active]) <= p.lam + 1e-10)
