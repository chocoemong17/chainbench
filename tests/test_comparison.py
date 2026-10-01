import copy
import json
import sys
from pathlib import Path

import pytest

from chainbench import comparison
from chainbench.cli import main
from chainbench.comparison import compare_experiments, read_comparison_inputs
from chainbench.comparison_views import comparison_html
from chainbench.experiments import config_digest, preset_config, run_experiment

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from smoke_comparison import exercise_comparison, validate_comparison  # noqa: E402


def make_record(kind='quadratic', steps=4):
    config = preset_config(kind)
    config['problem']['dimension'] = 3
    config['steps'] = steps
    config['include_iterates'] = True
    return run_experiment(config)


@pytest.fixture
def record():
    return make_record()


@pytest.mark.parametrize('kind', ['quadratic', 'diagonal-lasso', 'simplex'])
@pytest.mark.parametrize('metric', ['gap', 'stationarity', 'distance_to_reference'])
def test_exact_samples_and_no_solver_execution(kind, metric, monkeypatch):
    left, right = make_record(kind, 0), make_record(kind, 5)
    def forbidden(*args, **kwargs):
        raise AssertionError('comparing saved records must not run a solver')
    monkeypatch.setattr('chainbench.experiments.run_experiment', forbidden)
    monkeypatch.setattr('chainbench.workflows.run_experiment', forbidden)
    result = compare_experiments([left, right], metric=metric)
    audit = validate_comparison(result, [left, right], comparison_html(result, 'ko'))
    assert audit['metric'] == metric
    assert result['shared_recorded_problem']
    assert not result['pairs'][0]['same_config']
    assert [d['field'] for d in result['pairs'][0]['config_differences']] == ['steps']
    assert result['records'][0]['experiment']['runs'][0]['rows'] == left['runs'][0]['rows']


@pytest.mark.parametrize('wrong_metric', ['stationarity', 'distance_to_reference', None])
def test_installed_smoke_rejects_ignored_metric_flag(tmp_path, wrong_metric):
    # Intercept CLI output before scientific validation: the requested first
    # metric is gap, even if the returned report claims another valid metric.
    calls = []

    def fake_run(args, work, env):
        calls.append(args)
        if args[1] == 'experiment':
            Path(args[args.index('--output')+1]).write_text('{}', encoding='utf8')
            return ''
        assert args[args.index('--metric')+1] == 'gap'
        assert args[-2:] == ['--format', 'json']
        return json.dumps({'metric': wrong_metric})

    with pytest.raises(RuntimeError, match='requested metric'):
        exercise_comparison('chainbench', tmp_path, {}, fake_run)
    assert len(calls) == 5


def test_four_records_are_detached_and_duplicates_explicit(record):
    sources = [copy.deepcopy(record) for _ in range(4)]
    sources[-1]['environment']['python'] = 'different recorded environment'
    result = compare_experiments(sources)
    validate_comparison(result, sources, comparison_html(result))
    assert len(result['pairs']) == 6
    assert result['pairs'][0]['identical_record']
    assert not result['pairs'][2]['identical_record']
    assert not result['pairs'][2]['same_environment']
    sources[0]['runs'][0]['rows'][0]['gap'] = 500
    assert result['records'][0]['experiment'] == record


@pytest.mark.parametrize('difference', ['input', 'fixture', 'config', 'family'])
def test_problem_differences_disable_overlay(record, difference):
    other = copy.deepcopy(record)
    if difference == 'input':
        other['fixture']['input_sha256'] = '0'*64
    elif difference == 'fixture':
        other['fixture']['f_star'] += 1
    elif difference == 'config':
        other['config']['problem']['L'] = 2.
        other['config_sha256'] = config_digest(other['config'])
    else:
        other = make_record('simplex')
    result = compare_experiments([record, other])
    validate_comparison(result, [record, other], comparison_html(result))
    assert not result['shared_recorded_problem']
    assert len(result['charts']) == 2


@pytest.mark.parametrize('field,value', [
    ('L', None), ('L', True), ('L', 0), ('L', float('inf')), ('L', '1'),
    ('mu', None), ('mu', -1), ('mu', 2), ('f_star', False), ('f_star', float('nan')),
    ('definition', {}), ('start', 'custom'), ('stationarity_metric', 'unknown'),
])
def test_invalid_fixture_metadata_rejected(record, field, value):
    record['fixture'][field] = value
    with pytest.raises(ValueError):
        compare_experiments([record, record])


@pytest.mark.parametrize('value', [None, True, -1, 0, '1', {}, float('inf')])
def test_invalid_parameter_rejected(record, value):
    record['runs'][0]['parameters']['step_size'] = value
    with pytest.raises(ValueError):
        compare_experiments([record, record])


def test_unknown_parameters_and_inconsistent_options_rejected(record):
    original = copy.deepcopy(record)
    record['runs'][0]['parameters']['extra'] = 1
    with pytest.raises(ValueError):
        compare_experiments([record, original])
    cg = next(r for r in original['runs'] if r['method'] == 'cg')
    cg['parameters']['rtol'] = .1
    with pytest.raises(ValueError):
        compare_experiments([original, original])


@pytest.mark.parametrize('count', [0, 1, 5])
def test_record_count_bounds(record, count):
    with pytest.raises(ValueError):
        compare_experiments([record]*count)
    with pytest.raises(ValueError):
        read_comparison_inputs([Path('absent.json')]*count)


def test_byte_budgets_before_output(record, tmp_path, monkeypatch):
    text = json.dumps(record)
    path = tmp_path/'saved.json'
    path.write_text(text, encoding='utf8')
    monkeypatch.setattr(comparison, 'MAX_REPORT_BYTES', len(text.encode())-1)
    with pytest.raises(ValueError, match='byte limit'):
        read_comparison_inputs([path, path])
    monkeypatch.setattr(comparison, 'MAX_REPORT_BYTES', 8_000_000)
    monkeypatch.setattr(comparison, 'MAX_COMPARISON_BYTES', len(text.encode())*2-1)
    with pytest.raises(ValueError, match='byte limit'):
        read_comparison_inputs([path, path])
    monkeypatch.setattr(comparison, 'MAX_COMPARISON_BYTES', 1)
    with pytest.raises(ValueError, match='byte limit'):
        compare_experiments([record, record])


@pytest.mark.parametrize('raw', ['{"kind":1,"kind":2}', '{"x":NaN}', '{"x":1e999}', '[[]]', '[]', '\ufeff{}'])
def test_strict_import_rejects_malformed_json(raw, tmp_path):
    path = tmp_path/'invalid.json'
    path.write_text(raw, encoding='utf8')
    with pytest.raises(ValueError):
        read_comparison_inputs([path, path])


@pytest.mark.parametrize('part', ['hash', 'pair', 'plot', 'missing_plot'])
def test_corrupt_comparison_cannot_be_presented_as_valid(record, part):
    result = compare_experiments([record, record])
    if part == 'hash':
        result['records'][0]['record_sha256'] = '0'*64
    elif part == 'pair':
        result['pairs'][0]['same_input_digest'] = False
    elif part == 'plot':
        result['charts'][0]['chart']['series'][0]['y'][0] += 1
    else:
        result['charts'].pop()
    with pytest.raises(ValueError):
        comparison_html(result)
    with pytest.raises(RuntimeError):
        validate_comparison(result, [record, record])


def test_imported_strings_remain_text(record):
    record['environment']['os'] = '</pre><script>globalThis.pwned=1</script>'
    record['notice'] = '<img src="https://invalid.test/tracker">'
    result = compare_experiments([record, record])
    text = comparison_html(result)
    assert record['environment']['os'] not in text
    assert record['notice'] not in text
    assert '&lt;script&gt;' in text
    validate_comparison(result, [record, record], text)


@pytest.mark.parametrize('alias', ['same', 'hardlink', 'symlink'])
def test_cli_never_overwrites_any_input_even_with_force(record, tmp_path, alias):
    a, b = tmp_path/'a.json', tmp_path/'b.json'
    text = json.dumps(record)
    a.write_text(text, encoding='utf8')
    b.write_text(text, encoding='utf8')
    out = tmp_path/'output.json'
    if alias == 'same':
        out = b
    elif alias == 'hardlink':
        out.hardlink_to(b)
    else:
        try:
            out.symlink_to(b)
        except OSError:
            pytest.skip('OS account cannot create symlinks')
    with pytest.raises(SystemExit) as exc:
        main(['compare', str(a), str(b), '--output', str(out), '--force'])
    assert exc.value.code == 2
    assert a.read_text(encoding='utf8') == b.read_text(encoding='utf8') == text


def test_cli_records_and_output_protection(record, tmp_path, capsys):
    path = tmp_path/'saved.json'
    path.write_text(json.dumps(record), encoding='utf8')
    assert main(['compare', str(path), str(path), '--format', 'json']) == 0
    result = json.loads(capsys.readouterr().out)
    validate_comparison(result, [record, record])
    out = tmp_path/'comparison.html'
    assert main(['compare', str(path), str(path), '--output', str(out)]) == 0
    before = out.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(['compare', str(path), str(path), '--output', str(out)])
    assert exc.value.code == 2 and out.read_bytes() == before
