import copy
import xml.etree.ElementTree as ET
from fractions import Fraction as F

import numpy as np
import pytest
from test_reproductions import smoke_module

from chainbench._conjugacy import add_metric_coordinates
from chainbench._conjugacy_views import direction_svg, metric_path_svg
from chainbench.reproductions import run_reproduction


@pytest.mark.parametrize('steps', [2, 12, 40])
def test_positive_square_root_energy_and_independent_displacement_products(steps):
    data = run_reproduction(steps)
    t = np.array(data['metric_geometry']['transform'])
    a = np.array([[3, 2], [2, 6]])
    np.testing.assert_allclose(t.T, t, atol=1e-14)
    np.testing.assert_allclose(t.T @ t, a, atol=1e-14)
    assert np.linalg.eigvalsh(t).min() > 0
    for case in data['cases']:
        for run in case['runs'].values():
            for k, row in enumerate(run['rows']):
                z = np.array(row['metric_coordinates'])
                assert np.max(np.abs(z)) < 14  # shared plot range includes every actual point
                np.testing.assert_allclose(z, t @ (np.array(row['x'])-[2, -2]), atol=1e-14)
                assert z @ z/2 == pytest.approx(row['gap'], rel=1e-13, abs=1e-28)
                pair = row['step_pair']
                if k < 2:
                    assert pair is None
                    continue
                u = np.array(run['rows'][k-1]['x'])-run['rows'][k-2]['x']
                v = np.array(row['x'])-run['rows'][k-1]['x']
                # Cholesky provides an independent square root; it need not be
                # symmetric to preserve the same energy inner product.
                chol = np.linalg.cholesky(a).T
                assert pair['a_dot'] == pytest.approx((chol @ u) @ (chol @ v), abs=1e-13)
                for key, value in [('previous', u), ('current', v),
                                   ('transformed_previous', t @ u), ('transformed_current', t @ v)]:
                    np.testing.assert_allclose(pair[key], value, atol=1e-14)
                assert pair['cos_euclidean'] == pytest.approx(u @ v/np.linalg.norm(u)/np.linalg.norm(v), abs=1e-13)
                assert pair['cos_a'] == pytest.approx((chol @ u) @ (chol @ v)/np.linalg.norm(chol @ u)/np.linalg.norm(chol @ v), abs=1e-13)
    smoke_module().validate_reproduction(data)


def test_first_two_rational_steps_make_different_inner_products_zero():
    case = run_reproduction()['cases'][0]
    u = [F(52, 25), F(104, 75)]
    cg_v = [F(48, 25), F(-104, 75)]
    cg = case['runs']['cg']['rows'][2]['step_pair']
    assert cg['euclidean_dot'] == pytest.approx(float(sum(x*y for x, y in zip(u, cg_v))))
    assert abs(cg['cos_euclidean']) > .2
    assert abs(cg['cos_a']) < 1e-14
    sd = case['runs']['sd']['rows'][2]['step_pair']
    assert abs(sd['cos_euclidean']) < 1e-14
    assert abs(sd['cos_a']) > .2


def test_no_second_step_or_zero_vector_does_not_become_a_right_angle():
    data = run_reproduction()
    case = next(c for c in data['cases'] if c['start'] == [3, 0])
    assert all(len(r['rows']) == 2 for r in case['runs'].values())
    assert all(row['step_pair'] is None for r in case['runs'].values() for row in r['rows'])
    rows = [{'x': [0., 0.]}, {'x': [0., 0.]}, {'x': [1., 0.]}]
    add_metric_coordinates(data['problem'], [{'runs': {'test': {'rows': rows}}}])
    assert rows[2]['step_pair']['cos_a'] is None
    assert rows[2]['step_pair']['cos_euclidean'] is None


def test_svg_paths_and_normalized_directions_come_from_actual_vectors():
    for case in run_reproduction()['cases']:
        path = ET.fromstring(metric_path_svg(case))
        for line in path.findall('.//{*}polyline[@data-method]'):
            points = [[float(x) for x in pair.split(',')] for pair in line.attrib['data-points'].split('|')]
            expected = [[280+15*r['metric_coordinates'][0], 256-15*r['metric_coordinates'][1]]
                        for r in case['runs'][line.attrib['data-method']]['rows']]
            np.testing.assert_allclose(points, expected, rtol=0, atol=.000501)
        directions = ET.fromstring(direction_svg(case))
        for line in directions.findall('.//{*}line[@data-direction]'):
            method, metric, name = line.attrib['data-direction'].split('-')
            pair = case['runs'][method]['rows'][-1]['step_pair']
            vec = np.array(pair[('transformed_' if metric == 'a' else '')+name]) if pair else np.zeros(2)
            origin = np.array([float(v) for v in line.attrib['data-origin'].split(',')])
            expected = origin+68*vec/np.linalg.norm(vec)*[1, -1] if np.linalg.norm(vec) else origin
            np.testing.assert_allclose([float(line.attrib['x2']), float(line.attrib['y2'])], expected, atol=.000501)


@pytest.mark.parametrize('field', ['metric_coordinates', 'previous', 'transformed_current', 'cos_a', 'a_dot'])
def test_installed_validator_rejects_false_geometry(field):
    data = copy.deepcopy(run_reproduction())
    row = data['cases'][0]['runs']['cg']['rows'][2]
    if field == 'metric_coordinates':
        row[field][0] += .1
    elif field in ('previous', 'transformed_current'):
        row['step_pair'][field][0] += .1
    else:
        row['step_pair'][field] += .1
    with pytest.raises(RuntimeError, match='metric geometry'):
        smoke_module().validate_reproduction(data)
