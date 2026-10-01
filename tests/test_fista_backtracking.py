import copy
import importlib.util
import json
from pathlib import Path

import pytest

from chainbench.cli import main
from chainbench.fista_backtracking import run_fista_backtracking
from chainbench.fista_backtracking_views import fista_backtracking_html


def audit(record):
    path = Path(__file__).resolve().parents[1] / "scripts/smoke_fista_backtracking.py"
    spec = importlib.util.spec_from_file_location("bt_audit", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.validate_fista_backtracking(record)


@pytest.fixture(scope="module")
def record():
    return run_fista_backtracking(4)


@pytest.mark.parametrize("steps", [1, 18, 60])
def test_independent_full_grid_trial_recurrence_and_model_audit(steps):
    data = run_fista_backtracking(steps)
    audit(data)
    for c in data["cases"]:
        for p in [r["x"] for r in c["rows"]] + [s["anchor"] for s in c["stages"]]:
            assert all(abs(v) <= 3.5 for v in p)


def test_hand_computed_first_step_and_smallest_accepted_trial(record):
    case = next(c for c in record["cases"] if c["id"] == "lambda0.8-zero-L1")
    trials = case["stages"][0]["trials"]
    assert [t["L"] for t in trials] == [1, 2, 4, 8, 16]
    assert [t["accepted"] for t in trials] == [False, False, False, False, True]
    assert [t["stable_model_difference"] for t in trials] == pytest.approx(
        [163.84, 35.795, 6.36625, 0.3003125, -0.570546875]
    )
    assert trials[-1]["point"] == pytest.approx([0.0375, -0.4])
    assert case["stages"][1]["carried_L"] == 16
    assert case["stages"][1]["trials"][0]["L"] == 16
    assert len(case["stages"][1]["trials"]) == 1


def test_later_backtracking_nonmonotone_objectives_and_raw_roundoff_remain_visible():
    data = run_fista_backtracking(60)
    assert any(len(c["observations"]["accepted_L_changes"]) > 1 for c in data["cases"])
    assert all(c["observations"]["objective_increase_rounds"] for c in data["cases"])
    assert any(c["observations"]["raw_gate_disagreements"] for c in data["cases"])
    assert any(s["accepted_L"] < 9 for c in data["cases"] for s in c["stages"])
    assert any(
        min(t["slice"]["model_gap"]) < 0
        for c in data["cases"]
        for s in c["stages"]
        for t in s["trials"]
    )
    # A nonzero tiny, non-cancelling gate must not be accepted as a rounded zero.
    corrupted = copy.deepcopy(data)
    tiny = next(
        trial
        for c in corrupted["cases"]
        for stage in c["stages"]
        for trial in stage["trials"]
        if trial["L"] >= 9 and 0 < abs(trial["stable_model_difference"]) < 1e-18
    )
    tiny["stable_model_difference"] = 0.0
    with pytest.raises(RuntimeError, match="stable gate identity"):
        audit(corrupted)


@pytest.mark.parametrize("steps", [0, 61, True, 1.0, float("nan"), "18"])
def test_budget_rejected_before_computation(steps, monkeypatch):
    import chainbench.fista_backtracking as m

    monkeypatch.setattr(
        m, "DiagonalLassoProblem", lambda *a: pytest.fail("allocated before budget check")
    )
    with pytest.raises(ValueError, match="steps"):
        run_fista_backtracking(steps)


@pytest.mark.parametrize(
    "fault",
    [
        "missing-case",
        "duplicate-case",
        "initial-input",
        "reset-L",
        "wrong-gradient",
        "wrong-momentum",
        "skip-trial",
        "accepted-rejection",
        "rejected-acceptance",
        "gate-zero",
        "nan-gate",
        "raw-subtraction",
        "raw-status",
        "wrong-point",
        "wrong-threshold",
        "missing-corner",
        "wrong-model-slice",
        "wrong-slice-endpoint",
        "wrong-bound",
        "fake-stop",
        "hidden-trial-count",
    ],
)
def test_independent_audit_rejects_corrupted_evidence(record, fault):
    d = copy.deepcopy(record)
    c = d["cases"][0]
    s = c["stages"][0]
    v = s["trials"][0]
    if fault == "missing-case":
        d["cases"].pop()
    elif fault == "duplicate-case":
        d["cases"][1] = copy.deepcopy(c)
    elif fault == "initial-input":
        c["inputs"]["initial_L"] = 8
    elif fault == "reset-L":
        c["stages"][1]["carried_L"] = 0.25
    elif fault == "wrong-gradient":
        s["gradient"][0] += 1
    elif fault == "wrong-momentum":
        c["stages"][2]["next_momentum"] = 0
    elif fault == "skip-trial":
        s["trials"].pop(1)
    elif fault == "accepted-rejection":
        v["accepted"] = True
    elif fault == "rejected-acceptance":
        s["trials"][-1]["accepted"] = False
    elif fault == "gate-zero":
        v["stable_model_difference"] = 0
    elif fault == "nan-gate":
        v["stable_model_difference"] = float("nan")
    elif fault == "raw-subtraction":
        v["raw_model_difference"] += 1
    elif fault == "raw-status":
        v["raw_would_accept"] = not v["raw_would_accept"]
    elif fault == "wrong-point":
        v["point"][0] += 1
    elif fault == "wrong-threshold":
        v["threshold"] *= 2
    elif fault == "missing-corner":
        v["slice"]["parameter"].pop()
    elif fault == "wrong-model-slice":
        v["slice"]["model_gap"][0] += 1
    elif fault == "wrong-slice-endpoint":
        v["slice"]["points"][8][0] += 1
    elif fault == "wrong-bound":
        c["rows"][1]["bound"] /= 2
    elif fault == "fake-stop":
        c["termination"] = "converged"
    elif fault == "hidden-trial-count":
        c["observations"]["total_trials"] -= 1
    with pytest.raises(RuntimeError):
        audit(d)


def test_trial_exhaustion_is_an_error(monkeypatch):
    import chainbench.fista_backtracking as m

    original = m._trial

    def reject(*a, **kw):
        trial = original(*a, **kw)
        trial["accepted"] = False
        return trial

    monkeypatch.setattr(m, "_trial", reject)
    with pytest.raises(FloatingPointError, match="exhausted"):
        run_fista_backtracking(1)


def test_cli_embedded_record_native_coverage_and_exclusive_output(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from smoke_workflows import extract_record

    html, raw = tmp_path / "bt.html", tmp_path / "bt.json"
    args = ["geometry", "fista-backtracking", "--steps", "1"]
    assert main(args + ["--lang", "ko", "--output", str(html)]) == 0
    assert main(args + ["--format", "json", "--output", str(raw)]) == 0
    contents = html.read_text()
    data = json.loads(raw.read_text())
    assert extract_record(contents) == data
    assert contents.count("data-bt-case=") == 36
    assert contents.count("data-bt-native-row=") == sum(
        c["observations"]["total_trials"] for c in data["cases"]
    )
    for c in data["cases"]:
        for s in c["stages"]:
            for v in s["trials"]:
                assert contents.count(f'id="bt-{c["id"]}-k{s["iteration"]}-j{v["attempt"]}"') == 1
    before = html.read_bytes()
    with pytest.raises(SystemExit) as e:
        main(args + ["--output", str(html)])
    assert e.value.code == 2 and html.read_bytes() == before
    assert main(args + ["--output", str(html), "--force"]) == 0


@pytest.mark.parametrize("fault", ["missing", "duplicate", "nonfinite"])
def test_render_rejects_missing_duplicate_or_nonfinite_evidence(record, fault):
    d = copy.deepcopy(record)
    if fault == "missing":
        d["cases"].pop()
    elif fault == "duplicate":
        d["cases"][1] = copy.deepcopy(d["cases"][0])
    else:
        d["cases"][0]["stages"][0]["trials"][0]["stable_gap"] = float("nan")
    with pytest.raises(ValueError):
        fista_backtracking_html(d)
