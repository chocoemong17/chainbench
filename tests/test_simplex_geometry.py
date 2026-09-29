import copy
import importlib.util
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from chainbench.cli import main
from chainbench.simplex_geometry import run_simplex_geometry, simplex_html, simplex_svg


def smoke_module():
    spec = importlib.util.spec_from_file_location(
        'smoke_workflows', Path(__file__).resolve().parents[1]/'scripts/smoke_workflows.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize('steps', [1, 18, 60])
def test_all_cases_feasibility_certificates_and_recurrences(steps):
    result = run_simplex_geometry(steps)
    smoke_module().validate_simplex_geometry(result)
    assert result == run_simplex_geometry(steps)
    assert len({c['input_sha256'] for c in result['cases']}) == 12
    for case in result['cases']:
        if case['start_name'] != 'center':
            assert all(r['support'] <= r['iteration']+1 for r in case['rows'])


def test_independent_first_updates_and_nonmonotonic_counterexample():
    result = run_simplex_geometry(3)
    rows = result['cases'][0]['rows']
    np.testing.assert_allclose([r['x'] for r in rows],
                               [[1, 0, 0], [0, 0, 1], [0, 2/3, 1/3], [1/2, 1/3, 1/6]])
    assert [r['vertex_index'] for r in rows[:3]] == [2, 1, 0]
    assert [r['gamma'] for r in rows] == [1, 2/3, 1/2, None]
    case = next(c for c in result['cases'] if c['id'] == 'interior-center')
    assert case['rows'][0]['gap'] == pytest.approx(7/300)
    assert case['rows'][1]['gap'] == pytest.approx(19/100)
    assert case['rows'][1]['gap'] > case['rows'][0]['gap']


@pytest.mark.parametrize('steps', [0, -1, 61, True, 1.5, float('nan'), '18'])
def test_invalid_budget_rejected_before_calculation(steps, monkeypatch):
    import chainbench.simplex_geometry as module
    monkeypatch.setattr(module, 'SimplexQuadraticProblem', lambda *a: pytest.fail('allocated'))
    with pytest.raises(ValueError, match='steps'):
        run_simplex_geometry(steps)


def test_nonfinite_iterates_cannot_be_exported(monkeypatch):
    import chainbench.simplex_geometry as module
    original = module.frank_wolfe
    def broken(*args, **kwargs):
        trace = original(*args, **kwargs)
        trace.iterates[-1][0] = np.nan
        return trace
    monkeypatch.setattr(module, 'frank_wolfe', broken)
    with pytest.raises((ValueError, FloatingPointError)):
        run_simplex_geometry()


@pytest.mark.parametrize('surface', [False, True])
def test_every_marker_and_path_projects_the_actual_samples(surface):
    for case in run_simplex_geometry(4)['cases']:
        root = ET.fromstring(simplex_svg(case, surface=surface))
        ns = {'s': 'http://www.w3.org/2000/svg'}
        def project(x):
            # Independent barycentric embedding and objective height.
            u, v = x[1]+x[2]/2, math.sqrt(3)*x[2]/2
            gap = sum((a-b)**2 for a, b in zip(x, case['target']))/2
            return ((90+380*u-80*v, 435-170*v-240*gap) if surface
                    else (70+420*u, 440-420*v))
        path = root.find('.//s:polyline[@data-fw-history]', ns)
        actual = [[float(x) for x in p.split(',')] for p in path.attrib['points'].split()]
        np.testing.assert_allclose(actual, [project(r['x']) for r in case['rows']], atol=.00051)
        for name, vectors in (
            ('current', [r['x'] for r in case['rows'][:-1]]),
            ('oracle', [r['vertex'] for r in case['rows'][:-1]]),
            ('next', [r['x'] for r in case['rows'][1:]]),
        ):
            marker = root.find(f'.//s:circle[@data-marker="{name}"]', ns)
            frames = [[float(v) for v in p.split(',')] for p in marker.attrib['data-frames'].split('|')]
            np.testing.assert_allclose(frames, [project(x) for x in vectors], atol=.00051)


def test_cli_html_evidence_and_overwrite_contract(tmp_path):
    path, raw = tmp_path/'simplex.html', tmp_path/'simplex.json'
    args = ['geometry', 'frank-wolfe', '--steps', '3']
    assert main(args+['--lang', 'ko', '--output', str(path)]) == 0
    assert main(args+['--format', 'json', '--output', str(raw)]) == 0
    text = path.read_text(encoding='utf8')
    assert smoke_module().extract_record(text) == json.loads(raw.read_text(encoding='utf8'))
    assert text.count('data-fw-case=') == 12
    assert 'GEOMETRIC ILLUSTRATIONS' in text
    assert 'not a pointwise upper bound on g_FW' in text
    before = path.read_bytes()
    with pytest.raises(SystemExit) as exc:
        main(args+['--output', str(path)])
    assert exc.value.code == 2 and path.read_bytes() == before
    assert main(args+['--force', '--output', str(path)]) == 0
    bad = tmp_path/'invalid.html'
    with pytest.raises(SystemExit) as exc:
        main(['geometry', 'frank-wolfe', '--steps', '0', '--output', str(bad)])
    assert exc.value.code == 2 and not bad.exists()


@pytest.mark.parametrize('field,value', [('gap', float('nan')), ('dual_gap', -1),
                                        ('vertex', [1, 0, 0]), ('gamma', .1),
                                        ('support', 99), ('x', [0, 0, .8])])
def test_installed_validator_rejects_corrupted_evidence(field, value):
    result = copy.deepcopy(run_simplex_geometry(3))
    result['cases'][0]['rows'][1][field] = value
    with pytest.raises(RuntimeError):
        smoke_module().validate_simplex_geometry(result)


def test_html_rejects_unrelated_record():
    with pytest.raises(ValueError, match='not a simplex'):
        simplex_html({'kind': 'other'})
