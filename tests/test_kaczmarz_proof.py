import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from chainbench.kaczmarz import run_kaczmarz


def validate(data):
    spec = importlib.util.spec_from_file_location('conditional_smoke',Path(__file__).resolve().parents[1]/'scripts/smoke_kaczmarz.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_kaczmarz(data)


def test_all_observed_states_and_every_possible_row_are_preserved():
    data = run_kaczmarz()
    validate(data)
    assert [len(c['conditional_projection']['states']) for c in data['cases']]==[8,2,2,2,2,2]
    for c in data['cases']:
        for state in c['conditional_projection']['states']:
            assert len(state['outcomes'])==c['inputs']['equations']
            assert state['conditional_squared_error']==pytest.approx(state['theorem_conditional_upper'])
            assert state['conditional_squared_step']==pytest.approx(state['residual_energy_over_frobenius'])
            for row in state['outcomes']:
                e,d = np.array(row['remaining_error']),np.array(row['removed_error'])
                np.testing.assert_array_equal(e+d,state['x'])
                assert e@d==0
                assert e@e+d@d==state['squared_error']


def test_initial_conditional_mean_and_zero_error_degeneracy():
    data = run_kaczmarz(40,1)
    for c in data['cases']:
        proof = c['conditional_projection']
        initial = next(s for s in proof['states'] if s['x']==c['inputs']['start'])
        assert initial['conditional_squared_error']==pytest.approx(c['exact_expectation'][1])
        zero = next(s for s in proof['states'] if s['squared_error']==0)
        assert zero['conditional_ratio'] is None
        assert zero['conditional_squared_error']==zero['conditional_squared_step']==0
        assert all(r['squared_error']==r['squared_step']==0 for r in zero['outcomes'])
    cube = data['cases'][0]['conditional_projection']
    initial = next(s for s in cube['states'] if s['x']==[1,1,1])
    assert initial['conditional_squared_error']==2
    assert initial['conditional_squared_step']==1


def test_candidate_points_are_not_inserted_into_the_sampled_history():
    c = run_kaczmarz(1,1)['cases'][0]
    points = c['runs'][0]['iterates']
    assert len(points)==2
    initial = next(s for s in c['conditional_projection']['states'] if s['x']==[1,1,1])
    assert len(initial['outcomes'])==3
    assert sum(r['next'] in points for r in initial['outcomes'])==1


@pytest.mark.parametrize('fault',['missing_state','missing_outcome','point','inner_product','identity','mean','group','ratio','constant'])
def test_corrupted_conditional_evidence_is_rejected(fault):
    data = copy.deepcopy(run_kaczmarz(40,1))
    proof = data['cases'][0]['conditional_projection']
    state = proof['states'][-1]
    if fault=='missing_state':
        proof['states'].pop()
    elif fault=='missing_outcome':
        state['outcomes'].pop()
    elif fault=='point':
        state['outcomes'][0]['next'][0] = 99
    elif fault=='inner_product':
        state['outcomes'][0]['inner_product'] = 1
    elif fault=='identity':
        state['conditional_identity_residual'] = 1
    elif fault=='mean':
        state['conditional_squared_error'] = 0
    elif fault=='group':
        state['directions'][0]['probability'] = .5
    elif fault=='ratio':
        proof['states'][0]['conditional_ratio'] = 0
    else:
        proof['minimum_singular_squared'] = 9
    with pytest.raises(RuntimeError,match='conditional projection'):
        validate(data)


def test_legacy_record_without_optional_explanation_remains_valid():
    data = run_kaczmarz(1,1)
    for case in data['cases']:
        del case['conditional_projection']
    validate(data)
    from chainbench.kaczmarz_views import kaczmarz_html
    text = kaczmarz_html(data,'ko')
    assert '<div class="rk-proof"' not in text
    assert text.count('<section data-rk-case=')==6
