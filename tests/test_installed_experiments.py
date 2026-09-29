import copy
import importlib.util
from pathlib import Path

import pytest

from chainbench import __version__
from chainbench.experiments import PRESETS, preset_config, run_experiment


def smoke():
    path = Path(__file__).resolve().parents[1] / "scripts" / "smoke_install.py"
    spec = importlib.util.spec_from_file_location("smoke_install", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("preset", PRESETS)
def test_independent_smoke_validator_accepts_actual_experiments(preset):
    config = preset_config(preset)
    smoke().validate_experiment(run_experiment(config), config, __version__)


@pytest.mark.parametrize("path,value", [
    (("kind",), "other"), (("schema_version",), True), (("config",), {}),
    (("config_sha256",), "b"*64), (("environment", "chainbench"), "different"),
    (("environment", "numpy"), None), (("fixture", "input_sha256"), "wrong"),
    (("fixture", "dimension"), 999), (("runs",), []),
    (("runs", 0, "rows"), []), (("runs", 0, "updates"), True),
    (("runs", 0, "rows", 0, "iteration"), True),
    (("runs", 0, "rows", 0, "gap"), None), (("runs", 0, "rows", 0, "gap"), -1),
    (("runs", 0, "rows", 0, "gap"), float("inf")),
    (("runs", 0, "termination"), "converged"),
])
def test_independent_smoke_validator_fails_closed(path, value):
    config = preset_config("quadratic")
    result = copy.deepcopy(run_experiment(config))
    target = result
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(RuntimeError):
        smoke().validate_experiment(result, config, __version__)
