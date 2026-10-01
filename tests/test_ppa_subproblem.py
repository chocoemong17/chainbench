import copy
import json
import xml.etree.ElementTree as ET
from fractions import Fraction as F
from types import SimpleNamespace

import numpy as np
import pytest
from test_reproductions import smoke_module

from chainbench._ppa_subproblem import subproblem_record
from chainbench._ppa_subproblem_views import subproblem_svg
from chainbench.landscape import run_landscape
from chainbench.problems import QuadraticProblem


@pytest.mark.parametrize('condition,angle,steps', [(1.01,-85,2),(1.01,-85,80),(20,32,18),(10000,85,80),(20,0,18)])
def test_every_subproblem_matches_its_actual_trace_and_independent_system(condition,angle,steps):
    result = run_landscape(condition,angle,steps)
    smoke_module().validate_ppa_subproblems(result)
    record = result['proximal_subproblems']
    assert len(record['rows']) == steps
    for row in record['rows']:
        assert row['subproblem_value_above_f_star'] <= row['previous_objective_gap']+1e-13
        assert row['balance_norm'] < 2e-14
        assert np.linalg.norm(np.array(row['next'])-row['reference']) < 2e-14


def test_axis_aligned_first_resolvent_against_rational_reference():
    record = run_landscape(20,0,2)['proximal_subproblems']
    expected = [(F(-31,20)+F(1,20))/(1+F(1,20)),(F(29,20)-F(4,5))/2]
    first = record['rows'][0]
    assert first['next'] == pytest.approx([float(v) for v in expected])
    assert first['objective_gradient'] == pytest.approx([(float(expected[0])-1)/20,float(expected[1])+0.8])
    assert first['penalty_value'] > 0


def test_unchanged_iterate_does_not_erase_observed_floating_residual():
    rows = run_landscape(1.01,-85,80)['proximal_subproblems']['rows']
    unchanged = [r for r in rows if r['unchanged_iterate']]
    assert unchanged and any(r['balance_norm'] > 0 for r in unchanged)
    assert all(r['movement_norm'] == 0 and r['penalty_value'] == 0 for r in unchanged)
    assert any(r['relative_balance'] == pytest.approx(1.) for r in unchanged)


def test_subproblem_explanation_is_omitted_when_ppa_is_not_selected():
    record = run_landscape(methods=('cg','gd'))
    assert 'proximal_subproblems' not in record
    smoke_module().validate_ppa_subproblems(record)


def test_zero_gradient_balance_retains_an_undefined_relative_value():
    p = QuadraticProblem.from_reference(np.eye(2),np.zeros(2))
    trace = SimpleNamespace(iterates=[np.zeros(2),np.zeros(2)])
    row = subproblem_record(p,trace,1.)['rows'][0]
    assert row['balance_norm'] == row['balance_denominator'] == 0
    assert row['relative_balance'] is None and row['unchanged_iterate']


@pytest.mark.parametrize('condition,angle,steps', [(20,32,2),(1.01,-85,80),(10000,85,80)])
def test_all_contours_follow_the_shifted_energy_and_marker_coordinates(condition,angle,steps):
    record = run_landscape(condition,angle,steps)['proximal_subproblems']
    svg = ET.fromstring(subproblem_svg(record))
    frames = svg.findall('.//{*}g[@data-ppa-frame]')
    assert len(frames) == steps
    assert sum('hidden' not in frame.attrib for frame in frames) == 1
    hessian = np.array(record['hessian'])
    for frame,row in zip(frames,record['rows']):
        axes = json.loads(frame.attrib['data-axes'])
        scale, reference = axes['units_per_pixel'], np.array(row['reference'])
        assert scale > 0 and (not row['unchanged_iterate'] or axes['radius'] == 1.)
        for polyline in frame.findall('.//{*}polyline[@data-ppa-level]'):
            points = np.array([[float(v) for v in s.split(',')] for s in polyline.attrib['points'].split()])
            delta = (points-np.array([310.,240.]))*np.array([scale,-scale])
            energy = .5*np.einsum('ni,ij,nj->n',delta,hessian,delta)
            level = float(polyline.attrib['data-ppa-level'])
            eigenvalues = np.linalg.eigvalsh(hessian)
            # SVG coordinates round to 0.001 px. Bound the induced quadratic
            # energy error in this frame's actual units, even near roundoff.
            coordinate_error = np.sqrt(2)*.000501*scale
            energy_error = eigenvalues[-1]*(np.sqrt(2*level/eigenvalues[0])*coordinate_error+.5*coordinate_error**2)
            assert np.max(np.abs(energy-level)) <= energy_error+2e-14*level
        for key in ('previous','next','reference'):
            marker = frame.find(f'.//{{*}}circle[@data-ppa-point="{key}"]')
            offset = np.array(row[key])-reference
            expected = [310+offset[0]/scale,240-offset[1]/scale]
            assert [float(marker.attrib[a]) for a in ('cx','cy')] == pytest.approx(expected,abs=.00051)


@pytest.mark.parametrize('field,value', [('reference',[0.,0.]),('objective_gradient',[0.,0.]),
    ('balance_norm',float('nan')),('relative_balance',0.2),('completed_update',0),
    ('unchanged_iterate',True),('penalty_value',-1.),('rhs',[9.,9.]),('movement_norm',0.)])
def test_independent_validator_rejects_detached_subproblem_fields(field,value):
    result = copy.deepcopy(run_landscape(steps=2))
    result['proximal_subproblems']['rows'][0][field] = value
    with pytest.raises(RuntimeError,match='PPA subproblem'):
        smoke_module().validate_ppa_subproblems(result)
