import copy
import json
import re
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from _numeric_records import assert_recomputed_record
from test_reproductions import smoke_module

from chainbench.landscape import (
    COLORS,
    METHODS,
    contour_svg,
    landscape_html,
    run_landscape,
    surface_svg,
)


@pytest.mark.parametrize('condition,angle,steps', [(1.01, -85., 2), (20., 32., 18), (10000., 85., 80)])
@pytest.mark.parametrize('methods', [METHODS, ('proximal-point', 'cg', 'smooth-fista'), ('heavy-ball',)])
def test_actual_context_metrics_and_independent_scalar_recurrences(condition, angle, steps, methods):
    result = run_landscape(condition, angle, steps, methods)
    smoke_module().validate_landscape(result)
    assert result['methods'] == list(methods)
    assert_recomputed_record(result, run_landscape(condition, angle, steps, methods))
    p = result['problem']
    assert p['b'] == pytest.approx(np.array(p['Q']) @ p['x_star'])
    assert p['actual_condition_number'] == pytest.approx(condition)
    assert set(result['sources']) == set(methods)
    assert set(result['environment']) == {'chainbench', 'python', 'numpy', 'os'}


@pytest.mark.parametrize('width,height', [(720, 500), (430, 330)])
def test_equal_coordinate_scales_and_both_projection_paths(width, height):
    data = run_landscape(10000, -85, 80)
    for renderer in (contour_svg, surface_svg):
        root = ET.fromstring(renderer(data, width, height))
        meta = json.loads(root.find('{*}metadata').text)
        assert meta['input_sha256'] == data['input_sha256']
        assert meta['problem'] == data['problem']
        a = meta['axes']
        if meta['view'] == 'contour':
            assert (a['xmax']-a['xmin'])/a['width'] == pytest.approx((a['ymax']-a['ymin'])/a['height'])
            def project(x, y, z):
                return [a['left']+(x-a['xmin'])/a['units_per_pixel'],
                        a['top']+(a['ymax']-y)/a['units_per_pixel']]
        else:
            def project(x, y, z):
                xn, yn = 2*(x-a['xmin'])/(a['xmax']-a['xmin'])-1, 2*(y-a['ymin'])/(a['ymax']-a['ymin'])-1
                return [a['cx']+a['scale']*(xn-yn), a['cy']+a['scale']*(.48*(xn+yn)-1.55*z/a['zmax'])]
        for line in root.findall('.//{*}polyline[@data-trajectory-line]'):
            name = line.attrib['data-method']
            assert line.attrib['stroke'] == COLORS[name]
            points = np.array([[float(v) for v in p.split(',')] for p in line.attrib['points'].split(' ')])
            expected = [project(*x, z) for x, z in zip(data['traces'][name], data['gaps'][name])]
            np.testing.assert_allclose(points, expected, rtol=0, atol=.00501)
            assert np.all(points[:, 0] >= 0) and np.all(points[:, 0] <= width)
            assert np.all(points[:, 1] >= 0) and np.all(points[:, 1] <= height)


@pytest.mark.parametrize('methods', [METHODS, ('cg', 'heavy-ball'), ('smooth-fista', 'gd', 'proximal-point')])
def test_subset_order_does_not_change_method_colors_or_chart_samples(methods):
    data = run_landscape(methods=methods)
    text = landscape_html(data)
    chart = ET.fromstring(re.findall(r'<svg[^>]*>.*?</svg>', text)[-1])
    meta = json.loads(chart.find('{*}metadata').text)
    assert [s['label'] for s in meta['series']] == list(methods)
    for method, series in zip(methods, meta['series']):
        assert series['y'] == data['gaps'][method]
        assert COLORS[method] in ET.tostring(chart, encoding='unicode')
    # The renderer takes the ordered palette, not just unrelated matching text.
    lines = [el for el in chart.findall('.//{*}polyline') if el.attrib.get('stroke') in COLORS.values()]
    assert [el.attrib['stroke'] for el in lines] == [COLORS[m] for m in methods]
    assert smoke_module().extract_record(text) == data


@pytest.mark.parametrize('corrupt', ['hash', 'input', 'gap', 'residual', 'parameter', 'termination'])
def test_installed_validator_rejects_detached_evidence(corrupt):
    data = copy.deepcopy(run_landscape())
    if corrupt == 'hash':
        data['input_sha256'] = '0'*64
    elif corrupt == 'input':
        data['problem']['Q'][0][1] += .1
    elif corrupt == 'gap':
        data['gaps']['gd'][1] += 1.
    elif corrupt == 'residual':
        data['runs']['cg']['residual_norms'][1] += .1
    elif corrupt == 'parameter':
        data['method_parameters']['heavy-ball']['beta'] = 0.
    else:
        data['runs']['gd']['termination'] = 'converged'
    with pytest.raises(RuntimeError, match='landscape evidence'):
        smoke_module().validate_landscape(data)
