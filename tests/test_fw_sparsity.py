import copy
import importlib.util
import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from chainbench.fw_sparsity import DIMENSIONS, _SquaredNormSimplex, run_fw_sparsity
from chainbench.fw_sparsity_views import fw_sparsity_html
from chainbench.methods import frank_wolfe


@pytest.mark.parametrize("steps", [True, 0, -1, 257, 1.5, None])
def test_invalid_budget_is_rejected(steps):
    with pytest.raises(ValueError):
        run_fw_sparsity(steps)


@pytest.mark.parametrize("n", DIMENSIONS)
def test_source_scaling_and_existing_oracle(n):
    p = _SquaredNormSimplex(np.full(n, 1 / n))
    e = np.eye(n)[0]
    assert p.value(e) == 1
    assert p.f_star == 1 / n and p.curvature_upper_bound == 4
    np.testing.assert_array_equal(p.grad(e), 2 * e)
    np.testing.assert_array_equal(p.linear_minimizer(p.grad(e)), np.eye(n)[1])
    # Cf is attained along the segment between distinct vertices: second-order
    # remainder = 2*gamma², multiplied by 2/gamma² gives 4.
    gamma = Fraction(2, 7)
    value = (1 - gamma) ** 2 + gamma**2
    assert 2 * (value - 1 + 2 * gamma) / gamma**2 == 4


def test_every_iterate_against_exact_rational_recurrence():
    data = run_fw_sparsity(40)
    for case in data["cases"]:
        n = case["dimension"]
        x = [Fraction(int(i == 0)) for i in range(n)]
        for k, row in enumerate(case["rows"]):
            support = sum(v > 0 for v in x)
            objective = sum(v * v for v in x)
            oracle = min(range(n), key=x.__getitem__)
            np.testing.assert_allclose(row["x"], [float(v) for v in x], atol=2e-15, rtol=2e-14)
            assert row["support"] == support
            assert row["vertex_index"] == oracle
            assert row["objective"] == pytest.approx(float(objective), abs=2e-15)
            assert row["primal_gap"] == pytest.approx(float(objective - Fraction(1, n)), abs=2e-15)
            assert row["dual_gap"] == pytest.approx(float(2 * (objective - min(x))), abs=2e-15)
            assert objective >= Fraction(1, support)
            assert row["support_floor"] == pytest.approx(
                float(Fraction(1, support) - Fraction(1, n))
            )
            assert row["excess_over_support_minimum"] == pytest.approx(
                float(objective - Fraction(1, support)), abs=2e-15
            )
            assert row["balanced_objective"] == pytest.approx(1 / support)
            assert row["balanced_primal_gap"] == pytest.approx(1 / support - 1 / n, abs=2e-15)
            if support < n:
                assert row["dual_support_floor"] == 2 / support
                assert row["balanced_dual_gap"] == pytest.approx(2 / support)
            else:
                assert row["dual_support_floor"] is None
                assert row["balanced_dual_gap"] == 0
            if k:
                assert objective - Fraction(1, n) <= Fraction(8, k + 2)
                assert row["iteration_upper"] == 8 / (k + 2)
            else:
                assert row["iteration_upper"] is None
            if k < 40:
                gamma = Fraction(2, k + 2)
                x = [(1 - gamma) * v + gamma * int(i == oracle) for i, v in enumerate(x)]
            else:
                assert row["gamma"] is None
        assert case["rows"][0]["support"] == case["rows"][1]["support"] == 1
        assert case["rows"][0]["x"] != case["rows"][1]["x"]
        assert case["rows"][2]["support"] == 2


def test_full_public_construction_and_no_full_support_dual_bound():
    data = run_fw_sparsity(1)
    for case in data["cases"]:
        n = case["dimension"]
        for s, point in enumerate(case["construction"], start=1):
            assert point["support"] == s
            np.testing.assert_array_equal(point["x"], [1 / s] * s + [0.0] * (n - s))
            assert point["objective"] == pytest.approx(1 / s)
            assert point["primal_gap"] == pytest.approx(1 / s - 1 / n, abs=2e-15)
            if s < n:
                assert point["dual_floor"] == 2 / s
                assert point["dual_gap"] == pytest.approx(2 / s)
            else:
                assert point["dual_floor"] is None
                assert point["primal_gap"] == point["dual_gap"] == 0


def test_export_uses_existing_fw_and_preserves_full_inputs():
    data = run_fw_sparsity(12)
    for case in data["cases"]:
        n = case["dimension"]
        trace = frank_wolfe(_SquaredNormSimplex(np.full(n, 1 / n)), 12)
        np.testing.assert_array_equal([r["x"] for r in case["rows"]], trace.iterates)
        np.testing.assert_array_equal([r["objective"] for r in case["rows"]], trace.values)
        assert case["updates"] == 12 and case["termination"] == "fixed_budget"
        assert len(case["input_sha256"]) == 64
    assert data["parameters"]["seed"] is None


def validator():
    spec = importlib.util.spec_from_file_location(
        "sparsity_smoke", Path(__file__).resolve().parents[1] / "scripts/smoke_fw_sparsity.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_fw_sparsity


def test_independent_installed_validator_at_maximum_budget():
    validator()(run_fw_sparsity(256))


@pytest.mark.parametrize(
    "fault", ["full_support_dual", "k0_upper", "missing_point", "hash", "balanced", "objective"]
)
def test_corrupted_sparsity_evidence_is_rejected(fault):
    data = copy.deepcopy(run_fw_sparsity(5))
    c = data["cases"][0]
    if fault == "full_support_dual":
        c["rows"][3]["dual_support_floor"] = 2 / 3
    elif fault == "k0_upper":
        c["rows"][0]["iteration_upper"] = 4
    elif fault == "missing_point":
        c["construction"].pop()
    elif fault == "hash":
        c["input_sha256"] = "0" * 64
    elif fault == "balanced":
        c["rows"][2]["balanced"] = [1 / 3] * 3
    else:
        c["rows"][2]["objective"] *= 0.5
    with pytest.raises(RuntimeError):
        validator()(data)


def test_cli_defaults_and_incompatible_options(tmp_path, capsys):
    from chainbench.cli import main

    path = tmp_path / "sparsity.json"
    assert main(["case-study", "fw-sparsity", "--format", "json", "--output", str(path)]) == 0
    result = json.loads(path.read_text())
    assert result["parameters"]["steps"] == 40
    validator()(result)
    for options in (
        ["fw-sparsity", "--L", "1"],
        ["fw-sparsity", "--horizon", "20"],
        ["gd-tight", "--steps", "10"],
    ):
        with pytest.raises(SystemExit) as exc:
            main(["case-study", *options])
        assert exc.value.code == 2
        assert "only supported" in capsys.readouterr().err
    assert (
        main(["case-study", "gd-tight", "--format", "json", "--output", str(path), "--force"]) == 0
    )
    assert json.loads(path.read_text())["config"] == dict(
        horizon=20, L=1.0, R=1.0, h=1.0, dimension=1
    )


def test_scatter_keeps_repeated_supports_and_conditional_bound():
    import html
    import re

    result = run_fw_sparsity(5)
    text = fw_sparsity_html(result, "ko")
    raw = re.search(r'<pre id="chainbench-evidence">(.*?)</pre>', text, re.S)[1]
    assert json.loads(html.unescape(raw)) == result
    metadata = [
        json.loads(html.unescape(x)) for x in re.findall(r"<metadata>(.*?)</metadata>", text, re.S)
    ]
    scatters = [m for m in metadata if m.get("kind") == "chainbench.support-scatter"]
    assert len(scatters) == 4
    assert scatters[0]["rows"][0]["support"] == scatters[0]["rows"][1]["support"] == 1
    assert len(scatters[0]["rows"]) == 6
    dual = next(m for m in metadata if m.get("title") == "Dual-gap floor only before full support")
    assert dual["series"][1]["x"] == [0, 1, 2]
    assert dual["series"][1]["y"] == [2.0, 2.0, 1.0]
    assert "C_f=4" in text and "ONLY when s&lt;n" in text
