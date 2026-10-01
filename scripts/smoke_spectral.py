"""Independently validate the fixed published spectrum with scalar arithmetic."""
from __future__ import annotations

import math


def validate_spectral(result):
    def require(condition):
        if not condition:
            raise RuntimeError('spectral evidence differs from the source or computed errors')
    def close(actual, expected):
        if expected is None:
            require(actual is None)
        else:
            require(isinstance(actual, (int, float)) and math.isfinite(actual)
                    and math.isclose(actual, expected, rel_tol=2e-11, abs_tol=2e-13))
    def sequence(actual, expected):
        require(len(actual) == len(expected))
        for a, b in zip(actual, expected):
            close(a, b)
    g = result['spectral_geometry']
    require(g['eigenvalues'] == [2., 7.] and g['plot_domain'] == [0., 8.]
            and g['spectral_interval'] == [2., 7.])
    require(result['source']['envelope'] == 'Section 9.2, Eq. (52), printed p. 36 / PDF page 42')
    require(result['source']['spectral'] == 'Sections 9.1-9.2, Eq. (50), Figures 31(a-c)/33, printed pp. 33-36 / PDF pages 39-42')
    root = math.sqrt(5)
    sequence(g['eigenvectors'][0], [2/root, -1/root])
    sequence(g['eigenvectors'][1], [1/root, 2/root])
    require(len(g['polynomials']) == 3)
    for k, p in enumerate(g['polynomials']):
        require(p['degree'] == k)
        grid = [i*.05 for i in range(161)]
        sequence(p['abscissae'], grid)
        # Expanded coefficients differ from the product/Chebyshev expressions used by the exporter.
        def finite(t):
            return [1., 1-2*t/9, (14-9*t+t*t)/14][k]
        def interval(t):
            return finite(t) if k < 2 else (137-72*t+8*t*t)/137
        sequence(p['finite_spectrum'], [finite(t) for t in grid])
        sequence(p['interval'], [interval(t) for t in grid])
        sequence(p['finite_at_eigenvalues'], [finite(t) for t in (2, 7)])
        sequence(p['interval_at_eigenvalues'], [interval(t) for t in (2, 7)])
        close(p['finite_envelope_factor'], [1, 5/9, 0][k])
        close(p['interval_envelope_factor'], [1, 5/9, 25/137][k])
    require(g['finite_formulas'] == ['1', '1-2*t/9', '(1-t/2)*(1-t/7)'])
    require(g['interval_formulas'] == ['1', '1-2*t/9', '(137-72*t+8*t^2)/137'])
    for case in result['cases']:
        x0, y0 = case['start'][0]-2, case['start'][1]+2
        initial = [(2*x0-y0)/root, (x0+2*y0)/root]
        initial_energy = 3*x0*x0+4*x0*y0+6*y0*y0
        weights = [2*initial[0]**2, 7*initial[1]**2]
        sequence(case['spectral_initial']['coefficients'], initial)
        sequence(case['spectral_initial']['energy_squared'], weights)
        sequence(case['spectral_initial']['energy_weights'], [w/initial_energy for w in weights])
        for row in case['runs']['cg']['rows']:
            x, y = row['x'][0]-2, row['x'][1]+2
            coeff = [(2*x-y)/root, (x+2*y)/root]
            energies = [2*coeff[0]**2, 7*coeff[1]**2]
            r = row['spectral']
            sequence(r['coefficients'], coeff)
            sequence(r['component_ratios'], [c/base if base else None for c, base in zip(coeff, initial)])
            sequence(r['energy_squared'], energies)
            sequence(r['normalized_energy_squared'], [e/initial_energy for e in energies])
            close(r['energy_ratio'], row['energy_error']/math.sqrt(initial_energy))
            close(sum(energies), 2*row['gap'])
            require(r['reference_degree'] == min(row['iteration'], 2))
