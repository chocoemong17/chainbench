import copy
import importlib.util
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from chainbench._fw_segment import segment_profile
from chainbench._fw_segment_views import profile_svg
from chainbench.problems import SimplexQuadraticProblem
from chainbench.simplex_geometry import run_simplex_geometry, simplex_html, simplex_svg


@pytest.fixture(scope="module")
def checker():
    spec = importlib.util.spec_from_file_location(
        "fw_segment_checker", Path(__file__).resolve().parents[1]/"scripts/smoke_workflows.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_fw_segments


@pytest.fixture(scope="module")
def record():
    return run_simplex_geometry(3)


def test_hand_calculated_barycenter_and_near_vertex_steps(record):
    case = next(c for c in record["cases"] if c["id"] == "interior-center")
    p = case["rows"][0]["segment"]
    assert p["minimum_gamma"] == pytest.approx(.25)
    assert p["minimum_value"] == pytest.approx(1/400)
    assert p["slope"] == pytest.approx(-1/6)
    assert p["direction_norm_squared"] == pytest.approx(2/3)
    assert p["equal_value_gamma"] == pytest.approx(.5)
    np.testing.assert_allclose(p["minimum_point"], [.25, .25, .5])
    assert p["objective"][p["scheduled_index"]] == case["rows"][1]["gap"]
    case = next(c for c in record["cases"] if c["id"] == "near-vertex-e1")
    p = case["rows"][0]["segment"]
    assert p["minimum_gamma"] == pytest.approx(.13)
    assert p["minimum_value"] == pytest.approx(.0027)
    assert p["equal_value_gamma"] == pytest.approx(.26)


def test_zero_direction_and_boundary_minimum_are_explicit():
    p = segment_profile([1,0,0], [1,0,0], [1,0,0], .5, [1,0,0])
    assert p["minimum_gamma"] == 0 and p["equal_value_gamma"] is None
    assert p["minimum_value"] == 0
    assert set(p["objective"]) == {0}
    p = segment_profile([1,0,0], [0,1,0], [1,0,0], 1, [1,0,0])
    assert p["minimum_gamma"] == 1 and p["minimum_value"] == 0


@pytest.mark.parametrize("following", [[.1,.9,0], [float("nan"),0,1], [0,1]])
def test_missing_or_incorrect_actual_next_point_is_rejected(following):
    with pytest.raises(ValueError):
        segment_profile([.2,.3,.5], [1,0,0], [0,0,1], 1, following)


def test_all_stages_include_actual_step_and_final_row_has_no_invented_update(record, checker):
    checker(record, required=True)
    for case in record["cases"]:
        assert case["rows"][-1]["segment"] is None
        for row, nxt in zip(case["rows"], case["rows"][1:]):
            p = row["segment"]
            assert p["parameter"][p["scheduled_index"]] == row["gamma"]
            assert p["points"][p["scheduled_index"]] == nxt["x"]
            assert p["objective"][p["scheduled_index"]] == nxt["gap"]


@pytest.mark.parametrize("current,vertex,gamma", [
    ([0, 0, 1], [0, 1, 0], 1),
    ([0, 1, 0], [0, 1, 0], 0),  # scheduled point is also the segment minimum
])
def test_segment_retains_the_actual_next_value_including_roundoff(current, vertex, gamma):
    # At e2, half(.2**2 + .7**2 + .5**2) = .39.
    stored = math.nextafter(.39, math.inf)
    p = segment_profile([.2, .3, .5], current, vertex, gamma, [0, 1, 0],
                        following_value=stored)
    assert p['objective'][p['scheduled_index']] == stored
    assert p['minimum_value'] == p['objective'][p['minimum_index']]
    assert p['quadratic_roundoff_inf'] == max(
        abs(a-b) for a, b in zip(p['objective'], p['quadratic']))


def test_geometry_passes_stored_objectives_to_every_segment(monkeypatch, checker):
    original = SimplexQuadraticProblem.gap
    monkeypatch.setattr(SimplexQuadraticProblem, 'gap',
                        lambda self, x: math.nextafter(original(self, x), math.inf))
    result = run_simplex_geometry(3)
    checker(result, required=True)
    for case in result['cases']:
        for row, nxt in zip(case['rows'], case['rows'][1:]):
            p = row['segment']
            assert p['objective'][p['scheduled_index']] == nxt['gap']


@pytest.mark.parametrize("value", [.4, -.01, float('nan'), float('inf')])
def test_segment_rejects_incorrect_or_nonfinite_recorded_objective(value):
    with pytest.raises(ValueError, match='objective'):
        segment_profile([.2, .3, .5], [0, 0, 1], [1, 0, 0], 1, [1, 0, 0],
                        following_value=value)


@pytest.mark.parametrize("path,value", [
    (("minimum_gamma",), .7), (("minimum_value",), .7),
    (("direction_norm_squared",), 0), (("slope",), .2),
    (("equal_value_gamma",), None), (("scheduled_index",), 0),
    (("minimum_index",), 0), (("parameter",), [0,1]),
    (("points",0,0), .8), (("objective",1), .9),
    (("affine",1), float("nan")), (("quadratic",1), .4),
    (("minimum_point",0), .8), (("quadratic_roundoff_inf",), 1e-12),
])
def test_corrupted_segment_data_fails_independent_decimal_check(record, checker, path, value):
    bad = copy.deepcopy(record)
    node = bad["cases"][0]["rows"][0]["segment"]
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(RuntimeError):
        checker(bad)


def test_legacy_is_accepted_only_without_partial_segment_evidence(record, checker):
    old = copy.deepcopy(record)
    del old["segment_geometry"]
    with pytest.raises(RuntimeError):
        checker(old)
    for case in old["cases"]:
        for row in case["rows"]:
            del row["segment"]
    checker(old)
    with pytest.raises(RuntimeError):
        checker(old, required=True)
    assert '<polyline data-segment-ray=' not in simplex_html(old)
    bad = copy.deepcopy(record)
    bad["cases"][0]["rows"][-1]["segment"] = {}
    with pytest.raises(RuntimeError):
        checker(bad)
    bad = copy.deepcopy(record)
    bad["segment_geometry"]["source"]["locator"] = "Algorithm 1"
    with pytest.raises(RuntimeError):
        checker(bad)


def assert_xy(actual, expected):
    assert len(actual) == len(expected)
    assert all(math.isclose(a,b,rel_tol=0,abs_tol=5.1e-6)
               for xy,uv in zip(actual,expected) for a,b in zip(xy,uv))


def test_all_scalar_curve_and_surface_ray_frames_match_raw_points(record):
    for case in record["cases"]:
        profiles = [r["segment"] for r in case["rows"][:-1]]
        low = min(min(p["affine"]) for p in profiles)
        high = max(max(p["objective"]) for p in profiles)
        span = high-low or 1
        low, high = low-.06*span, high+.06*span
        svg = ET.fromstring(profile_svg(case))
        for element in svg.iter():
            if "data-segment-curve" not in element.attrib:
                continue
            key = element.attrib["data-segment-curve"]
            frames = element.attrib["data-segment-frames"].split("|")
            assert len(frames) == len(profiles)
            for frame, p in zip(frames,profiles):
                actual = [[float(v) for v in pair.split(",")] for pair in frame.split()]
                expected = [(86+460*g,302-210*(v-low)/(high-low))
                            for g,v in zip(p["parameter"],p[key])]
                assert_xy(actual,expected)
        svg = ET.fromstring(simplex_svg(case,surface=True))
        ray = next(e for e in svg.iter() if "data-segment-ray" in e.attrib)
        for frame,p in zip(ray.attrib["data-segment-frames"].split("|"),profiles):
            actual = [[float(v) for v in pair.split(",")] for pair in frame.split()]
            expected = []
            for x,value in zip(p["points"],p["objective"]):
                u,v = x[1]+.5*x[2],math.sqrt(3)/2*x[2]
                expected.append((90+380*u-80*v,435-170*v-240*value))
            assert_xy(actual,expected)


def test_native_tables_and_first_increase_shortcut_are_retained(record):
    html = simplex_html(record)
    assert html.count('<tr data-segment-row=') == 12*3
    assert html.count('<polyline data-segment-ray=') == 12
    assert 'First objective increase (&gt;10⁻¹²)' in html or 'First objective increase (>10⁻¹²)' in html
    assert 'not a comparison of two complete algorithms' in html
