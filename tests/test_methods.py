import numpy as np

from chainbench.methods import accelerated_gradient, fista, gradient_descent, heavy_ball, ista
from chainbench.problems import diagonal_lasso, smooth_convex_quadratic, strongly_convex_quadratic


def test_gradient_methods_reduce_quadratic_gap():
    p = smooth_convex_quadratic(30)
    gd = gradient_descent(p, 25)
    ag = accelerated_gradient(p, 25)
    assert gd.values[-1] < gd.values[0]
    assert ag.values[-1] < ag.values[0]


def test_heavy_ball_converges():
    p = strongly_convex_quadratic(30)
    trace, _, _ = heavy_ball(p, 100)
    assert np.linalg.norm(trace.iterates[-1] - p.x_star) < np.linalg.norm(trace.iterates[0] - p.x_star)


def test_fista_and_ista_reduce_objective():
    p = diagonal_lasso(30)
    assert ista(p, 30).values[-1] < ista(p, 30).values[0]
    assert fista(p, 30).values[-1] < fista(p, 30).values[0]
