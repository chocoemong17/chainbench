"""Bounded comparison of recorded observations, without rerunning a solver."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from itertools import combinations
from pathlib import Path

from .experiments import canonical_json
from .visuals import ChartSpec, LineSeries
from .workflows import MAX_REPORT_BYTES, load_report, validate_saved_experiment

MAX_COMPARISON_BYTES = 16_000_000
METRICS = {
    "gap": "objective gap",
    "stationarity": "stationarity",
    "distance_to_reference": "distance to reference",
}
NOTICE = (
    "Comparison of supplied schema-1 observations, not a rerun or authentication. "
    "Matching declared input fingerprints do not verify the actual input arrays or authorship. "
    "Different objectives can have different scales; equal updates are not equal work. "
    "No solver ranking, theorem certificate or independent reproduction is inferred."
)


def _number(value, name, *, positive=False, nonnegative=False):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid or (positive and value <= 0) or (nonnegative and value < 0):
        raise ValueError(f"invalid finite {name}")


def _validate_metadata(report):
    """Narrow schema-1 metadata contract; no array generation or spectral setup."""
    validate_saved_experiment(report)
    f, config = report["fixture"], report["config"]
    kind = f["kind"]
    metrics = {"quadratic": "gradient_norm", "diagonal-lasso": "proximal_gradient_mapping_norm",
               "simplex": "frank_wolfe_gap"}
    if (f["definition"] != "chainbench.deterministic.v1"
            or f["stationarity_metric"] != metrics[kind]
            or f["start"] != ("first_simplex_vertex" if kind == "simplex" else "zeros")):
        raise ValueError("unsupported fixture definition, stationarity metric or start")
    _number(f["L"], "fixture.L", positive=True)
    _number(f["f_star"], "fixture.f_star")
    if kind == "quadratic":
        _number(f["mu"], "fixture.mu", positive=True)
        if f["mu"] > f["L"]:
            raise ValueError("fixture.mu exceeds fixture.L")
    elif f["mu"] is not None:
        raise ValueError("nonquadratic fixture.mu must be null")
    if not isinstance(report["notice"], str) or not 1 <= len(report["notice"]) <= 4096:
        raise ValueError("invalid report notice")
    for run in report["runs"]:
        method, parameters = run["method"], run["parameters"]
        options = config["method_options"].get(method, {})
        extra = ({"step_size"} if method in ("gd", "smooth-fista", "ista", "fista")
                 else {"alpha", "beta"} if method == "heavy-ball"
                 else {"stopping_threshold"} if method == "cg"
                 else {"schedule"} if method == "frank-wolfe" else set())
        if set(parameters) != set(options) | extra:
            raise ValueError("invalid method parameter fields")
        for key, value in parameters.items():
            if key == "schedule":
                if value != "gamma[k]=2/(k+2), k starts at 0":
                    raise ValueError("unsupported Frank-Wolfe schedule")
                continue
            _number(value, f"parameter.{key}", nonnegative=True)
            if key in ("step_size", "alpha", "proximal_parameter") and value <= 0:
                raise ValueError("step parameters must be positive")
            if key == "beta" and value >= 1:
                raise ValueError("heavy-ball beta must be below one")
        if any(parameters[k] != v for k, v in options.items()):
            raise ValueError("method parameters disagree with config")


def read_comparison_inputs(paths: list[Path]) -> list[dict]:
    if not 2 <= len(paths) <= 4:
        raise ValueError("compare needs two to four saved experiment reports")
    reports, total = [], 0
    for path in paths:
        if not path.is_file():
            raise ValueError("comparison inputs must be regular local files")
        with path.open("rb") as stream:
            raw = stream.read(min(MAX_REPORT_BYTES, MAX_COMPARISON_BYTES - total) + 1)
        total += len(raw)
        if len(raw) > MAX_REPORT_BYTES or total > MAX_COMPARISON_BYTES:
            raise ValueError("comparison exceeds the per-record or combined byte limit")
        reports.append(load_report(raw.decode("utf-8")))
    return reports


def _differences(left, right):
    return [{"field": key, "left": left.get(key), "right": right.get(key)}
            for key in sorted(set(left) | set(right))
            if canonical_json(left.get(key)) != canonical_json(right.get(key))
            or (key in left) != (key in right)]


def compare_experiments(reports: list[dict], *, metric: str = "gap") -> dict:
    """Preserve records; diagnostics describe their claims, not their authenticity."""
    if not isinstance(reports, list) or not 2 <= len(reports) <= 4:
        raise ValueError("compare needs two to four saved experiment reports")
    if not isinstance(metric, str) or metric not in METRICS:
        raise ValueError("unsupported comparison metric")
    records, total = [], 0
    for index, report in enumerate(reports):
        try:
            text = canonical_json(report)
        except (TypeError, RecursionError, OverflowError) as exc:
            raise ValueError("report must contain bounded JSON data") from exc
        size = len(text.encode("utf-8"))
        total += size
        if size > MAX_REPORT_BYTES or total > MAX_COMPARISON_BYTES:
            raise ValueError("comparison exceeds the per-record or combined byte limit")
        # JSON also detaches caller-owned data; tuples/custom mappings cannot be inputs.
        _validate_metadata(report)
        records.append({"id": chr(65 + index), "record_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "experiment": json.loads(text)})
    pairs = []
    for left, right in combinations(records, 2):
        a, b = left["experiment"], right["experiment"]
        config_diff = _differences(a["config"], b["config"])
        fixture_diff = _differences(a["fixture"], b["fixture"])
        common = [m for m in a["config"]["methods"] if m in b["config"]["methods"]]
        pairs.append({
            "left": left["id"], "right": right["id"],
            "identical_record": left["record_sha256"] == right["record_sha256"],
            "same_config": not config_diff,
            "same_input_digest": a["fixture"]["input_sha256"] == b["fixture"]["input_sha256"],
            "same_recorded_problem": (not fixture_diff and a["config"]["problem"] == b["config"]["problem"]),
            "same_environment": a["environment"] == b["environment"],
            "shared_methods": common,
            "config_differences": config_diff, "fixture_differences": fixture_diff,
            "environment_differences": _differences(a["environment"], b["environment"]),
            "parameter_differences": _differences(
                {r["method"]: r["parameters"] for r in a["runs"]},
                {r["method"]: r["parameters"] for r in b["runs"]}),
        })
    shared_problem = all(p["same_recorded_problem"] for p in pairs)
    charts = []

    def chart(title, selections):
        series = tuple(LineSeries(f'{record["id"]} · {run["method"]}',
                                  tuple(row["iteration"] for row in run["rows"]),
                                  tuple(row[metric] for row in run["rows"]))
                       for record, run in selections)
        label = METRICS[metric]
        if metric == "stationarity":
            label = selections[0][0]["experiment"]["fixture"]["stationarity_metric"].replace("_", " ")
        return asdict(ChartSpec(title, "recorded iteration k", label, series))

    for record in records:
        charts.append({"id": "record-" + record["id"], "records": [record["id"]],
                       "chart": chart(f'Record {record["id"]}', [(record, r) for r in record["experiment"]["runs"]])})
    if shared_problem:
        methods = list(dict.fromkeys(r["method"] for record in records for r in record["experiment"]["runs"]))
        for method in methods:
            selected = [(record, run) for record in records for run in record["experiment"]["runs"]
                        if run["method"] == method]
            if len(selected) >= 2:
                charts.append({"id": "shared-" + method, "records": [r["id"] for r, _ in selected],
                               "chart": chart(method + " · shared recorded problem", selected)})
    return {"kind": "chainbench.comparison", "schema_version": 1, "metric": metric,
            "records": records, "pairs": pairs, "shared_recorded_problem": shared_problem,
            "charts": json.loads(canonical_json(charts)), "notice": NOTICE}
