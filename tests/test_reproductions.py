import copy
import hashlib
import importlib.util
import json
import struct
import xml.etree.ElementTree as ET
from fractions import Fraction as F
from pathlib import Path

import numpy as np
import pytest

from chainbench.cli import main
from chainbench.reproduction_views import contour_svg, reproduction_html, surface_svg
from chainbench.reproductions import run_reproduction


def smoke_module():
    spec = importlib.util.spec_from_file_location(
        "smoke_workflows", Path(__file__).resolve().parents[1] / "scripts/smoke_workflows.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_published_setup_and_independent_rational_iterates():
    result = run_reproduction(5)
    p = result['problem']
    assert p['A'] == [[3, 2], [2, 6]]
    assert p['b'] == [2, -8]
    assert p['x_star'] == [2, -2]
    assert p['f_star'] == -10
    assert [p['mu'], p['L'], p['kappa']] == pytest.approx([2, 7, 3.5])
    case = result['cases'][0]
    # Independent scalar rational arithmetic, no method/problem helpers.
    x, y = F(-2), F(-2)
    for row in case['runs']['sd']['rows']:
        assert row['x'] == pytest.approx([float(x), float(y)], abs=2e-14)
        assert row['objective'] == pytest.approx(float((3*x*x + 4*x*y + 6*y*y)/2 - 2*x + 8*y))
        r, s = 2 - 3*x - 2*y, -8 - 2*x - 6*y
        alpha = (r*r + s*s) / (3*r*r + 4*r*s + 6*s*s)
        x, y = x + alpha*r, y + alpha*s
    cg = case['runs']['cg']
    np.testing.assert_allclose([r['x'] for r in cg['rows']],
                               [[-2, -2], [2/25, -46/75], [2, -2]], atol=2e-14)
    assert cg['termination'] == 'converged'
    assert cg['updates'] == 2
    assert case['runs']['sd']['termination'] == 'max_steps'
    # The second CG displacement is A-conjugate, not Euclidean orthogonal.
    d = np.diff([r['x'] for r in cg['rows']], axis=0)
    assert abs(d[0] @ np.array([[3, 2], [2, 6]]) @ d[1]) < 1e-12
    assert abs(d[0] @ d[1]) > .1


@pytest.mark.parametrize('steps', [2, 12, 40])
def test_complete_start_grid_metrics_hashes_and_real_termination(steps):
    result = run_reproduction(steps)
    assert result == run_reproduction(steps)
    assert len(result['cases']) == 10
    assert {tuple(c['start']) for c in result['cases'][1:]} == {
        (x, y) for x in [-3, 0, 3] for y in [-4, 0, 3]}
    assert len({c['input_sha256'] for c in result['cases']}) == 10
    for c in result['cases']:
        expected = hashlib.sha256(struct.pack('<9d', 3, 2, 2, 6, 2, -8, 0, *c['start'])).hexdigest()
        assert c['input_sha256'] == expected
        assert c['evidence_level'] == ('published-example-reproduction' if c['id'] == 'paper'
                                       else 'controlled-variation')
        for method, run in c['runs'].items():
            assert run['updates'] == len(run['rows']) - 1
            first_residual = run['rows'][0]['residual_norm']
            for k, row in enumerate(run['rows']):
                assert row['iteration'] == k
                x, y = row['x']
                gap = (3*(x-2)**2 + 4*(x-2)*(y+2) + 6*(y+2)**2)/2
                norm = np.hypot(2-3*x-2*y, -8-2*x-6*y)
                assert row['gap'] == pytest.approx(gap, rel=1e-13, abs=1e-25)
                assert row['energy_error'] == pytest.approx(np.sqrt(2*gap), abs=1e-13)
                assert row['residual_norm'] == pytest.approx(norm, abs=1e-13)
                if method == 'cg' and k:
                    assert row['energy_error'] <= c['cg_envelope'][k] * (1+1e-12)
            converged = run['rows'][-1]['residual_norm'] <= 1e-12 * first_residual
            assert (run['termination'] == 'converged') == converged
            if not converged:
                assert run['updates'] == steps
        assert 1 <= c['runs']['cg']['updates'] <= 2


@pytest.mark.parametrize('steps', [-1, 0, 1, 41, True, 3.5, float('nan'), '12'])
def test_invalid_budget_is_rejected_before_calculation(steps, monkeypatch):
    import chainbench.reproductions as module
    monkeypatch.setattr(module, 'QuadraticProblem', lambda *a: pytest.fail('invalid budget allocated'))
    with pytest.raises(ValueError, match='steps'):
        run_reproduction(steps)


def test_geometry_coordinates_are_projections_of_raw_iterates():
    result = run_reproduction()
    for case in result['cases']:
        for renderer, project in (
            (contour_svg, lambda x, y, z: (70 + (x+4)*42, 466 - (y+6)*42)),
            (surface_svg, lambda x, y, z: (280 + 21*(x-y-2), 449 - 10*(x+y+10) - 1.10*z)),
        ):
            root = ET.fromstring(renderer(result['problem'], case))
            lines = root.findall('.//{*}polyline[@data-method]')
            assert len(lines) == 2
            for line in lines:
                actual = [[float(v) for v in pair.split(',')] for pair in line.attrib['data-points'].split('|')]
                rows = case['runs'][line.attrib['data-method']]['rows']
                expected = [project(*row['x'], row['gap']) for row in rows]
                np.testing.assert_allclose(actual, expected, rtol=0, atol=.000501)
                assert line.attrib['points'] == line.attrib['data-points'].replace('|', ' ')


@pytest.mark.parametrize('lang', ['ko', 'en'])
def test_html_preserves_evidence_and_every_energy_sample(lang):
    result = run_reproduction()
    text = reproduction_html(result, lang)
    assert smoke_module().extract_record(text) == result
    assert text.count('data-repro-case=') == 10
    assert text.count('class="case"') == 9
    assert 'PUBLISHED EXAMPLE' in text
    assert 'not paper figures' in text
    assert 'no copied pixels' in text
    assert 'connect-src \'none\'' in text
    assert 'script src=' not in text
    assert '<html lang="' + lang + '">' in text
    # Chart metadata must carry the same observations, not just a matching appendix.
    import re
    charts = [s for s in re.findall(r'<svg[^>]*>.*?</svg>', text) if '<metadata>' in s]
    assert len(charts) == len(result['cases'])
    for case, svg in zip(result['cases'], charts):
        root = ET.fromstring(svg)
        metadata = root.find('{*}metadata')
        assert metadata is not None
        chart = json.loads(metadata.text)
        assert chart['series'][0]['y'] == [r['energy_error'] for r in case['runs']['sd']['rows']]
        assert chart['series'][1]['y'] == [r['energy_error'] for r in case['runs']['cg']['rows']]
        assert chart['series'][2]['y'] == case['cg_envelope'][1:]


def test_cli_exports_overwrite_protection_and_bad_budget(tmp_path):
    path = tmp_path/'paper.html'
    raw = tmp_path/'paper.json'
    args = ['reproduce', 'shewchuk-1994', '--steps', '6']
    assert main(args + ['--output', str(path)]) == 0
    assert main(args + ['--format', 'json', '--output', str(raw)]) == 0
    data = json.loads(raw.read_text(encoding='utf8'))
    assert smoke_module().extract_record(path.read_text(encoding='utf8')) == data
    before = path.read_bytes()
    with pytest.raises(SystemExit) as error:
        main(args + ['--output', str(path)])
    assert error.value.code == 2
    assert path.read_bytes() == before
    assert main(args + ['--force', '--output', str(path)]) == 0
    bad = tmp_path/'invalid.html'
    with pytest.raises(SystemExit) as error:
        main(['reproduce', 'shewchuk-1994', '--steps', '999', '--output', str(bad)])
    assert error.value.code == 2
    assert not bad.exists()


def test_nonfinite_computation_cannot_be_exported(monkeypatch):
    import chainbench.reproductions as module
    original = module.conjugate_gradient
    def broken(*args, **kwargs):
        trace = original(*args, **kwargs)
        trace.iterates[-1][0] = np.nan
        return trace
    monkeypatch.setattr(module, 'conjugate_gradient', broken)
    with pytest.raises((ValueError, FloatingPointError)):
        module.run_reproduction()


def test_installed_validator_checks_actual_output():
    smoke_module().validate_reproduction(run_reproduction(6))


@pytest.mark.parametrize('field,value', [('gap', 0.), ('residual_norm', float('nan')),
                                        ('energy_error', 123.), ('iteration', 8)])
def test_installed_validator_rejects_corrupted_metrics(field, value):
    result = copy.deepcopy(run_reproduction(6))
    result['cases'][0]['runs']['sd']['rows'][1][field] = value
    with pytest.raises(RuntimeError):
        smoke_module().validate_reproduction(result)


def test_matching_method_colors_in_geometry_and_energy_chart():
    text = reproduction_html(run_reproduction())
    for color in ('#bc541d', '#176b91'):
        assert text.count('stroke="' + color + '"') > 20


@pytest.mark.parametrize('colors', [(), ('red',), ('#123456',), ('#123456', '#123456', 'url(x)')])
def test_chart_rejects_invalid_color_styles(colors):
    from chainbench.visuals import ChartSpec, LineSeries, render_line_chart
    spec = ChartSpec('x', 'k', 'e', (LineSeries('a', (0, 1), (1., .5)),
                                   LineSeries('b', (0, 1), (1., .2))))
    with pytest.raises(ValueError, match='colors'):
        render_line_chart(spec, colors=colors)
