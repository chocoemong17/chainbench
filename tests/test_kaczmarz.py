import copy
import importlib.util
import itertools
import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from chainbench.kaczmarz import run_kaczmarz
from chainbench.kaczmarz_views import kaczmarz_html, project_cube


def validator():
    spec = importlib.util.spec_from_file_location('smoke_kaczmarz',Path(__file__).resolve().parents[1]/'scripts/smoke_kaczmarz.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_kaczmarz


@pytest.mark.parametrize('steps,trials', [(True,1),(0,1),(161,1),(1.5,1),(1,True),(1,0),(1,129),(1,None)])
def test_invalid_budgets(steps,trials):
    with pytest.raises(ValueError):
        run_kaczmarz(steps,trials)


def test_all_declared_trials_and_independent_rational_validator():
    data = run_kaczmarz()
    validator()(data)
    assert len(data['cases']) == 6
    for case in data['cases']:
        a = np.array(case['inputs']['A'])
        singular_values = np.linalg.svd(a,compute_uv=False)
        assert (a*a).sum()/min(singular_values)**2 == pytest.approx(case['scaled_condition_squared'])
        for run in case['runs']:
            rng = np.random.Generator(np.random.PCG64(run['seed']))
            # Recreate the declared stream via inverse CDF, rather than Generator.choice.
            expected = np.searchsorted(np.cumsum(case['inputs']['row_probabilities']),rng.random(40),side='right')
            np.testing.assert_array_equal(run['row_indices'],expected)
        assert sum(case['first_zero_counts'])+case['unresolved_trials'] == 64


def test_expected_value_is_not_a_path_or_sample_mean_threshold():
    data = run_kaczmarz(40,1)
    case = data['cases'][3]
    assert case['runs'][0]['squared_errors'][1] == 1
    assert case['empirical_mean'][1] > case['theorem_upper'][1]
    validator()(data)  # This is valid evidence, not a rejected trial or failed bound.


def test_complete_small_probability_tree_attains_theorem():
    data = run_kaczmarz(4,1)
    for case in data['cases'][:2]:
        a = case['inputs']['A']
        m = len(a)
        for k in range(5):
            total = 0
            for sequence in itertools.product(range(m),repeat=k):
                x = case['inputs']['start'].copy()
                for row in sequence:
                    x[a[row].index(1)] = 0
                total += sum(v*v for v in x)
            assert float(Fraction(int(total),m**k)) == pytest.approx(case['exact_expectation'][k])


def test_fixed_budget_after_zero_and_seed_prefix_stability():
    small,big = run_kaczmarz(2,2),run_kaczmarz(40,4)
    for a,b in zip(small['cases'],big['cases']):
        for s in range(2):
            assert a['runs'][s]['row_indices'] == b['runs'][s]['row_indices'][:2]
            assert a['runs'][s]['iterates'] == b['runs'][s]['iterates'][:3]
    case = big['cases'][1]
    for run in case['runs']:
        first = run['first_zero']
        assert first is not None and first < 40
        assert len(run['row_indices']) == 40
        assert run['iterates'][first:] == [[0.,0.]]*(41-first)


@pytest.mark.parametrize('fault',['row','point','error','mean','expectation','hash','missing','zero','unresolved','seed'])
def test_validator_rejects_corrupted_evidence(fault):
    data = copy.deepcopy(run_kaczmarz(4,3))
    c = data['cases'][0]
    if fault=='row':
        c['runs'][0]['row_indices'][0] = 999
    elif fault=='point':
        c['runs'][0]['iterates'][1][0] = 9
    elif fault=='error':
        c['runs'][0]['squared_errors'][1] = 9
    elif fault=='mean':
        c['empirical_mean'][1] = 0
    elif fault=='expectation':
        c['exact_expectation'][1] = 1
    elif fault=='hash':
        c['input_sha256'] = '0'*64
    elif fault=='missing':
        c['runs'].pop()
    elif fault=='zero':
        c['first_zero_counts'][1] = 99
    elif fault=='unresolved':
        c['unresolved_trials'] = 99
    else:
        c['runs'][0]['seed'] = 9
    with pytest.raises(RuntimeError):
        validator()(data)


def test_maximum_budget_preserves_every_point():
    validator()(run_kaczmarz(160,128))


def test_html_records_all_trials_and_real_coordinate_projection():
    import html
    import re
    import xml.etree.ElementTree as ET

    data = run_kaczmarz(2,2)
    text = kaczmarz_html(data,'ko')
    raw = re.search(r'<pre id="chainbench-evidence">(.*?)</pre>',text,re.S)[1]
    assert json.loads(html.unescape(raw)) == data
    assert text.count('data-rk-run=') == 12
    assert text.count('data-rk-trial=') == 12
    for svg in re.findall(r'<svg .*?</svg>',text,re.S):
        ET.fromstring(svg)
    np.testing.assert_allclose(project_cube([1,0,0],0),[360,260])
    np.testing.assert_allclose(project_cube([0,1,0],0),[230,260-130*np.sin(np.deg2rad(25))])
    assert 'not objective height' in text


def test_cli_and_incompatible_flags(tmp_path,capsys):
    from chainbench.cli import main

    dest = tmp_path/'kaczmarz.json'
    assert main(['case-study','kaczmarz-expectation','--steps','2','--trials','1','--format','json','--output',str(dest)]) == 0
    validator()(json.loads(dest.read_text()))
    for opts in (['kaczmarz-expectation','--L','1'],['gd-tight','--trials','2'],['fw-sparsity','--trials','2']):
        with pytest.raises(SystemExit) as exc:
            main(['case-study',*opts])
        assert exc.value.code == 2 and 'only supported' in capsys.readouterr().err
