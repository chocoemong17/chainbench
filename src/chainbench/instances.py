"""Sealed numeric inputs and exact-input execution, separate from preset schema 1."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import platform

import numpy as np

from . import __version__
from ._validation import count
from .experiments import (
    METHODS,
    _bounded,
    _choice,
    _object,
    canonical_json,
    normalize_execution,
    observe_problem,
)
from .problems import DiagonalLassoProblem, QuadraticProblem, SimplexQuadraticProblem

MAX_INPUT_BYTES = 256_000
MAX_REPORT_BYTES = 8_000_000
MAX_DIMENSION = 64
MAX_OUTPUT_SCALARS = 100_000
GENERATOR = "chainbench.pcg64-normal-qr.v1"
NOTICE = (
    "Finite observations on stored float64 inputs, not theorem certificates or a universal "
    "ranking. Hashes bind recorded contents, not their author or claimed generation history. "
    "Equal updates are not equal work. A PSD quadratic may have nonunique minimizers; "
    "distance is to the supplied reference, not distance to the solution set."
)
RUN_KEYS = {"steps", "methods", "method_options", "include_iterates"}
RAW_KEYS = {"schema_version", "problem", "x0", "run"}
MANIFEST_KEYS = RAW_KEYS | {"kind", "origin", "input_sha256", "manifest_sha256"}
REPORT_KEYS = {"kind", "schema_version", "instance", "environment", "fixture", "notice", "runs"}


def _bounded_json(value, limit: int) -> str:
    def visit(v, depth=0):
        if depth > 16:
            raise ValueError("JSON nesting exceeds 16 levels")
        if type(v) is dict:
            if any(type(k) is not str for k in v):
                raise ValueError("JSON object keys must be strings")
            for item in v.values():
                visit(item, depth + 1)
        elif type(v) is list:
            for item in v:
                visit(item, depth + 1)
        elif type(v) in (int, float):
            try:
                finite = math.isfinite(v)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError("JSON contains a non-finite number")
        elif v is not None and type(v) not in (bool, str):
            raise ValueError("expected JSON values")
    visit(value)
    text = canonical_json(value)
    if len(text.encode("utf-8")) > limit:
        raise ValueError(f"JSON exceeds {limit} byte limit")
    return text


def parse_json(text: str, *, report: bool = False) -> dict:
    """Bound the transport before parsing, including whitespace and duplicate keys."""
    limit = MAX_REPORT_BYTES if report else MAX_INPUT_BYTES
    if not isinstance(text, str) or len(text.encode("utf-8")) > limit:
        raise ValueError(f"JSON exceeds {limit} byte limit")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError(f"non-standard JSON number: {value}")
    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
        _bounded_json(value, limit)
    except (RecursionError, OverflowError) as exc:
        raise ValueError("JSON nesting or number exceeds the supported range") from exc
    return value


def _version(value) -> None:
    if type(value) is not int or value != 1:
        raise ValueError("unsupported instance schema_version")


def _vector(value, name: str, dimension: int | None = None) -> np.ndarray:
    if type(value) is not list or not 1 <= len(value) <= MAX_DIMENSION:
        raise ValueError(f"{name} must be a vector of 1 to {MAX_DIMENSION} numbers")
    if dimension is not None and len(value) != dimension:
        raise ValueError(f"{name} has the wrong dimension")
    for v in value:
        if type(v) not in (int, float):
            raise ValueError(f"{name} must contain JSON numbers, not booleans or strings")
        try:
            valid = math.isfinite(v) and (type(v) is float or int(float(v)) == v)
        except (OverflowError, ValueError):
            valid = False
        if not valid:
            raise ValueError(f"{name} must be finite and representable as float64")
    return np.array(value, dtype=np.float64)


def _normalize_raw(raw: dict):
    _bounded_json(raw, MAX_INPUT_BYTES)
    _object(raw, RAW_KEYS, RAW_KEYS, "raw instance")
    _version(raw["schema_version"])
    p = raw["problem"]
    _object(p, {"kind", "Q", "b", "x_star", "a", "lam", "target"}, {"kind"}, "problem")
    kind = _choice(p["kind"], tuple(METHODS), "problem.kind")
    x0 = _vector(raw["x0"], "x0")
    d = len(x0)
    settings = _object(raw["run"], RUN_KEYS, set(), "run")
    settings = normalize_execution(settings, kind, d)
    samples = (settings["steps"] + 1) * len(settings["methods"])
    if samples * (5 + (d if settings["include_iterates"] else 0)) > MAX_OUTPUT_SCALARS:
        raise ValueError("recorded scalar budget exceeded; reduce steps, dimension or methods")
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        if kind == "quadratic":
            _object(p, {"kind", "Q", "b", "x_star"}, {"kind", "Q", "b", "x_star"}, "quadratic")
            if type(p["Q"]) is not list or len(p["Q"]) != d:
                raise ValueError("Q must be a square matrix matching x0")
            q = np.array([_vector(row, "Q row", d) for row in p["Q"]])
            if not np.array_equal(q, q.T):
                raise ValueError("Q must be exactly symmetric; import never symmetrizes inputs")
            b, star = _vector(p["b"], "b", d), _vector(p["x_star"], "x_star", d)
            problem = QuadraticProblem(q, b, star)
            if problem.Q.tobytes() != q.tobytes():
                raise ValueError("quadratic construction changed input bytes")
            if problem.L <= 0:
                raise ValueError("quadratic needs L > 0 for this teaching workflow")
            if problem.mu <= 0 and set(settings["methods"]) & {"cg", "heavy-ball"}:
                raise ValueError("CG and classical heavy-ball require a positive-definite quadratic")
            data = {"kind": kind, "Q": q.tolist(), "b": b.tolist(), "x_star": star.tolist()}
        elif kind == "diagonal-lasso":
            _object(p, {"kind", "a", "b", "lam"}, {"kind", "a", "b", "lam"}, "diagonal LASSO")
            a, b = _vector(p["a"], "a", d), _vector(p["b"], "b", d)
            lam = _vector([p["lam"]], "lam")[0]
            problem = DiagonalLassoProblem(a, b, float(lam))
            data = {"kind": kind, "a": a.tolist(), "b": b.tolist(), "lam": float(lam)}
        else:
            _object(p, {"kind", "target"}, {"kind", "target"}, "simplex")
            target = _vector(p["target"], "target", d)
            problem = SimplexQuadraticProblem(target)
            if np.any(x0 < 0) or not np.isclose(x0.sum(), 1., rtol=0, atol=1e-12):
                raise ValueError("x0 must lie on the probability simplex")
            data = {"kind": kind, "target": target.tolist()}
    normalized = {"schema_version": 1, "problem": data, "x0": x0.tolist(), "run": settings}
    return normalized, problem, x0


def input_digest(raw: dict) -> str:
    """Exact little-endian float64 arrays, including x0, domain/labels/shapes bound."""
    p = raw["problem"]
    h = hashlib.sha256(b"chainbench.numeric-input.v1\0" + p["kind"].encode("ascii") + b"\0")
    names = {"quadratic": ("Q", "b", "x_star"), "diagonal-lasso": ("a", "b", "lam"),
             "simplex": ("target",)}[p["kind"]]
    for name, value in [(key, p[key]) for key in names] + [("x0", raw["x0"])]:
        data = np.asarray(value, dtype="<f8", order="C")
        h.update(canonical_json({"name": name, "shape": list(data.shape)}).encode("ascii") + b"\0")
        h.update(data.tobytes(order="C"))
    return h.hexdigest()


def _sha(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _seal(raw: dict, origin: dict) -> dict:
    normalized, _, _ = _normalize_raw(raw)
    result = {"kind": "chainbench.instance", **normalized, "origin": copy.deepcopy(origin),
              "input_sha256": input_digest(normalized)}
    result["manifest_sha256"] = _sha(result)
    _bounded_json(result, MAX_INPUT_BYTES)
    return result


def import_instance(raw: dict) -> dict:
    """Seal explicit JSON inputs; unknown or previously claimed provenance is rejected."""
    return _seal(raw, {"type": "imported"})


def _generation_parameters(kind, dimension, seed, L, condition_number, lam) -> dict:
    kind = _choice(kind, tuple(METHODS), "kind")
    d = count(dimension, "dimension", 2 if kind == "simplex" else 1)
    seed = count(seed, "seed")
    if d > MAX_DIMENSION or seed > 2**32 - 1:
        raise ValueError(f"dimension <= {MAX_DIMENSION} and seed <= 2**32-1 required")
    result = {"kind": kind, "dimension": d, "seed": seed}
    if kind == "quadratic":
        if lam is not None:
            raise ValueError("lam is only available for diagonal LASSO")
        result.update(L=_bounded(1. if L is None else L, "L", 1e-6, 1e6),
                      condition_number=_bounded((1. if d == 1 else 10.) if condition_number is None else condition_number,
                                                "condition_number", 1, 1e6))
        if d == 1 and result["condition_number"] != 1:
            raise ValueError("a one-dimensional quadratic has condition_number=1")
    else:
        if L is not None or condition_number is not None:
            raise ValueError("L and condition_number are only available for quadratics")
        if kind == "diagonal-lasso":
            result["lam"] = _bounded(.12 if lam is None else lam, "lam", 0, 1e3)
        elif lam is not None:
            raise ValueError("lam is only available for diagonal LASSO")
    return result


def generate_instance(kind: str, *, dimension: int = 6, seed: int = 0,
                      run: dict | None = None, L=None, condition_number=None, lam=None) -> dict:
    """Generate numeric arrays once; replay never calls this function or the RNG."""
    params = _generation_parameters(kind, dimension, seed, L, condition_number, lam)
    rng = np.random.Generator(np.random.PCG64(seed))
    d = params["dimension"]
    if kind == "quadratic":
        rotation, _ = np.linalg.qr(rng.normal(size=(d, d)))
        eig = np.geomspace(params["L"] / params["condition_number"], params["L"], d)
        q = (rotation * eig) @ rotation.T
        q = .5 * q + .5 * q.T
        star = rng.uniform(-1., 1., d)
        problem = {"kind": kind, "Q": q.tolist(), "b": (q @ star).tolist(), "x_star": star.tolist()}
        x0 = rng.uniform(-2., 2., d)
    elif kind == "diagonal-lasso":
        a = rng.uniform(.5, 2., d) * rng.choice([-1., 1.], size=d)
        problem = {"kind": kind, "a": a.tolist(), "b": rng.uniform(-2., 2., d).tolist(),
                   "lam": params["lam"]}
        x0 = rng.uniform(-2., 2., d)
    else:
        target, x0 = rng.uniform(.1, 1., (2, d))
        target, x0 = target / target.sum(), x0 / x0.sum()
        problem = {"kind": kind, "target": target.tolist()}
    raw = {"schema_version": 1, "problem": problem, "x0": x0.tolist(), "run": {} if run is None else run}
    return _seal(raw, {"type": "generated", "generator": GENERATOR, "parameters": params})


def validate_instance(instance: dict):
    _bounded_json(instance, MAX_INPUT_BYTES)
    _object(instance, MANIFEST_KEYS, MANIFEST_KEYS, "instance manifest")
    if instance["kind"] != "chainbench.instance":
        raise ValueError("expected a chainbench.instance manifest")
    raw = {key: instance[key] for key in RAW_KEYS}
    normalized, problem, x0 = _normalize_raw(raw)
    if canonical_json(raw) != canonical_json(normalized):
        raise ValueError("instance inputs and run settings must be normalized")
    origin = instance["origin"]
    _object(origin, {"type", "generator", "parameters"}, {"type"}, "origin")
    if origin["type"] == "imported":
        _object(origin, {"type"}, {"type"}, "import origin")
    elif origin["type"] == "generated":
        _object(origin, {"type", "generator", "parameters"}, {"type", "generator", "parameters"}, "generation origin")
        if origin["generator"] != GENERATOR:
            raise ValueError("unsupported declared generator")
        p = origin["parameters"]
        _object(p, {"kind", "dimension", "seed", "L", "condition_number", "lam"},
                {"kind", "dimension", "seed"}, "generation parameters")
        expected = _generation_parameters(p["kind"], p["dimension"], p["seed"],
                                          p.get("L"), p.get("condition_number"), p.get("lam"))
        if (canonical_json(p) != canonical_json(expected) or p["kind"] != raw["problem"]["kind"]
                or p["dimension"] != problem.dim):
            raise ValueError("generation provenance does not match the instance")
    else:
        raise ValueError("origin.type must be imported or generated")
    if instance["input_sha256"] != input_digest(normalized):
        raise ValueError("numeric input digest mismatch")
    if instance["manifest_sha256"] != _sha({k: v for k, v in instance.items() if k != "manifest_sha256"}):
        raise ValueError("manifest digest mismatch")
    return problem, x0


def run_instance(instance: dict) -> dict:
    problem, x0 = validate_instance(instance)
    kind = instance["problem"]["kind"]
    result = {"kind": "chainbench.instance-experiment", "schema_version": 1,
              "instance": copy.deepcopy(instance), "notice": NOTICE,
              "environment": {"chainbench": __version__, "python": platform.python_version(),
                              "numpy": np.__version__, "os": platform.system()},
              "fixture": {"definition": "chainbench.numeric-input.v1", "kind": kind,
                          "dimension": problem.dim, "input_sha256": instance["input_sha256"],
                          "L": 1. if kind == "simplex" else problem.L,
                          "mu": problem.mu if kind == "quadratic" else None,
                          "f_star": problem.f_star, "x_star": problem.x_star.tolist(),
                          "start": "stored_vector",
                          "stationarity_metric": {"quadratic": "gradient_norm",
                                                  "diagonal-lasso": "proximal_gradient_mapping_norm",
                                                  "simplex": "frank_wolfe_gap"}[kind]},
              "runs": observe_problem(problem, instance["run"], x0=x0)}
    _bounded_json(result, MAX_REPORT_BYTES)
    return result


def _number(value, name: str, *, nonnegative: bool = False) -> None:
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or (nonnegative and value < 0):
        raise ValueError(f"invalid finite observation: {name}")


def validate_instance_report(saved: dict) -> None:
    """Validate structure and exact input/setting bindings before rerunning a solver."""
    _bounded_json(saved, MAX_REPORT_BYTES)
    _object(saved, REPORT_KEYS, REPORT_KEYS, "instance report")
    _version(saved["schema_version"])
    if saved["kind"] != "chainbench.instance-experiment" or saved["notice"] != NOTICE:
        raise ValueError("unsupported instance report kind or observation notice")
    instance = saved["instance"]
    problem, x0 = validate_instance(instance)
    env_keys = {"chainbench", "python", "numpy", "os"}
    env = _object(saved["environment"], env_keys, env_keys, "execution environment")
    if any(type(v) is not str or not v or len(v) > 256 for v in env.values()):
        raise ValueError("execution environment requires four nonempty bounded strings")
    fixture = saved["fixture"]
    keys = {"definition", "kind", "dimension", "input_sha256", "L", "mu", "f_star",
            "x_star", "start", "stationarity_metric"}
    _object(fixture, keys, keys, "fixture")
    kind = instance["problem"]["kind"]
    exact = {"definition": "chainbench.numeric-input.v1", "kind": kind,
             "dimension": problem.dim, "input_sha256": instance["input_sha256"],
             "start": "stored_vector", "stationarity_metric": {
                 "quadratic": "gradient_norm", "diagonal-lasso": "proximal_gradient_mapping_norm",
                 "simplex": "frank_wolfe_gap"}[kind]}
    if any(type(fixture[k]) is not type(v) or fixture[k] != v for k, v in exact.items()):
        raise ValueError("fixture does not match sealed input provenance")
    _number(fixture["L"], "L", nonnegative=True)
    if fixture["L"] == 0:
        raise ValueError("fixture L must be positive")
    _number(fixture["f_star"], "f_star")
    if kind == "quadratic":
        _number(fixture["mu"], "mu", nonnegative=True)
    elif fixture["mu"] is not None:
        raise ValueError("mu is only recorded for quadratics")
    _vector(fixture["x_star"], "fixture.x_star", problem.dim)
    settings, runs = instance["run"], saved["runs"]
    if type(runs) is not list or len(runs) != len(settings["methods"]):
        raise ValueError("missing method records")
    run_keys = {"method", "parameters", "updates", "termination", "rows"}
    row_keys = {"iteration", "objective", "gap", "stationarity", "distance_to_reference"}
    if settings["include_iterates"]:
        row_keys.add("iterate")
    for method, run in zip(settings["methods"], runs):
        _object(run, run_keys, run_keys, "method record")
        updates = run["updates"]
        if (run["method"] != method or type(updates) is not int
                or not 0 <= updates <= settings["steps"]):
            raise ValueError("method identity or update count disagrees with settings")
        states = ("converged", "max_steps") if method == "cg" else ("budget_complete",)
        if run["termination"] not in states or (run["termination"] != "converged" and updates != settings["steps"]):
            raise ValueError("inconsistent termination")
        options = settings["method_options"].get(method, {})
        param_keys = ({"rtol", "atol", "stopping_threshold"} if method == "cg" else
                      {"proximal_parameter"} if method == "proximal-point" else
                      {"alpha", "beta"} if method == "heavy-ball" else
                      {"schedule"} if method == "frank-wolfe" else {"step_size"})
        params = _object(run["parameters"], param_keys, param_keys, "method parameters")
        if method == "frank-wolfe":
            if params["schedule"] != "gamma[k]=2/(k+2), k starts at 0":
                raise ValueError("unexpected Frank-Wolfe schedule")
        else:
            for key, value in params.items():
                _number(value, key, nonnegative=True)
            if any(type(params[k]) is not type(v) or params[k] != v for k, v in options.items()):
                raise ValueError("recorded method options disagree with sealed settings")
        rows = run["rows"]
        if type(rows) is not list or len(rows) != updates + 1:
            raise ValueError("missing trajectory rows")
        for k, row in enumerate(rows):
            _object(row, row_keys, row_keys, "trajectory row")
            if type(row["iteration"]) is not int or row["iteration"] != k:
                raise ValueError("invalid trajectory index")
            for key in ("objective", "gap", "stationarity", "distance_to_reference"):
                _number(row[key], key, nonnegative=key != "objective")
            if settings["include_iterates"]:
                point = _vector(row["iterate"], "iterate", problem.dim)
                if k == 0 and point.tobytes() != x0.tobytes():
                    raise ValueError("initial iterate does not match the exact stored x0")


def replay_instance(saved: dict, *, rtol: float = 1e-7, atol: float = 1e-12) -> dict:
    """Rerun stored arrays. Neither preset generation nor the seed is executed."""
    validate_instance_report(saved)
    for name, value in (("rtol", rtol), ("atol", atol)):
        _number(value, name, nonnegative=True)
        if value > 1:
            raise ValueError(f"{name} must not exceed 1")
    fresh = run_instance(saved["instance"])
    samples, mismatches, details = 0, 0, []
    def mismatch(path, a, b):
        nonlocal mismatches
        mismatches += 1
        if len(details) < 20:
            details.append({"path": path, "saved": a, "replayed": b})
    def compare(a, b, path):
        nonlocal samples
        if type(a) is dict and type(b) is dict:
            if set(a) != set(b):
                mismatch(path + ".keys", sorted(a), sorted(b))
            for key in sorted(set(a) & set(b)):
                compare(a[key], b[key], path + "." + key)
        elif type(a) is list and type(b) is list:
            if len(a) != len(b):
                mismatch(path + ".length", len(a), len(b))
            for index, (av, bv) in enumerate(zip(a, b)):
                compare(av, bv, f"{path}[{index}]")
        elif type(a) in (int, float) and type(b) in (int, float):
            samples += 1
            discrete = path.endswith((".iteration", ".updates", ".dimension"))
            different = ((type(a) is not type(b) or a != b) if discrete
                         else not math.isclose(a, b, rel_tol=rtol, abs_tol=atol))
            if different:
                mismatch(path, a, b)
        elif type(a) is not type(b) or a != b:
            mismatch(path, a, b)
    compare(saved["fixture"], fresh["fixture"], "fixture")
    compare(saved["runs"], fresh["runs"], "runs")
    return {"kind": "chainbench.instance-replay", "schema_version": 1,
            "status": "MISMATCH" if mismatches else "MATCH", "same_input_bytes": True,
            "numeric_samples_compared": samples, "mismatch_count": mismatches,
            "first_mismatches": details, "rtol": rtol, "atol": atol,
            "saved_record_sha256": _sha(saved), "saved_environment": copy.deepcopy(saved["environment"]),
            "replayed_environment": fresh["environment"],
            "environment_changed": saved["environment"] != fresh["environment"], "replayed": fresh,
            "notice": "MATCH means a rerun of these exact stored inputs agrees within the displayed tolerances. Hashes and MATCH cannot authenticate who generated or executed the original record. The declared seed is metadata, not rerun authority."}
