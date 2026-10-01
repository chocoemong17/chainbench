"""Independent small recurrences and untrusted-input contracts for stored arrays."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from html import unescape

import numpy as np
import pytest

from chainbench import instances
from chainbench.cli import main
from chainbench.experiments import canonical_json, run_experiment
from chainbench.instance_reporting import instance_html
from chainbench.instances import (
    generate_instance,
    import_instance,
    parse_json,
    replay_instance,
    run_instance,
    validate_instance,
    validate_instance_report,
)


def quadratic(methods=None, steps=2):
    return {'schema_version': 1, 'problem': {'kind': 'quadratic', 'Q': [[2, 1], [1, 2]],
            'b': [1, -1], 'x_star': [1, -1]}, 'x0': [2, -1],
            'run': {'steps': steps, 'include_iterates': True,
                    'methods': methods or ['gd', 'smooth-fista', 'heavy-ball', 'cg', 'proximal-point']}}


def result():
    return run_instance(import_instance(quadratic()))


def rehash(manifest):
    manifest['manifest_sha256'] = hashlib.sha256(canonical_json(
        {k: v for k, v in manifest.items() if k != 'manifest_sha256'}).encode()).hexdigest()


def test_off_diagonal_first_updates_are_hand_computed():
    record = result()
    alpha = 4 / (math.sqrt(3) + 1)**2
    expected = {'gd': [4/3, -4/3], 'smooth-fista': [4/3, -4/3],
                'heavy-ball': [2-2*alpha, -1-alpha], 'cg': [9/7, -19/14],
                'proximal-point': [11/8, -9/8]}
    for run in record['runs']:
        assert run['rows'][0]['iterate'] == [2., -1.]
        assert run['rows'][0]['objective'] == 0
        assert run['rows'][0]['gap'] == 1
        assert run['rows'][0]['stationarity'] == pytest.approx(math.sqrt(5))
        assert run['rows'][1]['iterate'] == pytest.approx(expected[run['method']])
    assert record['runs'][3]['termination'] == 'converged'
    assert record['runs'][3]['rows'][-1]['iterate'] == pytest.approx([1, -1])


def test_psd_reference_distance_is_not_solution_set_distance():
    raw = quadratic(['gd', 'smooth-fista', 'proximal-point'])
    raw['problem'] = {'kind': 'quadratic', 'Q': [[0, 0], [0, 2]], 'b': [0, -2], 'x_star': [4, -1]}
    raw['x0'] = [0, 1]
    record = run_instance(import_instance(raw))
    row = record['runs'][0]['rows'][1]
    assert row['iterate'] == [0, -1]
    assert row['gap'] == 0 and row['stationarity'] == 0
    assert row['distance_to_reference'] == 4
    assert record['fixture']['mu'] == 0
    for method in ('cg', 'heavy-ball'):
        raw['run']['methods'] = [method]
        with pytest.raises(ValueError, match='positive-definite'):
            import_instance(raw)


def test_signed_diagonal_lasso_and_simplex_custom_start():
    lasso = {'schema_version': 1, 'problem': {'kind': 'diagonal-lasso', 'a': [2, -1],
              'b': [1, 1], 'lam': .5}, 'x0': [1, -1], 'run': {'steps': 2, 'include_iterates': True}}
    record = run_instance(import_instance(lasso))
    assert record['fixture']['x_star'] == [.375, -.5]
    for run in record['runs']:
        assert run['rows'][1]['iterate'] == [.375, -.875]
        assert run['rows'][1]['gap'] == .0703125
        assert run['rows'][1]['objective'] == .6640625
    simplex = {'schema_version': 1, 'problem': {'kind': 'simplex', 'target': [.25, .75]},
               'x0': [.5, .5], 'run': {'steps': 2, 'include_iterates': True}}
    rows = run_instance(import_instance(simplex))['runs'][0]['rows']
    assert rows[0]['stationarity'] == .25
    assert rows[1]['iterate'] == [0, 1]
    assert rows[2]['iterate'] == pytest.approx([2/3, 1/3])
    assert rows[2]['gap'] == pytest.approx(25/144)


@pytest.mark.parametrize('family', ['quadratic', 'diagonal-lasso', 'simplex'])
@pytest.mark.parametrize('seed', [0, 7, 2**32-1])
def test_seed_generates_real_data_and_replay_never_calls_generator(family, seed, monkeypatch):
    manifest = generate_instance(family, seed=seed, dimension=4, run={'steps': 6, 'include_iterates': True})
    other = generate_instance(family, seed=(seed+1) % 2**32, dimension=4, run={'steps': 6, 'include_iterates': True})
    assert manifest['problem'] != other['problem'] and manifest['x0'] != other['x0']
    record = run_instance(manifest)
    def forbidden(*args, **kwargs):
        raise AssertionError('replay must read stored numbers without generation')
    monkeypatch.setattr(instances, 'generate_instance', forbidden)
    monkeypatch.setattr(np.random, 'PCG64', forbidden)
    outcome = replay_instance(record)
    assert outcome['status'] == 'MATCH' and outcome['same_input_bytes'] is True
    assert outcome['numeric_samples_compared'] > 0
    assert outcome['replayed']['instance'] == manifest
    assert parse_json(json.dumps(manifest)) == manifest


@pytest.mark.parametrize('field,value', [('schema_version', True), ('x0', [True, 1]),
    ('x0', ['2', -1]), ('x0', [2, -1, 0]), ('x0', [float('nan'), -1]),
    ('x0', [2**53+1, -1]), ('x0', [1e400, -1]), ('x0', [[2], [-1]]), ('x0', [])])
def test_bad_raw_inputs(field, value):
    raw = quadratic()
    raw[field] = value
    with pytest.raises(ValueError):
        import_instance(raw)


@pytest.mark.parametrize('field,value', [('Q', [[2, 1+1e-13], [1, 2]]),
    ('Q', [[2, 0], [0, -1]]), ('Q', [[0, 0], [0, 0]]), ('Q', [[2, 1], [1]]),
    ('b', [0, 0]), ('x_star', [0, 0])])
def test_quadratic_is_not_silently_repaired(field, value):
    raw = quadratic()
    raw['problem'][field] = value
    with pytest.raises(ValueError):
        import_instance(raw)


@pytest.mark.parametrize('field,value', [('steps', 2001), ('steps', True),
    ('methods', ['gd', 'gd']), ('methods', ['ista']), ('include_iterates', 1),
    ('method_options', {'gd': {}}), ('unknown', 1)])
def test_bounded_settings(field, value):
    raw = quadratic()
    raw['run'][field] = value
    with pytest.raises(ValueError):
        import_instance(raw)


def test_scalar_and_work_budgets_precede_execution():
    with pytest.raises(ValueError, match='scalar budget'):
        generate_instance('diagonal-lasso', dimension=64, run={'steps': 2000, 'include_iterates': True})
    with pytest.raises(ValueError, match='work limit'):
        generate_instance('quadratic', dimension=64, run={'steps': 2000})
    with pytest.raises(ValueError, match='dimension'):
        generate_instance('quadratic', dimension=65)


@pytest.mark.parametrize('change', ['array', 'start', 'seed', 'run', 'input_hash', 'manifest_hash'])
def test_manifest_corruption_rejected(change):
    m = generate_instance('quadratic', run={'steps': 2})
    if change == 'array':
        m['problem']['x_star'][0] += .1
    elif change == 'start':
        m['x0'][0] += .1
    elif change == 'seed':
        m['origin']['parameters']['seed'] += 1
    elif change == 'run':
        m['run']['steps'] += 1
    else:
        m['input_sha256' if change == 'input_hash' else 'manifest_sha256'] = '0'*64
    with pytest.raises(ValueError):
        run_instance(m)


def test_rehashed_origin_wrong_dimension_is_rejected_and_import_has_no_claimed_origin():
    m = generate_instance('quadratic')
    m['origin']['parameters']['dimension'] = 5
    rehash(m)
    with pytest.raises(ValueError, match='provenance'):
        validate_instance(m)
    raw = quadratic()
    raw['origin'] = {'type': 'generated', 'seed': 42}
    with pytest.raises(ValueError, match='unknown keys'):
        import_instance(raw)


@pytest.mark.parametrize('bad', ['NaN', 'Infinity', '-Infinity', '1e400'])
def test_nonfinite_json_rejected(bad):
    with pytest.raises(ValueError):
        parse_json('{"x":'+bad+'}')


def test_transport_depth_duplicates_and_size():
    for text in ('{"x":1,"x":2}', '['*30+'0'+']'*30, ' '*256001, 'null'):
        with pytest.raises(ValueError):
            import_instance(parse_json(text))


@pytest.mark.parametrize('mutation', ['missing_row', 'missing_metric', 'nan', 'boolean',
    'index', 'updates', 'parameters', 'option', 'fixture', 'initial', 'missing_environment', 'extra'])
def test_malformed_reports_never_replay_as_match(mutation):
    saved = result()
    run = saved['runs'][0]
    if mutation == 'missing_row':
        run['rows'].pop()
    elif mutation == 'missing_metric':
        del run['rows'][1]['gap']
    elif mutation in ('nan', 'boolean'):
        run['rows'][1]['gap'] = float('nan') if mutation == 'nan' else True
    elif mutation == 'index':
        run['rows'][1]['iteration'] = 1.0
    elif mutation == 'updates':
        run['updates'] = True
    elif mutation == 'parameters':
        run['parameters']['extra'] = 1
    elif mutation == 'option':
        saved['runs'][3]['parameters']['rtol'] = .1
    elif mutation == 'fixture':
        saved['fixture']['input_sha256'] = '0'*64
    elif mutation == 'initial':
        run['rows'][0]['iterate'][0] += 1e-15
    elif mutation == 'missing_environment':
        del saved['environment']['numpy']
    else:
        saved['unexpected'] = 0
    with pytest.raises(ValueError):
        replay_instance(saved)


@pytest.mark.parametrize('path', ['objective', 'gap', 'stationarity', 'distance_to_reference', 'iterate', 'L', 'f_star', 'x_star'])
def test_valid_but_changed_observation_is_mismatch(path):
    saved = result()
    if path in ('L', 'f_star'):
        saved['fixture'][path] += .1
    elif path == 'x_star':
        saved['fixture'][path][0] += .1
    elif path == 'iterate':
        saved['runs'][0]['rows'][1][path][0] += .1
    else:
        saved['runs'][0]['rows'][1][path] += .1
    outcome = replay_instance(saved)
    assert outcome['status'] == 'MISMATCH'
    assert outcome['mismatch_count'] > 0 and outcome['first_mismatches']


def test_environment_tolerance_and_signed_zero_contracts():
    saved = result()
    saved['environment']['os'] = 'another OS'
    assert replay_instance(saved)['environment_changed'] is True
    saved['runs'][0]['rows'][1]['gap'] += 1e-10
    assert replay_instance(saved, rtol=0, atol=1e-12)['status'] == 'MISMATCH'
    assert replay_instance(saved, rtol=0, atol=1e-9)['status'] == 'MATCH'
    for bad in (True, -1., float('nan'), float('inf'), 1.1):
        with pytest.raises(ValueError):
            replay_instance(saved, rtol=bad)
    raw = quadratic(['gd'], steps=0)
    raw['x0'] = [0., -0.]
    first = import_instance(raw)
    raw['x0'][1] = 0.
    second = import_instance(raw)
    assert first['input_sha256'] != second['input_sha256']
    assert math.copysign(1, run_instance(first)['runs'][0]['rows'][0]['iterate'][1]) == -1


def test_manifest_detaches_inputs_and_no_iterates_can_replay():
    raw = quadratic()
    raw['run']['include_iterates'] = False
    m = import_instance(raw)
    saved = run_instance(m)
    snapshot = copy.deepcopy(saved)
    raw['x0'][0] = 100
    m['x0'][0] = 101
    assert saved == snapshot
    assert 'iterate' not in saved['runs'][0]['rows'][0]
    assert replay_instance(saved)['status'] == 'MATCH'


def test_old_schema_remains_a_preset_and_new_schema_is_distinct():
    saved = run_experiment({'schema_version': 1, 'problem': {'kind': 'quadratic'}, 'steps': 0})
    assert saved['kind'] == 'chainbench.experiment'
    assert saved['fixture']['start'] == 'zeros'
    assert 'instance' not in saved
    with pytest.raises(ValueError):
        validate_instance_report(saved)


def test_html_retains_inputs_every_sample_and_no_script_fallback():
    saved = result()
    html = instance_html(saved, 'ko')
    assert unescape(html.split('<pre id="chainbench-evidence">')[1].split('</pre>')[0]) == json.dumps(saved, indent=2, ensure_ascii=False)
    assert html.count('data-instance-chart=') == 3 and html.count('<metadata>') == 3
    assert 'x_star' in html and 'stored_vector' in html and 'lang="ko"' in html and 'lang="en"' in html
    assert 'connect-src' in html
    replay = replay_instance(saved)
    assert 'id="instance-replay"' in instance_html(replay['replayed'], replay=replay)


def test_cli_roundtrip_and_input_alias_protection(tmp_path, capsys):
    raw, manifest, report = (tmp_path/name for name in ('raw.json', 'input.json', 'result.json'))
    raw.write_text(json.dumps(quadratic()), encoding='utf8')
    assert main(['instance', 'import', str(raw), '--output', str(manifest)]) == 0
    assert main(['instance', 'run', str(manifest), '--output', str(report)]) == 0
    assert main(['instance', 'replay', str(report)]) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'MATCH'
    original = report.read_bytes()
    alias = tmp_path/'alias.json'
    alias.hardlink_to(report)
    for path in (report, alias):
        with pytest.raises(SystemExit) as exc:
            main(['instance', 'replay', str(report), '--output', str(path), '--force'])
        assert exc.value.code == 2
        assert report.read_bytes() == original
    changed = json.loads(original)
    changed['runs'][0]['rows'][1]['gap'] += 1
    report.write_text(json.dumps(changed), encoding='utf8')
    assert main(['instance', 'replay', str(report)]) == 1
    assert json.loads(capsys.readouterr().out)['status'] == 'MISMATCH'
