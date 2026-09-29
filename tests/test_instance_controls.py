import json

import pytest

from chainbench.cli import main


def test_preset_overrides_are_resolved_without_editing_json(capsys):
    assert main([
        "preset", "quadratic", "--dimension", "6", "--steps", "12",
        "--condition-number", "25", "--L", "2", "--rotation", "none",
        "--methods", "gd", "cg", "--include-iterates",
    ]) == 0
    config = json.loads(capsys.readouterr().out)
    assert config["problem"] == {
        "kind": "quadratic",
        "dimension": 6,
        "condition_number": 25.0,
        "L": 2.0,
        "rotation": "none",
    }
    assert config["steps"] == 12
    assert config["methods"] == ["gd", "cg"]
    assert set(config["method_options"]) == {"cg"}
    assert config["include_iterates"] is True


def test_seeded_preset_generation_is_deterministic_and_resolved(capsys):
    assert main(["preset", "quadratic", "--random-seed", "17"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert main(["preset", "quadratic", "--random-seed", "17"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert first == second
    assert "random_seed" not in first
    assert 2 <= first["problem"]["dimension"] <= 256
    assert 1 <= first["problem"]["condition_number"] <= 1e6


def test_different_seeds_can_produce_different_configs(capsys):
    assert main(["preset", "diagonal-lasso", "--random-seed", "1"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert main(["preset", "diagonal-lasso", "--random-seed", "2"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert first != second


def test_explicit_overrides_win_over_seeded_values(capsys):
    assert main([
        "preset", "quadratic", "--random-seed", "7", "--dimension", "9",
        "--steps", "13", "--condition-number", "50",
    ]) == 0
    config = json.loads(capsys.readouterr().out)
    assert config["problem"]["dimension"] == 9
    assert config["steps"] == 13
    assert config["problem"]["condition_number"] == 50


@pytest.mark.parametrize("args", [
    ["preset", "simplex", "--condition-number", "10"],
    ["preset", "quadratic", "--lam", "0.2"],
    ["preset", "diagonal-lasso", "--rotation", "none"],
])
def test_problem_specific_overrides_fail_cleanly(args):
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2


def test_config_file_and_cli_overrides_are_not_mixed(tmp_path):
    path = tmp_path / "config.json"
    assert main(["preset", "quadratic", "--output", str(path)]) == 0
    with pytest.raises(SystemExit) as exc:
        main(["experiment", "--config", str(path), "--steps", "4"])
    assert exc.value.code == 2


def test_direct_custom_experiment_can_render_html(tmp_path):
    target = tmp_path / "custom.html"
    assert main([
        "experiment", "--preset", "quadratic", "--dimension", "6",
        "--condition-number", "20", "--steps", "8", "--methods", "gd", "cg",
        "--format", "html", "--output", str(target),
    ]) == 0
    text = target.read_text(encoding="utf-8")
    assert "<svg" in text
    assert "gd" in text and "cg" in text
