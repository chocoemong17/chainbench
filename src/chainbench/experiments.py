"""Configurable, local-only experiments. Observations are not theorem certificates."""
from __future__ import annotations

import copy
import hashlib
import json
import platform
from typing import Any

import numpy as np

from . import __version__
from ._validation import count, scalar
from .methods import (
    accelerated_gradient,
    conjugate_gradient,
    fista,
    frank_wolfe,
    gradient_descent,
    heavy_ball,
    ista,
    proximal_point,
)
from .problems import (
    DiagonalLassoProblem,
    QuadraticProblem,
    SimplexQuadraticProblem,
    diagonal_lasso,
    simplex_quadratic,
)

SCHEMA_VERSION = 1
MAX_CONFIG_BYTES = 16_384
MAX_DIMENSION = 256
MAX_STEPS = 2_000
MAX_WORK = 100_000_000  # Conservative size proxy, not a runtime guarantee.
METHODS = {
    "quadratic": ("gd", "smooth-fista", "heavy-ball", "cg", "proximal-point"),
    "diagonal-lasso": ("ista", "fista"),
    "simplex": ("frank-wolfe",),
}
PRESETS = tuple(METHODS)
NOTICE = (
    "Finite deterministic observations, not a proof, solver certification or universal ranking. "
    "Equal iteration budgets do not imply equal work: CG rechecks residuals, proximal point "
    "solves a linear system, and dense spectral setup is outside the iteration budget."
)


def _object(value: Any, allowed: set[str], required: set[str], name: str) -> dict:
    if not isinstance(value, dict) or any(not isinstance(k, str) for k in value):
        raise ValueError(f"{name} must be a JSON object")
    extra, missing = set(value) - allowed, required - set(value)
    if extra or missing:
        raise ValueError(f"{name}: unknown keys={sorted(extra)}, missing keys={sorted(missing)}")
    return value


def _choice(value: Any, choices: tuple[str, ...], name: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{name} must be one of {', '.join(choices)}")
    return value


def _bounded(value: Any, name: str, lo: float, hi: float) -> float:
    try:
        value = scalar(value, name)
    except OverflowError as exc:
        raise ValueError(f"{name} cannot be represented as a float") from exc
    if not lo <= value <= hi:
        raise ValueError(f"{name} must be between {lo:g} and {hi:g}")
    return value


def normalize_config(config: dict) -> dict:
    """Return a detached, fully resolved configuration, rejecting unknown fields.

    Deliberately bounded presets are a teaching interface, not an arbitrary-data
    solver service. These size limits do not limit the underlying Python methods.
    """
    raw = _object(config, {"schema_version", "problem", "methods", "steps", "include_iterates",
                           "method_options"}, {"schema_version", "problem"}, "config")
    if count(raw["schema_version"], "schema_version", 1) != SCHEMA_VERSION:
        raise ValueError("unsupported config schema_version")
    p = _object(raw["problem"], {"kind", "dimension", "condition_number", "L", "rotation", "lam"},
                {"kind"}, "problem")
    kind = _choice(p["kind"], PRESETS, "problem.kind")
    fields = {"kind", "dimension"}
    fields |= {"condition_number", "L", "rotation"} if kind == "quadratic" else set()
    fields |= {"lam"} if kind == "diagonal-lasso" else set()
    _object(p, fields, {"kind"}, "problem")
    dim = count(p.get("dimension", 12), "dimension", 2)
    steps = count(raw.get("steps", 30), "steps")
    if dim > MAX_DIMENSION or steps > MAX_STEPS:
        raise ValueError(f"experiment limits: dimension<={MAX_DIMENSION}, steps<={MAX_STEPS}")
    problem = {"kind": kind, "dimension": dim}
    if kind == "quadratic":
        problem.update({
            "condition_number": _bounded(p.get("condition_number", 10.), "condition_number", 1, 1e6),
            "L": _bounded(p.get("L", 1.), "L", 1e-6, 1e6),
            "rotation": _choice(p.get("rotation", "householder"), ("householder", "none"), "rotation"),
        })
    elif kind == "diagonal-lasso":
        problem["lam"] = _bounded(p.get("lam", .12), "lam", 0, 1e3)
    return {"schema_version": SCHEMA_VERSION, "problem": problem,
            **normalize_execution(raw, kind, dim)}


def normalize_execution(raw: dict, kind: str, dim: int) -> dict:
    """Shared bounded method settings; callers validate their own input schema."""
    steps = count(raw.get("steps", 30), "steps")
    if steps > MAX_STEPS:
        raise ValueError(f"steps must not exceed {MAX_STEPS}")
    methods = raw.get("methods", list(METHODS[kind]))
    if not isinstance(methods, list) or not methods:
        raise ValueError("methods must be a nonempty list")
    for method in methods:
        _choice(method, METHODS[kind], "method")
    if len(set(methods)) != len(methods):
        raise ValueError("duplicate methods are not allowed")
    include = raw.get("include_iterates", False)
    if type(include) is not bool:
        raise ValueError("include_iterates must be a JSON boolean")
    options = _object(raw.get("method_options", {}), set(methods) & {"cg", "proximal-point"},
                      set(), "method_options")
    resolved = {}
    if "cg" in methods:
        cg = _object(options.get("cg", {}), {"rtol", "atol"}, set(), "cg options")
        resolved["cg"] = {
            "rtol": _bounded(cg.get("rtol", 1e-12), "cg.rtol", 0, 1),
            "atol": _bounded(cg.get("atol", 0.), "cg.atol", 0, 1e6),
        }
    if "proximal-point" in methods:
        pp = _object(options.get("proximal-point", {}), {"proximal_parameter"}, set(), "PPA options")
        resolved["proximal-point"] = {
            "proximal_parameter": _bounded(pp.get("proximal_parameter", 1.),
                                           "proximal_parameter", 1e-6, 1e6),
        }
    unit = dim * dim if kind == "quadratic" else dim
    work = max(steps, 1) * unit * len(methods)
    if kind == "quadratic":
        work += dim ** 3  # Spectral/rotation setup.
        if "proximal-point" in methods:
            work += steps * dim ** 3
    if work > MAX_WORK:
        raise ValueError("experiment exceeds the work limit; reduce dimension, steps or methods")
    return {"steps": steps,
            "methods": list(methods), "method_options": resolved, "include_iterates": include}


def preset_config(name: str) -> dict:
    """Get a detached preset that is installed as Python code (no checkout needed)."""
    name = _choice(name, PRESETS, "preset")
    return normalize_config({"schema_version": SCHEMA_VERSION, "problem": {"kind": name}})


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def config_digest(config: dict) -> str:
    return hashlib.sha256(canonical_json(normalize_config(config)).encode("utf-8")).hexdigest()


def load_config(text: str) -> dict:
    """Parse strict JSON; duplicate keys, NaN/Infinity and oversized inputs fail."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise ValueError(f"config must be UTF-8 JSON of at most {MAX_CONFIG_BYTES} bytes")

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
        raw = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
    except (RecursionError, OverflowError) as exc:
        raise ValueError("config is too deeply nested or contains an unrepresentable number") from exc
    return normalize_config(raw)


def _problem(config: dict):
    p, dim = config["problem"], config["problem"]["dimension"]
    if p["kind"] == "diagonal-lasso":
        return diagonal_lasso(dim, p["lam"])
    if p["kind"] == "simplex":
        return simplex_quadratic(dim)
    eig = np.geomspace(p["L"] / p["condition_number"], p["L"], dim)
    q = np.diag(eig)
    if p["rotation"] == "householder":
        u = np.arange(1, dim + 1, dtype=float)
        u /= np.linalg.norm(u)
        rotation = np.eye(dim) - 2 * np.outer(u, u)
        q = rotation @ q @ rotation.T
        q = .5 * q + .5 * q.T
    xs = np.linspace(-1, 1, dim)
    return QuadraticProblem(q, q @ xs, xs)


def _input_digest(problem) -> str:
    """Digest exact little-endian float64 inputs; not promised identical across BLAS builds."""
    h = hashlib.sha256()
    if isinstance(problem, QuadraticProblem):
        items = (("Q", problem.Q), ("b", problem.b), ("x_star", problem.x_star))
    elif isinstance(problem, DiagonalLassoProblem):
        items = (("a", problem.a), ("b", problem.b), ("lam", np.array([problem.lam])))
    else:
        items = (("target", problem.target),)
    for name, value in items:
        data = np.asarray(value, dtype="<f8", order="C")
        h.update(canonical_json({"name": name, "shape": list(data.shape)}).encode("ascii") + b"\0")
        h.update(data.tobytes(order="C"))
    return h.hexdigest()


def _stationarity(problem, x: np.ndarray) -> float:
    if isinstance(problem, QuadraticProblem):
        return float(np.hypot.reduce(problem.grad(x)))
    if isinstance(problem, DiagonalLassoProblem):
        step = 1 / problem.L
        mapping = (x - problem.prox_l1(x - step * problem.smooth_grad(x), step)) / step
        return float(np.hypot.reduce(mapping))
    g = problem.grad(x)
    gap = float(g @ (x - problem.linear_minimizer(g)))
    # At a simplex optimum the arithmetic gap can be slightly negative.
    if gap < -1e-12:
        raise FloatingPointError("negative Frank-Wolfe gap; feasibility or arithmetic failure")
    return max(0., gap)


def observe_problem(problem, normalized: dict, *, x0: np.ndarray | None = None) -> list[dict]:
    """Observe the existing recurrences on supplied inputs without generating a fixture."""
    steps = normalized["steps"]
    start = {} if x0 is None else {"x0": x0}
    dispatch = {"gd": gradient_descent, "smooth-fista": accelerated_gradient,
                "cg": conjugate_gradient, "proximal-point": proximal_point,
                "ista": ista, "fista": fista, "frank-wolfe": frank_wolfe}
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        runs = []
        for method in normalized["methods"]:
            options = normalized["method_options"].get(method, {})
            parameters = copy.deepcopy(options)
            if method in ("gd", "smooth-fista", "ista", "fista"):
                parameters["step_size"] = 1 / problem.L
            elif method == "frank-wolfe":
                parameters["schedule"] = "gamma[k]=2/(k+2), k starts at 0"
            if method == "heavy-ball":
                trace, alpha, beta = heavy_ball(problem, steps, **start)
                parameters.update({"alpha": alpha, "beta": beta})
            else:
                trace = dispatch[method](problem, steps, **start, **options)
            updates = len(trace.iterates) - 1
            if len(trace.values) != updates + 1 or not 0 <= updates <= steps:
                raise ValueError("method returned a malformed trajectory")
            termination = "budget_complete"
            if method == "cg":
                tolerance = max(options["atol"], options["rtol"] * _stationarity(problem, trace.iterates[0]))
                actual = _stationarity(problem, trace.iterates[-1])
                termination = "converged" if actual <= tolerance else "max_steps"
                if trace.termination != termination or (termination == "max_steps" and updates != steps):
                    raise ValueError("CG termination disagrees with the measured true residual")
                parameters["stopping_threshold"] = tolerance
            elif updates != steps:
                raise ValueError("fixed-budget method returned fewer updates than requested")
            rows = []
            for k, x in enumerate(trace.iterates):
                row = {"iteration": k, "objective": float(problem.value(x)),
                       "gap": float(problem.gap(x)), "stationarity": _stationarity(problem, x),
                       "distance_to_reference": float(np.hypot.reduce(x - problem.x_star))}
                if any(not np.isfinite(v) for v in row.values()):
                    raise FloatingPointError("non-finite trajectory observation")
                if any(row[key] < 0 for key in ("gap", "stationarity", "distance_to_reference")):
                    raise FloatingPointError("negative trajectory error observation")
                if normalized["include_iterates"]:
                    row["iterate"] = x.tolist()
                rows.append(row)
            runs.append({"method": method, "parameters": parameters, "updates": updates,
                         "termination": termination, "rows": rows})
    return runs


def run_experiment(config: dict) -> dict:
    """Run selected existing algorithms and return a JSON-serializable provenance envelope.

    No network, arbitrary code, external file references, wall-clock leaderboard or
    theorem pass/fail labels are part of this interface.
    """
    normalized = normalize_config(config)
    kind = normalized["problem"]["kind"]
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        problem = _problem(normalized)
        runs = observe_problem(problem, normalized)
        metric = {"quadratic": "gradient_norm", "diagonal-lasso": "proximal_gradient_mapping_norm",
                  "simplex": "frank_wolfe_gap"}[kind]
        fixture = {"definition": "chainbench.deterministic.v1", "kind": kind,
                   "dimension": problem.dim, "input_sha256": _input_digest(problem),
                   "L": problem.L if not isinstance(problem, SimplexQuadraticProblem) else 1.,
                   "mu": problem.mu if isinstance(problem, QuadraticProblem) else None,
                   "f_star": problem.f_star, "stationarity_metric": metric,
                   "start": "first_simplex_vertex" if kind == "simplex" else "zeros"}
    result = {"kind": "chainbench.experiment", "schema_version": SCHEMA_VERSION,
              "config": normalized, "config_sha256": config_digest(normalized),
              "environment": {"chainbench": __version__, "python": platform.python_version(),
                              "numpy": np.__version__, "os": platform.system()},
              "fixture": fixture, "notice": NOTICE, "runs": runs}
    # Fail before a report can be presented as complete if any metadata is non-finite.
    json.dumps(result, allow_nan=False)
    return result
