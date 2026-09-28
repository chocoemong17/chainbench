import numpy as np

from chainbench.checks import run_check
from chainbench.methods import conjugate_gradient
from chainbench.problems import strongly_convex_quadratic


def test_conjugate_gradient_reduces_a_norm_error():
    problem = strongly_convex_quadratic(dim=20, mu=0.1, L=1.0)
    trace = conjugate_gradient(problem, steps=12)
    errors = [
        np.sqrt((x - problem.x_star) @ problem.Q @ (x - problem.x_star))
        for x in trace.iterates
    ]
    assert errors[-1] < errors[0]


def test_conjugate_gradient_literature_check_is_consistent():
    result = run_check("hestenes-stiefel-1952")
    assert result.consistent is True
    assert result.observed <= result.threshold
