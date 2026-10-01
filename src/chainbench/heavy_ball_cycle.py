"""Published heavy-ball counterexample, Lessard--Recht--Packard §4.6 / Appendix B."""

from __future__ import annotations

import hashlib
import json
import platform

import numpy as np

from . import __version__
from .methods import gradient_descent, heavy_ball

SOURCE = 'https://arxiv.org/pdf/1408.3595v7'
CYCLE = (792/1225, -2208/1225, 2592/1225)
STARTS = (3.3, .5, 1., 1.5, 2., 2.5, 3., 3.5, 4.)


class PiecewiseCycleProblem:
    """C1, 1-strongly convex, 25-smooth; not C2 at the two joins."""

    dim, L, mu = 1, 25., 1.

    @staticmethod
    def value(x):
        v = float(np.asarray(x).item())
        return (12.5*v*v if v < 1 else
                .5*v*v+24*v-12 if v < 2 else 12.5*v*v-24*v+36)

    @staticmethod
    def grad(x):
        v = float(np.asarray(x).item())
        return np.array([25*v if v < 1 else v+24 if v < 2 else 25*v-24])


def run_heavy_ball_cycle(steps: int = 50) -> dict:
    if type(steps) is not int or not 1 <= steps <= 500:
        raise ValueError('steps must be an integer between 1 and 500')
    problem = PiecewiseCycleProblem()
    cases = []
    for i, start in enumerate(STARTS):
        hb, alpha, beta = heavy_ball(problem, steps, np.array([start]))
        gd = gradient_descent(problem, steps, np.array([start]))
        runs = {}
        for method, trace in [('heavy-ball', hb), ('gd', gd)]:
            rows = []
            step, momentum = (alpha, beta) if method == 'heavy-ball' else (1/problem.L, 0.)
            for k, (point, objective) in enumerate(zip(trace.iterates, trace.values)):
                x = float(point[0])
                previous = float(trace.iterates[k-1][0]) if k else start
                gradient = float(problem.grad(point)[0])
                rows.append({
                    'iteration': k, 'x': x, 'previous': previous,
                    'objective': float(objective), 'gradient': gradient,
                    'stationarity': abs(gradient), 'distance_to_optimizer': abs(x),
                    'region': 'x<1' if x < 1 else '1<=x<2' if x < 2 else 'x>=2',
                    'gradient_step': -step*gradient if k < steps else None,
                    'momentum_step': momentum*(x-previous) if k < steps else None,
                    'distance_to_cycle_set': min(abs(x-c) for c in CYCLE),
                    'three_step_difference': abs(x-float(trace.iterates[k-3][0])) if k >= 3 else None,
                })
            runs[method] = {'step_size': step, 'momentum': momentum, 'rows': rows,
                            'updates': steps, 'termination': 'fixed_budget'}
        inputs = {'x_minus_1': start, 'x0': start, 'mu': 1., 'L': 25.,
                  'joins': [1., 2.], 'gradient_slopes': [25., 1., 25.],
                  'gradient_intercepts': [0., 24., -24.],
                  'objective_constants': [0., -12., 36.]}
        encoded = json.dumps(inputs, sort_keys=True, separators=(',', ':'), allow_nan=False)
        cases.append({'id': 'published' if i == 0 else f'grid-{i}', 'start': start,
                      'evidence_level': 'published-example-reproduction' if i == 0 else 'controlled-start-variation',
                      'inputs': inputs, 'input_sha256': hashlib.sha256(encoded.encode()).hexdigest(),
                      'runs': runs})
    # The plot domain includes every actual point and the source's transition points.
    all_x = [r['x'] for c in cases for run in c['runs'].values() for r in run['rows']]
    lo, hi = min(all_x+[0., 1., 2., *CYCLE]), max(all_x+[0., 1., 2., *CYCLE])
    margin = .06*(hi-lo)
    samples = sorted(set(np.linspace(lo-margin, hi+margin, 401).tolist()+[0., 1., 2., *CYCLE]))
    result = {
        'kind': 'chainbench.heavy-ball-cycle', 'schema_version': 1,
        'evidence_level': 'published-counterexample-with-labelled-variations',
        'source': {'url': SOURCE, 'doi': '10.1137/15M1009597',
                   'authors': 'Laurent Lessard, Benjamin Recht, Andrew Packard',
                   'journal_year': 2016, 'preprint_version': 'v7, 28 October 2015',
                   'function': 'Section 4.6, Eq. (4.11), PDF page 23',
                   'figures': 'Figures 6 and 7, PDF page 24',
                   'recurrence_and_cycle': 'Appendix B, Eqs. (B.1)-(B.3), PDF page 39',
                   'attraction_argument': 'Appendix B, PDF page 40'},
        'parameters': {'steps': steps, 'paper_plot_updates': 50, 'seed': None,
                       'initial_memory': 'x[-1]=x[0]', 'alpha': alpha, 'beta': beta},
        'problem': {'dimension': 1, 'mu': 1., 'L': 25., 'condition_number': 25.,
                    'x_star': 0., 'f_star': 0., 'joins': [1., 2.],
                    'gradient': '25x for x<1; x+24 for 1<=x<2; 25x-24 for x>=2',
                    'objective': '12.5x^2; 0.5x^2+24x-12; 12.5x^2-24x+36',
                    'regularity': 'C1 with Lipschitz gradient; not twice differentiable at 1 and 2'},
        'cycle_reference': {'values': list(CYCLE), 'exact': ['792/1225', '-2208/1225', '2592/1225'],
                            'phase_for_published_start': 'x[3n]->p, x[3n+1]->q, x[3n+2]->r',
                            'role': 'Published analytical reference, not a fitted cycle or numerical stopping rule'},
        'design': 'Published start 3.3 plus every point of the declared 0.5:0.5:4.0 grid; no filtering',
        'input_hash_encoding': 'SHA-256 of UTF-8 json.dumps(inputs,sort_keys=True,separators=(comma,colon))',
        'cases': cases,
        'landscape': {'x': samples, 'objective': [problem.value([x]) for x in samples],
                      'gradient': [float(problem.grad([x])[0]) for x in samples]},
        'environment': {'chainbench': __version__, 'numpy': np.__version__, 'python': platform.python_version()},
        'differences': [
            'Independent NumPy float64 evaluation; source figures are not digitized or copied.',
            'Default output includes x[0] through x[50], fifty actual updates; different budgets are labelled.',
            'The antiderivative is normalized to f(0)=0, matching the displayed source objective.',
            'GD at 1/L, eight extra starts, state-plane paths and diagnostic metrics are ChainBench additions.',
        ],
        'limits': [
            'Reproduces one published counterexample, not the paper\'s IQC/SDP analyses or parameter searches.',
            'The classical parameters are optimized for quadratics; this globally strongly convex function is not quadratic.',
            'A small three-step difference also occurs at a fixed point. Inspect gradient norm and distance to the cycle separately.',
            'The source proves attraction for its stated setup; finite trajectories alone are not a proof about infinitely many updates.',
            'No claim that all heavy-ball parameter choices or all nonquadratic problems fail.',
        ],
    }
    json.dumps(result, allow_nan=False)
    return result
