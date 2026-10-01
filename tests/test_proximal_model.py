import copy
import xml.etree.ElementTree as ET
from fractions import Fraction as F

import numpy as np
import pytest
from test_proximal_geometry import smoke_module

from chainbench._proximal_model import model_slice
from chainbench._proximal_model_views import model_svg
from chainbench.problems import DiagonalLassoProblem
from chainbench.proximal_geometry import run_proximal_geometry


@pytest.mark.parametrize('steps', [2, 18, 60])
def test_every_model_matches_independent_expansion_at_all_samples(steps):
    result = run_proximal_geometry(steps)
    smoke_module().validate_proximal_models(result)
    for case in result['cases']:
        for method, run in case['runs'].items():
            for stage in run['stages']:
                model = stage['upper_model']
                # Contact at y and the actual minimizer are sampled exactly.
                zero, one = (model['parameter'].index(t) for t in (0., 1.))
                assert model['objective_gap'][zero] == model['model_gap'][zero] == model['anchor_gap']
                assert model['model_gap'][one] == pytest.approx(model['model_next_gap'], abs=1e-28)
                assert min(model['model_gap']) >= model['model_next_gap']-1e-13
                if method == 'ista':
                    assert model['anchor_gap'] == model['previous_gap']


def test_first_published_rule_update_against_rational_surrogate():
    case = next(c for c in run_proximal_geometry(2)['cases'] if c['id'] == 'lambda-2-opposite')
    y, nxt, star, lam = [F(-9,5), F(6,5)], [F(-61,45), F(-32,45)], [F(3,5), F(-32,45)], F(4,5)
    def objective(x):
        return ((x[0]-F(7,5))**2+(3*x[1]+F(12,5))**2)/2+lam*sum(abs(v) for v in x)
    exact_excess = 4*(nxt[0]-y[0])**2
    m = case['runs']['fista']['stages'][0]['upper_model']
    assert m['anchor_gap'] == pytest.approx(float(objective(y)-objective(star)))
    assert m['model_excess_next'] == pytest.approx(float(exact_excess))
    assert m['model_next_gap'] == pytest.approx(float(objective(nxt)-objective(star)+exact_excess))


def test_actual_fista_increase_still_descends_from_the_extrapolated_anchor():
    cases = run_proximal_geometry()['cases']
    rising = [s['upper_model'] for c in cases for s in c['runs']['fista']['stages']
              if s['upper_model']['next_gap'] > s['upper_model']['previous_gap']+1e-12]
    assert rising
    assert all(m['next_gap'] <= m['model_next_gap'] <= m['anchor_gap']+1e-13 for m in rising)


def test_zero_length_slice_is_flat_without_rounding_small_steps_to_zero():
    p = DiagonalLassoProblem(np.array([1.,3.]),np.array([1.4,-2.4]),1.8)
    anchor = p.x_star
    stationary = model_slice(p,anchor,anchor,anchor)
    assert stationary['zero_step'] and len(set(stationary['objective_gap'])) == 1
    next_x = np.nextafter(anchor,np.ones(2))
    assert not model_slice(p,anchor,anchor,next_x)['zero_step']


def test_model_svg_all_samples_markers_and_height_scales_follow_saved_values():
    ns = {'s': 'http://www.w3.org/2000/svg'}
    for case in run_proximal_geometry(3)['cases']:
        root = ET.fromstring(model_svg(case))
        for method, run in case['runs'].items():
            for k, stage in enumerate(run['stages']):
                m = stage['upper_model']
                maximum = max(m['model_gap']+[m['previous_gap']])
                top = maximum*1.1 if maximum else 1.
                for key in ('objective_gap', 'model_gap'):
                    el = root.find(f'.//s:polyline[@data-model-points="{key}"]', ns)
                    actual = [[float(v) for v in p.split(',')] for p in el.attrib['data-'+method].split('|')[k].split()]
                    expected = [(86+(t+.25)*460/1.5, 292-210*g/top) for t, g in zip(m['parameter'],m[key])]
                    np.testing.assert_allclose(actual, expected, atol=.00051)
                for key, t in [('anchor_gap',0), ('next_gap',1), ('model_next_gap',1)]:
                    el = root.find(f'.//s:circle[@data-model-marker="{key}"]',ns)
                    actual = [float(v) for v in el.attrib['data-'+method].split('|')[k].split(',')]
                    assert actual == pytest.approx([86+(t+.25)*460/1.5,292-210*m[key]/top],abs=.00051)


@pytest.mark.parametrize('fault', ['missing-corner', 'curve', 'model', 'anchor', 'previous', 'slack', 'zero', 'direction', 'nonfinite'])
def test_independent_model_validator_rejects_corrupt_explanations(fault):
    result = run_proximal_geometry(3)
    stage = result['cases'][0]['runs']['fista']['stages'][0]
    model = stage['upper_model']
    if fault == 'missing-corner':
        model['parameter'].pop(0)
    elif fault == 'curve':
        model['objective_gap'][12] += .1
    elif fault == 'model':
        model['model_gap'][12] += .1
    elif fault in ('anchor', 'previous'):
        model[fault+'_gap'] += .1
    elif fault == 'slack':
        model['model_excess_next'] += .1
    elif fault == 'zero':
        model['zero_step'] = True
    elif fault == 'direction':
        model['direction'][1] += .1
    else:
        model['next_gap'] = float('nan')
    with pytest.raises(RuntimeError, match='upper model'):
        smoke_module().validate_proximal_models(result)


def test_returned_contract_mutation_does_not_change_the_next_run():
    first = run_proximal_geometry(2)
    expected = copy.deepcopy(first['upper_model'])
    first['upper_model']['parameter_interval'][0] = -99
    assert run_proximal_geometry(2)['upper_model'] == expected
