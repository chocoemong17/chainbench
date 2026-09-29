"""Offline review helper for the *published* ChainBench 0.2.0 wheel.

This is review infrastructure, not a new package version or a theorem validator.
No network calls, installation, uploads, arbitrary configs or shell execution.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import re
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

VERSION = "0.2.0"
SOURCE_COMMIT = "a5a274f9f5891a84cbb9acc4e2df8d1e0584491c"
WHEEL_SHA256 = "34173a4d0e2dc731602ec45db0c99acc17c27da26e702410d843194bbeaed069"
KIT_VERSION = 1
MAX_BYTES = 2_000_000
MODULE_HASHES = {
    "__init__.py": "c3ec5a58e77dd7b887c4ef9cfb8dd2c8d69464933330e9c75d1849d4c0b56b6a",
    "__main__.py": "935a1c1166b0c1ea35a82256345000bf2c73ded718d77773bc27a71ecce28f7d",
    "_validation.py": "a8cb68dddb3dcf781a3032ef89bb0e0f4a6e8774f7c905be13c8f3c13184d505",
    "checks.py": "4d7472a31ef5776590302be9d0d01684d0325eb5b7162475e15b7c48ff8ca9c7",
    "cli.py": "b3d9c65c43caf28f69544e20006f3de430322852ab56208a19539810f767dadb",
    "experiment_reporting.py": "11442c535ef206b32d65f522de9c79ce7360d2946ea0ede6c775a4536d8b7c79",
    "experiments.py": "d8c304f5fdc37fee5d8cbdb35a0e2907c304f419476584e8fbe99ff67c4b7410",
    "methods.py": "4722ef2ea06adfd285bc121937bf6b08c374c78ac1136b2570878dc6bda48517",
    "problems.py": "9eea0dce74bfbde03f33c672ef928aabc5924fd8e5f7ff373fd05c606dc840cb",
    "reporting.py": "8cf7907cadbefb3a80bf2b2d99f2ace660b8679613d21e2b38d565cadf92d5fe"
}
SLUGS = (
    "gd-baseline", "nesterov-1983", "polyak-1964", "hestenes-stiefel-1952",
    "jaggi-2013", "rockafellar-1976", "beck-teboulle-2009", "ista-vs-fista",
)
METHODS = {
    "quadratic": ["gd", "smooth-fista", "heavy-ball", "cg", "proximal-point"],
    "diagonal-lasso": ["ista", "fista"], "simplex": ["frank-wolfe"],
}
METRICS = {
    "quadratic": "gradient_norm", "diagonal-lasso": "proximal_gradient_mapping_norm",
    "simplex": "frank_wolfe_gap",
}
ENV_KEYS = {"chainbench", "python", "numpy", "os"}
STEPS = ("source_bytes", "check_suite", "preset_reruns", "tiny_gd_oracle", "negative_inputs")
NOTICE = (
    "Locally collected, self-reported observations. Not independent review, proof of execution, "
    "endorsement, security attestation or theorem certification. Inspect before sharing. "
    "This file deliberately excludes names, emails, hostnames, paths, timestamps and raw logs."
)


class ReviewError(ValueError):
    """A bounded public error message; never include subprocess output or local paths."""


def require(condition, message: str) -> None:
    if not condition:
        raise ReviewError(message)


def number(value, *, nonnegative=False) -> float:
    require(type(value) in (int, float), "Missing or nonnumeric observation")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ReviewError("Observation outside floating-point range") from exc
    require(math.isfinite(result), "Nonfinite observation")
    require(not nonnegative or result >= 0, "Negative error metric")
    return result


def integer(value, lo: int, hi: int) -> int:
    require(type(value) is int and lo <= value <= hi, "Invalid integer field")
    return value


def obj(value, keys: set[str]) -> dict:
    require(type(value) is dict and set(value) == keys, "Unexpected or missing object fields")
    return value


def canonical(value) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, RecursionError, OverflowError) as exc:
        raise ReviewError("Unrepresentable JSON value") from exc


def digest(value) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def strict_json(text: str):
    require(isinstance(text, str) and len(text.encode("utf-8")) <= MAX_BYTES,
            "JSON exceeds review size limit")

    # Bound nesting explicitly: Python JSON recursion limits vary across releases.
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            require(depth <= 32, "Review JSON nesting exceeds 32 levels")
        elif char in "]}":
            depth -= 1

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result

    def invalid(_):
        raise ReviewError("Nonstandard JSON number")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, RecursionError, OverflowError) as exc:
        raise ReviewError("Invalid, duplicate-key or too-deep JSON") from exc


def load(path: Path):
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        require(len(raw) <= MAX_BYTES, "Review file exceeds size limit")
        if raw.startswith(b"\x1f\x8b"):
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                raw = stream.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES, "Expanded review exceeds size limit")
        return strict_json(raw.decode("utf-8"))
    except (OSError, UnicodeError, EOFError, zlib.error) as exc:
        raise ReviewError("Cannot read a UTF-8 review file") from exc


def write_new(path: Path, value) -> None:
    """Serialize before opening; never overwrite or follow an existing output symlink."""
    text = json.dumps(value, indent=2, allow_nan=False) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    except OSError as exc:
        raise ReviewError("Cannot create output; choose a new filename in an existing directory") from exc


def expected_config(kind: str) -> dict:
    problem = {"kind": kind, "dimension": 12}
    options = {}
    if kind == "quadratic":
        problem.update(condition_number=10., L=1., rotation="householder")
        options = {"cg": {"rtol": 1e-12, "atol": 0.},
                   "proximal-point": {"proximal_parameter": 1.}}
    elif kind == "diagonal-lasso":
        problem["lam"] = .12
    return {"schema_version": 1, "problem": problem, "steps": 30, "methods": METHODS[kind],
            "method_options": options, "include_iterates": False}


def tiny_config() -> dict:
    return {"schema_version": 1,
            "problem": {"kind": "quadratic", "dimension": 2, "condition_number": 4.,
                        "L": 4., "rotation": "none"},
            "steps": 3, "methods": ["gd"], "method_options": {}, "include_iterates": True}


def environment(value) -> dict:
    value = obj(value, ENV_KEYS)
    require(value["chainbench"] == VERSION, "Wrong installed/reported package version")
    for key in ("python", "numpy"):
        require(type(value[key]) is str and re.fullmatch(r"[0-9A-Za-z.+_-]{1,60}", value[key]),
                "Invalid software version (paths and free text are not accepted)")
    require(value["os"] in ("Linux", "Darwin", "Windows"), "Unsupported OS label")
    return value


def validate_checks(rows) -> None:
    require(type(rows) is list and len(rows) == len(SLUGS), "Missing check suite")
    keys = {"slug", "title", "reference", "statement", "metric", "observed", "threshold",
            "status", "note"}
    for row, slug in zip(rows, SLUGS):
        obj(row, keys)
        require(row["slug"] == slug, "Check registry mismatch")
        value = number(row["observed"], nonnegative=True)
        for key in ("title", "reference", "statement", "metric", "note"):
            require(type(row[key]) is str and 0 < len(row[key]) <= 2000, "Invalid check text")
        if slug == "ista-vs-fista":
            require(row["status"] == "INFO" and row["threshold"] is None, "Invalid INFO result")
        else:
            threshold = .08 if slug == "polyak-1964" else 1.
            require(number(row["threshold"]) == threshold, "Unexpected threshold")
            require(row["status"] == "CONSISTENT" and value <= threshold + 1e-10,
                    "A quantitative check did not meet its condition")


def validate_experiment(report, config: dict, env: dict) -> None:
    obj(report, {"kind", "schema_version", "config", "config_sha256", "environment",
                 "fixture", "notice", "runs"})
    require(report["kind"] == "chainbench.experiment", "Invalid experiment envelope")
    integer(report["schema_version"], 1, 1)
    require(canonical(report["config"]) == canonical(config), "Experiment config differs")
    require(report["config_sha256"] == digest(config), "Configuration fingerprint mismatch")
    require(environment(report["environment"]) == env, "Inconsistent environment")
    require(type(report["notice"]) is str and 0 < len(report["notice"]) < 2000, "Missing notice")
    p, fixture = config["problem"], report["fixture"]
    obj(fixture, {"definition", "kind", "dimension", "input_sha256", "L", "mu", "f_star",
                  "stationarity_metric", "start"})
    require(fixture["definition"] == "chainbench.deterministic.v1", "Unknown fixture")
    require(fixture["kind"] == p["kind"], "Wrong problem family")
    integer(fixture["dimension"], p["dimension"], p["dimension"])
    require(type(fixture["input_sha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", fixture["input_sha256"]), "Invalid input fingerprint")
    require(fixture["stationarity_metric"] == METRICS[p["kind"]], "Wrong stationarity metric")
    require(fixture["start"] == ("first_simplex_vertex" if p["kind"] == "simplex" else "zeros"),
            "Wrong initial-point convention")
    require(number(fixture["L"], nonnegative=True) > 0, "Invalid L")
    number(fixture["f_star"])
    if p["kind"] == "quadratic":
        require(0 < number(fixture["mu"]) <= fixture["L"], "Invalid strong convexity")
    else:
        require(fixture["mu"] is None, "Unexpected strong-convexity field")
    runs = report["runs"]
    require(type(runs) is list and len(runs) == len(config["methods"]), "Missing methods")
    for run, method in zip(runs, config["methods"]):
        obj(run, {"method", "parameters", "updates", "termination", "rows"})
        require(run["method"] == method, "Method order/set mismatch")
        updates = integer(run["updates"], 0, config["steps"])
        keys = {"alpha", "beta"} if method == "heavy-ball" else {"step_size"}
        if method == "cg":
            keys = {"rtol", "atol", "stopping_threshold"}
        elif method == "proximal-point":
            keys = {"proximal_parameter"}
        elif method == "frank-wolfe":
            keys = {"schedule"}
        parameters = obj(run["parameters"], keys)
        for key, value in parameters.items():
            if key == "schedule":
                require(value == "gamma[k]=2/(k+2), k starts at 0", "Wrong step schedule")
            else:
                number(value, nonnegative=True)
        rows = run["rows"]
        require(type(rows) is list and len(rows) == updates + 1, "Incomplete trajectory")
        for k, row in enumerate(rows):
            fields = {"iteration", "objective", "gap", "stationarity", "distance_to_reference"}
            if config["include_iterates"]:
                fields.add("iterate")
            obj(row, fields)
            integer(row["iteration"], k, k)
            for key in fields - {"iteration", "iterate"}:
                number(row[key], nonnegative=key != "objective")
            if "iterate" in row:
                require(type(row["iterate"]) is list and len(row["iterate"]) == p["dimension"],
                        "Wrong coordinate count")
                for value in row["iterate"]:
                    number(value)
        if method == "cg":
            opts = config["method_options"]["cg"]
            require(parameters["rtol"] == opts["rtol"] and parameters["atol"] == opts["atol"],
                    "CG parameters changed")
            limit = max(opts["atol"], opts["rtol"] * rows[0]["stationarity"])
            require(parameters["stopping_threshold"] == limit, "CG threshold mismatch")
            expected = "converged" if rows[-1]["stationarity"] <= limit else "max_steps"
            require(run["termination"] == expected, "CG termination contradicts its residual")
            require(expected == "converged" or updates == config["steps"], "Premature CG stop")
        else:
            require(updates == config["steps"] and run["termination"] == "budget_complete",
                    "Budget completion is not a convergence claim")


def validate_tiny(report) -> None:
    """A stdlib, hand-computed oracle: Q=diag(1,4), x*=(-1,1), GD step=1/4."""
    fixture = report["fixture"]
    require(fixture["L"] == 4 and fixture["mu"] == 1 and fixture["f_star"] == -2.5,
            "Tiny problem does not match the independent oracle")
    for k, row in enumerate(report["runs"][0]["rows"]):
        x = [0., 0.] if k == 0 else [-1. + .75**k, 1.]
        gap = 2.5 if k == 0 else .5 * (.75**k)**2
        require(row["iterate"] == x and row["gap"] == gap, "Tiny GD recurrence oracle failed")


def validate_bundle(bundle) -> None:
    obj(bundle, {"kind", "schema_version", "kit_version", "release", "environment", "outcome",
                 "source_modules", "checks", "experiments", "tiny_gd", "completed_steps", "notice"})
    require(bundle["kind"] == "chainbench.release_review", "Not a release review")
    integer(bundle["schema_version"], 1, 1)
    integer(bundle["kit_version"], KIT_VERSION, KIT_VERSION)
    require(bundle["release"] == {"version": VERSION, "commit": SOURCE_COMMIT,
                                  "wheel_sha256": WHEEL_SHA256}, "Wrong release identity")
    require(bundle["outcome"] == "observations_collected", "Incomplete review")
    require(bundle["source_modules"] == MODULE_HASHES, "Source fingerprints differ from release")
    require(bundle["completed_steps"] == list(STEPS), "Missing validation stages")
    require(bundle["notice"] == NOTICE, "Missing interpretation notice")
    env = environment(bundle["environment"])
    validate_checks(bundle["checks"])
    obj(bundle["experiments"], set(METHODS))
    for kind in METHODS:
        validate_experiment(bundle["experiments"][kind], expected_config(kind), env)
    validate_experiment(bundle["tiny_gd"], tiny_config(), env)
    validate_tiny(bundle["tiny_gd"])


PROBE = '''
import hashlib, importlib.metadata as md, json, pathlib, platform
import chainbench, numpy
root = pathlib.Path(chainbench.__file__).resolve().parent
dist = md.distribution("chainbench")
direct = json.loads(dist.read_text("direct_url.json") or "{}")
print(json.dumps({"version": dist.version,
 "editable": bool(direct.get("dir_info", {}).get("editable", False)),
 "environment": {"chainbench": chainbench.__version__, "numpy": numpy.__version__,
                 "python": platform.python_version(), "os": platform.system()},
 "modules": {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(root.rglob("*.py"))}}))
'''


def command(args: list[str], work: Path, *, expected_code=0) -> str:
    try:
        p = subprocess.run([sys.executable, "-I", *args], cwd=work, capture_output=True,
                           text=True, encoding="utf-8", timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReviewError("Isolated package process could not finish") from exc
    require(p.returncode == expected_code,
            "Isolated package command returned an unexpected status; rerun it locally for details")
    require(len(p.stdout.encode("utf-8")) <= MAX_BYTES, "Package output exceeds review limit")
    return p.stdout


def collect() -> dict:
    """Run a fixed local review; no user-supplied code, paths or configs enter the package."""
    with tempfile.TemporaryDirectory(prefix="chainbench-review-") as temp:
        work = Path(temp)
        info = strict_json(command(["-c", PROBE], work))
        require(type(info) is dict and info.get("version") == VERSION and info.get("editable") is False,
                "Install the published 0.2.0 wheel in a new environment, not an editable checkout")
        require(info.get("modules") == MODULE_HASHES, "Installed Python sources differ from release")
        env = environment(info.get("environment"))
        checks = strict_json(command(["-m", "chainbench", "check", "all", "--json"], work))
        validate_checks(checks)
        reports = {}
        for kind in METHODS:
            path = work / f"{kind}.json"
            command(["-m", "chainbench", "preset", kind, "--output", str(path)], work)
            cfg = load(path)
            require(canonical(cfg) == canonical(expected_config(kind)), "Installed preset changed")
            args = ["-m", "chainbench", "experiment", "--config", str(path)]
            result = strict_json(command(args, work))
            validate_experiment(result, cfg, env)
            require(canonical(result) == canonical(strict_json(command(args, work))),
                    "Saved-config repeat changed within the same environment")
            reports[kind] = result
        tiny_path = work / "tiny.json"
        write_new(tiny_path, tiny_config())
        tiny = strict_json(command(["-m", "chainbench", "experiment", "--config", str(tiny_path)], work))
        validate_experiment(tiny, tiny_config(), env)
        validate_tiny(tiny)
        bad = work / "bad.json"
        bad.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        command(["-m", "chainbench", "experiment", "--config", str(bad)], work, expected_code=2)
        occupied = work / "occupied.json"
        occupied.write_text("KEEP ME\n", encoding="utf-8")
        command(["-m", "chainbench", "preset", "quadratic", "--output", str(occupied)],
                work, expected_code=2)
        require(occupied.read_text(encoding="utf-8") == "KEEP ME\n", "Existing output was modified")
    result = {"kind": "chainbench.release_review", "schema_version": 1, "kit_version": KIT_VERSION,
              "release": {"version": VERSION, "commit": SOURCE_COMMIT, "wheel_sha256": WHEEL_SHA256},
              "environment": env, "outcome": "observations_collected", "source_modules": MODULE_HASHES,
              "checks": checks, "experiments": reports, "tiny_gd": tiny,
              "completed_steps": list(STEPS), "notice": NOTICE}
    validate_bundle(result)
    return result


def compare(left, right, *, rtol=1e-7, atol=1e-12) -> dict:
    """Compare self-reported observations, not the identity/independence of their authors."""
    validate_bundle(left)
    validate_bundle(right)
    rtol, atol = number(rtol, nonnegative=True), number(atol, nonnegative=True)
    require(rtol <= .1 and atol <= .1, "Tolerance too large for the fixed modest-scale review suite")
    differences, input_changes = [], []
    compared = 0

    def walk(a, b, path):
        nonlocal compared
        if path.endswith("/environment"):
            return  # Environment is recorded separately, never asserted identical across machines.
        if path.endswith("/input_sha256"):
            if a != b:
                input_changes.append(path)
            return
        if type(a) in (float, int) and type(b) in (float, int):
            compared += 1
            if not math.isclose(a, b, rel_tol=rtol, abs_tol=atol):
                differences.append({"field": path, "left": a, "right": b})
        elif type(a) is dict and type(b) is dict and set(a) == set(b):
            for key in sorted(a):
                walk(a[key], b[key], path + "/" + key)
        elif type(a) is list and type(b) is list and len(a) == len(b):
            for i, (va, vb) in enumerate(zip(a, b)):
                walk(va, vb, path + "/" + str(i))
        elif a != b:
            differences.append({"field": path, "left_type": type(a).__name__,
                                "right_type": type(b).__name__, "reason": "structure or text differs"})

    walk(left, right, "")
    status = "DIFFERENT" if differences else (
        "REVIEW_INPUT_DIFFERENCE" if input_changes else "MATCH_WITHIN_TOLERANCE")
    return {"kind": "chainbench.review_comparison", "schema_version": 1, "status": status,
            "rtol": rtol, "atol": atol, "numeric_fields_compared": compared,
            "difference_count": len(differences), "first_differences": differences[:20],
            "input_fingerprint_changes": input_changes, "left_environment": left["environment"],
            "right_environment": right["environment"],
            "notice": "Only finite recorded observations are compared. A match is not proof of "
                      "execution or correctness. Different generated input bytes need human review; "
                      "CG trajectory length may legitimately vary near a stopping threshold."}


def summary(bundle) -> str:
    validate_bundle(bundle)
    env = bundle["environment"]
    lines = ["# ChainBench v0.2.0 local reproduction report", "", NOTICE, "",
             f"Environment: {env['os']}; Python {env['python']}; NumPy {env['numpy']}.",
             "", "Published Python module bytes: matched. Independent tiny GD oracle: matched.",
             "Saved configurations repeated identically in this environment.",
             "Duplicate JSON and overwrite rejection checks completed.", "",
             "| Experiment | Method | Updates | Final gap | Final stationarity | Termination |",
             "|---|---|---:|---:|---:|---|"]
    for kind in METHODS:
        for run in bundle["experiments"][kind]["runs"]:
            row = run["rows"][-1]
            lines.append(f"| {kind} | {run['method']} | {run['updates']} | {row['gap']:.8g} | "
                         f"{row['stationarity']:.8g} | {run['termination']} |")
    lines += ["", "Stationarity has different definitions across problem families. Equal update",
              "counts are not equal computational work. A completed budget is not convergence.",
              "No reviewer identity, independence, adoption count or endorsement is inferred.", ""]
    return "\n".join(lines)


def verify_wheel(path: Path) -> None:
    try:
        with path.open("rb") as stream:
            raw = stream.read(1_000_001)
    except OSError as exc:
        raise ReviewError("Cannot read wheel") from exc
    require(len(raw) <= 1_000_000 and hashlib.sha256(raw).hexdigest() == WHEEL_SHA256,
            "Wheel does not match the fixed v0.2.0 release digest")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    c = sub.add_parser("collect", help="Collect fixed observations from an already installed wheel")
    c.add_argument("--output", type=Path, required=True)
    c = sub.add_parser("compare", help="Compare two recorded bundles without running their content")
    c.add_argument("left", type=Path)
    c.add_argument("right", type=Path)
    c.add_argument("--rtol", type=float, default=1e-7)
    c.add_argument("--atol", type=float, default=1e-12)
    c = sub.add_parser("summary", help="Render a locally collected bundle as Markdown")
    c.add_argument("report", type=Path)
    c = sub.add_parser("verify-wheel", help="Verify local wheel SHA-256 without installing it")
    c.add_argument("wheel", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "verify-wheel":
            verify_wheel(args.wheel)
            print("Local wheel matches the fixed v0.2.0 SHA-256. This is not a signature check.")
        elif args.action == "collect":
            require(not args.output.exists() and not args.output.is_symlink(), "Output already exists")
            result = collect()
            write_new(args.output, result)
            print("Observations collected locally. Inspect the JSON before sharing; nothing was uploaded.")
        elif args.action == "summary":
            print(summary(load(args.report)))
        else:
            result = compare(load(args.left), load(args.right), rtol=args.rtol, atol=args.atol)
            print(json.dumps(result, indent=2, allow_nan=False))
            return {"MATCH_WITHIN_TOLERANCE": 0, "DIFFERENT": 1, "REVIEW_INPUT_DIFFERENCE": 3}[result["status"]]
        return 0
    except (ReviewError, OSError, UnicodeError, RecursionError) as exc:
        # Deliberately do not expose paths or raw subprocess output in a shareable error.
        message = str(exc) if isinstance(exc, ReviewError) else "Local review I/O or parsing failed"
        print("Review incomplete: " + message, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
