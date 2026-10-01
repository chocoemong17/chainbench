import copy
import importlib.util
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from chainbench.cg_spectrum import run_cg_spectrum
from chainbench.cg_spectrum_views import cg_spectrum_html, energy_svg, ratio_svg
from chainbench.methods import conjugate_gradient
from chainbench.problems import QuadraticProblem


@pytest.fixture(scope='module')
def checker():
    spec = importlib.util.spec_from_file_location(
        'cg_spectrum_checker', Path(__file__).resolve().parents[1]/'scripts/smoke_cg_spectrum.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_cg_spectrum


@pytest.fixture(scope='module')
def record():
    return run_cg_spectrum()


@pytest.mark.parametrize('steps', [1,32,64])
def test_all_cases_pass_independent_unscaled_decimal_replay(steps, checker):
    data = run_cg_spectrum(steps)
    checker(data)
    assert len(data['cases']) == 18
    assert max(c['completed_updates'] for c in data['cases']) <= steps


def test_same_interval_can_have_different_observed_stopping_counts(record):
    for case in record['cases']:
        expected = 1 if case['start_profile']=='single-mode' else {
            'two-values':2, 'two-clusters':12, 'spread':16}[case['spectrum']]
        assert case['completed_updates'] == expected
        assert case['declared_condition_number'] == 3.5
        assert case['realized_condition_number'] == pytest.approx(3.5,abs=1e-13)
        assert case['termination'] == 'converged'
        assert case['rows'][-1]['true_residual_norm'] <= case['residual_tolerance']


def test_report_retains_exact_shared_solver_iterates_including_roundoff(record):
    nonzero_final_errors = 0
    for case in record['cases']:
        problem = QuadraticProblem(np.array(case['A']),np.array(case['b']),np.array(case['x_star']))
        trace = conjugate_gradient(problem,32,x0=np.array(case['start']),rtol=1e-12,atol=0)
        assert np.array_equal(np.array([r['x'] for r in case['rows']]),np.array(trace.iterates))
        assert np.array_equal(np.array([r['objective'] for r in case['rows']]),trace.values)
        nonzero_final_errors += case['rows'][-1]['energy_ratio'] > 0
    assert nonzero_final_errors > 0


def test_mode_ratios_do_not_invent_initial_components(record):
    for case in record['cases']:
        if case['start_profile']=='single-mode':
            assert case['active_declared_eigenvalues'] == [2.]
            assert case['rows'][0]['component_ratios'] == [1.]+[None]*15
            assert all(row['component_ratios'][1:]==[None]*15 for row in case['rows'])


def test_orthogonal_coordinate_change_preserves_the_observed_error_to_precision(record):
    cases = {c['id']:c for c in record['cases']}
    for case in record['cases']:
        if case['basis_name'] != 'diagonal':
            continue
        rotated = cases[case['id'].replace('-diagonal-','-hadamard-')]
        q = np.array(rotated['basis'])
        assert np.array_equal(q.T@q,np.eye(16))
        np.testing.assert_allclose(
            np.array([r['x'] for r in rotated['rows']]),
            np.array([r['x'] for r in case['rows']])@q.T,atol=2e-14,rtol=0)


def test_source_comparison_polynomial_is_normalized_and_does_not_claim_actual_cg(record):
    comparisons = record['comparisons']
    assert comparisons[0]['interval_envelope'] == 1
    assert comparisons[0]['looser_envelope'] == 2
    assert comparisons[1]['interval_envelope'] == pytest.approx(5/9)
    assert comparisons[2]['interval_envelope'] == pytest.approx(25/137)
    for reference in comparisons:
        assert reference['values'][0] == 1
    for case in record['cases']:
        assert 'not an actual CG polynomial' in case['quadratic_witness']['scope']


@pytest.mark.parametrize('steps', [0,65,True,1.5,'32'])
def test_invalid_budgets_fail(steps):
    with pytest.raises(ValueError,match='steps'):
        run_cg_spectrum(steps)


@pytest.mark.parametrize('path,value', [
    (('parameters','rtol'),1e-6),
    (('cases',0,'input_sha256'),'0'*64),
    (('cases',0,'A',0,0),2.01),
    (('cases',0,'rows',1,'x',0),0.9),
    (('cases',0,'rows',1,'component_ratios'),[]),
    (('cases',0,'rows',1,'mode_energy',0),0.),
    (('cases',0,'rows',1,'true_residual_norm'),0.),
    (('cases',0,'rows',1,'energy_identity_difference'),1e-9),
    (('cases',0,'rows',1,'energy_ratio'),float('nan')),
    (('cases',0,'termination'),'max_steps'),
    (('cases',0,'quadratic_witness','roots',0),2.1),
    (('cases',0,'quadratic_witness','scope'),'actual CG polynomial'),
    (('comparisons',1,'values',2),0.),
    (('comparisons',1,'interval_envelope'),1.),
])
def test_corrupt_input_trajectory_or_comparison_fails(record,checker,path,value):
    bad = copy.deepcopy(record)
    parent = bad
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    with pytest.raises(RuntimeError):
        checker(bad)


def test_omitting_a_case_or_an_observed_step_fails(record,checker):
    bad = copy.deepcopy(record)
    bad['cases'].pop()
    with pytest.raises(RuntimeError):
        checker(bad)
    bad = copy.deepcopy(record)
    bad['cases'][0]['rows'].pop()
    with pytest.raises(RuntimeError):
        checker(bad)


def test_svg_coordinates_are_the_recorded_modes_with_fixed_case_scales(record):
    for case in record['cases']:
        ratios = [v for r in case['rows'] for v in r['component_ratios'] if v is not None]
        low, high = min(-1,min(ratios))*1.1, max(1,max(ratios))*1.1
        energy_high = max(v for r in case['rows'] for v in r['normalized_mode_energy'])*1.08
        for row in case['rows']:
            svg = ET.fromstring(ratio_svg(case,row,record['comparisons'][row['iteration']]))
            dots = [e for e in svg.iter() if 'data-cg-ratio' in e.attrib]
            active = [i for i,v in enumerate(row['component_ratios']) if v is not None]
            assert [int(e.attrib['data-cg-ratio']) for e in dots]==active
            for i,e in zip(active,dots):
                assert float(e.attrib['cx']) == pytest.approx(70+85*case['declared_eigenvalues'][i],abs=.00051)
                assert float(e.attrib['cy']) == pytest.approx(270-200*(row['component_ratios'][i]-low)/(high-low),abs=.00051)
            bars = [e for e in ET.fromstring(energy_svg(case,row)).iter() if 'data-cg-mode' in e.attrib]
            assert len(bars)==16
            for i,e in enumerate(bars):
                height = 200*row['normalized_mode_energy'][i]/energy_high
                assert float(e.attrib['height']) == pytest.approx(height,abs=.00051)
                assert float(e.attrib['y']) == pytest.approx(270-height,abs=.00051)


@pytest.mark.parametrize('lang',['ko','en'])
def test_html_retains_all_cases_stages_and_raw_record_without_a_server(record,lang):
    from html import unescape

    html = cg_spectrum_html(record,lang)
    assert html.count('<section data-cg-case=')==18
    assert html.count('<details data-cg-frame=')==sum(len(c['rows']) for c in record['cases'])
    assert html.count('<details data-cg-overview>')==6
    payload = html.split('<pre id="chainbench-evidence">')[1].split('</pre>')[0]
    assert json.loads(unescape(payload))==record
    assert 'not a fitted actual CG polynomial' in html
    assert 'No actual k=2 row' in html
    assert '<script src=' not in html and 'fetch(' not in html


def test_cli_uses_default_and_explicit_budget_and_rejects_irrelevant_options(capsys):
    from chainbench.cli import main

    assert main(['case-study','cg-spectrum','--format','json'])==0
    assert json.loads(capsys.readouterr().out)['parameters']['steps']==32
    assert main(['case-study','cg-spectrum','--steps','1','--lang','ko'])==0
    assert '<html lang="ko">' in capsys.readouterr().out
    for option in ('--trials','--horizon','--L','--R','--h'):
        with pytest.raises(SystemExit) as exc:
            main(['case-study','cg-spectrum',option,'1'])
        assert exc.value.code==2
