import copy
import hashlib
import importlib.util
import json
import math
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from chainbench.cli import main
from chainbench.proximal_geometry import run_proximal_geometry
from chainbench.proximal_views import _contour, proximal_html, proximal_svg


def smoke_module():
    spec = importlib.util.spec_from_file_location('smoke_workflows',
        Path(__file__).resolve().parents[1]/'scripts/smoke_workflows.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize('steps', [2, 18, 60])
def test_all_declared_cases_and_independent_stage_optimality(steps):
    result = run_proximal_geometry(steps)
    assert len(result['cases']) == 9
    assert {c['lambda'] for c in result['cases']} == {.1, .8, 1.8}
    assert len({c['input_sha256'] for c in result['cases']}) == 9
    for c in result['cases']:
        lam = c['lambda']
        star = [max(1.4-lam, 0), -max(7.2-lam, 0)/9]
        assert c['x_star'] == pytest.approx(star)
        assert c['input_sha256'] == hashlib.sha256(struct.pack('<7d', 1, 3, 1.4, -2.4, lam, *c['start'])).hexdigest()
        for method, run in c['runs'].items():
            assert len(run['rows']) == steps+1 and len(run['stages']) == steps
            assert run['rows'][0]['x'] == c['start']
            for k, (r, stage) in enumerate(zip(run['rows'], run['stages'])):
                assert stage['x'] == r['x']
                assert stage['next_x'] == run['rows'][k+1]['x']
                assert stage['threshold'] == pytest.approx(lam/9)
                y = stage['y']
                gradient = [y[0]-1.4, 9*y[1]+7.2]
                assert stage['gradient'] == pytest.approx(gradient)
                assert stage['z'] == pytest.approx([y[j]-gradient[j]/9 for j in range(2)])
                for z, xn, zero in zip(stage['z'], stage['next_x'], stage['zeroed']):
                    if zero:
                        assert xn == 0 and abs(z) <= lam/9
                        assert abs(9*(z-xn)) <= lam+1e-14
                    else:
                        assert 9*(z-xn) == pytest.approx(math.copysign(lam, xn), abs=1e-14)
                assert all(-2.5 <= p[0] <= 2.5 and -2 <= p[1] <= 2
                           for p in [stage['x'], stage['y'], stage['z'], stage['next_x']])
                if method == 'ista':
                    assert y == r['x'] and stage['momentum'] == 0
            radius2 = sum((x-y)**2 for x, y in zip(c['start'], star))
            for k, r in enumerate(run['rows']):
                x, y = r['x']
                objective = ((x-1.4)**2+(3*y+2.4)**2)/2+lam*(abs(x)+abs(y))
                assert r['objective'] == pytest.approx(objective, abs=1e-14)
                assert r['gap'] == pytest.approx(objective-c['f_star'], abs=1e-13)
                if k:
                    bound = 9*radius2/(2*k) if method == 'ista' else 18*radius2/(k+1)**2
                    assert c['bounds'][method][k-1] == pytest.approx(bound)
                    assert r['gap'] <= bound+1e-13
                if method == 'ista' and k:
                    assert r['gap'] <= run['rows'][k-1]['gap']+1e-13


def test_rational_first_update_and_actual_momentum_separation():
    result = run_proximal_geometry()
    c = next(c for c in result['cases'] if c['id'] == 'lambda-2-opposite')
    for run in c['runs'].values():
        assert run['stages'][0]['z'] == pytest.approx([-13/9, -4/5])
        assert run['rows'][1]['x'] == pytest.approx([-61/45, -32/45])
    assert c['runs']['ista']['rows'][:3] == c['runs']['fista']['rows'][:3]
    assert c['runs']['ista']['rows'][3]['x'] != c['runs']['fista']['rows'][3]['x']
    stages = c['runs']['fista']['stages']
    t1 = (1+math.sqrt(5))/2
    t2 = (1+math.sqrt(1+4*t1*t1))/2
    beta = (t1-1)/t2
    expected = [x+beta*(x-y) for x, y in zip(stages[2]['x'], stages[1]['x'])]
    assert stages[2]['y'] == pytest.approx(expected)
    rows = c['runs']['fista']['rows']
    assert any(rows[k]['gap'] > rows[k-1]['gap']+1e-10 for k in range(1, len(rows)))


@pytest.mark.parametrize('steps', [0, 1, 61, True, float('nan'), '18'])
def test_invalid_budget_preflight(steps, monkeypatch):
    import chainbench.proximal_geometry as module
    monkeypatch.setattr(module, 'DiagonalLassoProblem', lambda *args: pytest.fail('allocated'))
    with pytest.raises(ValueError, match='steps'):
        run_proximal_geometry(steps)


def test_annotator_rejects_inconsistent_or_nonfinite_method_output(monkeypatch):
    import chainbench.proximal_geometry as module
    original = module.fista
    def broken(*args, **kwargs):
        trace = original(*args, **kwargs)
        trace.iterates[1][0] += .01
        return trace
    monkeypatch.setattr(module, 'fista', broken)
    with pytest.raises(FloatingPointError, match='annotation disagrees'):
        run_proximal_geometry()


def test_contour_levels_follow_composite_objective_even_across_kinks():
    for c in run_proximal_geometry(2)['cases'][::3]:
        for level in (.05, .8, 12.):
            points = _contour(c, level)
            x, y = points.T
            objective = ((x-1.4)**2+(3*y+2.4)**2)/2+c['lambda']*(np.abs(x)+np.abs(y))
            np.testing.assert_allclose(objective-c['f_star'], level, atol=5e-11)


@pytest.mark.parametrize('surface', [False, True])
def test_all_path_and_stage_marker_coordinates_match_actual_data(surface):
    for c in run_proximal_geometry(3)['cases']:
        root = ET.fromstring(proximal_svg(c, surface=surface))
        ns = {'s': 'http://www.w3.org/2000/svg'}
        def project(p):
            x, y = p
            gap = ((x-1.4)**2+(3*y+2.4)**2)/2+c['lambda']*(abs(x)+abs(y))-c['f_star']
            return (310+70*x+45*y, 380-15*x+24*y-5*gap) if surface else (310+100*x, 260-100*y)
        for method, run in c['runs'].items():
            path = root.find(f'.//s:polyline[@data-prox-path="{method}"]', ns)
            points = [[float(v) for v in p.split(',')] for p in path.attrib['points'].split()]
            np.testing.assert_allclose(points, [project(r['x']) for r in run['rows']], atol=.00051)
            for field in ('x', 'y', 'z', 'next_x'):
                marker = root.find(f'.//s:circle[@data-point="{field}"]', ns)
                frames = [[float(v) for v in p.split(',')] for p in marker.attrib['data-'+method].split('|')]
                np.testing.assert_allclose(frames, [project(s[field]) for s in run['stages']], atol=.00051)


def test_cli_html_json_and_overwrite_contract(tmp_path):
    path, raw = tmp_path/'proximal.html', tmp_path/'proximal.json'
    args = ['geometry', 'ista-fista', '--steps', '3']
    assert main(args+['--lang', 'ko', '--output', str(path)]) == 0
    assert main(args+['--format', 'json', '--output', str(raw)]) == 0
    html = path.read_text(encoding='utf8')
    assert smoke_module().extract_record(html) == json.loads(raw.read_text(encoding='utf8'))
    assert html.count('data-prox-case=') == 9
    assert 'unhalved squared loss' in html and 'not rounding' in html
    before = path.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(args+['--output', str(path)])
    assert error.value.code == 2 and path.read_bytes() == before
    assert main(args+['--force', '--output', str(path)]) == 0
    with pytest.raises(ValueError):
        proximal_html({'kind': 'wrong'})


def test_nonfinite_evidence_rejected():
    result = copy.deepcopy(run_proximal_geometry(2))
    result['cases'][0]['runs']['fista']['rows'][0]['gap'] = float('nan')
    with pytest.raises(ValueError):
        proximal_html(result)


def test_installed_scalar_validator_accepts_real_records(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    smoke_module().validate_proximal_geometry(run_proximal_geometry(6))


@pytest.mark.parametrize('field,value', [('y', [0., 0.]), ('z', [1., 1.]),
                                        ('next_x', [2., 2.]), ('momentum', 99.),
                                        ('threshold', float('nan')), ('zeroed', [True, True])])
def test_installed_validator_rejects_corrupt_stages(field, value):
    result = run_proximal_geometry(6)
    result['cases'][0]['runs']['fista']['stages'][2][field] = value
    with pytest.raises(RuntimeError):
        smoke_module().validate_proximal_geometry(result)
