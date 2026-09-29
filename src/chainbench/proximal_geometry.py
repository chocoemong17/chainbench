"""Recorded proximal stages on small diagonal-LASSO illustrations."""
from __future__ import annotations

import hashlib
import json
import platform

import numpy as np

from . import __version__
from .methods import fista, ista
from .problems import DiagonalLassoProblem

SOURCE = 'https://www.tau.ac.il/~becka/FISTA.pdf'
LAMBDAS = (.1, .8, 1.8)
STARTS = {'opposite': (-1.8, 1.2), 'zero': (0., 0.), 'near': (2., -1.4)}
A = (1., 3.)
B = (1.4, -2.4)


def _stages(problem, trace, accelerated):
    """Annotate existing method output, verifying every reconstructed proximal step."""
    y, t, beta = trace.iterates[0].copy(), 1., 0.
    stages = []
    step = 1/problem.L
    for k, (x, xn) in enumerate(zip(trace.iterates[:-1], trace.iterates[1:])):
        if not accelerated:
            y = x.copy()
        gradient = problem.smooth_grad(y)
        z = y-step*gradient
        expected = np.sign(z)*np.maximum(np.abs(z)-step*problem.lam, 0.)
        if not np.allclose(expected, xn, rtol=1e-13, atol=1e-14):
            raise FloatingPointError('proximal annotation disagrees with method output')
        stages.append({'iteration': k, 'x': x.tolist(), 'y': y.tolist(), 'gradient': gradient.tolist(),
                       'z': z.tolist(), 'next_x': xn.tolist(), 'momentum': float(beta),
                       't': float(t), 'threshold': step*problem.lam,
                       'zeroed': (np.abs(z) <= step*problem.lam).tolist()})
        if accelerated:
            tn = .5*(1+np.sqrt(1+4*t*t))
            beta = (t-1)/tn
            y = xn+beta*(xn-x)
            t = tn
    return stages


def run_proximal_geometry(steps: int = 18) -> dict:
    if type(steps) is not int or not 2 <= steps <= 60:
        raise ValueError('steps must be an integer between 2 and 60')
    cases = []
    for index, lam in enumerate(LAMBDAS):
        p = DiagonalLassoProblem(np.array(A), np.array(B), lam)
        for name, start in STARTS.items():
            x0 = np.array(start)
            radius2 = float((x0-p.x_star)@(x0-p.x_star))
            runs = {}
            for method, fn in (('ista', ista), ('fista', fista)):
                trace = fn(p, steps, x0=x0)
                rows = [{'iteration': k, 'x': x.tolist(), 'gap': p.gap(x), 'objective': p.value(x)}
                        for k, x in enumerate(trace.iterates)]
                runs[method] = {'rows': rows, 'stages': _stages(p, trace, method == 'fista'),
                                'updates': steps, 'termination': 'fixed_budget'}
            raw = np.array([*A, *B, lam, *start], dtype='<f8').tobytes()
            cases.append({'id': f'lambda-{index+1}-{name}', 'lambda': lam, 'start_name': name,
                          'start': list(start), 'x_star': p.x_star.tolist(), 'f_star': p.f_star,
                          'input_sha256': hashlib.sha256(raw).hexdigest(), 'radius_squared': radius2,
                          'bounds': {'iterations': list(range(1, steps+1)),
                                     'ista': [p.L*radius2/(2*k) for k in range(1, steps+1)],
                                     'fista': [2*p.L*radius2/(k+1)**2 for k in range(1, steps+1)]},
                          'runs': runs})
    result = {'kind': 'chainbench.proximal-geometry', 'schema_version': 1,
              'evidence_level': 'controlled-geometric-illustrations',
              'source': {'url': SOURCE, 'shrinkage': 'Eq. (1.5), printed p.185 / PDF page 3',
                         'proximal_model': 'Eqs. (2.5)-(2.6), printed p.189 / PDF page 7',
                         'ista': 'Eq. (3.1), printed p.191 / PDF page 9',
                         'fista': 'Eqs. (4.1)-(4.3), printed p.193 / PDF page 11',
                         'bounds': 'Theorems 3.1 and 4.4; fixed step alpha=1',
                         'indexing': 'stage k=0 maps to original algorithm step k=1',
                         'scaling': 'This fixture uses 0.5||Ax-b||^2, unlike the unhalved loss in Eq. (1.3).'},
              'problem': {'objective': 'F(x)=0.5||diag(a)x-b||_2^2+lambda||x||_1',
                          'a': list(A), 'b': list(B), 'dimension': 2, 'L': 9., 'mu_smooth': 1.,
                          'kappa_smooth': 9., 'solution': 'soft(a*b,lambda)/a^2',
                          'domain': 'R^2', 'seed': None},
              'parameters': {'steps': steps, 'step_size': 1/9,
                             'threshold': 'lambda/9', 'stopping': 'fixed budget, no early stopping'},
              'design': 'all 3 regularization strengths x all 3 starts; both methods; no filtering',
              'input_hash_encoding': 'SHA-256 of little-endian float64 a,b,lambda,x0 in order',
              'cases': cases, 'environment': {'chainbench': __version__, 'numpy': np.__version__,
                                             'python': platform.python_version()},
              'limits': ['Controlled 2D illustrations, not original-paper deblurring figures.',
                         'Diagonal data with known solutions; no representative real-data claim.',
                         'FISTA is not monotone; better envelopes do not rank every iterate.',
                         'Projected surface chords connect samples, not continuous algorithm motion.']}
    json.dumps(result, allow_nan=False)
    return result
