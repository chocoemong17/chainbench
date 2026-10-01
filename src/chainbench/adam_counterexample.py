"""Finite instantiations of Reddi–Kale–Kumar's Theorem 1 counterexample.

This is the paper's no-debiasing, beta1=0 analysis variant on periodic online
linear losses, not a neural-network benchmark or the Figure 1 experiment.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform

import numpy as np

from . import __version__

SOURCE = "https://arxiv.org/pdf/1904.09237v1"
METHODS = ("adam", "amsgrad")


def _run(inputs, gradients, rates, gradient_sums, method):
    beta2 = inputs['beta2']
    x, m, v, maximum = 1., 0., 0., 0.
    loss, regret, previous_inverse = 0., 0., None
    series = {key: [] for key in (
        'first_moment', 'second_moment', 'denominator_memory', 'effective_rate',
        'inverse_rate', 'inverse_rate_difference', 'proposal', 'displacement',
        'projection_correction', 'loss', 'regret_increment', 'cumulative_loss',
        'cumulative_regret', 'average_regret', 'loss_regret_difference',
    )}
    series['x'] = [x]
    for t, (g, alpha_t, gradient_sum) in enumerate(zip(gradients, rates, gradient_sums), 1):
        # Loss is incurred at x_t, before observing its gradient and updating.
        incurred = g*x
        increment = g*(x+1)
        loss += incurred
        regret += increment
        m = inputs['beta1']*m+(1-inputs['beta1'])*g
        v = beta2*v+(1-beta2)*g*g
        maximum = max(maximum, v)
        memory = maximum if method == 'amsgrad' else v
        effective = alpha_t/math.sqrt(memory)
        inverse = math.sqrt(memory)/alpha_t
        proposed = x-effective*m
        following = min(1., max(-1., proposed))
        values = {
            'first_moment': m, 'second_moment': v, 'denominator_memory': memory,
            'effective_rate': effective, 'inverse_rate': inverse,
            'inverse_rate_difference': None if previous_inverse is None else inverse-previous_inverse,
            'proposal': proposed, 'displacement': following-x,
            'projection_correction': following-proposed,
            'loss': incurred, 'regret_increment': increment,
            'cumulative_loss': loss, 'cumulative_regret': regret, 'average_regret': regret/t,
            'loss_regret_difference': regret-(loss+gradient_sum),
        }
        for key, value in values.items():
            series[key].append(value)
        x, previous_inverse = following, inverse
        series['x'].append(x)
    lower = 2*inputs['C']-4
    cycles = []
    for start in range(0, len(gradients)-2, 3):
        actual = math.fsum(series['regret_increment'][start:start+3])
        cycles.append({
            'first_round': start+1, 'last_round': start+3,
            'start_x': series['x'][start], 'end_x': series['x'][start+3],
            'regret': actual, 'source_lower': lower if method=='adam' else None,
            'lower_margin': actual-lower if method=='adam' else None,
        })
    return {
        'method': method, 'updates': len(gradients), 'termination': 'fixed_budget',
        'series': series, 'complete_cycles': cycles,
        'observations': {
            'final_x': x, 'min_x': min(series['x']), 'max_x': max(series['x']),
            'final_average_regret': regret/len(gradients),
            'inverse_rate_decreases': [t for t, value in enumerate(series['inverse_rate_difference'], 1)
                                       if value is not None and value < 0],
            'projection_rounds': [t for t, value in enumerate(series['projection_correction'], 1) if value != 0],
            'computed_cycle_start_states_equal_one': all(value==1 for value in series['x'][::3]),
            'all_computed_states_positive': all(value>0 for value in series['x']),
        },
    }


def run_adam_counterexample(steps: int = 3000) -> dict:
    if type(steps) is not int or not 1 <= steps <= 12000:
        raise ValueError('steps must be an integer between 1 and 12000')
    cases = []
    for C in (3, 10, 100):
        beta2 = 1/(1+C*C)
        for fraction in (.1, .5, .9):
            alpha = fraction*math.sqrt(1-beta2)
            inputs = {
                'C': C, 'alpha_fraction': fraction, 'alpha': alpha,
                'beta1': 0., 'beta2': beta2, 'bias_correction': False, 'epsilon': 0.,
                'initial_x': 1., 'initial_m': 0., 'initial_v': 0., 'initial_max_v': 0.,
                'domain': [-1., 1.], 'period': 3, 'gradient_pattern': [float(C), -1., -1.],
                'steps': steps, 'step_schedule': 'alpha/sqrt(t), t=1..T',
                'loss_timing': 'g_t*x_t before the update to x_(t+1)',
            }
            gradients = [float(C) if t%3==1 else -1. for t in range(1, steps+1)]
            rates = [alpha/math.sqrt(t) for t in range(1, steps+1)]
            gradient_sums = []
            total = 0.
            for g in gradients:
                total += g
                gradient_sums.append(total)
            digest = hashlib.sha256(json.dumps(inputs, sort_keys=True, separators=(',', ':'),
                                              allow_nan=False).encode()).hexdigest()
            cases.append({
                'id': f'c{C}-a{fraction:g}', 'inputs': inputs, 'input_sha256': digest,
                'rounds': list(range(1, steps+1)), 'gradients': gradients,
                'step_sizes': rates, 'gradient_sums': gradient_sums,
                'best_fixed_point': -1., 'best_fixed_cumulative_loss': [-v for v in gradient_sums],
                'cycle_mean_loss_slope': (C-2)/3,
                'source_reference': {
                    'block_regret_lower': 2*C-4,
                    'average_regret_lower': 2*(C-2)/3,
                    'rounds': list(range(3, steps+1, 3)),
                    'scope': 'Adam source variant, complete three-round blocks, x1=1 and stated alpha/beta conditions',
                },
                'native_rounds': sorted({t for t in (1,2,3,4,5,6,9,30,300,3000,steps) if t<=steps}),
                'runs': {method: _run(inputs, gradients, rates, gradient_sums, method) for method in METHODS},
            })
    data = {
        'kind': 'chainbench.adam-counterexample', 'schema_version': 1,
        'evidence_level': 'published-counterexample-family-with-declared-finite-instantiations',
        'source': {
            'authors': ['Sashank J. Reddi', 'Satyen Kale', 'Sanjiv Kumar'],
            'title': 'On the Convergence of Adam and Beyond',
            'venue_year': 2018, 'version': 'arXiv:1904.09237v1 (2019-04-19)', 'url': SOURCE,
            'adam': 'Algorithm 1 / Eq. (1), p.3; no debiasing as in footnote 1',
            'counterexample': 'Section 3 / Theorem 1, p.4; Appendix A / Eqs. (4)-(6), pp.10-11',
            'amsgrad': 'Algorithm 2, p.5, specialized to beta1=0',
            'inverse_rate': 'Eq. (2), p.4; current-minus-previous inverse learning rate for t>=2',
        },
        'parameters': {
            'steps': steps, 'C_values': [3,10,100], 'alpha_fractions': [.1,.5,.9],
            'methods': list(METHODS), 'seed': None,
            'design': 'all 3 C values x 3 alpha fractions, both source variants, no outcome filtering',
        },
        'input_hash_encoding': 'SHA-256 of sorted-key compact JSON inputs, encoded UTF-8',
        'series_indexing': 'x[j] is x_(j+1); every other series[j] belongs to round t=j+1',
        'regret_definition': 'R_T=sum_(t=1)^T g_t*x_t - min_(x in [-1,1]) sum_(t=1)^T g_t*x',
        'regret_computation': 'accumulate g_t*(x_t+1); retain difference from cumulative_loss-best_fixed_loss',
        'initial_average_regret': None,
        'cases': cases,
        'environment': {'chainbench': __version__, 'numpy': np.__version__, 'python': platform.python_version()},
        'differences': [
            'The source specifies a counterexample family; C, alpha fractions and finite budgets are declared instantiations.',
            'This reproduces Theorem 1 / Appendix A, not the different period-101 Figure 1 experiment.',
            'Use the paper analysis variant: beta1=0, no moment debiasing, no epsilon, projection onto [-1,1].',
            'AMSGrad is a finite comparison using the same inputs, not a neural-network performance comparison.',
        ],
        'limits': [
            'Losses change with the round: regret is not an objective gap of one fixed function.',
            'The loss is incurred before its update; x_(T+1) has no invented next-round loss.',
            'An individual regret increment may be negative; average regret at T=0 is undefined.',
            'The displayed positive lower bound is scoped to Adam and completed three-round blocks.',
            'Every declared case is retained, including an AMSGrad path still far from -1 at the default budget.',
            'Finite numerical checks are not an asymptotic proof, a universal algorithm ranking or a claim about default modern Adam.',
        ],
    }
    json.dumps(data, allow_nan=False)
    return data
