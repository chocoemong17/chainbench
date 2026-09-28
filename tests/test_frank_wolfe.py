import numpy as np

from chainbench.checks import run_check
from chainbench.methods import frank_wolfe
from chainbench.problems import simplex_quadratic


def test_frank_wolfe_iterates_stay_on_simplex():
    problem = simplex_quadratic(dim=12)
    trace = frank_wolfe(problem, steps=20)
    for x in trace.iterates:
        assert np.all(x >= -1e-12)
        assert np.isclose(np.sum(x), 1.0, atol=1e-12)


def test_frank_wolfe_literature_check_is_consistent():
    result = run_check("jaggi-2013")
    assert result.consistent is True
    assert result.observed <= result.threshold
