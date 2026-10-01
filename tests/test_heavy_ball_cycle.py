import copy
import importlib.util
import json
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from chainbench.cli import main
from chainbench.heavy_ball_cycle import CYCLE, PiecewiseCycleProblem, run_heavy_ball_cycle
from chainbench.heavy_ball_views import cycle_svg, heavy_ball_cycle_html


def validator():
    spec = importlib.util.spec_from_file_location('smoke_heavy_ball_cycle',
        Path(__file__).resolve().parents[1]/'scripts/smoke_heavy_ball_cycle.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_heavy_ball_cycle


@pytest.mark.parametrize('steps', [1, 50, 500])
def test_every_counterexample_row_matches_independent_scalar_recurrence(steps):
    result = run_heavy_ball_cycle(steps)
    validator()(result)
    assert result == run_heavy_ball_cycle(steps)


def test_piece_joins_and_global_secant_bounds():
    p = PiecewiseCycleProblem()
    assert p.value([1]) == 12.5 and p.value([2]) == 38
    assert p.grad([1])[0] == 25 and p.grad([2])[0] == 26
    for x in [-4., 0., .5, 1., 1.5, 2., 4.]:
        derivative = (p.value([x+1e-5])-p.value([x-1e-5]))/2e-5
        assert derivative == pytest.approx(p.grad([x])[0], abs=7e-5)
        for y in [-5., -.1, .9, 1.1, 1.9, 2.1, 5.]:
            slope = (p.grad([y])[0]-p.grad([x])[0])/(y-x)
            assert 1-1e-12 <= slope <= 25+1e-12
            assert p.value([y]) >= p.value([x])+p.grad([x])[0]*(y-x)+.5*(y-x)**2-1e-12


def test_rational_initial_updates_and_source_cycle_equations():
    def gradient(x):
        return 25*x if x < 1 else x+24 if x < 2 else 25*x-24
    def update(x, previous):
        return Fraction(13, 9)*x-Fraction(4, 9)*previous-gradient(x)/9
    current = previous = Fraction(33, 10)
    expected = [current]
    for _ in range(12):
        previous, current = current, update(current, previous)
        expected.append(current)
    rows = run_heavy_ball_cycle(12)['cases'][0]['runs']['heavy-ball']['rows']
    np.testing.assert_allclose([r['x'] for r in rows], [float(v) for v in expected], atol=2e-13)
    p, q, r = [Fraction(n, 1225) for n in (792, -2208, 2592)]
    assert update(p, r) == q and update(q, p) == r and update(r, q) == p
    assert p < 1 and q < 1 and r > 2
    assert (float(p), float(q), float(r)) == CYCLE


def test_periodic_tail_is_not_stationary_and_small_period_defect_is_not_enough():
    runs = run_heavy_ball_cycle()['cases'][0]['runs']
    tail = runs['heavy-ball']['rows'][-3:]
    assert max(row['distance_to_cycle_set'] for row in tail) < 1e-6
    assert min(row['stationarity'] for row in tail) > 15
    gd = runs['gd']['rows'][-1]
    assert gd['stationarity'] == 0 and gd['three_step_difference'] == 0
    assert gd['distance_to_cycle_set'] > .6


@pytest.mark.parametrize('steps', [0, -1, 501, True, 2.5, float('nan')])
def test_invalid_counterexample_budget(steps):
    with pytest.raises(ValueError, match='steps'):
        run_heavy_ball_cycle(steps)


@pytest.mark.parametrize('key,value', [('x', 0.), ('objective', -1.), ('previous', 99.),
                                     ('gradient_step', None), ('three_step_difference', float('nan'))])
def test_counterexample_validator_rejects_corrupted_observations(key, value):
    result = copy.deepcopy(run_heavy_ball_cycle(10))
    result['cases'][0]['runs']['heavy-ball']['rows'][5][key] = value
    with pytest.raises(RuntimeError):
        validator()(result)


@pytest.mark.parametrize('view', ['objective', 'phase', 'history'])
def test_all_signed_geometry_points_preserve_the_actual_states(view):
    result = run_heavy_ball_cycle(50)
    ns = {'s': 'http://www.w3.org/2000/svg'}
    for case in result['cases']:
        svg = ET.fromstring(cycle_svg(case, result['landscape'], view=view))
        axes = json.loads(svg.attrib['data-axes'])
        assert axes['ymin'] < 0 if view != 'objective' else axes['ymin'] == 0
        if view == 'phase':
            assert axes['xmax']-axes['xmin'] == axes['ymax']-axes['ymin']
            assert axes['width'] == axes['height']
        for name, run in case['runs'].items():
            node = svg.find(f'.//s:polyline[@data-cycle-history="{name}"]', ns)
            actual = [[float(v) for v in point.split(',')] for point in node.attrib['points'].split()]
            expected = []
            for row in run['rows']:
                x = row['iteration'] if view == 'history' else row['previous'] if view == 'phase' else row['x']
                y = row['objective'] if view == 'objective' else row['x']
                expected.append([axes['left']+axes['width']*(x-axes['xmin'])/(axes['xmax']-axes['xmin']),
                                 axes['top']+axes['height']-axes['height']*(y-axes['ymin'])/(axes['ymax']-axes['ymin'])])
            np.testing.assert_allclose(actual, expected, atol=.00051)


def test_counterexample_cli_defaults_evidence_and_overwrite(tmp_path):
    html, raw = tmp_path/'cycle.html', tmp_path/'cycle.json'
    assert main(['reproduce', 'lessard-2016', '--output', str(html)]) == 0
    assert main(['reproduce', 'lessard-2016', '--format', 'json', '--output', str(raw)]) == 0
    result = json.loads(raw.read_text(encoding='utf8'))
    assert result['parameters']['steps'] == 50
    validator()(result)
    assert html.read_text(encoding='utf8') == heavy_ball_cycle_html(result)
    original = html.read_bytes()
    with pytest.raises(SystemExit):
        main(['reproduce', 'lessard-2016', '--output', str(html)])
    assert html.read_bytes() == original
    assert main(['reproduce', 'lessard-2016', '--output', str(html), '--force']) == 0
    bad = tmp_path/'bad.html'
    with pytest.raises(SystemExit):
        main(['reproduce', 'lessard-2016', '--steps', '501', '--output', str(bad)])
    assert not bad.exists()
