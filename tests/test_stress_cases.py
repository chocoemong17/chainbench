import hashlib
import importlib.util
import json
import math
import struct
from pathlib import Path

import numpy as np
import pytest
from _numeric_records import assert_recomputed_record

from chainbench.cli import main
from chainbench.problems import DiagonalLassoProblem, QuadraticProblem
from chainbench.stress import run_stress, run_stress_case, stress_case_html, stress_html
from chainbench.stress_cases import TOPICS, trial


def independent_digest(arrays):
    digest = hashlib.sha256()
    for name in sorted(arrays):
        value = arrays[name]
        shape = [len(value), len(value[0])] if isinstance(value[0], list) else [len(value)]
        flat = [x for row in value for x in row] if len(shape) == 2 else value
        digest.update(name.encode('ascii')+b'\0')
        digest.update(json.dumps(shape, separators=(',', ':')).encode('ascii')+b'\0')
        digest.update(struct.pack('<'+str(len(flat))+'d', *flat))
    return digest.hexdigest()


def independent_samples(row):
    a = row['inputs']
    if row['family'] == 'quadratic':
        q, sol = np.array(a['Q']), np.array(a['x_star'])
        np.testing.assert_allclose(q@sol, a['b'], atol=1e-13)
        assert row['parameters']['L'] == pytest.approx(np.linalg.eigvalsh(q)[-1])
        def gap(x):
            return float((x-sol)@q@(x-sol)/2)
    elif row['family'] == 'simplex-quadratic':
        sol = np.array(a['target'])
        def gap(x):
            return float(np.sum((x-sol)**2)/2)
    else:
        diagonal, b, lam = np.array(a['a']), np.array(a['b']), a['lam'][0]
        sol = np.array([math.copysign(max(abs(v*w)-lam, 0), v*w)/(v*v)
                        for v, w in zip(diagonal, b)])
        def gap(x):
            d = x-sol
            return float(np.sum(.5*(diagonal*d)**2 + lam*(np.abs(x)-np.abs(sol))
                                + diagonal*(diagonal*sol-b)*d))
    assert row['instance_sha256'] == independent_digest(a)
    for run in row['runs'].values():
        np.testing.assert_array_equal(run['iterates'][0], a['x0'])
        assert len(run['iterates']) == run['updates']+1 == len(run['gaps'])
        np.testing.assert_allclose(run['gaps'], [gap(np.array(x)) for x in run['iterates']], atol=1e-13)
        if row['family'] == 'simplex-quadratic':
            xs = np.array(run['iterates'])
            assert np.min(xs) >= 0
            np.testing.assert_allclose(xs.sum(axis=1), 1, atol=1e-14)
    return sol


@pytest.mark.parametrize('topic', TOPICS)
def test_full_strata_and_independent_metrics(topic):
    result = run_stress(topic, 16, 0)
    assert result['schema_version'] == 2
    assert [r['seed'] for r in result['rows']] == list(range(16))
    assert {r['dim'] for r in result['rows']} == {6, 12, 24, 40}
    for row in result['rows']:
        sol = independent_samples(row)
        runs, params, curves = row['runs'], row['parameters'], row['curve']['series']
        if topic in ('gd-baseline', 'nesterov-1983', 'beck-teboulle-2009', 'jaggi-2013'):
            radius2 = sum((x-y)**2 for x, y in zip(row['inputs']['x0'], sol))
            assert params['radius_squared'] == pytest.approx(radius2)
            expected = []
            for k in range(1, row['steps']+1):
                bound = (params['L']*radius2/(2*k) if topic == 'gd-baseline' else
                         4/(k+2) if topic == 'jaggi-2013' else 2*params['L']*radius2/(k+1)**2)
                expected.append(bound)
            np.testing.assert_allclose(curves[1]['values'], expected)
            metric = max(g/b for g, b in zip(next(iter(runs.values()))['gaps'][1:], expected))
        elif topic == 'hestenes-stiefel-1952':
            errors = np.sqrt(2*np.array(runs['cg']['gaps']))
            rho = (math.sqrt(params['condition_number'])-1)/(math.sqrt(params['condition_number'])+1)
            bound = [2*rho**k*errors[0] for k in range(1, len(errors))]
            np.testing.assert_allclose(curves[1]['values'], bound)
            metric = max(e/b for e, b in zip(errors[1:], bound))
        elif topic in ('polyak-1964', 'rockafellar-1976'):
            run = next(iter(runs.values()))
            errors = [math.sqrt(sum((x-y)**2 for x, y in zip(v, sol))) for v in run['iterates']]
            floor = 1e-10 if topic == 'polyak-1964' else 1e-12
            indices = [k for k in range(1, len(errors)) if errors[k-1] > floor]
            assert curves[0]['iterations'] == row['measurement']['indices'] == indices
            ratios = [errors[k]/errors[k-1] for k in indices]
            np.testing.assert_allclose(curves[0]['values'], ratios)
            metric = (abs(float(np.median(ratios[-20:]))-params['rho'])/params['rho']
                      if topic == 'polyak-1964' else max(ratios)/params['contraction'])
        else:
            metric = runs['fista']['gaps'][-1]/runs['ista']['gaps'][-1]
            assert row['threshold'] is None
        assert row['metric'] == pytest.approx(metric, abs=1e-14)
        assert_recomputed_record(row, run_stress_case(topic, row['seed'])['case'])
    if result['rows'][0]['family'] == 'quadratic':
        assert len({(r['dim'], r['orientation'], r['start_kind']) for r in result['rows']}) == 16


def test_rank_selection_is_declared_and_no_rows_disappear():
    result = run_stress('ista-vs-fista', 16, 0)
    ranked = sorted(enumerate(result['rows'], 1), key=lambda pair: (pair[1]['metric'], pair[1]['seed']))
    for name, rank in [('median-ranked', 8), ('p90-ranked', 15), ('maximum-observed', 16)]:
        i, row = ranked[rank-1]
        assert result['selected'][name] == {'trial': i, 'seed': row['seed'], 'metric': row['metric'], 'rank': rank}
    assert result['summary']['max'] > 1  # Preserve a real case where FISTA's final gap is larger.
    assert result['summary']['median'] == pytest.approx(np.median([r['metric'] for r in result['rows']]))
    html = stress_html(result)
    assert html.count('class="stress-case"') == 16
    assert 'Maximum observed is not a certified worst case' in html


@pytest.mark.parametrize('topic', ['beck-teboulle-2009', 'ista-vs-fista'])
def test_zero_radius_and_unresolved_denominator_are_retained_not_resampled(topic, monkeypatch):
    import chainbench.stress_cases as module
    calls = []
    def zero_problem(topic, seed, rng):
        calls.append(seed)
        p = DiagonalLassoProblem(np.ones(6), np.zeros(6), .1)
        return p, np.zeros(6), {'a': [1.]*6, 'b': [0.]*6, 'lam': [.1], 'x0': [0.]*6}, {
            'family': 'diagonal-lasso', 'orientation': 'diagonal', 'start_kind': 'zero'}
    monkeypatch.setattr(module, '_problem', zero_problem)
    result = run_stress(topic, 3, 7)
    assert calls == [7, 8, 9]
    assert all(r['metric'] is None and r['status'] == 'unresolved' and r['reason'] for r in result['rows'])
    assert result['summary']['measured'] == 0 and result['summary']['unresolved'] == 3
    assert result['summary']['median'] is None and result['selected'] == {}
    assert result['summary'].get('within_threshold', 0) == 0
    assert 'No resolved ratios' in stress_html(result)
    assert 'UNRESOLVED' in stress_case_html(run_stress_case(topic, 7))


def test_all_error_ratios_at_floor_are_unresolved(monkeypatch):
    import chainbench.stress_cases as module
    def zero_problem(topic, seed, rng):
        p = QuadraticProblem.from_reference(np.diag([1., 2.]), np.zeros(2))
        return p, np.zeros(2), {'Q': p.Q.tolist(), 'b': [0., 0.], 'x_star': [0., 0.], 'x0': [0., 0.]}, {
            'family': 'quadratic', 'orientation': 'diagonal', 'start_kind': 'zero'}
    monkeypatch.setattr(module, '_problem', zero_problem)
    for topic in ('polyak-1964', 'rockafellar-1976', 'hestenes-stiefel-1952'):
        result = run_stress(topic, 2)
        assert result['summary']['unresolved'] == 2
        assert result['summary']['within_threshold'] == 0
        stress_html(result)


@pytest.mark.parametrize('seed', [True, -1, 2**63, '0', 1.5])
def test_invalid_seeds_preflight(seed, monkeypatch):
    import chainbench.stress_cases as module
    monkeypatch.setattr(module, '_problem', lambda *args: pytest.fail('allocated before validation'))
    with pytest.raises(ValueError):
        trial('gd-baseline', seed)


def test_input_fingerprint_includes_start_and_budget():
    from chainbench.stress_cases import input_digest
    result = trial('gd-baseline', 0)
    result['inputs']['x0'][0] += 1
    assert input_digest(result['inputs']) != result['instance_sha256']
    result['inputs']['x0'][0] -= 1
    result['inputs']['update_budget'][0] += 1
    assert input_digest(result['inputs']) != result['instance_sha256']


def test_nonfinite_trace_cannot_be_summarized(monkeypatch):
    import chainbench.stress_cases as module
    original = module.fista
    def broken(*args, **kwargs):
        trace = original(*args, **kwargs)
        trace.iterates[-1][0] = np.nan
        return trace
    monkeypatch.setattr(module, 'fista', broken)
    with pytest.raises((FloatingPointError, ValueError)):
        run_stress('ista-vs-fista', 2)


def test_single_case_cli_reruns_selected_case_and_protects_output(tmp_path, capsys):
    selected = run_stress('nesterov-1983', 3, 9)['rows'][1]
    args = ['stress-case', 'nesterov-1983', '--seed', '10']
    assert main(args+['--format', 'json']) == 0
    actual = json.loads(capsys.readouterr().out)
    assert_recomputed_record(actual['case'], selected)
    path = tmp_path/'case.html'
    assert main(args+['--lang', 'ko', '--output', str(path)]) == 0
    before = path.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(args+['--output', str(path)])
    assert error.value.code == 2 and path.read_bytes() == before
    assert main(args+['--force', '--output', str(path)]) == 0


def smoke_module():
    spec = importlib.util.spec_from_file_location('smoke_workflows',
        Path(__file__).resolve().parents[1]/'scripts/smoke_workflows.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize('topic', ['nesterov-1983', 'ista-vs-fista'])
def test_installed_validator_checks_outputs_and_rejects_corruption(topic):
    row = trial(topic, 10)
    smoke_module().validate_stress_sample(topic, row)
    row['metric'] += 1
    with pytest.raises(RuntimeError, match='metric'):
        smoke_module().validate_stress_sample(topic, row)
    row = trial(topic, 10)
    row['inputs']['x0'][0] += 1
    with pytest.raises(RuntimeError, match='fingerprint'):
        smoke_module().validate_stress_sample(topic, row)


def test_mixed_unresolved_summary_and_rank_exclusion():
    result = run_stress('ista-vs-fista', 64, 0)
    unresolved = [r for r in result['rows'] if r['metric'] is None]
    assert unresolved  # A real floor case, also checked independently in the installed workflow.
    for row in unresolved:
        smoke_module().validate_stress_sample('ista-vs-fista', row)
        assert row['runs']['ista']['gaps'][-1] <= 1e-28
        assert row['seed'] not in [s['seed'] for s in result['selected'].values()]
    assert result['summary']['measured']+result['summary']['unresolved'] == 64
    metrics = [r['metric'] for r in result['rows'] if r['metric'] is not None]
    assert result['summary']['median'] == pytest.approx(np.median(metrics))
