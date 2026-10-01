"""Independent scalar validation of the published heavy-ball counterexample export."""

from __future__ import annotations

import hashlib
import json
import math


def validate_heavy_ball_cycle(result):
    def close(a, b):
        if a is None or not math.isfinite(a) or not math.isclose(a, b, rel_tol=2e-10, abs_tol=2e-12):
            raise RuntimeError('heavy-ball counterexample observation differs')

    def gradient(x):
        return 25*x if x < 1 else x+24 if x < 2 else 25*x-24

    def objective(x):
        # Independent integral from zero, adding continuous pieces at the joins.
        if x < 1:
            return 25*x*x/2
        if x < 2:
            return 12.5 + (x*x-1)/2 + 24*(x-1)
        return 38 + 25*(x*x-4)/2 - 24*(x-2)

    if result.get('kind') != 'chainbench.heavy-ball-cycle':
        raise RuntimeError('missing heavy-ball counterexample')
    steps = result['parameters']['steps']
    if type(steps) is not int or not 1 <= steps <= 500:
        raise RuntimeError('counterexample budget differs')
    starts = (3.3, .5, 1., 1.5, 2., 2.5, 3., 3.5, 4.)
    cycle = (792/1225, -2208/1225, 2592/1225)
    if (tuple(c['start'] for c in result['cases']) != starts
            or tuple(result['cycle_reference']['values']) != cycle
            or result['cycle_reference']['exact'] != ['792/1225', '-2208/1225', '2592/1225']
            or result['problem']['x_star'] != 0 or result['problem']['f_star'] != 0):
        raise RuntimeError('counterexample design or analytical cycle differs')
    for index, (case, start) in enumerate(zip(result['cases'], starts)):
        expected_inputs = {'x_minus_1': start, 'x0': start, 'mu': 1., 'L': 25.,
                           'joins': [1., 2.], 'gradient_slopes': [25., 1., 25.],
                           'gradient_intercepts': [0., 24., -24.],
                           'objective_constants': [0., -12., 36.]}
        encoded = json.dumps(expected_inputs, sort_keys=True, separators=(',', ':'))
        level = 'published-example-reproduction' if index == 0 else 'controlled-start-variation'
        if (case['inputs'] != expected_inputs or case['evidence_level'] != level
                or case['input_sha256'] != hashlib.sha256(encoded.encode()).hexdigest()
                or set(case['runs']) != {'heavy-ball', 'gd'}):
            raise RuntimeError('counterexample inputs or provenance differ')
        for name, run in case['runs'].items():
            step, beta = (1/9, 4/9) if name == 'heavy-ball' else (1/25, 0.)
            close(run['step_size'], step)
            close(run['momentum'], beta)
            if len(run['rows']) != steps+1 or run['updates'] != steps or run['termination'] != 'fixed_budget':
                raise RuntimeError('counterexample trace is incomplete')
            x = previous = start
            history = []
            for k, row in enumerate(run['rows']):
                if row['iteration'] != k or row['region'] != ('x<1' if x < 1 else '1<=x<2' if x < 2 else 'x>=2'):
                    raise RuntimeError('counterexample indexing or region differs')
                for key, value in [('x', x), ('previous', previous), ('objective', objective(x)),
                                   ('gradient', gradient(x)), ('stationarity', abs(gradient(x))),
                                   ('distance_to_optimizer', abs(x)),
                                   ('distance_to_cycle_set', min(abs(x-c) for c in cycle))]:
                    close(row[key], value)
                if k < 3:
                    if row['three_step_difference'] is not None:
                        raise RuntimeError('missing period comparison was invented')
                else:
                    close(row['three_step_difference'], abs(x-history[k-3]))
                history.append(x)
                if k < steps:
                    close(row['gradient_step'], -step*gradient(x))
                    close(row['momentum_step'], beta*(x-previous))
                    previous, x = x, x-step*gradient(x)+beta*(x-previous)
                elif row['gradient_step'] is not None or row['momentum_step'] is not None:
                    raise RuntimeError('counterexample invented a final update')
    landscape = result['landscape']
    if not {0., 1., 2., *cycle}.issubset(landscape['x']):
        raise RuntimeError('counterexample geometry omits joins or reference points')
    if not len(landscape['x']) == len(landscape['objective']) == len(landscape['gradient']):
        raise RuntimeError('counterexample geometry is incomplete')
    for x, value, g in zip(landscape['x'], landscape['objective'], landscape['gradient']):
        close(value, objective(x))
        close(g, gradient(x))
