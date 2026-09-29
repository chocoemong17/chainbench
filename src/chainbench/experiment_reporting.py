"""Portable exports for configurable experiments; full metadata stays in every format."""
from __future__ import annotations

import csv
import io
import json

from .experiments import canonical_json


def render_experiment(result: dict, format_name: str = "json") -> str:
    if format_name == "json":
        return json.dumps(result, indent=2, allow_nan=False) + "\n"
    if format_name == "csv":
        buffer = io.StringIO()
        fields = ["schema_version", "config_sha256", "input_sha256", "config_json", "fixture_json",
                  "parameters_json", "notice", "chainbench_version",
                  "python_version", "numpy_version", "os", "method", "iteration", "objective",
                  "gap", "stationarity_metric", "stationarity", "distance_to_reference",
                  "termination", "iterate_json"]
        writer = csv.DictWriter(buffer, fields, lineterminator="\n")
        writer.writeheader()
        env, fixture = result["environment"], result["fixture"]
        metadata = {"schema_version": result["schema_version"], "fixture_json": canonical_json(fixture),
                    "notice": result["notice"], "config_sha256": result["config_sha256"], "input_sha256": fixture["input_sha256"],
                    "config_json": canonical_json(result["config"]), "chainbench_version": env["chainbench"],
                    "python_version": env["python"], "numpy_version": env["numpy"], "os": env["os"],
                    "stationarity_metric": fixture["stationarity_metric"]}
        for run in result["runs"]:
            for row in run["rows"]:
                clean = {k: v for k, v in row.items() if k != "iterate"}
                writer.writerow({**metadata, **clean, "method": run["method"],
                                 "parameters_json": canonical_json(run["parameters"]),
                                 "termination": run["termination"] if row["iteration"] == run["updates"] else "",
                                 "iterate_json": canonical_json(row["iterate"]) if "iterate" in row else ""})
        return buffer.getvalue()
    if format_name != "markdown":
        raise ValueError(f"unknown experiment format: {format_name}")
    lines = ["# ChainBench configurable experiment", "", result["notice"], "",
             f"Configuration SHA-256: `{result['config_sha256']}`", "",
             f"Input-byte SHA-256: `{result['fixture']['input_sha256']}`", "",
             "## Configuration", "", "```json", json.dumps(result["config"], indent=2), "```", "",
             "## Environment and fixture", "", "```json",
             json.dumps({"environment": result["environment"], "fixture": result["fixture"]}, indent=2),
             "```", "", "## Final observations", "",
             "| Method | Updates | Final gap | Stationarity | Termination |",
             "|---|---:|---:|---:|---|"]
    for run in result["runs"]:
        row = run["rows"][-1]
        lines.append(f"| {run['method']} | {run['updates']} | {row['gap']:.8g} | "
                     f"{row['stationarity']:.8g} | {run['termination']} |")
    lines.extend(["", f"Stationarity metric: `{result['fixture']['stationarity_metric']}`.",
                  "`budget_complete` means the requested updates ran; it does not assert convergence.", ""])
    for run in result["runs"]:
        lines.extend([f"## {run['method']} trajectory", "",
                      f"Parameters: `{canonical_json(run['parameters'])}`", "",
                      "| k | Objective | Gap | Stationarity | Distance to reference |",
                      "|---:|---:|---:|---:|---:|"])
        for row in run["rows"]:
            lines.append(f"| {row['iteration']} | {row['objective']:.8g} | {row['gap']:.8g} | "
                         f"{row['stationarity']:.8g} | {row['distance_to_reference']:.8g} |")
        if result["config"]["include_iterates"]:
            lines.extend(["", "Iterates:", "```json",
                          json.dumps([r["iterate"] for r in run["rows"]]), "```"])
        lines.append("")
    return "\n".join(lines)
