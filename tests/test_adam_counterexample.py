import copy
import importlib.util
import json
import math
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path

import pytest

from chainbench._adam_cycles import block_values
from chainbench.adam_counterexample import run_adam_counterexample
from chainbench.adam_counterexample_views import _record_json, adam_counterexample_html, path_svg
from chainbench.cli import main


@pytest.fixture(scope='module')
def checker():
    spec = importlib.util.spec_from_file_location('adam_checker',Path(__file__).resolve().parents[1]/'scripts/smoke_adam_counterexample.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_adam_counterexample


@pytest.fixture(scope='module')
def record():
    return run_adam_counterexample(30)


@pytest.mark.parametrize('steps',[1,4,3000,12000])
def test_every_declared_case_matches_independent_decimal_recurrence(steps,checker):
    checker(run_adam_counterexample(steps))


def test_first_three_rounds_loss_timing_and_projected_return(record):
    c = record['cases'][1]  # C=3, alpha/sqrt(1-beta2)=1/2
    s = c['runs']['adam']['series']
    assert s['x'][1] == pytest.approx(.5,abs=1e-15)
    assert s['second_moment'][:3] == pytest.approx([8.1,1.71,1.071])
    x3 = .5 + math.sqrt(.9)/2/math.sqrt(2*1.71)
    assert s['x'][2] == pytest.approx(x3)
    assert s['proposal'][2] > 1 and s['x'][3] == 1
    assert s['loss'][:3] == pytest.approx([3,-.5,-x3])
    assert s['regret_increment'][1] < 0
    assert s['cumulative_regret'][2] == pytest.approx(6-1.5-(1+x3))
    assert s['inverse_rate_difference'][0] is None
    assert s['inverse_rate_difference'][1] < 0
    a = c['runs']['amsgrad']['series']
    assert a['denominator_memory'][:3] == pytest.approx([8.1]*3,abs=2e-15,rel=0)
    assert a['inverse_rate_difference'][1] > 0


def test_partial_cycles_have_no_invented_bound_or_final_loss():
    data = run_adam_counterexample(4)
    assert data['initial_average_regret'] is None
    for c in data['cases']:
        assert c['source_reference']['rounds'] == [3]
        for method,r in c['runs'].items():
            assert len(r['series']['x']) == 5 and len(r['series']['loss']) == 4
            assert len(r['complete_cycles']) == 1
            assert r['complete_cycles'][0]['last_round'] == 3
            assert (r['complete_cycles'][0]['source_lower'] is None) == (method=='amsgrad')


def test_slow_amsgrad_case_is_retained_and_runs_do_not_stop_early():
    data = run_adam_counterexample()
    slow = data['cases'][0]['runs']['amsgrad']
    assert slow['observations']['final_x'] == pytest.approx(-.24818403380499046)
    assert slow['observations']['final_average_regret'] > .38
    for c in data['cases']:
        for run in c['runs'].values():
            assert run['updates']==3000 and len(run['series']['x'])==3001
    assert any(v!=0 for c in data['cases'] for r in c['runs'].values() for v in r['series']['loss_regret_difference'])


@pytest.mark.parametrize('steps',[0,12001,True,3.5,'3'])
def test_bad_budget_fails(steps):
    with pytest.raises(ValueError,match='steps'):
        run_adam_counterexample(steps)


@pytest.mark.parametrize('path,value',[
    (('source','counterexample'),'Figure 1'),
    (('cases',0,'inputs','bias_correction'),True),
    (('cases',0,'inputs','epsilon'),1e-8),
    (('cases',0,'input_sha256'),'0'*64),
    (('cases',0,'source_reference','rounds'),[1,2,3]),
    (('cases',0,'runs','adam','series','loss',0),2.7),
    (('cases',0,'runs','adam','series','x',2),.5),
    (('cases',0,'runs','adam','series','second_moment',1),8.1),
    (('cases',0,'runs','amsgrad','series','denominator_memory',1),1.71),
    (('cases',0,'runs','adam','series','inverse_rate_difference',0),0.),
    (('cases',0,'runs','adam','series','regret_increment',1),1.),
    (('cases',0,'runs','adam','series','average_regret',1),float('nan')),
    (('cases',0,'runs','adam','series','projection_correction',2),.2),
    (('cases',0,'runs','adam','complete_cycles',0,'end_x'),.9),
    (('cases',0,'runs','amsgrad','complete_cycles',0,'source_lower'),2),
    (('cases',0,'runs','adam','observations','final_x'),-1),
])
def test_independent_audit_rejects_wrong_protocol_timing_memory_and_scope(record,checker,path,value):
    bad = copy.deepcopy(record)
    parent = bad
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    with pytest.raises(RuntimeError):
        checker(bad)


def test_missing_case_or_round_fails(record,checker):
    for key in ('case','round'):
        bad = copy.deepcopy(record)
        if key=='case':
            bad['cases'].pop()
        else:
            bad['cases'][0]['runs']['adam']['series']['x'].pop()
        with pytest.raises(RuntimeError):
            checker(bad)


def test_chart_contains_every_actual_point_and_only_scoped_reference_dots(record):
    for case in record['cases']:
        for metric in ('x','average_regret'):
            root = ET.fromstring(path_svg(case,metric))
            lo,hi = float(root.attrib['data-low']),float(root.attrib['data-high'])
            for path in (e for e in root.iter() if 'data-adam-path' in e.attrib):
                ys = case['runs'][path.attrib['data-adam-path']]['series'][metric]
                points = [list(map(float,p.split(','))) for p in path.attrib['points'].split()]
                assert len(points)==len(ys)
                for j,((x,y),v) in enumerate(zip(points,ys)):
                    assert x==pytest.approx(85+655*(j+int(metric!='x'))/30,abs=.00051)
                    assert y==pytest.approx(245-180*(v-lo)/(hi-lo),abs=.00051)
            bound = [int(e.attrib['data-adam-bound']) for e in root.iter() if 'data-adam-bound' in e.attrib]
            assert bound == ([] if metric=='x' else list(range(3,31,3)))


def test_offline_html_preserves_every_case_native_fallback_and_exact_record(record):
    html = adam_counterexample_html(record,'ko')
    assert html.count('data-adam-case=')==9
    assert html.count('data-adam-native=')==9*2*len(record['cases'][0]['native_rounds'])
    assert '<html lang="ko">' in html and 'no moment debiasing' in html
    raw = html.split('<pre id="chainbench-evidence">')[1].split('</pre>')[0]
    assert json.loads(unescape(raw))==record
    assert 'default-src \'none\'' in html
    assert html.count('data-adam-native-cycle')==9
    assert html.count('data-adam-cycle-method="adam"')==10
    assert html.count('data-adam-cycle-method="amsgrad"')==10


def test_first_cycle_explains_return_despite_positive_gradient_sum(record):
    case = record['cases'][1]
    adam, summary = block_values(case,'adam',2)
    ams, ams_summary = block_values(case,'amsgrad',2)
    assert [r['gradient'] for r in adam]==[3,-1,-1]
    assert sum(r['gradient'] for r in adam)>0
    assert adam[0]['displacement']==pytest.approx(-.5)
    assert all(r['displacement']>0 for r in adam[1:])
    assert adam[-1]['projection']<0 and summary['end_x']==summary['start_x']==1
    assert ams_summary['end_x']<1 and all(r['projection']==0 for r in ams)
    assert all(r['regret_increment']<0 for r in adam[1:])
    assert summary['regret']==math.fsum(r['regret_increment'] for r in adam)
    assert summary['source_lower']==2 and ams_summary['source_lower'] is None


@pytest.mark.parametrize('steps',[1,2,4,5,7,8])
def test_partial_cycle_never_invents_future_rounds_or_complete_regret(steps):
    for case in run_adam_counterexample(steps)['cases']:
        for method in ('adam','amsgrad'):
            rows, summary = block_values(case,method,steps)
            assert [r['round'] for r in rows]==list(range(3*((steps-1)//3)+1,steps+1))
            assert summary['regret'] is None and summary['source_lower'] is None
            assert summary['end_x']==case['runs'][method]['series']['x'][-1]


def test_same_complete_block_for_each_phase_and_all_methods(record):
    for case in record['cases']:
        for method in ('adam','amsgrad'):
            for first in range(1,30,3):
                assert block_values(case,method,first)==block_values(case,method,first+1)==block_values(case,method,first+2)


def test_raw_json_structural_wrapping_preserves_strings_and_limits_numeric_lines():
    data = {'quoted':'literal \\n vs newline\n,[]{}:" and 한국어','numbers':list(range(3000))}
    wrapped = _record_json(data)
    assert json.loads(wrapped)==data
    assert max(map(len,wrapped.split('\n')))<=240


def test_cli_json_default_budget_rejects_seed_and_protects_output(tmp_path,capsys):
    path = tmp_path/'adam.json'
    assert main(['reproduce','reddi-2018','--steps','4','--format','json','--output',str(path)])==0
    assert json.loads(path.read_text())['parameters']['steps']==4
    with pytest.raises(SystemExit) as error:
        main(['reproduce','reddi-2018','--steps','4','--output',str(path)])
    assert error.value.code==2
    assert 'exists' in capsys.readouterr().err
    with pytest.raises(SystemExit) as error:
        main(['reproduce','reddi-2018','--seed','1'])
    assert error.value.code==2
    assert 'only supported' in capsys.readouterr().err
