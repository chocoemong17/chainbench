"""Install BOTH distributions into separate clean environments outside the checkout."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def validate_rows(rows: list[dict], listing: list[str]) -> None:
    """Validate evidence, not just the absence of a recognized failure label."""
    if not listing or len(set(listing)) != len(listing):
        raise RuntimeError("Empty or duplicate check registry")
    if not isinstance(rows, list) or len(rows) != len(listing):
        raise RuntimeError("CLI registry and report disagree")
    if [r.get("slug") for r in rows] != listing:
        raise RuntimeError("CLI registry and report disagree")
    quantitative = 0
    for row in rows:
        value = row.get("observed")
        if type(value) not in (float, int) or not math.isfinite(value):
            raise RuntimeError("Missing or non-finite installed check observation")
        status, threshold = row.get("status"), row.get("threshold")
        if status == "CONSISTENT":
            if type(threshold) not in (float, int) or not math.isfinite(threshold):
                raise RuntimeError("Missing quantitative threshold")
            if value > threshold + 1e-10:
                raise RuntimeError("Quantitative check exceeds its threshold")
            quantitative += 1
        elif status != "INFO" or threshold is not None:
            raise RuntimeError("Failed or unrecognized installed check status")
    if not quantitative:
        raise RuntimeError("No quantitative evidence in installed suite")



PRESET_METHODS = {
    "quadratic": ["gd", "smooth-fista", "heavy-ball", "cg", "proximal-point"],
    "diagonal-lasso": ["ista", "fista"],
    "simplex": ["frank-wolfe"],
}


def validate_experiment(result: dict, config: dict, version: str) -> None:
    """Validate installed experiment evidence independently of the package serializer."""
    if not isinstance(result, dict) or result.get("kind") != "chainbench.experiment":
        raise RuntimeError("Missing experiment envelope")
    if type(result.get("schema_version")) is not int or result["schema_version"] != 1:
        raise RuntimeError("Unexpected experiment schema")
    if result.get("config") != config:
        raise RuntimeError("Experiment did not run the supplied configuration")
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), allow_nan=False)
    expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if result.get("config_sha256") != expected_hash:
        raise RuntimeError("Experiment configuration hash mismatch")
    environment = result.get("environment")
    if not isinstance(environment, dict) or environment.get("chainbench") != version:
        raise RuntimeError("Experiment version mismatch")
    if any(not isinstance(environment.get(k), str) or not environment[k]
           for k in ("numpy", "python", "os")):
        raise RuntimeError("Missing experiment environment")
    fixture = result.get("fixture")
    if (not isinstance(fixture, dict)
            or not re.fullmatch(r"[0-9a-f]{64}", str(fixture.get("input_sha256", "")))
            or fixture.get("kind") != config["problem"]["kind"]
            or fixture.get("dimension") != config["problem"]["dimension"]):
        raise RuntimeError("Missing experiment input provenance")
    runs = result.get("runs")
    if (not isinstance(runs, list) or not runs
            or [r.get("method") for r in runs] != config["methods"]):
        raise RuntimeError("Experiment method set mismatch")
    for run in runs:
        rows, updates = run.get("rows"), run.get("updates")
        if (type(updates) is not int or not 0 <= updates <= config["steps"]
                or not isinstance(rows, list) or len(rows) != updates + 1):
            raise RuntimeError("Missing experiment trajectory")
        expected_states = ("converged", "max_steps") if run["method"] == "cg" else ("budget_complete",)
        if run.get("termination") not in expected_states:
            raise RuntimeError("Unexpected experiment termination")
        if run["termination"] != "converged" and updates != config["steps"]:
            raise RuntimeError("Experiment stopped before its budget without convergence")
        for k, row in enumerate(rows):
            if type(row.get("iteration")) is not int or row["iteration"] != k:
                raise RuntimeError("Experiment trajectory indices are inconsistent")
            for field in ("objective", "gap", "stationarity", "distance_to_reference"):
                value = row.get(field)
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise RuntimeError("Missing or non-finite experiment observation")
                if field != "objective" and value < 0:
                    raise RuntimeError("Negative experiment error metric")


def exercise_experiments(cli: str, work: Path, env: dict[str, str], version: str) -> list[dict]:
    records = []
    for name, methods in PRESET_METHODS.items():
        path = work / f"{name}-config.json"
        run([cli, "preset", name, "--output", str(path)], work, env)
        config = json.loads(path.read_text(encoding="utf-8"))
        if config.get("methods") != methods:
            raise RuntimeError("Installed preset lost or changed expected methods")
        result = json.loads(run([cli, "experiment", "--preset", name], work, env))
        validate_experiment(result, config, version)
        rerun = json.loads(run([cli, "experiment", "--config", str(path)], work, env))
        if rerun != result:
            raise RuntimeError("Saved configuration rerun differs from the preset")
        for format_name in ("json", "csv", "markdown", "html"):
            target = work / f"{name}-experiment.{format_name}"
            run([cli, "experiment", "--config", str(path), "--format", format_name,
                 "--output", str(target)], work, env)
            text = target.read_text(encoding="utf-8")
            if not text:
                raise RuntimeError("Empty installed experiment export")
            if format_name == "json":
                if json.loads(text) != result:
                    raise RuntimeError("Experiment JSON differs from the actual run")
            elif format_name == "csv":
                with target.open(newline="", encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                flattened = [(t["method"], r) for t in result["runs"] for r in t["rows"]]
                if len(rows) != len(flattened):
                    raise RuntimeError("Experiment CSV lost trajectory rows")
                for row, (method, expected) in zip(rows, flattened):
                    if (row["method"] != method or int(row["iteration"]) != expected["iteration"]
                            or float(row["gap"]) != expected["gap"]
                            or json.loads(row["config_json"]) != config
                            or row["config_sha256"] != result["config_sha256"]):
                        raise RuntimeError("Experiment CSV differs from the actual run")
            elif format_name == "html":
                if "<svg" not in text or result["fixture"]["kind"] not in text:
                    raise RuntimeError("Experiment HTML lost its visual result")
            elif result["config_sha256"] not in text or result["fixture"]["input_sha256"] not in text:
                raise RuntimeError("Experiment Markdown lost its provenance")
        records.append({"preset": name, "config_sha256": result["config_sha256"],
                        "methods": methods, "rows": sum(len(r["rows"]) for r in result["runs"]),
                        "exports": ["json", "csv", "markdown", "html"],
                        "saved_config_rerun": "matched"})
    return records


def main() -> None:
    dist = ROOT / "dist"
    wheels, sdists = sorted(dist.glob("*.whl")), sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise RuntimeError("Expected exactly one wheel and one sdist")
    artifacts = wheels + sdists
    expected = json.loads((ROOT / "release-manifest.json").read_text())["version"]
    records = []
    for artifact in artifacts:
        with tempfile.TemporaryDirectory(prefix="chainbench-install-") as tmp:
            work = Path(tmp)
            envdir = work / "venv"
            venv.EnvBuilder(with_pip=True).create(envdir)
            bindir = envdir / ("Scripts" if os.name == "nt" else "bin")
            python = str(bindir / ("python.exe" if os.name == "nt" else "python"))
            cli = str(bindir / ("chainbench.exe" if os.name == "nt" else "chainbench"))
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)
            env["PYTHONNOUSERSITE"] = "1"
            run([python, "-m", "pip", "install", str(artifact.resolve())], work, env)
            run([python, "-m", "pip", "check"], work, env)
            code = (
                "import json,chainbench; from importlib.metadata import version; "
                "print(json.dumps({'file':chainbench.__file__,"
                "'module_version':chainbench.__version__,'version':version('chainbench')}))"
            )
            info = json.loads(run([python, "-I", "-c", code], work, env))
            if ROOT in Path(info["file"]).resolve().parents:
                raise RuntimeError("Smoke test imported the checkout instead of the distribution")
            if info["version"] != expected or info["module_version"] != expected:
                raise RuntimeError("Installed version does not match the release manifest")
            listing = run([cli, "list"], work, env).splitlines()
            rows = json.loads(run([cli, "check", "all", "--json"], work, env))
            validate_rows(rows, listing)
            run([python, "-I", "-m", "chainbench", "--version"], work, env)
            for format_name in ("html", "markdown", "json", "csv"):
                target = work / f"report.{format_name}"
                run([cli, "report", "--format", format_name, "--output", str(target)], work, env)
                if not target.stat().st_size:
                    raise RuntimeError("Empty exported report")
                if format_name == "json":
                    exported = json.loads(target.read_text(encoding="utf-8"))
                    validate_rows(exported, listing)
                    if exported != rows:
                        raise RuntimeError("JSON report differs from installed checks")
                elif format_name == "csv":
                    with target.open(newline="") as f:
                        exported = list(csv.DictReader(f))
                    if [r["slug"] for r in exported] != listing:
                        raise RuntimeError("CSV registry differs from installed checks")
                    if [r["status"] for r in exported] != [r["status"] for r in rows]:
                        raise RuntimeError("CSV statuses differ from installed checks")
                elif "<svg" not in target.read_text(encoding="utf-8"):
                    raise RuntimeError("HTML report did not contain visual plots")
            plot = work / "nesterov.svg"
            run([cli, "plot", "nesterov-1983", "--output", str(plot)], work, env)
            if "<svg" not in plot.read_text(encoding="utf-8"):
                raise RuntimeError("Standalone plot export is not SVG")
            experiments = exercise_experiments(cli, work, env, expected)
            records.append({
                "artifact": artifact.name,
                "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                "version": expected,
                "checks": len(rows), "slugs": listing,
                "statuses": [r["status"] for r in rows],
                "installed_outside_checkout": True,
                "pip_check": "passed", "exports": ["html", "markdown", "csv", "json"],
                "plot_svg": "passed", "experiments": experiments,
            })
            print(f"CLEAN INSTALL PASSED: {artifact.name}", flush=True)
    report = {"python": platform.python_version(), "artifacts": records,
              "source_commit": os.environ.get("GITHUB_SHA")}
    (dist / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    sums = [
        f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}"
        for p in sorted(dist.iterdir()) if p.is_file() and p.name != "SHA256SUMS"
    ]
    (dist / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
