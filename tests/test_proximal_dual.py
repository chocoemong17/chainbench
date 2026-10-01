import copy
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

from chainbench._lasso_duality import residual_dual_bound
from chainbench._proximal_dual_views import dual_svg
from chainbench.proximal_geometry import run_proximal_geometry
from chainbench.proximal_views import proximal_html


def validate(data, **kwargs):
    path = Path(__file__).resolve().parents[1] / "scripts/smoke_proximal_dual.py"
    spec = importlib.util.spec_from_file_location("independent_dual", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.validate_proximal_dual(data, **kwargs)


@pytest.mark.parametrize("steps", [2, 18, 60])
def test_all_cases_match_decimal_dual_and_strong_duality(steps):
    data = run_proximal_geometry(steps)
    validate(data, required=True)
    for c in data["cases"]:
        g = c["dual_geometry"]
        assert g["reference_value"] == pytest.approx(c["f_star"], abs=2e-15)
        np.testing.assert_allclose(
            np.array(data["problem"]["a"]) * c["x_star"] - data["problem"]["b"],
            g["reference"],
            atol=1e-15,
        )
        for method, points in g["runs"].items():
            for row, d in zip(c["runs"][method]["rows"], points):
                assert d["primal_gap"] == row["gap"]
                assert d["suboptimality_upper_bound"] >= row["gap"]
                assert max(abs(v) for v in d["normalized"]) < 1


def test_half_loss_dual_matches_rescaled_full_loss_with_double_penalty():
    data = run_proximal_geometry(2)
    a, b = np.array(data["problem"]["a"]), np.array(data["problem"]["b"])
    for c in data["cases"]:
        d = c["dual_geometry"]["runs"]["fista"][1]
        x = np.array(c["runs"]["fista"]["rows"][1]["x"])
        full = residual_dual_bound(a * x - b, b, x, lambda nu: a * nu, 2 * c["lambda"])
        assert full["scale"] == d["scale"]
        assert full["lower_bound"] / 2 == pytest.approx(d["lower_bound"], abs=1e-15)
        assert full["suboptimality_upper_bound"] / 2 == pytest.approx(
            d["suboptimality_upper_bound"], abs=2e-15
        )


def test_inactive_primal_coordinate_corresponds_to_interior_dual_coordinate():
    data = run_proximal_geometry(2)
    c = next(c for c in data["cases"] if c["id"] == "lambda-3-zero")
    assert c["x_star"][0] == 0
    assert c["dual_geometry"]["reference"] == pytest.approx([-1.4, 0.6])
    assert abs(c["dual_geometry"]["reference_normalized"][0]) < 1


@pytest.mark.parametrize("surface", [False, True])
def test_actual_candidate_markers_and_paths_use_completed_next_point(surface):
    ns = {"s": "http://www.w3.org/2000/svg"}
    for c in run_proximal_geometry(3)["cases"]:
        g = c["dual_geometry"]
        svg = ET.fromstring(dual_svg(c, surface=surface))
        if surface:
            mesh = svg.findall(".//s:polyline[@data-dual-mesh]", ns)
            assert len(mesh) == 26
            for el, (axis, fixed) in zip(
                mesh, [(i, v) for i in (0, 1) for v in np.linspace(-1, 1, 13)]
            ):
                actual = [[float(v) for v in xy.split(",")] for xy in el.attrib["points"].split()]
                expected = []
                for free in np.linspace(-1, 1, 33):
                    u, v = (fixed, free) if axis == 0 else (free, fixed)
                    nu = np.array([u, v]) * g["box_half_width"]
                    height = -sum(nu * nu) / 2 - np.array([1.4, -2.4]) @ nu
                    z = (height - g["surface_minimum"]) / (
                        g["surface_maximum"] - g["surface_minimum"]
                    )
                    expected.append([310 + 145 * u + 70 * v, 320 - 35 * u + 65 * v - 150 * z])
                np.testing.assert_allclose(actual, expected, atol=5.1e-6)

        def project(d):
            u, v = d["normalized"]
            if surface:
                z = (d["lower_bound"] - g["surface_minimum"]) / (
                    g["surface_maximum"] - g["surface_minimum"]
                )
                return [310 + 145 * u + 70 * v, 320 - 35 * u + 65 * v - 150 * z]
            return [310 + 155 * u, 245 - 155 * v]

        for method, rows in g["runs"].items():
            path = svg.find(f'.//s:polyline[@data-dual-path="{method}"]', ns)
            coords = [
                [float(v) for v in s.split(",")] for s in path.attrib["data-points"].split("|")
            ]
            np.testing.assert_allclose(coords, [project(d) for d in rows], atol=5.1e-6)
            for key, offset in (("previous", 0), ("next", 1)):
                el = svg.find(f'.//s:circle[@data-dual-marker="{key}"]', ns)
                coords = [
                    [float(v) for v in s.split(",")] for s in el.attrib["data-" + method].split("|")
                ]
                np.testing.assert_allclose(
                    coords, [project(d) for d in rows[offset : 3 + offset]], atol=5.1e-6
                )


@pytest.mark.parametrize(
    "fault", ["nu", "scale", "half-loss", "feasibility", "reference", "deficit", "missing", "nan"]
)
def test_independent_dual_validator_rejects_corruption(fault):
    data = run_proximal_geometry(2)
    g = data["cases"][0]["dual_geometry"]
    d = g["runs"]["fista"][0]
    if fault == "nu":
        d["nu"][0] += 0.01
    elif fault == "scale":
        d["scale"] *= 2
    elif fault == "half-loss":
        d["lower_bound"] *= 2
    elif fault == "feasibility":
        d["dual_adjoint_inf"] = 0.1000000000001
    elif fault == "reference":
        g["reference"][0] += 0.1
    elif fault == "deficit":
        d["dual_deficit"] += 0.1
    elif fault == "missing":
        g["runs"]["fista"].pop()
    else:
        d["suboptimality_upper_bound"] = float("nan")
    with pytest.raises(RuntimeError, match="proximal dual"):
        validate(data)


def test_legacy_proximal_records_still_validate_and_render():
    data = run_proximal_geometry(2)
    old = copy.deepcopy(data)
    del old["duality"]
    for c in old["cases"]:
        del c["dual_geometry"]
    validate(old)
    with pytest.raises(RuntimeError):
        validate(old, required=True)
    assert 'class="prox-dual"' not in proximal_html(old)
    assert proximal_html(data).count('class="prox-dual"') == 9
