import copy
import json
from dataclasses import asdict
from html.parser import HTMLParser

import pytest

from chainbench._pages import bi
from chainbench.case_studies import case_html, gd_tight_case
from chainbench.checks import CHECKS, run_check
from chainbench.cli import main
from chainbench.experiments import canonical_json, config_digest, preset_config, run_experiment
from chainbench.learning import LESSONS, learning_html, ratio_chart
from chainbench.visuals import build_check_chart
from chainbench.workflows import (
    load_report,
    replay_experiment,
    run_sweep,
    validate_saved_experiment,
)


class Evidence(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.reading = False
        self.text = ''
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        if tag == 'pre' and dict(attrs).get('id') == 'chainbench-evidence':
            self.reading = True
    def handle_endtag(self, tag):
        if tag == 'pre':
            self.reading = False
    def handle_data(self, data):
        if self.reading:
            self.text += data


@pytest.mark.parametrize('slug', list(CHECKS))
def test_learning_preserves_actual_check_and_chart(slug):
    html = learning_html(slug, 'ko')
    data = json.loads(Evidence(html).text)
    assert data['results'] == [asdict(run_check(slug))]
    assert data['charts'][slug] == json.loads(json.dumps(asdict(build_check_chart(slug))))
    assert data['kind'] == 'chainbench.learning'
    assert '<html lang="ko">' in html
    for field in ('question', 'mechanism', 'assumptions', 'reason', 'reading', 'limit'):
        assert len(LESSONS[slug][field]) == 2
        assert all(LESSONS[slug][field])
    assert 'data-action="language"' in html
    assert 'https://' in html  # optional source links, not resource loads


@pytest.mark.parametrize('slug', list(CHECKS))
def test_learning_ratio_semantics(slug):
    curve = ratio_chart(slug, build_check_chart(slug))
    result = run_check(slug)
    if slug in ('polyak-1964', 'ista-vs-fista'):
        assert curve is None
    else:
        assert max(curve.series[0].y) == pytest.approx(result.observed, rel=1e-9)
        assert set(curve.series[1].y) == {1.}


def test_escape_data_and_unknown_learning_topic():
    assert '<script>' not in bi('<script>', 'x')
    with pytest.raises(ValueError):
        learning_html('unknown')
    with pytest.raises(ValueError):
        learning_html(lang='unknown')


@pytest.mark.parametrize('preset,parameter,values', [
    ('quadratic', 'condition_number', [1., 10., 100.]),
    ('quadratic', 'L', [.1, 1., 2.]),
    ('diagonal-lasso', 'lam', [0., .1, 100.]),
    ('simplex', 'dimension', [2, 4, 10]),
    ('simplex', 'steps', [0, 5, 10]),
])
def test_sweep_is_actual_one_field_experiment(preset, parameter, values):
    base = preset_config(preset)
    original = copy.deepcopy(base)
    data = run_sweep(base, parameter, values)
    assert base == original
    assert len(data['experiments']) == len(values)
    for v, exp in zip(values, data['experiments']):
        restored = copy.deepcopy(exp['config'])
        target = restored if parameter == 'steps' else restored['problem']
        assert target[parameter] == v
        target[parameter] = base[parameter] if parameter == 'steps' else base['problem'][parameter]
        assert restored == base
        assert exp == run_experiment(exp['config'])


@pytest.mark.parametrize('parameter,values', [
    ('unknown', [1,2]), ('lam',[1,2]), ('condition_number', []),
    ('steps', [1]), ('steps', [1]*9), ('steps', [1,1]), ('steps', [True,2]),
    ('steps', [0, float('nan')]), ('steps', [1, 1.5]),
    ('dimension', [1,2]), ('condition_number', [1, float('inf')]),
])
def test_bad_sweeps_fail_before_running(monkeypatch, parameter, values):
    import chainbench.workflows as w
    monkeypatch.setattr(w, 'run_experiment', lambda _: pytest.fail('must reject before calculation'))
    with pytest.raises(ValueError):
        run_sweep(preset_config('quadratic'), parameter, values)


def test_sweep_shared_work_limit(monkeypatch):
    import chainbench.workflows as w
    base = preset_config('quadratic')
    base['problem']['dimension'] = 80
    base['steps'] = 100
    monkeypatch.setattr(w, 'run_experiment', lambda _: pytest.fail('combined limit before allocation'))
    with pytest.raises(ValueError, match='combined'):
        run_sweep(base, 'L', [1,2])


@pytest.mark.parametrize('n,h,L,R', [
    (1,1,1,1), (20,1,1,1), (10,.5,2,3), (500,.0001,1e6,1e-6), (500,1,1e-6,1e6),
])
def test_public_huber_case_attains_bound(n,h,L,R):
    data = gd_tight_case(n,L,R,h)
    assert data['target'] == L*R*R/(4*n*h+2)
    assert data['observed_ratio'] == pytest.approx(1., abs=1e-10)
    assert data['matches_target']
    a = R/(2*n*h+1)
    for row in data['rows']:
        k = row['iteration']
        assert row['x'] == pytest.approx(R-k*h*a, rel=1e-10)
        assert row['gradient'] == pytest.approx(L*a)
        assert row['gap'] <= row['upper_bound']*(1+1e-9)
    assert json.loads(Evidence(case_html(data, 'ko')).text) == json.loads(json.dumps(data))


def test_huber_case_hand_calculation_and_smooth_join():
    result = gd_tight_case(1)
    assert result['rows'][-1]['x'] == pytest.approx(2/3)
    assert result['rows'][-1]['gap'] == pytest.approx(1/6)
    a = result['transition']
    assert .5*a*a == pytest.approx(a*abs(a)-.5*a*a)
    assert result['reference']['url'].endswith('1206.3209')


@pytest.mark.parametrize('kwargs', [
    {'horizon':0}, {'horizon':True}, {'horizon':501}, {'h':1.1}, {'h':0},
    {'R':-1}, {'L':float('inf')}, {'R':float('nan')},
])
def test_huber_case_rejects_out_of_scope(kwargs):
    with pytest.raises(ValueError):
        gd_tight_case(**kwargs)


@pytest.fixture
def saved():
    config = preset_config('quadratic')
    config['methods']=['gd','cg']
    config['method_options'].pop('proximal-point')
    config['steps']=7
    config['include_iterates']=True
    return run_experiment(config)


def test_replay_matches_every_observation(saved):
    original = copy.deepcopy(saved)
    result = replay_experiment(load_report(canonical_json(saved)))
    assert result['status'] == 'MATCH'
    assert result['numeric_samples_compared'] > 100
    assert result['mismatch_count'] == 0
    assert result['replayed'] == saved
    assert original == saved


@pytest.mark.parametrize('path,value', [
    (('runs',0,'rows',1,'gap'), 100.),
    (('runs',0,'parameters','step_size'), 900.),
    (('runs',0,'rows',1,'iterate',0), -100.),
    (('fixture','f_star'), 100.),
])
def test_replay_detects_finite_false_values(saved, path, value):
    ptr = saved
    for key in path[:-1]:
        ptr = ptr[key]
    ptr[path[-1]] = value
    result = replay_experiment(saved)
    assert result['status'] == 'MISMATCH'
    assert result['mismatch_count'] >= 1


def test_replay_distinguishes_input_and_environment_changes(saved):
    saved['environment']['os']='OtherOS'
    result = replay_experiment(saved)
    assert result['environment_changed'] and result['status'] == 'MATCH'
    saved['fixture']['input_sha256']='0'*64
    result = replay_experiment(saved)
    assert result['status'] == 'INPUT_DIFFERENCE'
    assert result['mismatch_count'] == 0


@pytest.mark.parametrize('path,value', [
    (('runs',),[]), (('runs',0,'rows'),[]), (('runs',0,'updates'),True),
    (('runs',0,'rows',0,'gap'), None), (('runs',0,'rows',0,'gap'), float('nan')),
    (('runs',0,'rows',0,'gap'), -1), (('runs',0,'rows',0,'gap'), 10**1000), (('runs',0,'rows',0,'gap'), True),
    (('runs',0,'rows',0,'iteration'), False), (('runs',0,'rows',0,'iterate'),[]),
    (('environment',),{}), (('config_sha256',),'f'*64), (('fixture','input_sha256'),'missing'),
])
def test_missing_or_invalid_saved_evidence_rejected(saved, path, value):
    ptr = saved
    for key in path[:-1]:
        ptr = ptr[key]
    ptr[path[-1]] = value
    with pytest.raises(ValueError):
        replay_experiment(saved)


def test_config_digest_cannot_hide_normalization(saved):
    saved['config']['steps']=2
    assert saved['config_sha256'] != config_digest(saved['config'])
    with pytest.raises(ValueError):
        validate_saved_experiment(saved)


@pytest.mark.parametrize('text', ['{"x":1,"x":2}', '{"x":NaN}', '[1,2]', '{}', 'a'*8_000_001])
def test_strict_saved_json(text):
    with pytest.raises(ValueError):
        load_report(text)


@pytest.mark.parametrize('tol',[True, -1, float('nan'), 2])
def test_invalid_replay_tolerance(saved,tol):
    with pytest.raises(ValueError):
        replay_experiment(saved,rtol=tol)


def test_new_cli_end_to_end(tmp_path, saved):
    src=tmp_path/'saved.json'
    src.write_text(json.dumps(saved),encoding='utf8')
    for name,args in [
        ('learn',['learn','--lang','ko']),
        ('sweep',['sweep','--preset','simplex','--parameter','dimension','--values','2','4']),
        ('replay',['replay',str(src)]),
        ('tight',['case-study','gd-tight','--horizon','2']),
    ]:
        out=tmp_path/f'{name}.html'
        assert main(args+['--output',str(out)]) == 0
        assert out.read_text(encoding='utf8').startswith('<!doctype html>')
        with pytest.raises(SystemExit):
            main(args+['--output',str(out)])
    with pytest.raises(SystemExit):
        main(['replay',str(src),'--output',str(src),'--force'])
    with pytest.raises(SystemExit):
        main(['sweep','--preset','simplex','--parameter','steps','--steps','2','--values','2','4'])


def test_cli_replay_mismatch_not_silent_success(tmp_path, saved):
    saved['runs'][0]['rows'][1]['gap']=10.
    p=tmp_path/'false.json'
    p.write_text(json.dumps(saved),encoding='utf8')
    assert main(['replay',str(p),'--format','json']) == 1
