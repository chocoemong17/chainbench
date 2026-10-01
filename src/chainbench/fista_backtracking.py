"""Recorded backtracking FISTA on a declared diagonal, two-dimensional grid."""
from __future__ import annotations

import hashlib
import json
import math
import platform

import numpy as np

from . import __version__
from .problems import DiagonalLassoProblem

SOURCE = 'https://www.tau.ac.il/~becka/FISTA.pdf'
A, B = (1., 3.), (1.4, -2.4)
LAMBDAS = (.1, .8, 1.8)
STARTS = {'opposite': (-1.8, 1.2), 'zero': (0., 0.),
          'near': (2., -1.4), 'low-mode': (-3., -.8)}
INITIAL_L = (.25, 1., 4.)
ETA = 2.


def _difference(a, L, direction):
    """F(q)-Q_L(q,y); exact quadratic identity evaluated in float64."""
    return float(.5*np.sum((a*a-L)*direction*direction))


def _slice(problem, y, q, L):
    direction = q-y
    parameters = {-.25+i/32 for i in range(49)}
    for anchor, delta in zip(y, direction):
        if delta != 0:
            crossing = float(-anchor/delta)
            if -.25 < crossing < 1.25:
                parameters.add(crossing)
    parameters = sorted(parameters)
    points = y+np.array(parameters)[:, None]*direction
    points[parameters.index(0.)] = y
    points[parameters.index(1.)] = q
    gaps = [problem.gap(point) for point in points]
    models = [gap-_difference(problem.a, L, point-y) for gap, point in zip(gaps, points)]
    return dict(parameter=parameters, points=points.tolist(), objective_gap=gaps, model_gap=models,
                zero_direction=bool(np.array_equal(y, q)))


def _trial(problem, y, gradient, L, attempt):
    z = y-gradient/L
    q = np.sign(z)*np.maximum(np.abs(z)-problem.lam/L, 0.)
    direction = q-y
    difference = _difference(problem.a, L, direction)
    smooth_y = float(.5*np.sum((problem.a*y-problem.b)**2))
    objective = problem.value(q)
    model = float(smooth_y+gradient@direction+.5*L*(direction@direction)
                  +problem.lam*np.sum(np.abs(q)))
    raw_difference = objective-model
    gap = problem.gap(q)
    return dict(attempt=attempt, L=L, step_size=1/L, threshold=problem.lam/L,
                gradient_step=z.tolist(), point=q.tolist(), displacement=direction.tolist(),
                zeroed=(np.abs(z)<=problem.lam/L).tolist(),
                objective=objective, raw_model=model, stable_gap=gap,
                stable_model_gap=gap-difference, stable_model_difference=difference,
                raw_model_difference=raw_difference, accepted=difference<=0.,
                raw_would_accept=raw_difference<=0.,
                slice=_slice(problem, y, q, L))


def _run(problem, inputs):
    x = np.array(inputs['x0'])
    y, t, L = x.copy(), 1., inputs['initial_L']
    radius2 = float((x-problem.x_star)@(x-problem.x_star))
    rows = [dict(iteration=0, x=x.tolist(), objective=problem.value(x),
                 stable_gap=problem.gap(x), raw_gap=problem.value(x)-problem.f_star,
                 stable_gap_change=None, bound=None)]
    stages = []
    for k in range(1, inputs['steps']+1):
        carried_L = L
        gradient = problem.smooth_grad(y)
        trials = []
        # For this declared grid, doubling reaches 16 >= L(f)=9 in <=7 trials.
        # Failure is explicit; an exhausted trial budget never invents acceptance.
        for attempt in range(7):
            trial = _trial(problem, y, gradient, L, attempt)
            trials.append(trial)
            if trial['accepted']:
                break
            L *= ETA
        else:
            raise FloatingPointError('backtracking exhausted the declared trial budget')
        q = np.array(trial['point'])
        tn = .5*(1+math.sqrt(1+4*t*t))
        beta = (t-1)/tn
        yn = q+beta*(q-x)
        stages.append(dict(iteration=k, previous_x=x.tolist(), anchor=y.tolist(),
            gradient=gradient.tolist(), t=t, next_t=tn, next_momentum=beta,
            next_anchor=yn.tolist(), carried_L=carried_L, accepted_L=L, trials=trials,
            previous_gap=rows[-1]['stable_gap'], anchor_gap=problem.gap(y)))
        gap = problem.gap(q)
        rows.append(dict(iteration=k, x=q.tolist(), objective=problem.value(q),
            stable_gap=gap, raw_gap=problem.value(q)-problem.f_star,
            stable_gap_change=gap-rows[-1]['stable_gap'],
            bound=2*ETA*problem.L*radius2/(k+1)**2))
        x, y, t = q, yn, tn
    return dict(rows=rows, stages=stages, updates=inputs['steps'], termination='fixed_budget',
        radius_squared=radius2,
        observations=dict(total_trials=sum(len(s['trials']) for s in stages),
            rejected_trials=sum(len(s['trials'])-1 for s in stages),
            accepted_L_changes=[dict(iteration=s['iteration'], L=s['accepted_L'])
                for i, s in enumerate(stages) if i==0 or s['accepted_L']!=stages[i-1]['accepted_L']],
            objective_increase_rounds=[r['iteration'] for r in rows[1:] if r['stable_gap_change']>1e-12],
            raw_gate_disagreements=[dict(iteration=s['iteration'], attempt=v['attempt'])
                for s in stages for v in s['trials'] if v['accepted']!=v['raw_would_accept']]))


def run_fista_backtracking(steps: int = 18) -> dict:
    if type(steps) is not int or not 1<=steps<=60:
        raise ValueError('steps must be an integer between 1 and 60')
    cases = []
    for lam in LAMBDAS:
        problem = DiagonalLassoProblem(np.array(A), np.array(B), lam)
        for name, start in STARTS.items():
            for initial in INITIAL_L:
                inputs = dict(a=list(A), b=list(B), **{'lambda':lam}, x0=list(start),
                    initial_L=initial, eta=ETA, steps=steps, initial_t=1.,
                    policy='carry accepted L forward; double after a rejected trial',
                    stopping='fixed budget; no early stopping')
                fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True,
                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()
                cases.append(dict(id=f'lambda{lam:g}-{name}-L{initial:g}', start_name=name,
                    inputs=inputs, input_sha256=fingerprint,
                    optimum=dict(point=problem.x_star.tolist(), value=problem.f_star),
                    **_run(problem, inputs)))
    result = dict(kind='chainbench.fista-backtracking-geometry', schema_version=1,
        evidence_level='controlled-geometric-illustrations',
        source=dict(url=SOURCE,
            algorithm='Unnumbered FISTA with backtracking panel, printed p.194 / PDF page 12',
            model='Eqs. (2.5)-(2.6), printed p.189 / PDF page 7',
            bound='Theorem 4.4 / Eq. (4.4), printed p.195 / PDF page 13; alpha=eta=2',
            scaling='Half-squared loss here; Eq. (1.3) in the paper uses unhalved loss.',
            indexing='Stage k is source step k>=1; row zero is the supplied start.'),
        problem=dict(objective='F(x)=0.5||diag(a)x-b||_2^2+lambda||x||_1',
            smooth_L=9., smooth_mu=1., dimension=2, seed=None),
        parameters=dict(steps=steps, lambdas=list(LAMBDAS), starts=list(STARTS),
            initial_L=list(INITIAL_L), eta=ETA),
        design='All 12 objective/start inputs x all 3 initial L guesses; 36 complete runs, no filtering.',
        gate=dict(condition='F(q)<=Q_L(q,y)',
            evaluated_difference='0.5*sum((a_i^2-L)*(q_i-y_i)^2)',
            arithmetic='Quadratic identity in float64, no added acceptance tolerance; retain raw F-Q separately.',
            scope='Candidate test at the extrapolated anchor; not a global upper-model certificate or monotone objective test.'),
        geometry=dict(slice='u(s)=y+s*(q-y)', interval=[-.25,1.25], base_samples=49,
            corners='Include 0, 1 and every coordinate zero crossing strictly inside the interval.',
            height='Stable F(u)-F* and Q_L(u,y)-F*; rejected models may lie below zero.',
            paths='Only accepted x iterates form trajectories; rejected q are trial proposals.'),
        input_hash_encoding='SHA-256 of sorted compact finite JSON inputs', cases=cases,
        environment=dict(chainbench=__version__, numpy=np.__version__, python=platform.python_version()),
        limits=[
            'Declared diagonal illustrations, not original image-deblurring data or figures.',
            'Specialized quadratic gate, not a general-purpose black-box line-search solver.',
            'All initial L<=9; the displayed bound uses alpha=eta=2 and the initial distance.',
            'The bound counts accepted updates; trial counts are separate and are not wall-clock timings.',
            'Backtracking FISTA need not decrease F relative to the previous accepted x.',
            'A candidate can pass with L<9 without certifying a global Lipschitz constant.',
            'Surface chords join saved samples, not continuous optimizer motion.',
        ])
    json.dumps(result, allow_nan=False)
    return result
