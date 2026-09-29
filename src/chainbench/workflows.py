"""Bounded one-factor sweeps and replay of saved experiment observations."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from html import escape
from numbers import Real

from ._pages import bi, evidence, page
from .experiments import MAX_WORK, canonical_json, config_digest, normalize_config, run_experiment
from .visuals import experiment_chart, render_line_chart


def _finite(value) -> bool:
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError):
        return False


MAX_REPORT_BYTES = 8_000_000
MAX_SWEEP_POINTS = 8
PARAMETERS = ("condition_number", "L", "lam", "dimension", "steps")


def work_proxy(config: dict) -> int:
    d, n = config["problem"]["dimension"], config["steps"]
    quadratic = config["problem"]["kind"] == "quadratic"
    return (max(n, 1)*(d*d if quadratic else d)*len(config["methods"])
            + (d**3 if quadratic else 0)
            + (n*d**3 if quadratic and "proximal-point" in config["methods"] else 0))


def run_sweep(base_config: dict, parameter: str, values: list[float]) -> dict:
    """Resolve every input and the total work budget before running any method."""
    base = normalize_config(base_config)
    if parameter not in PARAMETERS:
        raise ValueError(f"parameter must be one of {PARAMETERS}")
    if not isinstance(values, list) or not 2 <= len(values) <= MAX_SWEEP_POINTS:
        raise ValueError("a sweep needs 2 to 8 values")
    configs, resolved_values = [], []
    for raw in values:
        if isinstance(raw, bool) or not isinstance(raw, Real) or not _finite(raw):
            raise ValueError("sweep values must be finite real numbers")
        value = float(raw)
        if parameter in ("dimension", "steps"):
            if not value.is_integer():
                raise ValueError("dimension and steps must be integers")
            value = int(value)
        candidate = copy.deepcopy(base)
        target = candidate if parameter == "steps" else candidate["problem"]
        target[parameter] = value
        configs.append(normalize_config(candidate))
        resolved_values.append(value)
    if len(set(resolved_values)) != len(resolved_values):
        raise ValueError("duplicate sweep values are not allowed")
    total = sum(work_proxy(c) for c in configs)
    if total > MAX_WORK:
        raise ValueError("combined sweep exceeds work limit; reduce points, size or methods")
    runs = [run_experiment(c) for c in configs]
    return {"kind": "chainbench.sweep", "schema_version": 1, "parameter": parameter,
            "values": resolved_values, "base_config": base, "total_work_proxy": total,
            "configs_sha256": hashlib.sha256(canonical_json(configs).encode()).hexdigest(),
            "experiments": runs,
            "notice": "One requested configuration field varies. Derived spectral constants, inputs and optimal values may change too. Equal updates are not equal work; this is not a universal ranking or a worst-case search."}


def sweep_html(result: dict, lang: str = "en") -> str:
    parameter, experiments = result["parameter"], result["experiments"]
    intro = bi('조건 하나만 바꾸면 곡선이 어떻게 달라지는지 비교합니다. 각 패널의 문제·시작점·종료 기준을 함께 확인하세요.', 'Vary one configuration field and inspect each trajectory with its input and stopping context.')
    panels = []
    for index, (value, exp) in enumerate(zip(result["values"], experiments)):
        title = f'{parameter} = {value:g}'
        plot = render_line_chart(experiment_chart(exp, "gap", title, "objective gap"))
        config = escape(json.dumps(exp["config"], indent=2, ensure_ascii=False))
        panels.append(f'<section id="sample-{index}"><h2>{escape(title)}</h2><p class="small">'
                      + f'Dimension {exp["fixture"]["dimension"]} · Budget {exp["config"]["steps"]} · '
                      + escape(', '.join(exp["config"]["methods"])) + '</p><div class="plot">' + plot
                      + '</div><details><summary>' + bi('이 패널의 설정', 'Configuration for this panel')
                      + '</summary><pre>' + config + '</pre></details></section>')
    nav = '<nav class="panel">' + ''.join(f'<a href="#sample-{i}">{escape(parameter)}={v:g}</a>' for i, v in enumerate(result["values"])) + '</nav>'
    warning = '<p class="callout caution">' + bi('패널마다 y축 범위가 다를 수 있습니다. 선의 기울기나 높이만 비교하지 말고 축 눈금을 보세요. L·차원·정규화 계수가 바뀌면 목적함수의 척도도 달라지므로 최종 gap만으로 순위를 매기지 않습니다.', 'Y-axis ranges are per panel. Check tick values, not just slope or height. Changes to L, dimension or regularization can change objective scale; final gaps alone are not a fair ranking.') + '</p>'
    return page('One change · several trajectories', intro, nav + warning + ''.join(panels) + evidence(result, 'sweep.json'), lang=lang)


def load_report(text: str) -> dict:
    """No external paths, code execution or non-standard JSON are accepted."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_REPORT_BYTES:
        raise ValueError("saved report exceeds the byte limit")
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError(f"duplicate JSON key: {k}")
            out[k] = v
        return out
    def invalid(value):
        raise ValueError(f"non-standard JSON number: {value}")
    try:
        result = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
    except (RecursionError, OverflowError) as exc:
        raise ValueError("report is too deeply nested or numeric input overflows") from exc
    validate_saved_experiment(result)
    return result


def validate_saved_experiment(report: dict) -> None:
    """Validate a complete schema-1 experiment before recomputing its bounded config."""
    expected = {"kind", "schema_version", "config", "config_sha256", "environment", "fixture", "notice", "runs"}
    if not isinstance(report, dict) or set(report) != expected:
        raise ValueError("expected a complete chainbench.experiment JSON report, not a config")
    if report["kind"] != "chainbench.experiment" or type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise ValueError("unsupported experiment report schema")
    config = normalize_config(report["config"])
    if canonical_json(report["config"]) != canonical_json(config) or report["config_sha256"] != config_digest(config):
        raise ValueError("saved config is not normalized or its digest is inconsistent")
    env = report["environment"]
    if not isinstance(env, dict) or set(env) != {"chainbench", "python", "numpy", "os"} or any(not isinstance(v, str) or not v or len(v) > 256 for v in env.values()):
        raise ValueError("missing execution environment")
    fixture = report["fixture"]
    keys = {"definition", "kind", "dimension", "input_sha256", "L", "mu", "f_star", "stationarity_metric", "start"}
    if not isinstance(fixture, dict) or set(fixture) != keys:
        raise ValueError("missing fixture provenance")
    fingerprint = fixture["input_sha256"]
    if (not isinstance(fingerprint, str) or len(fingerprint) != 64
            or any(c not in '0123456789abcdef' for c in fingerprint)):
        raise ValueError("invalid input digest")
    if fixture["kind"] != config["problem"]["kind"] or type(fixture["dimension"]) is not int or fixture["dimension"] != config["problem"]["dimension"]:
        raise ValueError("fixture does not agree with config")
    runs = report["runs"]
    if not isinstance(runs, list) or len(runs) != len(config["methods"]):
        raise ValueError("missing method observations")
    row_keys = {"iteration", "objective", "gap", "stationarity", "distance_to_reference"}
    if config["include_iterates"]:
        row_keys.add("iterate")
    for method, run in zip(config["methods"], runs):
        if not isinstance(run, dict) or set(run) != {"method", "parameters", "updates", "termination", "rows"} or run["method"] != method:
            raise ValueError("invalid method record")
        updates = run["updates"]
        if type(updates) is not int or not 0 <= updates <= config["steps"]:
            raise ValueError("invalid update count")
        termination = run["termination"]
        states = ("converged", "max_steps") if method == "cg" else ("budget_complete",)
        if termination not in states or (termination != "converged" and updates != config["steps"]):
            raise ValueError("inconsistent termination")
        rows = run["rows"]
        if not isinstance(rows, list) or len(rows) != updates + 1 or not isinstance(run["parameters"], dict):
            raise ValueError("missing trajectory or parameters")
        for k, row in enumerate(rows):
            if not isinstance(row, dict) or set(row) != row_keys or type(row["iteration"]) is not int or row["iteration"] != k:
                raise ValueError("invalid trajectory indices/fields")
            for key in ("objective", "gap", "stationarity", "distance_to_reference"):
                if type(row[key]) not in (int, float) or not _finite(row[key]) or (key != "objective" and row[key] < 0):
                    raise ValueError("missing, negative or non-finite observation")
            if config["include_iterates"] and (not isinstance(row["iterate"], list) or len(row["iterate"]) != fixture["dimension"] or any(type(v) not in (int, float) or not _finite(v) for v in row["iterate"])):
                raise ValueError("invalid saved iterate")
    def finite_tree(value, depth=0):
        if depth > 16:
            raise ValueError("report is too deeply nested")
        if isinstance(value, dict):
            for v in value.values():
                finite_tree(v, depth+1)
        elif isinstance(value, list):
            for v in value:
                finite_tree(v, depth+1)
        elif type(value) in (int, float) and not _finite(value):
            raise ValueError("non-finite metadata")
    finite_tree(report)


def replay_experiment(saved: dict, *, rtol: float = 1e-7, atol: float = 1e-12) -> dict:
    validate_saved_experiment(saved)
    for name, v in (("rtol", rtol), ("atol", atol)):
        if type(v) not in (int, float) or not _finite(v) or not 0 <= v <= 1:
            raise ValueError(f"{name} must be finite and between 0 and 1")
    fresh = run_experiment(saved["config"])
    details, mismatches, compared = [], 0, 0
    def mismatch(path, a, b):
        nonlocal mismatches
        mismatches += 1
        if len(details) < 20:
            details.append({"path": path, "saved": a, "replayed": b})
    def compare(a, b, path):
        nonlocal compared
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a) != set(b):
                mismatch(path+'.keys', sorted(a), sorted(b))
            for key in sorted(set(a) & set(b)):
                compare(a[key], b[key], path+'.'+key)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                mismatch(path+'.length', len(a), len(b))
            for i, (av, bv) in enumerate(zip(a, b)):
                compare(av, bv, f'{path}[{i}]')
        elif type(a) in (int, float) and type(b) in (int, float):
            compared += 1
            # Dimensions, indices and update budgets are discrete, never tolerant.
            discrete = path.endswith(('.iteration', '.updates', '.dimension'))
            if (a != b if discrete else not math.isclose(a, b, rel_tol=rtol, abs_tol=atol)):
                mismatch(path, a, b)
        elif type(a) is not type(b) or a != b:
            mismatch(path, a, b)
    compare(saved["runs"], fresh["runs"], "runs")
    compare({k:v for k,v in saved["fixture"].items() if k != 'input_sha256'},
            {k:v for k,v in fresh["fixture"].items() if k != 'input_sha256'}, "fixture")
    same_input = saved["fixture"]["input_sha256"] == fresh["fixture"]["input_sha256"]
    status = "MISMATCH" if mismatches else "MATCH" if same_input else "INPUT_DIFFERENCE"
    return {"kind": "chainbench.replay", "schema_version": 1, "status": status,
            "numeric_samples_compared": compared, "mismatch_count": mismatches, "first_mismatches": details,
            "same_input_bytes": same_input, "rtol": rtol, "atol": atol,
            "saved_environment": saved["environment"], "replayed_environment": fresh["environment"],
            "environment_changed": saved["environment"] != fresh["environment"],
            "saved_record_sha256": hashlib.sha256(canonical_json(saved).encode()).hexdigest(),
            "replayed": fresh,
            "notice": "MATCH means these recorded observations agree with this rerun within the displayed tolerances and input bytes match. It cannot authenticate who ran the saved report or certify any theorem. Environment differences remain visible."}


def replay_html(result: dict, lang: str = "en") -> str:
    intro = bi('저장된 설정으로 실제로 다시 실행하고, 원래 결과와 항목별로 대조합니다.', 'Run the saved configuration again and compare the actual observations field by field.')
    body = ('<section><h2>' + escape(result["status"]) + '</h2><p>'
            + bi('대조한 수치 항목', 'Numeric samples compared') + f': {result["numeric_samples_compared"]} · '
            + bi('차이', 'Mismatches') + f': {result["mismatch_count"]}</p><p>'
            + f'rtol={result["rtol"]:g} · atol={result["atol"]:g}</p><p>'
            + bi('입력 바이트 일치', 'Matching input bytes') + ': ' + str(result["same_input_bytes"])
            + ' · ' + bi('환경 변경', 'Environment changed') + ': ' + str(result["environment_changed"])
            + '</p><p class="callout caution">' + bi('MATCH는 이 재실행과의 일치입니다. 누가 원본을 실행했는지, 보고서가 진짜인지, 정리가 참인지를 인증하지 않습니다. 입력 해시가 다르면 수치가 비슷해도 별도로 표시합니다.', 'MATCH is agreement with this rerun, not authentication, adoption evidence or a theorem certificate. An input-digest difference is reported even if numbers are close.')
            + '</p></section>' + evidence(result, 'replay.json'))
    return page('Replay · inspect the evidence', intro, body, lang=lang)
