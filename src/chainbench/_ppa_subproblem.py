"""Explain already computed exact-quadratic PPA steps and their solve residuals."""
from __future__ import annotations

import numpy as np

SOURCE = 'https://sites.math.washington.edu/~rtr/papers/rtr066-MonoOpProxPoint.pdf'


def subproblem_record(problem, trace, parameter):
    hessian = problem.Q+np.eye(problem.dim)/parameter
    rows = []
    for k, (previous, point) in enumerate(zip(trace.iterates[:-1], trace.iterates[1:]), 1):
        rhs = problem.b+previous/parameter
        reference = np.linalg.solve(hessian, rhs)
        gradient = problem.grad(point)
        penalty_gradient = (point-previous)/parameter
        balance = gradient+penalty_gradient
        denominator = float(np.linalg.norm(gradient)+np.linalg.norm(penalty_gradient))
        residual = float(np.linalg.norm(balance))
        movement = point-previous
        error = point-reference
        reference_balance = hessian@reference-rhs
        rows.append({'completed_update': k, 'previous': previous.tolist(), 'next': point.tolist(),
                     'rhs': rhs.tolist(), 'reference': reference.tolist(),
                     'objective_gradient': gradient.tolist(), 'penalty_gradient': penalty_gradient.tolist(),
                     'balance': balance.tolist(), 'balance_norm': residual,
                     'relative_balance': residual/denominator if denominator else None,
                     'balance_denominator': denominator,
                     'reference_balance': reference_balance.tolist(),
                     'previous_objective_gap': problem.gap(previous),
                     'next_objective_gap': problem.gap(point),
                     'penalty_value': float(movement@movement/(2*parameter)),
                     'subproblem_value_above_f_star': problem.gap(point)+float(movement@movement/(2*parameter)),
                     'reference_error_energy': float(.5*error@hessian@error),
                     'unchanged_iterate': bool(np.array_equal(previous, point)),
                     'movement_norm': float(np.linalg.norm(movement))})
    return {'kind': 'exact-quadratic-ppa-subproblems', 'parameter': float(parameter),
            'objective': 'phi_k(u)=f(u)+||u-x_k||^2/(2c)',
            'hessian': hessian.tolist(), 'stationarity': 'grad f(next)+(next-previous)/c=0 in exact arithmetic',
            'source': {'url': SOURCE, 'proximal_problem': 'Eqs. (1.7)-(1.9), printed p.878 / PDF page 2',
                       'residual_operator': 'Eq. (1.16), printed p.880 / PDF page 4'},
            'scope': 'Existing exact quadratic specialization, not the general inexact monotone-operator algorithm.',
            'reference_scope': 'A floating-point solve of the shifted 2D system; residuals are retained.',
            'indexing': 'completed_update k shows the solve from stored x[k-1] to x[k]; no solve at k=0',
            'rows': rows}
