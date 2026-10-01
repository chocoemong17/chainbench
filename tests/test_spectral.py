import copy
import importlib.util
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from chainbench._spectral_views import polynomial_svg
from chainbench.reproductions import run_reproduction


@pytest.fixture(scope='module')
def record():
    return run_reproduction()


def validator():
    spec = importlib.util.spec_from_file_location('spectral_smoke',
        Path(__file__).resolve().parents[1]/'scripts/smoke_spectral.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.validate_spectral


def test_explicit_basis_diagonalizes_the_published_problem(record):
    basis = np.array(record['spectral_geometry']['eigenvectors'])
    np.testing.assert_allclose(basis @ basis.T, np.eye(2), atol=2e-16)
    np.testing.assert_allclose(basis @ np.array(record['problem']['A']) @ basis.T,
                               np.diag([2, 7]), atol=1e-15)
    for case in record['cases']:
        for row in case['runs']['cg']['rows']:
            coeff = np.array(row['spectral']['coefficients'])
            np.testing.assert_allclose(basis.T @ coeff, np.array(row['x'])-[2, -2], atol=2e-15)
            assert sum(row['spectral']['energy_squared']) == pytest.approx(2*row['gap'], rel=2e-13, abs=2e-28)


def test_actual_weighted_minimum_differs_from_finite_spectrum_minimax(record):
    case = record['cases'][0]
    row = case['runs']['cg']['rows'][1]['spectral']
    assert row['component_ratios'] == pytest.approx([49/75, -16/75], abs=2e-15)
    assert case['spectral_initial']['energy_squared'] == pytest.approx([128/5, 112/5])
    assert row['energy_ratio']**2 == pytest.approx(56/225, abs=2e-15)
    assert row['component_ratios'][0] > 5/9
    assert row['energy_ratio'] < 5/9
    # Direct scalar line search: the actual alpha is the minimizer of this quadratic.
    def energy(alpha):
        return (128/5)*(1-2*alpha)**2+(112/5)*(1-7*alpha)**2
    assert sum(row['energy_squared']) == pytest.approx(energy(13/75))
    assert energy(13/75) < energy(2/9)


def test_source_polynomials_interpolate_eigenvalues_not_the_whole_interval(record):
    ref = record['spectral_geometry']['polynomials'][2]
    assert ref['finite_at_eigenvalues'] == [0, 0]
    midpoint = ref['abscissae'].index(4.5)
    assert ref['finite_spectrum'][midpoint] == pytest.approx(-25/56)
    assert ref['interval'][midpoint] == pytest.approx(-25/137)
    assert ref['interval_at_eigenvalues'] == pytest.approx([25/137]*2)
    for p in record['spectral_geometry']['polynomials']:
        assert p['finite_spectrum'][0] == p['interval'][0] == 1


def test_missing_initial_mode_remains_undefined_and_does_not_invent_iterations(record):
    case = next(c for c in record['cases'] if c['start'] == [3, 0])
    assert case['spectral_initial']['coefficients'][0] == 0
    assert case['runs']['cg']['updates'] == 1
    for row in case['runs']['cg']['rows']:
        assert row['spectral']['component_ratios'][0] is None
        assert math.isfinite(row['spectral']['energy_squared'][0])


@pytest.mark.parametrize('steps', [2, 12, 40])
def test_independent_spectral_validation(steps):
    validator()(run_reproduction(steps))


@pytest.mark.parametrize('fault', ['coefficient', 'ratio', 'energy', 'weight', 'curve', 'factor', 'null', 'source'])
def test_independent_validator_rejects_spectral_corruption(record, fault):
    data = copy.deepcopy(record)
    row = data['cases'][0]['runs']['cg']['rows'][1]['spectral']
    if fault in ('coefficient', 'ratio', 'energy'):
        key = {'coefficient':'coefficients', 'ratio':'component_ratios', 'energy':'energy_squared'}[fault]
        row[key][0] += .01
    elif fault == 'weight':
        data['cases'][0]['spectral_initial']['energy_weights'][0] = 1
    elif fault == 'curve':
        data['spectral_geometry']['polynomials'][2]['finite_spectrum'][90] = 0
    elif fault == 'factor':
        data['spectral_geometry']['polynomials'][2]['interval_envelope_factor'] = 0
    elif fault == 'source':
        data['source']['envelope'] = 'PDF page 43'
    else:
        case = next(c for c in data['cases'] if c['start'] == [3, 0])
        case['runs']['cg']['rows'][0]['spectral']['component_ratios'][0] = 0
    with pytest.raises(RuntimeError, match='spectral'):
        validator()(data)


def test_static_svg_keeps_all_reference_curves_and_only_actual_mode_markers(record):
    for case in record['cases']:
        root = ET.fromstring(polynomial_svg(case, record['spectral_geometry']))
        groups = [e for e in root.iter() if 'data-spectral-degree' in e.attrib]
        assert len(groups) == 3
        active = [e for e in groups if 'hidden' not in e.attrib]
        assert int(active[0].get('data-spectral-degree')) == case['runs']['cg']['updates']
        markers = [e for e in root.iter() if 'data-spectral-marker' in e.attrib]
        assert len(markers) == 2
        for j, marker in enumerate(markers):
            ratio = case['runs']['cg']['rows'][-1]['spectral']['component_ratios'][j]
            assert marker.get('visibility') == ('hidden' if ratio is None else 'visible')
            if ratio is not None:
                assert float(marker.get('cy')) == pytest.approx(186.25-85*ratio, abs=.00051)
