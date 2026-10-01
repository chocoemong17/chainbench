import copy
import importlib.util
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest
from _numeric_records import assert_recomputed_record

from chainbench.checks import CHECKS
from chainbench.methods import (
    accelerated_gradient,
    conjugate_gradient,
    fista,
    frank_wolfe,
    gradient_descent,
    heavy_ball,
    ista,
    proximal_point,
)
from chainbench.problems import DiagonalLassoProblem, QuadraticProblem, SimplexQuadraticProblem
from chainbench.visuals import build_check_chart


def validator():
    spec = importlib.util.spec_from_file_location('smoke_canonical',
        Path(__file__).resolve().parents[1]/'scripts/smoke_install.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_canonical_plot


@pytest.mark.parametrize('slug', CHECKS)
def test_retained_inputs_rerun_every_plotted_observation(slug):
    chart = build_check_chart(slug)
    c = chart.instance
    a, options = c['inputs'], c['method_parameters']
    if c['family'] == 'quadratic':
        problem = QuadraticProblem(a['Q'], a['b'], a['x_star'])
    elif c['family'] == 'diagonal-lasso':
        problem = DiagonalLassoProblem(a['a'], a['b'], a['lam'][0])
    else:
        problem = SimplexQuadraticProblem(a['target'])
    np.testing.assert_allclose(problem.x_star, c['optimizer'])
    assert problem.f_star == pytest.approx(c['f_star'])
    for name, run in c['runs'].items():
        kwargs = {'x0': np.asarray(a['x0'])}
        if name == 'heavy-ball':
            trace, alpha, beta = heavy_ball(problem, c['budget'], **kwargs)
            assert (alpha, beta) == (options[name]['alpha'], options[name]['beta'])
        else:
            methods = {'gd': gradient_descent, 'smooth-fista': accelerated_gradient,
                       'cg': conjugate_gradient, 'proximal-point': proximal_point,
                       'frank-wolfe': frank_wolfe, 'ista': ista, 'fista': fista}
            if name == 'cg':
                kwargs.update(rtol=options[name]['rtol'], atol=options[name]['atol'])
            elif name == 'proximal-point':
                kwargs['proximal_parameter'] = options[name]['c']
            trace = methods[name](problem, c['budget'], **kwargs)
        assert run['updates'] == len(trace.iterates)-1
        assert run['termination'] == (trace.termination or 'fixed_budget')
        assert_recomputed_record(run['true_residual_norm'], trace.residual_norm)
        series = chart.series[1 if slug == 'ista-vs-fista' and name == 'fista' else 0]
        gaps = np.array([problem.gap(x) for x in trace.iterates])
        observed = gaps
        if name == 'cg':
            observed = np.sqrt(2*gaps)
        if name in ('heavy-ball', 'proximal-point'):
            observed = np.array([np.linalg.norm(x-problem.x_star) for x in trace.iterates])
        expected = [observed[int(k)]/observed[int(k)-1] if name == 'heavy-ball'
                    else observed[int(k)] for k in series.x]
        np.testing.assert_allclose(series.y, expected, rtol=1e-12, atol=1e-14)
    validator()(json.loads(json.dumps(asdict(chart))))


@pytest.mark.parametrize('field', ['instance', 'hash', 'input', 'L', 'step', 'first_sample', 'bound', 'budget', 'updates'])
def test_installed_validator_rejects_context_or_sample_corruption(field):
    record = json.loads(json.dumps(asdict(build_check_chart('gd-baseline'))))
    broken = copy.deepcopy(record)
    c = broken['instance']
    if field == 'instance':
        broken.pop('instance')
    elif field == 'hash':
        c['input_sha256'] = '0'*64
    elif field == 'input':
        c['inputs']['x0'][1] += 1
    elif field == 'L':
        c['constants']['L'] *= 2
    elif field == 'step':
        c['method_parameters']['gd']['step'] *= 2
    elif field == 'first_sample':
        broken['series'][0]['y'][0] += 1
    elif field == 'bound':
        broken['series'][1]['y'][-1] += 1
    elif field == 'budget':
        c['budget'] = 0
    else:
        c['runs']['gd']['updates'] = 0
    with pytest.raises(RuntimeError):
        validator()(broken)


def test_context_records_singular_conditioning_and_feasible_start_without_infinity():
    smooth = build_check_chart('nesterov-1983').instance
    assert smooth['constants']['mu'] == 0
    assert smooth['constants']['condition_number'] is None
    assert smooth['dimension'] == 80 and smooth['seed'] is None
    simplex = build_check_chart('jaggi-2013').instance
    assert simplex['inputs']['x0'] == [1.]+[0.]*49
    assert simplex['constants']['curvature'] == 2
    json.dumps([smooth, simplex], allow_nan=False)
