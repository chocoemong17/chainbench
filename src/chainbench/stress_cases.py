"""Versioned synthetic stress cases with actual inputs and complete trajectories."""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np

from .methods import (
    accelerated_gradient,
    conjugate_gradient,
    fista,
    frank_wolfe,
    gradient_descent,
    heavy_ball,
    ista,
    proximal_point,
)
from .problems import DiagonalLassoProblem, QuadraticProblem, SimplexQuadraticProblem

TOPICS = ('gd-baseline', 'nesterov-1983', 'polyak-1964', 'hestenes-stiefel-1952',
          'jaggi-2013', 'rockafellar-1976', 'beck-teboulle-2009', 'ista-vs-fista')
DIMENSIONS = (6, 12, 24, 40)
SAMPLER = 'stratified-pcg64-v2'


def validate_seed(seed):
    if type(seed) is not int or not 0 <= seed <= 2**63-1:
        raise ValueError('seed must be an integer between 0 and 2^63-1')


def input_digest(arrays: dict) -> str:
    """Sorted names, shapes and little-endian float64 bytes, including x0."""
    h = hashlib.sha256()
    for name in sorted(arrays):
        arr = np.ascontiguousarray(np.asarray(arrays[name], dtype='<f8'))
        h.update(name.encode('ascii') + b'\0')
        h.update(json.dumps(arr.shape, separators=(',', ':')).encode('ascii') + b'\0')
        h.update(arr.tobytes(order='C'))
    return h.hexdigest()


def _mix(rng, dim):
    result = np.eye(dim)
    for _ in range(3):
        v = rng.normal(size=dim)
        norm = float(np.hypot.reduce(v))
        if not math.isfinite(norm) or norm == 0:
            raise FloatingPointError('invalid sampled rotation vector')
        v = v/norm
        result = (np.eye(dim)-2*np.outer(v, v)) @ result
    return result


def _problem(topic, seed, rng):
    dim = DIMENSIONS[seed % 4]
    rotated = (seed//4) % 2 == 1
    random_start = (seed//8) % 2 == 1
    if topic in ('beck-teboulle-2009', 'ista-vs-fista'):
        problem = DiagonalLassoProblem(rng.uniform(.4, 2., dim), rng.uniform(-1.6, 1.6, dim),
                                       float(10**rng.uniform(-2., -.25)))
        arrays = {'a': problem.a.tolist(), 'b': problem.b.tolist(), 'lam': [problem.lam]}
        orientation = 'diagonal'
        x0 = rng.uniform(-1., 1., dim) if random_start else np.zeros(dim)
        family = 'diagonal-lasso'
    elif topic == 'jaggi-2013':
        raw = rng.uniform(.05, 1., dim)
        problem = SimplexQuadraticProblem(raw/raw.sum())
        arrays = {'target': problem.target.tolist()}
        orientation = 'simplex-basis'
        if random_start:
            raw = rng.uniform(.05, 1., dim)
            x0 = raw/raw.sum()
        else:
            x0 = np.eye(1, dim)[0]
        family = 'simplex-quadratic'
    else:
        L = float(10**rng.uniform(-.35, .35))
        kappa = (1e5 if topic in ('gd-baseline', 'nesterov-1983')
                 else float(10**rng.uniform(.5, 3.)))
        eig = np.r_[L/kappa, np.sort(10**rng.uniform(math.log10(L/kappa), math.log10(L), dim-2)), L]
        mix = _mix(rng, dim) if rotated else np.eye(dim)
        q = mix.T @ np.diag(eig) @ mix
        problem = QuadraticProblem.from_reference((q+q.T)/2, rng.uniform(-1., 1., dim))
        arrays = {'Q': problem.Q.tolist(), 'b': problem.b.tolist(), 'x_star': problem.x_star.tolist()}
        orientation = 'seeded-householder' if rotated else 'diagonal'
        x0 = rng.uniform(-1., 1., dim) if random_start else np.zeros(dim)
        family = 'quadratic'
    arrays['x0'] = x0.tolist()
    return problem, x0, arrays, {'family': family, 'orientation': orientation,
                                'start_kind': ('seeded-feasible' if family == 'simplex-quadratic'
                                               else 'seeded-uniform') if random_start else
                                              ('vertex-e1' if family == 'simplex-quadratic' else 'zero')}


def _curve(label, indices, values, role='observed'):
    values = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(values)) or np.any(values < 0):
        raise FloatingPointError('invalid stress curve')
    return {'label': label, 'iterations': [int(k) for k in indices],
            'values': values.tolist(), 'role': role}


def _record(problem, trace):
    gaps = np.asarray([problem.gap(x) for x in trace.iterates])
    if (not np.all(np.isfinite(gaps)) or np.any(gaps < 0)
            or not np.all(np.isfinite(trace.iterates))):
        raise FloatingPointError('invalid stress trajectory')
    return {'iterates': [x.tolist() for x in trace.iterates], 'gaps': gaps.tolist(),
            'updates': len(trace.iterates)-1, 'termination': trace.termination or 'fixed_budget'}


def trial(topic: str, seed: int) -> dict:
    if topic not in TOPICS:
        raise ValueError('unknown stress topic')
    validate_seed(seed)
    rng = np.random.Generator(np.random.PCG64(seed))
    p, x0, arrays, design = _problem(topic, seed, rng)
    parameters = {'L': 1. if isinstance(p, SimplexQuadraticProblem) else p.L}
    if isinstance(p, QuadraticProblem):
        parameters.update(mu=p.mu, condition_number=p.L/p.mu)
    elif isinstance(p, DiagonalLassoProblem):
        parameters['lambda'] = p.lam
    else:
        parameters['curvature'] = p.curvature_upper_bound
    threshold, evidence_kind = 1., 'theorem-specialization'
    reason, measurement, runs, curves = None, {}, {}, []
    metric = None
    if topic in ('gd-baseline', 'nesterov-1983', 'beck-teboulle-2009', 'jaggi-2013'):
        method, fn, steps = {
            'gd-baseline': ('gd', gradient_descent, 40),
            'nesterov-1983': ('smooth-fista', accelerated_gradient, 40),
            'beck-teboulle-2009': ('fista', fista, 50),
            'jaggi-2013': ('frank-wolfe', frank_wolfe, 40),
        }[topic]
        trace = fn(p, steps, x0=x0)
        runs[method] = _record(p, trace)
        gaps = np.asarray(runs[method]['gaps'])
        k = np.arange(1, steps+1)
        radius2 = float((x0-p.x_star) @ (x0-p.x_star))
        parameters['radius_squared'] = radius2
        if topic == 'gd-baseline':
            bound = p.L*radius2/(2*k)
            formula = 'L*R^2/(2*k), k>=1'
        elif topic == 'jaggi-2013':
            bound = 2*p.curvature_upper_bound/(k+2)
            formula = '2*C_f/(k+2), k>=1'
        else:
            bound = 2*p.L*radius2/(k+1)**2
            formula = '2*L*R^2/(k+1)^2, k>=1'
        curves = [_curve('objective gap', range(steps+1), gaps),
                  _curve(formula, k, bound, 'bound')]
        measurement = {'definition': 'max objective gap / bound over k>=1',
                       'formula': formula, 'indices': k.tolist(), 'denominator_floor': 0.}
        if np.any(bound <= 0):
            reason = 'zero_radius_bound; ratio is undefined, original case retained'
        else:
            metric = float(np.max(gaps[1:]/bound))
        units = 'objective gap'
    elif topic == 'hestenes-stiefel-1952':
        steps = min(20, p.dim)
        trace = conjugate_gradient(p, steps, x0=x0, rtol=1e-12, atol=0.)
        parameters.update(rtol=1e-12, atol=0.)
        runs['cg'] = _record(p, trace)
        errors = np.sqrt(2*np.asarray(runs['cg']['gaps']))
        rho = (np.sqrt(p.L/p.mu)-1)/(np.sqrt(p.L/p.mu)+1)
        k = np.arange(1, len(errors))
        bound = 2*rho**k*errors[0]
        curves = [_curve('energy error', range(len(errors)), errors),
                  _curve('2*rho^k*initial energy', k, bound, 'bound')]
        measurement = {'definition': 'max energy error / bound over computed k>=1',
                       'indices': k.tolist(), 'denominator_floor': 0.}
        if not k.size or np.any(bound <= 0):
            reason = 'no_positive_energy_bound; ratio is undefined'
        else:
            metric = float(np.max(errors[1:]/bound))
        units = 'energy error'
    elif topic in ('polyak-1964', 'rockafellar-1976'):
        heavy = topic == 'polyak-1964'
        steps = 180 if heavy else 24
        if heavy:
            trace, alpha, beta = heavy_ball(p, steps, x0=x0)
            reference = float((np.sqrt(p.L)-np.sqrt(p.mu))/(np.sqrt(p.L)+np.sqrt(p.mu)))
            parameters.update(alpha=alpha, beta=beta, rho=reference)
            threshold, evidence_kind, floor, method = .08, 'empirical', 1e-10, 'heavy-ball'
        else:
            c = float(10**rng.uniform(-.6, .6))
            trace = proximal_point(p, steps, c, x0=x0)
            reference = 1/(1+c*p.mu)
            parameters.update(proximal_parameter=c, contraction=reference)
            arrays['proximal_parameter'] = [c]
            floor, method = 1e-12, 'proximal-point'
        runs[method] = _record(p, trace)
        errors = np.asarray([np.linalg.norm(x-p.x_star) for x in trace.iterates])
        indices = np.flatnonzero(errors[:-1] > floor)+1
        ratios = errors[indices]/errors[indices-1]
        curves = [_curve('consecutive error ratio', indices, ratios),
                  _curve('spectral rho' if heavy else 'contraction bound', indices,
                         np.full(len(indices), reference), 'reference' if heavy else 'bound')]
        measurement = {'definition': 'relative deviation of last-20-valid median ratio from rho' if heavy
                       else 'max consecutive error ratio / contraction bound',
                       'indices': indices.tolist(), 'denominator_floor': floor,
                       'excluded_updates': (np.flatnonzero(errors[:-1] <= floor)+1).tolist()}
        if not indices.size:
            reason = 'all_previous_errors_below_floor; ratio is unresolved'
        else:
            metric = (abs(float(np.median(ratios[-20:]))-reference)/reference if heavy
                      else float(np.max(ratios/reference)))
        units = 'consecutive distance ratio'
    else:
        steps = 50
        threshold, evidence_kind = None, 'informational'
        for method, fn in (('ista', ista), ('fista', fista)):
            runs[method] = _record(p, fn(p, steps, x0=x0))
            curves.append(_curve(method+' objective gap', range(steps+1), runs[method]['gaps']))
        gi, gf = runs['ista']['gaps'][-1], runs['fista']['gaps'][-1]
        measurement = {'definition': 'final FISTA gap / final ISTA gap', 'indices': [steps],
                       'denominator_floor': 1e-28, 'numerator': gf, 'denominator': gi}
        if gi <= 1e-28:
            reason = 'ISTA_gap_below_comparison_floor; ratio is unresolved'
        else:
            metric = float(gf/gi)
        units = 'objective gap'
    if metric is not None and (not math.isfinite(metric) or metric < 0):
        raise FloatingPointError('invalid stress metric')
    arrays['update_budget'] = [steps]
    result = {'seed': seed, 'metric': metric, 'status': 'unresolved' if reason else 'measured',
              'reason': reason, 'threshold': threshold, 'evidence_kind': evidence_kind,
              'dim': p.dim, 'steps': steps, **design, 'parameters': parameters,
              'inputs': arrays, 'instance_sha256': input_digest(arrays), 'runs': runs,
              'measurement': measurement, 'curve': {'units': units, 'series': curves,
              'scale': 'linear' if 'ratio' in units else 'log'}}
    json.dumps(result, allow_nan=False)
    return result
