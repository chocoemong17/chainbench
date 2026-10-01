"""Independent scalar/Decimal checks of the declared CG spectral case study."""
from __future__ import annotations

import hashlib
import json
import math
import struct
from decimal import Decimal, localcontext


def validate_cg_spectrum(data):
    def fail(message):
        raise RuntimeError("CG spectrum: " + message)

    def close(actual, expected, *, relative=False):
        tolerance = 1e-300 if relative else 1e-14
        if (type(actual) not in (int, float) or not math.isfinite(actual)
                or not math.isclose(actual, float(expected), rel_tol=2e-12 if relative else 0,
                                    abs_tol=tolerance)):
            fail("numeric value differs")

    def vector(actual, expected, *, relative=False):
        if len(actual) != len(expected):
            fail("vector length differs")
        for a, b in zip(actual, expected):
            close(a, b, relative=relative)

    def linear(first, last, count):
        values = [first+i*((last-first)/(count-1)) for i in range(count)]
        values[-1] = last
        return values

    def dot(a, b):
        return math.fsum(x*y for x, y in zip(a, b))

    if (data['kind'] != 'chainbench.cg-spectrum' or data['schema_version'] != 1
            or data['evidence_level'] != 'controlled-spectral-illustrations'):
        fail("evidence identity differs")
    params = data['parameters']
    steps = params['steps']
    if (type(steps) is not int or not 1 <= steps <= 64
            or params['dimension'] != 16 or params['rtol'] != 1e-12 or params['atol'] != 0
            or params['seed'] is not None or params['declared_interval'] != [2., 7.]
            or params['declared_condition_number'] != 3.5
            or params['stopping'] != 'true residual norm <= rtol times initial true residual norm, or budget exhausted'
            or params['recurrence'] != 'existing scaled correction-equation CG; no new optimizer'):
        fail("protocol differs")
    if data['source'] != {
        'author': 'Jonathan Richard Shewchuk', 'year': 1994,
        'url': 'https://www.cs.cmu.edu/~quake-papers/painless-conjugate-gradient.pdf',
        'polynomial': 'Section 9.1, pp.33–35 / PDF 39–41, Eq. (50), Figure 31',
        'interval': 'Section 9.2, p.36 / PDF 42, Eqs. (51)–(52), Figure 33',
        'scope': "new declared inputs illustrating the published spectral reasoning; not Figure 31(d)'s original data",
    }:
        fail("source attribution differs")
    spectra = {
        'two-values': [2.]*8+[7.]*8,
        'two-clusters': linear(2., 2.1, 8)+linear(6.9, 7., 8),
        'spread': linear(2., 7., 16),
    }
    expected_ids = [f'{s}-{b}-{p}' for s in spectra for b in ('diagonal', 'hadamard')
                    for p in ('equal-coefficients', 'equal-energy', 'single-mode')]
    if (data['design'] != 'all 3 spectra x 2 orthogonal bases x 3 initial-error profiles, without performance filtering'
            or data['problem'] != 'f(x)=0.5*x^T*A*x; b=0; x*=0; ||x0||_2=1'
            or data['input_hash_encoding'] != 'SHA-256 little-endian float64 row-major A, then b, then x0'
            or [c['id'] for c in data['cases']] != expected_ids):
        fail("case coverage or ordering differs")
    for case in data['cases']:
        name, basis_name, profile = case['spectrum'], case['basis_name'], case['start_profile']
        if case['id'] != f'{name}-{basis_name}-{profile}' or case['dimension'] != 16:
            fail("case labels differ")
        values = spectra[name]
        # Independent closed-form Walsh entries, rather than Sylvester block assembly.
        basis = [[float(i == j) if basis_name == 'diagonal'
                  else (-1. if bin(i & j).count('1') % 2 else 1.)/4
                  for j in range(16)] for i in range(16)]
        matrix = [[math.fsum(basis[i][k]*values[k]*basis[j][k] for k in range(16))
                   for j in range(16)] for i in range(16)]
        if case['declared_eigenvalues'] != values:
            fail("declared spectrum differs")
        for actual, expected in zip(case['basis'], basis):
            vector(actual, expected)
        if len(case['basis']) != 16 or len(case['A']) != 16:
            fail("matrix dimension differs")
        for actual, expected in zip(case['A'], matrix):
            vector(actual, expected)
        matrix = case['A']
        if case['b'] != [0.]*16 or case['x_star'] != [0.]*16:
            fail("declared solution or right hand side differs")
        initial = [1.]*16 if profile == 'equal-coefficients' else (
            [1/math.sqrt(v) for v in values] if profile == 'equal-energy' else [1.]+[0.]*15)
        norm = math.sqrt(dot(initial, initial))
        initial = [v/norm for v in initial]
        start = [dot(row, initial) for row in basis]
        vector(case['declared_initial_coefficients'], initial)
        vector(case['start'], start)
        start = case['start']
        digest = hashlib.sha256(struct.pack('<288d', *[v for row in matrix for v in row],
                                            *case['b'], *start)).hexdigest()
        if digest != case['input_sha256']:
            fail("input fingerprint differs")
        actual_initial = case['actual_initial_coefficients']
        vector(actual_initial, [math.fsum(basis[i][j]*start[i] for i in range(16))
                                for j in range(16)])
        initial_energy = dot(start, [dot(row, start) for row in matrix])
        initial_spectral = math.fsum(v*c*c for v, c in zip(values, actual_initial))
        close(case['initial_energy'], initial_energy, relative=True)
        close(case['initial_spectral_energy'], initial_spectral, relative=True)
        initial_residual = math.hypot(*[-dot(row, start) for row in matrix])
        close(case['initial_residual_norm'], initial_residual, relative=True)
        close(case['residual_tolerance'], 1e-12*case['initial_residual_norm'], relative=True)
        if (case['declared_condition_number'] != 3.5
                or case['distinct_declared_eigenvalues'] != len(set(values))
                or case['active_declared_eigenvalues'] != sorted({v for v,c in zip(case['declared_eigenvalues'],actual_initial) if c != 0})
                or case['basis_layout'] != 'columns are the declared construction modes'):
            fail("spectral metadata differs")
        close(case['realized_mu'], 2.)
        close(case['realized_L'], 7.)
        close(case['realized_condition_number'], case['realized_L']/case['realized_mu'])
        close(case['basis_orthogonality_error_inf'], 0.)
        eigen_error = max(abs(dot(matrix[i], [basis[j][k] for j in range(16)])-basis[i][k]*values[k])
                          for i in range(16) for k in range(16))
        close(case['eigen_equation_error_inf'], eigen_error)
        rows = case['rows']
        if (type(case['completed_updates']) is not int or case['completed_updates'] != len(rows)-1
                or not 1 <= len(rows)-1 <= steps or rows[0]['x'] != start
                or rows[0]['coefficients'] != actual_initial):
            fail("recorded budget or initial iterate differs")
        with localcontext() as context:
            context.prec = 60
            a = [[Decimal.from_float(v) for v in row] for row in matrix]
            x = [Decimal.from_float(v) for v in start]
            residual = [-sum(v*w for v,w in zip(row,x)) for row in a]
            direction = list(residual)
            rr = sum(v*v for v in residual)
            for k, row in enumerate(rows):
                if type(row['iteration']) is not int or row['iteration'] != k:
                    fail("iteration index differs")
                vector(row['x'], x)
                if k+1 < len(rows):
                    ad = [sum(v*w for v,w in zip(arow,direction)) for arow in a]
                    alpha = rr/sum(v*w for v,w in zip(direction,ad))
                    x = [v+alpha*w for v,w in zip(x,direction)]
                    residual = [v-alpha*w for v,w in zip(residual,ad)]
                    following_rr = sum(v*v for v in residual)
                    direction = [v+(following_rr/rr)*w for v,w in zip(residual,direction)]
                    rr = following_rr
        for row in rows:
            if len(row['component_ratios']) != 16:
                fail("mode ratio coverage differs")
            x = row['x']
            vector(row['coefficients'], [math.fsum(basis[i][j]*x[i] for i in range(16))
                                         for j in range(16)])
            coefficients = row['coefficients']
            energies = [v*c*c for v,c in zip(case['declared_eigenvalues'],coefficients)]
            vector(row['mode_energy'], energies, relative=True)
            vector(row['normalized_mode_energy'], [v/case['initial_spectral_energy'] for v in energies], relative=True)
            direct = dot(x, [dot(arow,x) for arow in matrix])
            close(row['direct_energy'], direct, relative=True)
            close(row['spectral_energy'], math.fsum(energies), relative=True)
            if row['energy_identity_difference'] != row['direct_energy']-row['spectral_energy']:
                fail("raw energy reconstruction difference was changed")
            close(row['energy_ratio'], math.sqrt(row['direct_energy']/case['initial_energy']), relative=True)
            close(row['spectral_energy_ratio'], math.sqrt(row['spectral_energy']/case['initial_spectral_energy']), relative=True)
            close(row['objective'], direct/2, relative=True)
            close(row['euclidean_error'], math.hypot(*x), relative=True)
            vector(row['true_residual'], [-dot(arow,x) for arow in matrix])
            close(row['true_residual_norm'], math.hypot(*row['true_residual']), relative=True)
            for actual, value, base in zip(row['component_ratios'], coefficients, actual_initial):
                if base == 0:
                    if actual is not None:
                        fail("a missing initial mode has a fabricated ratio")
                else:
                    close(actual, value/base, relative=True)
        tolerance = case['residual_tolerance']
        if any(row['true_residual_norm'] <= tolerance for row in rows[:-1]):
            fail("CG continued after its stopping criterion")
        expected_stop = 'converged' if rows[-1]['true_residual_norm'] <= tolerance else 'max_steps'
        if case['termination'] != expected_stop or (expected_stop == 'max_steps' and len(rows)-1 != steps):
            fail("termination reason differs")
        witness = case['quadratic_witness']
        roots = [math.fsum(values[:8])/8, math.fsum(values[8:])/8]
        vector(witness['roots'], roots)
        grid = [i/20 for i in range(161)]
        vector(witness['abscissae'], grid)
        vector(witness['values'], [(1-v/roots[0])*(1-v/roots[1]) for v in grid])
        node_values = [(1-v/roots[0])*(1-v/roots[1]) for v in values]
        vector(witness['at_eigenvalues'], node_values)
        close(witness['all_spectrum_factor'], max(abs(v) for v in node_values))
        close(witness['active_spectrum_factor'], max(abs(v) for v,c in zip(node_values,actual_initial) if c != 0))
        close(witness['weighted_energy_factor'], math.sqrt(math.fsum(
            v*c*c*w*w for v,c,w in zip(values,actual_initial,node_values))/initial_spectral))
        if (witness['degree'] != 2 or witness['rule'] != 'roots at the arithmetic means of sorted modes 0:8 and 8:16'
                or witness['scope'] != 'declared comparison polynomial, not an actual CG polynomial'):
            fail("quadratic witness scope differs")
    comparisons = data['comparisons']
    if len(comparisons) != max(c['completed_updates'] for c in data['cases'])+1:
        fail("comparison degree coverage differs")
    for k, reference in enumerate(comparisons):
        if reference['degree'] != k:
            fail("comparison degree differs")
        grid = [i/20 for i in range(161)]
        vector(reference['abscissae'], grid)
        denominator = math.cosh(k*math.acosh(9/5))
        def chebyshev(value):
            if abs(value) <= 1:
                return math.cos(k*math.acos(value))
            return (1 if value > 1 or k % 2 == 0 else -1)*math.cosh(k*math.acosh(abs(value)))
        vector(reference['values'], [chebyshev((9-2*v)/5)/denominator for v in grid])
        close(reference['interval_envelope'], 1/denominator, relative=True)
        rho = (math.sqrt(3.5)-1)/(math.sqrt(3.5)+1)
        close(reference['looser_envelope'], 2*rho**k, relative=True)


def exercise_cg_spectrum(cli, work, env, run, extract_record):
    for steps in (1, 32, 64):
        args = [cli, 'case-study', 'cg-spectrum', '--steps', str(steps)]
        data = json.loads(run(args+['--format','json'],work,env))
        validate_cg_spectrum(data)
        html = run(args+['--lang','ko'],work,env)
        if (extract_record(html) != data or html.count('<section data-cg-case=') != 18
                or html.count('<details data-cg-frame=') != sum(len(c['rows']) for c in data['cases'])):
            raise RuntimeError('CG spectrum HTML differs from installed JSON or omits stages')
