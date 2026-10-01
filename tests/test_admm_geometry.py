import copy
import importlib.util
from pathlib import Path

import pytest

from chainbench.admm_geometry import run_admm_geometry


@pytest.fixture(scope='module')
def audit():
    spec = importlib.util.spec_from_file_location('admm_audit',Path(__file__).resolve().parents[1]/'scripts/smoke_admm_geometry.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_admm_geometry


@pytest.fixture(scope='module')
def record():
    return run_admm_geometry(12)


@pytest.mark.parametrize('steps',[1,60,160])
def test_all_cases_match_independent_decimal_paths_and_closed_form_optima(steps,audit):
    audit(run_admm_geometry(steps))


def test_hand_computed_first_diagonal_and_coupled_updates(record):
    diagonal = next(c for c in record['cases'] if c['id']=='diagonal-lambda0.1-zero-rho1')
    row = diagonal['rows'][1]
    assert row['x']==pytest.approx([.7,-.72],abs=5e-15)
    assert row['z']==pytest.approx([0,0],abs=5e-15)
    assert row['split_objective']==pytest.approx(.2738)
    assert row['objective_z']==pytest.approx(3.86)
    assert diagonal['optimum']['point']==pytest.approx([.68,-.72])
    assert diagonal['optimum']['value']==pytest.approx(1.296)
    assert row['split_minus_optimum']<0<row['stable_gap_z']
    coupled = next(c for c in record['cases'] if c['id']=='coupled-lambda0.1-zero-rho1')
    row = coupled['rows'][1]
    assert row['x']==pytest.approx([.8,-1.1])
    assert row['z']==pytest.approx([.46,-.76])
    assert row['u']==pytest.approx([.34,-.34])
    assert row['dual_residual']==pytest.approx([-.46,.76])
    assert row['dual_stationarity']==pytest.approx(row['dual_residual'])


def test_optimal_original_point_does_not_imply_a_feasible_split_state(record):
    high = [c for c in record['cases'] if c['inputs']['lambda_fraction']==1.1 and c['start_name']=='zero']
    assert len(high)==6
    for case in high:
        assert case['rows'][0]['stable_gap_z']==0
        first = case['rows'][1]
        assert first['stable_gap_z']==0 and first['dual_norm']==0
        assert first['primal_norm']>first['eps_primal']
        assert first['stopping_passed'] is False
        assert first['split_minus_optimum']<0


def test_all_penalties_starts_and_support_regimes_remain_visible(record):
    assert len(record['cases'])==36
    assert {tuple(c['optimum']['active_coordinates']) for c in record['cases']}=={(),(0,1),(1,)}
    for case in record['cases']:
        initial = case['rows'][0]
        assert initial['x'] is None and initial['primal_norm'] is None
        assert initial['split_objective'] is None and initial['stopping_passed'] is None
        assert case['updates']==12 and case['termination']=='fixed_budget'
        assert case['native_iterations']==[0,1,2,5,10,12]


@pytest.mark.parametrize('steps',[0,161,True,2.5,'60'])
def test_invalid_budget_is_rejected(steps):
    with pytest.raises(ValueError,match='steps'):
        run_admm_geometry(steps)


@pytest.mark.parametrize('path,value',[
    (('evidence_level',),'published-figure-reproduction'),
    (('source','role'),'new algorithm introduced in 2011'),
    (('problem','constraint_matrices'),'A and -I'),
    (('geometry','surface_height'),'split objective minus optimum'),
    (('geometry','dual_coordinates'),'measurement-space residual dual'),
    (('cases',0,'inputs','relaxation'),1.5),
    (('cases',0,'input_sha256'),'0'*64),
    (('cases',0,'optimum','point'),[0,0]),
    (('cases',0,'rows',0,'x'),[0,0]),
    (('cases',0,'rows',0,'stopping_passed'),True),
    (('cases',0,'rows',1,'x'),[0,0]),
    (('cases',0,'rows',1,'u'),[0,0]),
    (('cases',0,'rows',1,'y'),[7,7]),
    (('cases',0,'rows',1,'primal_residual'),[0,0]),
    (('cases',2,'rows',1,'dual_residual'),[0,0]),
    (('cases',0,'rows',1,'dual_box_excess'),[0,0]),
    (('cases',0,'rows',1,'objective_z'),float('nan')),
    (('cases',0,'rows',1,'split_objective'),100),
    (('cases',0,'rows',1,'gap_roundoff_difference'),.01),
    (('cases',0,'rows',1,'eps_primal'),100),
    (('cases',0,'first_residual_pass'),0),
    (('cases',0,'termination'),'converged'),
    (('cases',0,'observations','final_primal_norm'),0),
])
def test_independent_audit_rejects_wrong_scope_states_residuals_and_observations(record,audit,path,value):
    bad = copy.deepcopy(record)
    target = bad
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(RuntimeError):
        audit(bad)


def test_missing_case_or_update_cannot_pass(record,audit):
    for kind in ('case','row'):
        bad = copy.deepcopy(record)
        if kind=='case':
            bad['cases'].pop()
        else:
            bad['cases'][0]['rows'].pop()
        with pytest.raises(RuntimeError):
            audit(bad)
