"""The published upper model evaluated on each already computed proximal step."""
from __future__ import annotations

import numpy as np


def model_slice(problem, x, y, next_x):
    """Sample an actual update line, retaining its endpoints and every L1 corner."""
    direction = next_x-y
    parameters = set(np.linspace(-.25, 1.25, 49).tolist()) | {0., 1.}
    for anchor, delta in zip(y, direction):
        if delta != 0:
            crossing = float(-anchor/delta)
            if -.25 < crossing < 1.25:
                parameters.add(crossing)
    parameters = sorted(parameters)
    points = y+np.array(parameters)[:, None]*direction
    # Pin saved endpoints: y + (next_x-y) can round differently from next_x.
    points[parameters.index(0.)] = y
    points[parameters.index(1.)] = next_x
    gaps = np.array([problem.gap(point) for point in points])
    # For this quadratic f, Q_L(u,y)-F(u) is exactly this PSD quadratic.
    # Use the stable objective gap rather than subtracting nearly equal values.
    excess = .5*np.sum((problem.L-problem.a**2)*(points-y)**2, axis=1)
    next_excess = float(.5*np.sum((problem.L-problem.a**2)*direction**2))
    return {'parameter': parameters, 'objective_gap': gaps.tolist(),
            'model_gap': (gaps+excess).tolist(), 'direction': direction.tolist(),
            'zero_step': bool(np.array_equal(y, next_x)),
            'anchor_gap': problem.gap(y), 'previous_gap': problem.gap(x),
            'next_gap': problem.gap(next_x), 'model_excess_next': next_excess,
            'model_next_gap': problem.gap(next_x)+next_excess}


CONTRACT = {
    'kind': 'actual-proximal-upper-model-slices',
    'model': 'Q_L(u,y)=f(y)+grad(f,y) dot (u-y)+(L/2)||u-y||^2+g(u)',
    'slice': 'u(t)=y+t*(x_next-y)', 'parameter_interval': [-.25, 1.25],
    'base_samples': 49, 'corners': 'include t=0,1 and every coordinate zero crossing in the interval',
    'height': 'F(u)-F* and Q_L(u,y)-F*; the same F* shifts both curves',
    'excess': '0.5*(u-y)^T*(L*I-diag(a^2))*(u-y)',
    'scope': 'Constructed 1D slices of the nine existing 2D illustrations, not source-paper figures.',
    'descent': 'F(x_next)<=Q_L(x_next,y)<=Q_L(y,y)=F(y); ISTA has y=x, FISTA need not.',
    'source': 'Beck-Teboulle (2009), Eqs. (2.5)-(2.7), p.189/PDF 7; Remark 3.1, p.191/PDF 9',
}
