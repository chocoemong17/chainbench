"""Portable exports for configurable experiments; full metadata stays in every format."""
from __future__ import annotations

import csv
import io
import json
from html import escape

from .experiments import canonical_json
from .visuals import experiment_chart, render_line_chart


def _render_html(result: dict) -> str:
    gap = render_line_chart(
        experiment_chart(result, "gap", "Objective-gap trajectories", "objective gap")
    )
    stationarity = render_line_chart(
        experiment_chart(
            result,
            "stationarity",
            "Stationarity trajectories",
            result["fixture"]["stationarity_metric"].replace("_", " "),
        )
    )
    cards = []
    for run in result["runs"]:
        row = run["rows"][-1]
        cards.append(
            '<article class="method"><h3>' + escape(run["method"]) + '</h3>'
            f'<p><strong>Final gap</strong><br>{row["gap"]:.7g}</p>'
            f'<p><strong>Final stationarity</strong><br>{row["stationarity"]:.7g}</p>'
            '<p><strong>Termination</strong><br>' + escape(run["termination"]) + '</p></article>'
        )
    raw = escape(json.dumps(
        {
            "config": result["config"],
            "environment": result["environment"],
            "fixture": result["fixture"],
        },
        indent=2,
    ))
    css = """
:root{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#172033;background:#f6f8fb}
*{box-sizing:border-box}body{margin:0}main{max-width:1100px;margin:auto;padding:36px 22px 70px}
.hero{background:#172554;color:white;border-radius:20px;padding:30px}.hero h1{margin:0 0 9px}
.hero p{line-height:1.55;max-width:850px}.grid{display:grid;
grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:20px 0}.method,.panel{
background:white;border:1px solid #e2e8f0;border-radius:16px;padding:16px}.method h3{margin:0 0 10px}
.method p{font-size:13px;line-height:1.45}.panel{margin:20px 0}.panel svg{display:block;width:100%;
min-width:660px;height:auto}.scroll{overflow-x:auto}.note{font-size:13px;color:#64748b;line-height:1.55}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0f172a;color:#e2e8f0;border-radius:12px;
padding:14px;font-size:12px}summary{cursor:pointer;font-weight:700}
"""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>ChainBench experiment</title><style>' + css + '</style></head><body><main>'
        '<header class="hero"><h1>ChainBench configurable experiment</h1>'
        '<p>This page visualizes one configured synthetic fixture. Curves are observations, '
        'not theorem certificates or an equal-compute algorithm ranking.</p>'
        f'<p>Problem: <strong>{escape(result["fixture"]["kind"])}</strong> · '
        f'Dimension: <strong>{result["fixture"]["dimension"]}</strong> · '
        f'Budget: <strong>{result["config"]["steps"]}</strong> updates</p></header>'
        '<section><h2>Final observations</h2><div class="grid">' + "".join(cards)
        + '</div></section><section class="panel"><h2>How the objective gap changes</h2>'
        '<div class="scroll">' + gap + '</div></section>'
        '<section class="panel"><h2>How stationarity changes</h2><div class="scroll">'
        + stationarity + '</div></section>'
        '<p class="note"><code>budget_complete</code> means the requested update budget ran; '
        'it does not certify convergence. Different methods can have very different work per update.'
        '</p><details class="panel"><summary>Configuration, environment and fixture provenance'
        '</summary><pre>' + raw + '</pre></details></main></body></html>'
    )


def render_experiment(result: dict, format_name: str = "json") -> str:
    if format_name == "html":
        return _render_html(result)
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
