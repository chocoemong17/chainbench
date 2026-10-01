import copy
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from chainbench.nonuniform_sampling import periodic_weights, project_row, run_nonuniform_sampling


def validate(data):
    spec = importlib.util.spec_from_file_location(
        "sampling_reference", Path(__file__).resolve().parents[1] / "scripts/smoke_nonuniform.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.validate_nonuniform(data)


def test_periodic_cell_weights_use_neighbors_across_the_endpoint():
    t = np.array([0.1, 0.2, 0.6, 0.9])
    np.testing.assert_allclose(periodic_weights(t), [0.15, 0.25, 0.35, 0.25], atol=1e-16)
    assert periodic_weights(t).sum() == pytest.approx(1.0)


@pytest.mark.parametrize(
    "nodes",
    [[0, 0.1, 0.1], [0.2, 0.1, 0.3], [-0.1, 0.2, 0.8], [0, 0.3, 1], [0, 0.2, np.nan], [0.1, 0.2]],
)
def test_invalid_sampling_nodes_are_rejected(nodes):
    with pytest.raises(ValueError):
        periodic_weights(nodes)


def test_complex_projection_conjugation_constraint_and_pythagorean_identity():
    row = np.array([1, 1j, -1], dtype=complex)
    truth = np.array([1 + 2j, 3 - 1j, -2 + 0.5j])
    previous = np.array([0.5 - 1j, -1 + 0.2j, 2 + 1j])
    observed = row @ truth
    nxt = project_row(previous, row, observed)
    np.testing.assert_allclose(row @ nxt, observed, atol=2e-15)
    assert np.vdot(nxt - truth, nxt - previous).real == pytest.approx(0.0, abs=5e-15)
    assert np.linalg.norm(previous - truth) ** 2 == pytest.approx(
        np.linalg.norm(nxt - truth) ** 2 + np.linalg.norm(nxt - previous) ** 2, abs=2e-14
    )
    np.testing.assert_allclose(
        project_row(previous, np.sqrt(0.03) * row, np.sqrt(0.03) * observed), nxt, atol=2e-15
    )


@pytest.mark.parametrize("steps", [True, 0, -1, 15001, 1.5])
def test_invalid_budget_fails_before_matrix_allocation(steps, monkeypatch):
    import chainbench.nonuniform_sampling as mod

    monkeypatch.setattr(mod, "_case", lambda *a: pytest.fail("allocated"))
    with pytest.raises(ValueError):
        run_nonuniform_sampling(steps)


@pytest.fixture(scope="module")
def record():
    return run_nonuniform_sampling(13)


def test_three_declared_inputs_and_all_projection_choices_are_replayed(record):
    validate(record)
    first, second, third = record["cases"]
    assert not first["conditioning"]["theorem4_applicable"]
    assert first["conditioning"]["theorem4_condition_upper"] is None
    assert (
        second["conditioning"]["theorem4_applicable"]
        and third["conditioning"]["theorem4_applicable"]
    )
    assert all(not c["conditioning"]["theorem4_bound_three_applicable"] for c in record["cases"])
    assert record["parameters"]["snapshot_iterations"] == [0, 1, 10, 13]
    for case in record["cases"]:
        for run in case["runs"].values():
            assert len(run["error_l2"]) == 14
            assert run["snapshots"][0]["last_projection"] is None
            assert run["snapshots"][-1]["last_projection"]["row"] == run["rows"][-1]


@pytest.mark.parametrize(
    "fault",
    [
        "row",
        "squared-metric",
        "probability",
        "hash",
        "hypothesis",
        "initial-projection",
        "snapshot",
        "nan",
    ],
)
def test_corrupted_sampling_evidence_is_rejected(record, fault):
    data = copy.deepcopy(record)
    case = data["cases"][0]
    run = case["runs"]["weighted"]
    if fault == "row":
        run["rows"][0] = (run["rows"][0] + 1) % 700
    elif fault == "squared-metric":
        run["error_l2"][1] = run["error_squared"][1]
    elif fault == "probability":
        case["probabilities"][0] += 0.01
    elif fault == "hash":
        case["input_hashes"]["nodes"] = "0" * 64
    elif fault == "hypothesis":
        case["conditioning"]["theorem4_condition_upper"] = 3.0
    elif fault == "initial-projection":
        run["snapshots"][0]["last_projection"] = {}
    elif fault == "snapshot":
        run["snapshots"].pop()
    else:
        run["error_l2"][1] = float("nan")
    with pytest.raises(RuntimeError):
        validate(data)


def test_waveform_svg_coordinates_use_actual_complex_reconstruction_real_part(record):
    import xml.etree.ElementTree as ET

    from chainbench.nonuniform_views import signal_svg

    ns = {"s": "http://www.w3.org/2000/svg"}
    for case in record["cases"]:
        expected_values = case["truth_signal"]["real"] + case["observed_samples"]["real"]
        for run in case["runs"].values():
            for snapshot in run["snapshots"]:
                expected_values += snapshot["signal"]["real"]
                projection = snapshot["last_projection"]
                if projection and "signal_update" in projection:
                    expected_values += projection["signal_update"]["previous_signal"]["real"]
                    expected_values += projection["signal_update"]["next_signal"]["real"]
        low, high = min(expected_values), max(expected_values)
        pad = 0.06 * (high - low)
        low, high = low - pad, high + pad
        for method, run in case["runs"].items():
            for snapshot in run["snapshots"]:
                svg = ET.fromstring(
                    signal_svg(case, record["display_grid"], method, snapshot["iteration"])
                )
                assert float(svg.attrib["data-signal-low"]) == low
                assert float(svg.attrib["data-signal-high"]) == high
                line = svg.find("s:polyline[@data-sampling-prediction]", ns)
                points = np.array(
                    [[float(v) for v in pair.split(",")] for pair in line.attrib["points"].split()]
                )
                expected = np.column_stack(
                    (
                        80 + 800 * np.array(record["display_grid"]),
                        300 - 220 * (np.array(snapshot["signal"]["real"]) - low) / (high - low),
                    )
                )
                np.testing.assert_allclose(points, expected, atol=0.000501, rtol=0)
                marker = svg.find("s:circle[@data-picked-sample]", ns)
                assert marker.attrib["visibility"] == (
                    "hidden" if snapshot["iteration"] == 0 else "visible"
                )
                if snapshot["last_projection"]:
                    row = snapshot["last_projection"]["row"]
                    assert float(marker.attrib["cx"]) == pytest.approx(
                        80 + 800 * case["nodes"][row], abs=0.000501
                    )
                    assert float(marker.attrib["cy"]) == pytest.approx(
                        300 - 220 * (case["observed_samples"]["real"][row] - low) / (high - low),
                        abs=0.000501,
                    )


def test_report_retains_all_three_cases_all_curves_and_no_script_snapshots(record, monkeypatch):
    import json
    import re
    from html import unescape

    from chainbench.nonuniform_views import nonuniform_html

    html = nonuniform_html(record, "ko")
    exported = json.loads(
        unescape(re.search(r'<pre id="chainbench-evidence">(.*?)</pre>', html, re.S)[1])
    )
    assert exported == record
    assert html.count('class="sampling-case"') == 3
    assert html.count("data-sampling-gallery=") == 3 * 3 * 4
    assert "sufficient condition is inapplicable" in html
    assert "not an expectation" in html
    metadata = [
        json.loads(unescape(s)) for s in re.findall(r"<metadata>(.*?)</metadata>", html, re.S)
    ]
    assert len(metadata) == 3
    for chart, case in zip(metadata, record["cases"]):
        assert chart["y_label"] == "coefficient error ||x_k−x_true||₂"
        for series, method in zip(chart["series"], ("cyclic", "uniform", "weighted")):
            assert series["x"] == list(range(14))
            assert series["y"] == case["runs"][method]["error_l2"]


def test_cli_wires_default_budget_and_explicit_preview_without_recomputing(
    monkeypatch, capsys, record
):
    import json

    from chainbench import cli

    calls = []

    def compute(steps):
        calls.append(steps)
        return record

    monkeypatch.setattr(cli, "run_nonuniform_sampling", compute)
    assert cli.main(["reproduce", "kaczmarz-sampling", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out) == record
    assert calls == [15000]
    assert cli.main(["reproduce", "kaczmarz-sampling", "--steps", "13", "--lang", "ko"]) == 0
    assert "700 irregular samples" in capsys.readouterr().out
    assert calls == [15000, 13]
    with pytest.raises(SystemExit) as error:
        cli.main(["reproduce", "kaczmarz-sampling", "--seed", "1"])
    assert error.value.code == 2
    assert "only supported for fista-wavelet" in capsys.readouterr().err
    assert calls == [15000, 13]
