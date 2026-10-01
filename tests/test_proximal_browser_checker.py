"""Hand-calculated SVG fixture and corruptions for the browser checker's oracle."""

import copy
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def checker():
    spec = importlib.util.spec_from_file_location(
        "proximal_browser_checker",
        Path(__file__).resolve().parents[1] / "scripts/check_proximal_browser.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fixture():
    model = {
        "parameter": [0, 1], "model_gap": [1, .5], "objective_gap": [1, .2],
        "previous_gap": 1, "anchor_gap": 1, "model_next_gap": .5, "next_gap": .2,
        "zero_step": False,
    }
    previous = {"normalized": [0, 0], "lower_bound": -2}
    following = {
        "normalized": [.5, -.25], "lower_bound": -1, "primal_gap": .2,
        "dual_deficit": .8, "suboptimality_upper_bound": 1,
    }
    case = {
        "runs": {method: {"stages": [{"upper_model": model}]} for method in ("ista", "fista")},
        "dual_geometry": {
            "surface_minimum": -2, "surface_maximum": 0,
            "runs": {method: [previous, following] for method in ("ista", "fista")},
        },
    }
    frame = {
        "step": "ISTA · k=0 → 1 · actual update line", "values": "y=next: false",
        "curves": [
            {"key": "model_gap", "points": "162.667,101.091 469.333,196.545"},
            {"key": "objective_gap", "points": "162.667,101.091 469.333,253.818"},
        ],
        "markers": [
            {"key": "anchor_gap", "cx": "162.667", "cy": "101.091"},
            {"key": "model_next_gap", "cx": "469.333", "cy": "196.545"},
            {"key": "next_gap", "cx": "469.333", "cy": "253.818"},
        ],
        "dual_values": "ISTA · completed k=1 · D=-1 · F−F*=0.2 · D*−D=0.8 · F−D=1",
        "dual_spaces": [
            {
                "key": "plane",
                "markers": [
                    {"key": "previous", "cx": "310", "cy": "245"},
                    {"key": "next", "cx": "387.5", "cy": "283.75"},
                ],
                "paths": [
                    {"key": method, "points": "310,245 387.5,283.75"}
                    for method in ("ista", "fista")
                ],
            },
            {
                "key": "surface",
                "markers": [
                    {"key": "previous", "cx": "310", "cy": "320"},
                    {"key": "next", "cx": "365", "cy": "211.25"},
                ],
                "paths": [
                    {"key": method, "points": "310,320 365,211.25"}
                    for method in ("ista", "fista")
                ],
            },
        ],
    }
    return case, frame


def test_hand_calculated_plane_surface_and_model_coordinates(checker, fixture):
    case, frame = fixture
    assert checker.check_frame(frame, case, "ista", 0) == (7, 12)


@pytest.mark.parametrize("path,value", [
    (("step",), "FISTA · k=0 → 1 · actual update line"),
    (("values",), "y=next: true"),
    (("curves",), []),
    (("curves", 1, "key"), "model_gap"),
    (("curves", 0, "points"), "162.667,101.091"),
    (("curves", 0, "points"), "162.667,101.091 469.333,196.546"),
    (("curves", 0, "points"), "162.667,101.091 nan,196.545"),
    (("curves", 0, "points"), "162.667,101.091 inf,196.545"),
    (("curves", 0, "points"), "162.667,101.091 469.333,196.545,0"),
    (("markers",), []),
    (("markers", 2, "cx"), "469.334"),
    (("markers", 2, "cy"), "253.819"),
    (("dual_spaces",), []),
    (("dual_spaces", 1, "key"), "plane"),
    (("dual_spaces", 0, "markers"), []),
    (("dual_spaces", 0, "markers", 0, "cx"), "310.00001"),
    (("dual_spaces", 1, "markers", 1, "cy"), "211.25001"),
    (("dual_spaces", 1, "paths"), []),
    (("dual_spaces", 1, "paths", 1, "key"), "ista"),
    (("dual_spaces", 1, "paths", 1, "points"), "310,320"),
    (("dual_spaces", 1, "paths", 1, "points"), "310,320 365,211.25001"),
    (("dual_values",), "ISTA · completed k=2 · D=-1 · F−F*=0.2 · D*−D=0.8 · F−D=1"),
    (("dual_values",), "ISTA · completed k=1 · D=-1 · F−F*=0.2 · D*−D=0.8 · F−D=2"),
])
def test_corrupted_geometry_or_missing_elements_fail(checker, fixture, path, value):
    case, original = fixture
    frame = copy.deepcopy(original)
    parent = frame
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    with pytest.raises(AssertionError):
        checker.check_frame(frame, case, "ista", 0)


def test_legacy_report_has_model_checks_without_fabricating_dual_geometry(checker, fixture):
    case, frame = fixture
    del case["dual_geometry"]
    frame["dual_spaces"], frame["dual_values"] = [], None
    assert checker.check_frame(frame, case, "ista", 0) == (7, 0)
    frame["dual_values"] = "unexpected dual display"
    with pytest.raises(AssertionError):
        checker.check_frame(frame, case, "ista", 0)
