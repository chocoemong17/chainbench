import csv
import importlib.util
import io
from pathlib import Path

import pytest


def example():
    path = Path(__file__).resolve().parents[1] / "examples" / "compare_quadratic.py"
    spec = importlib.util.spec_from_file_location("compare_example", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_comparison_example_produces_parseable_trajectories(capsys):
    assert example().main(["--dim", "6", "--steps", "8"]) == 0
    rows = list(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert {row["method"] for row in rows} == {"gd", "smooth-fista", "cg", "heavy-ball"}
    assert all(float(row["gap"]) >= 0 for row in rows)
    cg = [row for row in rows if row["method"] == "cg"]
    assert cg[-1]["cg_termination"] == "converged"
    assert float(cg[-1]["residual_norm"]) < 1e-10


@pytest.mark.parametrize("args", [["--dim", "0"], ["--condition", "nan"], ["--steps", "-1"]])
def test_comparison_example_rejects_invalid_parameters(args):
    with pytest.raises(SystemExit) as exc:
        example().main(args)
    assert exc.value.code == 2
