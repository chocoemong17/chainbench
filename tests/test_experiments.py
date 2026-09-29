import copy
import csv
import io
import json
from pathlib import Path

import numpy as np
import pytest

from chainbench import __version__
from chainbench.cli import main
from chainbench.experiment_reporting import render_experiment
from chainbench.experiments import (
    MAX_CONFIG_BYTES,
    METHODS,
    PRESETS,
    _input_digest,
    _problem,
    config_digest,
    load_config,
    normalize_config,
    preset_config,
    run_experiment,
)


@pytest.mark.parametrize("name", PRESETS)
def test_all_presets_are_detached_and_normalized(name):
    p = preset_config(name)
    assert p == normalize_config(p) == load_config(json.dumps(p))
    p["methods"].clear()
    assert preset_config(name)["methods"] == list(METHODS[name])


@pytest.mark.parametrize("name", PRESETS)
def test_complete_observations_and_reproducible_metadata(name):
    config = preset_config(name)
    original = copy.deepcopy(config)
    result = run_experiment(config)
    assert config == original
    assert result == run_experiment(config)
    assert result["kind"] == "chainbench.experiment"
    assert result["environment"]["chainbench"] == __version__
    assert set(result["environment"]) == {"chainbench", "python", "numpy", "os"}
    assert result["config_sha256"] == config_digest(original)
    assert len(result["fixture"]["input_sha256"]) == 64
    assert [r["method"] for r in result["runs"]] == config["methods"]
    for run in result["runs"]:
        assert len(run["rows"]) == run["updates"] + 1
        for row in run["rows"]:
            assert all(np.isfinite(v) for v in row.values())
            assert row["gap"] >= 0 and row["stationarity"] >= 0
        assert run["termination"] in ("budget_complete", "converged", "max_steps")
        assert "status" not in run  # Not a theorem pass/fail label.
    config["problem"]["dimension"] = 99
    assert result["config"] == original


def test_normalization_hash_ignores_json_key_order_and_equivalent_defaults():
    p = {"schema_version": 1, "problem": {"kind": "quadratic"}}
    reordered = {"problem": {"kind": "quadratic"}, "schema_version": 1}
    assert config_digest(p) == config_digest(reordered) == config_digest(preset_config("quadratic"))
    changed = preset_config("quadratic")
    changed["steps"] += 1
    assert config_digest(p) != config_digest(changed)


@pytest.mark.parametrize("field,value", [("dimension", 6), ("L", 3.), ("rotation", "none"),
                                         ("condition_number", 20.)])
def test_problem_inputs_change_fingerprint(field, value):
    baseline = preset_config("quadratic")
    changed = copy.deepcopy(baseline)
    changed["problem"][field] = value
    assert _input_digest(_problem(changed)) != _input_digest(_problem(baseline))


def test_diagonal_quadratic_first_update_matches_hand_calculation():
    config = {"schema_version": 1, "problem": {"kind": "quadratic", "dimension": 2,
              "rotation": "none", "condition_number": 4, "L": 2},
              "methods": ["gd"], "steps": 1, "include_iterates": True}
    result = run_experiment(config)
    first = result["runs"][0]["rows"][1]
    # Q=diag(.5,2), x*=(-1,1), b=(-.5,2), x1=b/2=(-.25,1).
    assert first["iterate"] == [-.25, 1.]
    assert first["gap"] == .140625
    assert first["stationarity"] == .375
    assert first["distance_to_reference"] == .75
    assert result["runs"][0]["parameters"]["step_size"] == .5


def test_lasso_stationarity_is_proximal_mapping_not_smooth_gradient():
    p = preset_config("diagonal-lasso")
    p["problem"]["lam"] = 100.
    result = run_experiment(p)
    assert result["fixture"]["stationarity_metric"] == "proximal_gradient_mapping_norm"
    for run in result["runs"]:
        assert run["rows"][0]["stationarity"] == 0
        assert run["rows"][0]["gap"] == 0


def test_simplex_stationarity_is_frank_wolfe_gap():
    p = preset_config("simplex")
    p["problem"]["dimension"] = 4
    p["steps"] = 0
    result = run_experiment(p)
    assert result["fixture"]["stationarity_metric"] == "frank_wolfe_gap"
    assert result["runs"][0]["rows"][0]["stationarity"] == 1.
    assert result["runs"][0]["rows"][0]["gap"] == .375


@pytest.mark.parametrize("steps", [0, 1, 30])
def test_cg_true_residual_and_budget_are_distinguished(steps):
    config = preset_config("quadratic")
    config["methods"] = ["cg"]
    config["method_options"].pop("proximal-point")
    config["steps"] = steps
    run = run_experiment(config)["runs"][0]
    success = run["rows"][-1]["stationarity"] <= run["parameters"]["stopping_threshold"]
    assert (run["termination"] == "converged") == success
    if not success:
        assert run["updates"] == steps
        assert run["termination"] == "max_steps"


@pytest.mark.parametrize("name", PRESETS)
def test_zero_updates_are_valid_observations_not_convergence_claims(name):
    p = preset_config(name)
    p["steps"] = 0
    r = run_experiment(p)
    assert all(len(t["rows"]) == 1 for t in r["runs"])
    assert all(t["termination"] != "converged" for t in r["runs"])


@pytest.mark.parametrize("edit", [
    {"schema_version": 2}, {"schema_version": True}, {"schema_version": 1.0},
    {"steps": -1}, {"steps": True}, {"steps": 1.5}, {"steps": 2001},
    {"include_iterates": 1}, {"include_iterates": "yes"}, {"unknown": 1},
    {"methods": []}, {"methods": ["gd", "gd"]}, {"methods": ["fista"]},
    {"methods": "gd"}, {"methods": [False]}, {"method_options": {"gd": {}}},
    {"method_options": {"cg": {"unknown": 1}}},
    {"method_options": {"cg": {"rtol": -1}}},
    {"method_options": {"cg": {"rtol": 2}}},
    {"method_options": {"proximal-point": {"proximal_parameter": 0}}},
])
def test_invalid_top_level_configuration_is_rejected(edit):
    config = {"schema_version": 1, "problem": {"kind": "quadratic"}, **edit}
    with pytest.raises(ValueError):
        run_experiment(config)


@pytest.mark.parametrize("edit", [
    {"kind": "unknown"}, {"dimension": 0}, {"dimension": 257},
    {"condition_number": .5}, {"condition_number": float("nan")},
    {"condition_number": float("inf")}, {"condition_number": 10**400},
    {"L": 0}, {"rotation": "random"}, {"lam": 0}, {"dimension": False},
])
def test_invalid_problem_configuration_is_rejected(edit):
    with pytest.raises(ValueError):
        run_experiment({"schema_version": 1, "problem": {"kind": "quadratic", **edit}})


@pytest.mark.parametrize("text", [
    '{"schema_version":1,"schema_version":1,"problem":{"kind":"quadratic"}}',
    '{"schema_version":1,"problem":{"kind":"quadratic","L":NaN}}',
    '{"schema_version":1,"problem":{"kind":"quadratic","L":Infinity}}',
    '{"schema_version":1,"problem":{"kind":"quadratic","L":1e999}}',
    '[]', 'null', '1', '{"schema_version":1}', '{"problem":{"kind":"simplex"}}',
    '{"schema_version":1,"problem":{"kind":"simplex","L":1}}',
    ' ' * (MAX_CONFIG_BYTES + 1), '[' * 2000 + '0' + ']' * 2000,
])
def test_json_parser_rejects_missing_ambiguous_or_unbounded_input(text):
    with pytest.raises(ValueError):
        load_config(text)


def test_work_limit_rejects_before_constructing_a_problem(monkeypatch):
    def forbidden(*args):
        raise AssertionError("should not allocate or run a matrix before validation")
    monkeypatch.setattr("chainbench.experiments._problem", forbidden)
    p = {"schema_version": 1, "problem": {"kind": "quadratic", "dimension": 256}, "steps": 2000}
    with pytest.raises(ValueError, match="work limit"):
        run_experiment(p)


@pytest.mark.parametrize("name", PRESETS)
def test_all_report_formats_retain_full_configuration_and_metadata(name):
    config = preset_config(name)
    config["steps"] = 3
    config["include_iterates"] = True
    result = run_experiment(config)
    assert json.loads(render_experiment(result, "json")) == result
    rows = list(csv.DictReader(io.StringIO(render_experiment(result, "csv"))))
    flattened = [(t, r) for t in result["runs"] for r in t["rows"]]
    assert len(rows) == len(flattened)
    for row, (trace, point) in zip(rows, flattened):
        assert json.loads(row["config_json"]) == config
        assert row["config_sha256"] == result["config_sha256"]
        assert row["input_sha256"] == result["fixture"]["input_sha256"]
        assert float(row["gap"]) == point["gap"]
        assert row["method"] == trace["method"]
        assert json.loads(row["fixture_json"]) == result["fixture"]
        assert json.loads(row["parameters_json"]) == trace["parameters"]
        assert row["notice"] == result["notice"]
        assert json.loads(row["iterate_json"]) == point["iterate"]
        final = point["iteration"] == trace["updates"]
        assert row["termination"] == (trace["termination"] if final else "")
    md = render_experiment(result, "markdown")
    assert result["config_sha256"] in md and result["fixture"]["input_sha256"] in md
    assert json.dumps(config, indent=2) in md
    assert "Equal iteration budgets do not imply equal work" in md
    with pytest.raises(ValueError):
        render_experiment(result, "html")


@pytest.mark.parametrize("name", PRESETS)
def test_installed_style_cli_can_save_config_rerun_and_export(tmp_path, name, capsys):
    config_path = tmp_path / "config.json"
    report = tmp_path / "report.json"
    assert main(["preset", name, "--output", str(config_path)]) == 0
    assert main(["experiment", "--config", str(config_path), "--output", str(report)]) == 0
    actual = json.loads(report.read_text())
    assert actual == run_experiment(preset_config(name))
    assert main(["experiment", "--preset", name, "--format", "csv"]) == 0
    assert "config_sha256" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exc:
        main(["preset", name, "--output", str(config_path)])
    assert exc.value.code == 2
    assert main(["preset", name, "--output", str(config_path), "--force"]) == 0


def test_cli_never_overwrites_its_input_even_with_force(tmp_path):
    path = tmp_path / "config.json"
    original = json.dumps(preset_config("quadratic"))
    path.write_text(original)
    with pytest.raises(SystemExit) as exc:
        main(["experiment", "--config", str(path), "--output", str(path), "--force"])
    assert exc.value.code == 2
    assert path.read_text() == original


@pytest.mark.parametrize("content", [b'not json', b'\xff', b' ' * (MAX_CONFIG_BYTES + 1)])
def test_cli_invalid_config_does_not_truncate_existing_output(tmp_path, content):
    config, output = tmp_path / "input.json", tmp_path / "output.json"
    config.write_bytes(content)
    output.write_text("preserve")
    with pytest.raises(SystemExit) as exc:
        main(["experiment", "--config", str(config), "--output", str(output), "--force"])
    assert exc.value.code == 2
    assert output.read_text() == "preserve"


def test_bad_method_trace_is_not_exported_as_success(monkeypatch):
    from chainbench.methods import Trace

    monkeypatch.setattr("chainbench.experiments.gradient_descent",
                        lambda p, steps: Trace([np.zeros(p.dim)], np.array([0.])))
    c = {"schema_version": 1, "problem": {"kind": "quadratic"}, "methods": ["gd"], "steps": 3}
    with pytest.raises(ValueError, match="fewer updates"):
        run_experiment(c)


def test_false_cg_termination_is_rejected(monkeypatch):
    from chainbench.methods import Trace

    monkeypatch.setattr("chainbench.experiments.conjugate_gradient",
                        lambda p, steps, **kw: Trace([np.zeros(p.dim)], np.array([0.]), "converged"))
    c = {"schema_version": 1, "problem": {"kind": "quadratic"}, "methods": ["cg"]}
    with pytest.raises(ValueError, match="termination"):
        run_experiment(c)


def test_repository_presets_match_installed_definitions():
    root = Path(__file__).resolve().parents[1]
    for name in PRESETS:
        path = root / "examples" / "configs" / f"{name}.json"
        assert load_config(path.read_text()) == preset_config(name)


def test_cli_does_not_overwrite_hardlinked_input(tmp_path):
    config, alias = tmp_path / "config.json", tmp_path / "alias.json"
    original = json.dumps(preset_config("simplex"))
    config.write_text(original)
    try:
        alias.hardlink_to(config)
    except OSError:
        pytest.skip("this filesystem does not support hardlinks")
    with pytest.raises(SystemExit):
        main(["experiment", "--config", str(config), "--output", str(alias), "--force"])
    assert config.read_text() == original
