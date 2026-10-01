import json
import math
import xml.etree.ElementTree as ET
from decimal import Decimal, localcontext

import pytest

from chainbench._admm_subproblems import model_values, quadratic_svg, shrink_bound, shrink_svg
from chainbench.admm_geometry import run_admm_geometry


@pytest.fixture(scope='module')
def result():
    return run_admm_geometry(160)


def quadratic_cost(ip,w,a):
    D = lambda v:Decimal(str(v))  # noqa: E731
    return (sum((sum(D(Aij)*D(wj) for Aij,wj in zip(Ai,w))-D(bi))**2
                for Ai,bi in zip(ip['A'],ip['b']))
            +D(ip['rho'])*sum((D(wi)-D(ai))**2 for wi,ai in zip(w,a)))/2


def test_every_model_readout_uses_previous_memory_and_the_actual_quadratic(result):
    before = json.dumps(result)
    with localcontext() as ctx:
        ctx.prec = 60
        for case in result['cases']:
            assert all(v is None for v in model_values(case,0).values())
            for k,row in enumerate(case['rows'][1:],1):
                old,ip = case['rows'][k-1],case['inputs']
                values = model_values(case,k)
                a = [z-u for z,u in zip(old['z'],old['u'])]
                assert values['old_z']==old['z'] and values['old_u']==old['u']
                assert values['target']==a
                assert values['v']==[x+u for x,u in zip(row['x'],old['u'])]
                assert values['new_z']==row['z']
                # Subtract independently evaluated 60-digit objectives. The
                # plotted centered identity must agree despite a distant target.
                gap = quadratic_cost(ip,old['z'],a)-quadratic_cost(ip,row['x'],a)
                assert values['old_z_gap']==pytest.approx(float(gap),abs=3e-12,rel=3e-11)
                assert values['old_z_gap']>=0
                tau = values['tau']
                for v,z in zip(values['v'],row['z']):
                    slope = ip['rho']*(v-z)
                    if z:
                        assert slope==pytest.approx(math.copysign(ip['lambda'],z),abs=3e-13)
                        assert abs(v-z)==pytest.approx(tau,abs=3e-13)
                    else:
                        assert abs(slope)<=ip['lambda']+3e-13
                        assert abs(v)<=tau+3e-13
    assert json.dumps(result)==before


def test_actual_contour_vertices_are_levels_of_the_selected_quadratic(result):
    with localcontext() as ctx:
        ctx.prec = 60
        for case in result['cases']:
            svg = ET.fromstring(quadratic_svg(case,2.5))
            center = next(n for n in svg.iter() if 'data-admm-model-center' in n.attrib)
            row = case['rows'][1]
            assert center.attrib['transform']==f'translate({330+72*row["x"][0]:.3f} {245-72*row["x"][1]:.3f})'
            contours = [n for n in center if 'data-admm-model-level' in n.attrib]
            assert [float(n.attrib['data-admm-model-level']) for n in contours]==[.1,.5,2.,10.]
            minimum = quadratic_cost(case['inputs'],row['x'],row['x_target'])
            for contour in contours:
                offsets = json.loads(contour.attrib['data-offsets'])
                pixels = [tuple(map(float,p.split(','))) for p in contour.attrib['points'].split()]
                assert len(offsets)==len(pixels)==129
                for d,pixel in zip(offsets,pixels):
                    w = [x+v for x,v in zip(row['x'],d)]
                    value = quadratic_cost(case['inputs'],w,row['x_target'])-minimum
                    assert float(value)==pytest.approx(float(contour.attrib['data-admm-model-level']),abs=2e-12)
                    assert pixel==pytest.approx((72*d[0],-72*d[1]),abs=.00051)


def test_shrink_axes_keep_extreme_memory_and_thresholds_in_view(result):
    extreme = 0
    for case in result['cases']:
        bound = shrink_bound(case)
        svg = ET.fromstring(shrink_svg(case))
        assert float(svg.attrib['data-bound'])==bound
        tau = case['inputs']['lambda']/case['inputs']['rho']
        assert float(svg.attrib['data-tau'])==tau
        assert 0<tau<bound
        assert all(abs(v)<bound for row in case['rows'][1:]
                   for name in ('shrink_input','z') for v in row[name])
        extreme = max(extreme,*[abs(v) for row in case['rows'][1:] for v in row['shrink_input']])
        for element in svg.iter():
            if 'data-admm-shrink-point' in element.attrib:
                name,index = element.attrib['data-admm-shrink-point'].split(':')
                value = case['rows'][1]['shrink_input' if name=='v' else 'z'][int(index)]
                assert float(element.attrib['cx'])==pytest.approx(330+250*value/bound,abs=.00051)
                assert 80<float(element.attrib['cx'])<580
    assert extreme>50  # The old primal window would lose real shrinkage inputs.


def test_model_window_cannot_silently_drop_recorded_points(result):
    with pytest.raises(ValueError,match='omits'):
        quadratic_svg(result['cases'][0],.01)
