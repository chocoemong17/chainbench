"""Source comparison polynomials and actual errors, with no new optimizer."""
from __future__ import annotations

import math


def add_spectral_coordinates(problem: dict, cases: list[dict]) -> dict:
    """For the fixed published A, use v2=(2,-1)/sqrt(5), v7=(1,2)/sqrt(5).

    Only observed values at the two eigenvalues are attributed to the actual run.
    The continuous curves are source comparison polynomials, not fitted CG curves.
    """
    if problem['A'] != [[3., 2.], [2., 6.]]:
        raise ValueError('spectral explanation requires the published 2x2 matrix')
    root = math.sqrt(5)
    eigenvalues = [2., 7.]
    grid = [i/20 for i in range(161)]
    polynomials = []
    for degree in range(3):
        def finite(t):
            return 1. if degree == 0 else 1-2*t/9 if degree == 1 else (1-t/2)*(1-t/7)
        def interval(t):
            return finite(t) if degree < 2 else (2*((9-2*t)/5)**2-1)/(2*(9/5)**2-1)
        polynomials.append({
            'degree': degree, 'abscissae': grid,
            'finite_spectrum': [finite(t) for t in grid],
            'interval': [interval(t) for t in grid],
            'finite_at_eigenvalues': [finite(t) for t in eigenvalues],
            'interval_at_eigenvalues': [interval(t) for t in eigenvalues],
            'finite_envelope_factor': [1., 5/9, 0.][degree],
            'interval_envelope_factor': [1., 5/9, 25/137][degree],
        })
    for case in cases:
        def coefficients(x):
            e0, e1 = x[0]-problem['x_star'][0], x[1]-problem['x_star'][1]
            return [(2*e0-e1)/root, (e0+2*e1)/root]
        initial = coefficients(case['start'])
        weights = [lam*c*c for lam, c in zip(eigenvalues, initial)]
        total = sum(weights)
        case['spectral_initial'] = {'coefficients': initial, 'energy_squared': weights,
                                    'energy_weights': [w/total for w in weights]}
        for row in case['runs']['cg']['rows']:
            coeff = coefficients(row['x'])
            energy = [lam*c*c for lam, c in zip(eigenvalues, coeff)]
            degree = min(row['iteration'], 2)
            row['spectral'] = {
                'coefficients': coeff,
                'component_ratios': [c/base if base != 0 else None
                                     for c, base in zip(coeff, initial)],
                'energy_squared': energy,
                'normalized_energy_squared': [e/total for e in energy],
                'energy_ratio': math.sqrt(sum(energy)/total),
                'reference_degree': degree,
            }
    return {
        'eigenvalues': eigenvalues, 'eigenvectors': [[2/root, -1/root], [1/root, 2/root]],
        'basis_layout': 'rows are unit eigenvectors ordered by eigenvalue 2, 7',
        'identity': 'c_j = v_j^T (x-x*); ||x-x*||_A^2 = sum_j lambda_j c_j^2',
        'polynomials': polynomials,
        'finite_formulas': ['1', '1-2*t/9', '(1-t/2)*(1-t/7)'],
        'interval_formulas': ['1', '1-2*t/9', '(137-72*t+8*t^2)/137'],
        'scope': 'source comparison curves; actual component ratios only at eigenvalues',
        'missing': 'component ratio null when its initial coefficient is exactly zero',
        'roundoff': 'source envelopes use exact arithmetic; computed errors are not forced to zero',
        'plot_domain': [0., 8.], 'spectral_interval': [2., 7.],
    }
