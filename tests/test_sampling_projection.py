import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from chainbench._sampling_projection import normalized_dirichlet, projection_response
from chainbench.nonuniform_sampling import project_row, run_nonuniform_sampling


def array(record):
    values = np.empty(np.shape(record["real"]), dtype=complex)
    values.real, values.imag = record["real"], record["imag"]
    return values


@pytest.fixture(scope="module")
def reference():
    spec = importlib.util.spec_from_file_location(
        "response_reference", Path(__file__).resolve().parents[1] / "scripts/smoke_nonuniform.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_nonuniform


def test_kernel_center_integer_periodicity_and_three_frequency_formula():
    offsets = np.array([0, 1, -1, 0.125, 0.25, 0.5, 0.75, 0.875, 1 + 1e-10])
    np.testing.assert_allclose(
        normalized_dirichlet(offsets, 1),
        (1 + 2 * np.cos(2 * np.pi * offsets)) / 3,
        atol=1e-15,
        rtol=0,
    )
    assert np.array_equal(normalized_dirichlet(offsets, 0), np.ones(len(offsets)))
    assert np.array_equal(normalized_dirichlet([0, 1, -1], 50), np.ones(3))
    np.testing.assert_allclose(
        normalized_dirichlet(offsets, 50), normalized_dirichlet(offsets + 3, 50), atol=1e-14, rtol=0
    )


@pytest.mark.parametrize(
    "offsets,r", [([np.nan], 1), ([np.inf], 1), ([0], -1), ([0], True), ([0], 1.5)]
)
def test_invalid_kernel_inputs_fail(offsets, r):
    with pytest.raises(ValueError):
        normalized_dirichlet(offsets, r)


@pytest.mark.parametrize("node", [0.125, 0.137])
def test_actual_update_records_prior_state_and_selected_observation(node):
    frequencies = np.arange(-1, 2)
    row = np.exp(2j * np.pi * node * frequencies)
    truth = np.array([1 - 1j, 2, 1 + 1j])
    previous = np.array([0.25 + 0.2j, 1.2, 0.25 - 0.2j])
    observed = row @ truth
    following = project_row(previous, row, observed)
    saved = projection_response(
        previous, following, row, observed, node, frequencies, np.linspace(0, 1, 9)
    )
    assert np.array_equal(array(saved["previous_coefficients"]), previous)
    assert np.array_equal(array(saved["coefficient_correction"]), following - previous)
    center = saved["node_index"]
    assert saved["grid"][center] == node
    assert len(saved["grid"]) == (9 if node == 0.125 else 10)
    assert saved["normalized_kernel"][center] == 1
    assert array(saved["previous_signal"])[center] == pytest.approx(row @ previous, abs=1e-15)
    assert array(saved["next_signal"])[center] == pytest.approx(observed, abs=1e-15)
    assert array(saved["correction_signal"])[center] == pytest.approx(
        observed - row @ previous, abs=1e-15
    )
    np.testing.assert_allclose(
        array(saved["correction_signal"]), array(saved["ideal_signal_correction"]), atol=2e-15
    )


def test_zero_residual_retains_zero_change_and_finite_unit_response():
    frequencies = np.arange(-1, 2)
    node = 0.31
    row = np.exp(2j * np.pi * node * frequencies)
    previous = np.array([1 + 1j, 2, 1 - 1j])
    observed = np.dot(row, previous)
    following = project_row(previous, row, observed)
    result = projection_response(
        previous, following, row, observed, node, frequencies, np.linspace(0, 1, 17)
    )
    for field in ("coefficient_correction", "correction_signal", "ideal_signal_correction"):
        assert np.count_nonzero(array(result[field])) == 0
    assert result["normalized_kernel"][result["node_index"]] == 1
    assert result["coefficient_roundoff_inf"] == result["kernel_comparison_error_inf"] == 0


@pytest.fixture(scope="module")
def record():
    return run_nonuniform_sampling(13)


def test_independent_replay_validates_all_methods_and_previous_states(record, reference):
    reference(record, require_projection=True)
    for case in record["cases"]:
        for run in case["runs"].values():
            assert run["snapshots"][0]["last_projection"] is None
            first = run["snapshots"][1]["last_projection"]["signal_update"]
            assert np.count_nonzero(array(first["previous_coefficients"])) == 0


def test_legacy_records_remain_valid_but_do_not_satisfy_new_required_evidence(record, reference):
    old = copy.deepcopy(record)
    del old["projection_geometry"]
    for case in old["cases"]:
        for run in case["runs"].values():
            for s in run["snapshots"]:
                if s["last_projection"]:
                    del s["last_projection"]["signal_update"]
    reference(old)
    with pytest.raises(RuntimeError, match="explanation missing"):
        reference(old, require_projection=True)


@pytest.mark.parametrize(
    "fault",
    [
        "previous",
        "correction",
        "kernel",
        "grid",
        "center",
        "residual",
        "diagnostic",
        "missing",
        "partial-root",
    ],
)
def test_corrupted_response_is_rejected(record, reference, fault):
    data = copy.deepcopy(record)
    projection = data["cases"][0]["runs"]["weighted"]["snapshots"][1]["last_projection"]
    update = projection["signal_update"]
    if fault == "previous":
        update["previous_coefficients"]["real"][0] += 0.001
    elif fault == "correction":
        update["coefficient_correction"]["real"][0] += 0.001
    elif fault == "kernel":
        update["normalized_kernel"][0] += 0.01
    elif fault == "grid":
        update["grid"][1] += 1e-5
    elif fault == "center":
        update["node_index"] += 1
    elif fault == "residual":
        update["projection_residual"]["imag"] += 0.001
    elif fault == "diagnostic":
        update["kernel_comparison_error_inf"] += 1e-9
    elif fault == "missing":
        del projection["signal_update"]
    else:
        del data["projection_geometry"]
    with pytest.raises(RuntimeError):
        reference(data)


def test_response_curves_use_retained_arrays_and_explicit_axis_scales(record):
    import xml.etree.ElementTree as ET

    from chainbench._sampling_projection_views import response_svg
    from chainbench.nonuniform_views import _signal_limits

    ns = {"s": "http://www.w3.org/2000/svg"}
    for case in record["cases"]:
        limits = _signal_limits(case)
        for run in case["runs"].values():
            for snapshot in run["snapshots"][1:]:
                projection = snapshot["last_projection"]
                response = projection["signal_update"]
                svg = ET.fromstring(response_svg(projection, limits))
                expected = {
                    "before": response["previous_signal"]["real"],
                    "after": response["next_signal"]["real"],
                    "kernel": response["normalized_kernel"],
                    "actual": response["correction_signal"]["real"],
                    "ideal": response["ideal_signal_correction"]["real"],
                }
                found = 0
                amplitude = max(abs(v) for v in expected["actual"] + expected["ideal"])
                radius = 1.08 * amplitude if amplitude else 1
                for group in svg.findall("s:g", ns):
                    kind = group.attrib["data-response-axis"]
                    lo, hi = float(group.attrib["data-low"]), float(group.attrib["data-high"])
                    assert (lo, hi) == (
                        limits
                        if kind == "waveforms"
                        else (-0.3, 1.1)
                        if kind == "kernel"
                        else (-radius, radius)
                    )
                    top, height = (
                        float(group.attrib["data-top"]),
                        float(group.attrib["data-height"]),
                    )
                    for curve in group.findall("s:polyline", ns):
                        xy = np.array(
                            [
                                [float(v) for v in p.split(",")]
                                for p in curve.attrib["points"].split()
                            ]
                        )
                        field = curve.attrib["data-response-curve"]
                        values = np.column_stack(
                            (
                                80 + 800 * np.array(response["grid"]),
                                top
                                + height
                                - height * (np.array(expected[field]) - lo) / (hi - lo),
                            )
                        )
                        np.testing.assert_allclose(xy, values, atol=0.000051, rtol=0)
                        found += 1
                assert found == 5


def test_initial_projection_is_empty_and_all_native_stages_are_retained(record):
    from chainbench.nonuniform_views import nonuniform_html

    html = nonuniform_html(record, "ko")
    assert html.count("data-projection-frame=") == 3 * 3 * 4
    assert html.count("data-response-curve=") == 3 * 3 * 3 * 5
    assert html.count("data-projection-first") == 4  # Three buttons and the script selector.
    assert "exact-arithmetic derivation" in html
    assert "axis rescales at each selection" in html
    assert "no completed projection or previous waveform" in html
