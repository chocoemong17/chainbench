"""Coordinate-only explanation of the existing published SPD trajectories."""
from __future__ import annotations

import numpy as np


def add_metric_coordinates(problem: dict, cases: list[dict]) -> dict:
    """Retain actual displacements; never replace a missing angle by zero.

    For a 2x2 SPD A, Cayley-Hamilton gives its unique symmetric positive square
    root T=(A+sqrt(det(A))*I)/sqrt(trace(A)+2*sqrt(det(A))). This is a display
    transform of already computed iterates, not a preconditioned solver.
    """
    a = np.array(problem['A'])
    root_det = np.sqrt(np.linalg.det(a))
    transform = (a + root_det*np.eye(2)) / np.sqrt(np.trace(a)+2*root_det)
    star = np.array(problem['x_star'])
    for case in cases:
        for run in case['runs'].values():
            rows = run['rows']
            for k, row in enumerate(rows):
                row['metric_coordinates'] = (transform @ (np.array(row['x'])-star)).tolist()
                row['step_pair'] = None
                if k < 2:
                    continue
                u = np.array(rows[k-1]['x']) - rows[k-2]['x']
                v = np.array(row['x']) - rows[k-1]['x']
                tu, tv = transform @ u, transform @ v
                euclidean_denominator = float(np.linalg.norm(u)*np.linalg.norm(v))
                metric_denominator = float(np.linalg.norm(tu)*np.linalg.norm(tv))
                row['step_pair'] = {
                    'previous': u.tolist(), 'current': v.tolist(),
                    'transformed_previous': tu.tolist(), 'transformed_current': tv.tolist(),
                    'euclidean_dot': float(u @ v), 'a_dot': float(u @ a @ v),
                    'cos_euclidean': float(u @ v)/euclidean_denominator
                    if euclidean_denominator else None,
                    'cos_a': float(u @ a @ v)/metric_denominator
                    if metric_denominator else None,
                }
    return {'transform': transform.tolist(), 'formula': 'z = T(x-x*); T = A^(1/2)',
            'identity': 'T^T T = A; 0.5 ||z||_2^2 = f(x)-f*',
            'step_pair': 'at row k>=2: u=x[k-1]-x[k-2], v=x[k]-x[k-1]',
            'normalization': 'each displayed direction has unit Euclidean length in its own view',
            'missing': 'null before two updates; cosine null if either displacement is zero',
            'scope': 'display transform of existing iterates, not a preconditioned solve'}
