import numpy as np

from chainbench.checks import run_check
from chainbench.methods import proximal_point
from chainbench.problems import strongly_convex_quadratic


def test_proximal_point_reduces_distance_to_optimizer():
    problem = strongly_convex_quadratic(dim=20, mu=0.1, L=1.0)
    trace = proximal_point(problem, steps=8, proximal_parameter=1.0)
    errors = [np.linalg.norm(x - problem.x_star) for x in trace.iterates]
    assert errors[-1] < errors[0]


def test_rockafellar_literature_check_is_consistent():
    result = run_check("rockafellar-1976")
    assert result.consistent is True
    assert result.observed <= result.threshold
