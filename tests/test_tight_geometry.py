import copy
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from chainbench.case_studies import gd_tight_case
from chainbench.tight_views import _point, center_svg, function_svg


def validator():
    spec = importlib.util.spec_from_file_location('tight_smoke',
        Path(__file__).resolve().parents[1]/'scripts/smoke_workflows.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_tight_geometry


@pytest.mark.parametrize('N,L,R,h', [(1,1,1,1), (20,1,1,1), (500,1,1,1),
    (500,1e6,1e-6,1e-4), (500,1e-6,1e6,1), (1,1e-6,1e-6,1e-4)])
def test_geometry_resolves_actual_scaled_function_and_all_stored_iterates(N,L,R,h):
    result = gd_tight_case(N,L,R,h)
    a, geometry = result['transition'], result['geometry']
    values = result['charts']['function']['series'][0]
    x,y = np.array(values['x']),np.array(values['y'])
    assert np.all(np.diff(x)>0)
    assert np.count_nonzero(np.abs(x)<=a) >= 81
    assert all(join in x for join in (-a,0.,a))
    np.testing.assert_allclose(y,L*np.where(np.abs(x)<=a,.5*x*x,a*np.abs(x)-.5*a*a),rtol=1e-14)
    u = np.array(geometry['normalized_x'])
    np.testing.assert_allclose(geometry['normalized_value'],np.where(np.abs(u)<=1,.5*u*u,np.abs(u)-.5),rtol=1e-13)
    for sign,join in zip((-1,1),geometry['transition_points']):
        assert join['gradient'] == sign*L*a
        assert join['value'] == pytest.approx(L*a*a/2,rel=1e-14,abs=0.)
        # Both analytic one-sided derivatives equal the recorded join gradient.
        assert L*join['x'] == sign*L*a
    xml = ET.fromstring(function_svg(result))
    path = next(el for el in xml.iter() if 'data-tight-path' in el.attrib)
    points = np.array([[float(v) for v in pair.split(',')] for pair in path.attrib['points'].split()])
    expected = [_point(result,r['x'],r['gap']) for r in result['rows']]
    np.testing.assert_allclose(points,expected,atol=.00051,rtol=0.)
    assert len(points)==N+1
    zoom = ET.fromstring(center_svg(result))
    line = next(el for el in zoom.iter() if 'data-tight-center' in el.attrib)
    points = np.array([[float(v) for v in pair.split(',')] for pair in line.attrib['points'].split()])
    np.testing.assert_allclose(points[:,0],70+520*(u+2)/4,atol=.00051,rtol=0.)
    np.testing.assert_allclose(points[:,1],330-240*np.array(geometry['normalized_value'])/1.5,atol=.00051,rtol=0.)
    validator()(result)


def test_horizon_changes_the_function_but_not_the_normalized_centre():
    short,long = gd_tight_case(1),gd_tight_case(500)
    assert short['transition'] > long['transition']
    np.testing.assert_allclose(short['geometry']['normalized_value'],long['geometry']['normalized_value'],rtol=1e-13)
    assert short['rows'][0]['gap'] != long['rows'][0]['gap']
    assert len(long['rows'])==501


@pytest.mark.parametrize('field', ['missing','centre','scale','sample','trajectory','join','rows'])
def test_installed_geometry_validation_rejects_missing_or_corrupted_evidence(field):
    data = copy.deepcopy(gd_tight_case())
    if field == 'missing':
        data.pop('geometry')
    elif field == 'centre':
        data['charts']['function']['series'][0]['x'] = [-1.,0.,1.]
    elif field == 'scale':
        data['geometry']['value_scale'] *= 2
    elif field == 'sample':
        data['geometry']['normalized_value'][50] += 1
    elif field == 'join':
        data['geometry']['transition_points'][0]['gradient'] *= 2
    elif field == 'rows':
        data['rows'].pop(1)
    else:
        data['rows'][2]['x'] += .1
    with pytest.raises(RuntimeError):
        validator()(data)
