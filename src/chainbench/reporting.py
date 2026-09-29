from __future__ import annotations

import csv
import io
import json

from .checks import CheckResult


def result_status(result: CheckResult) -> str:
    if result.consistent is None:
        return "INFO"
    return "CONSISTENT" if result.consistent else "NOT CONSISTENT"


def result_to_dict(result: CheckResult) -> dict[str, object]:
    return {
        "slug": result.slug, "title": result.title, "reference": result.reference,
        "statement": result.statement, "metric": result.metric, "observed": result.observed,
        "threshold": result.threshold, "status": result_status(result), "note": result.note,
    }


def render_json(results: list[CheckResult]) -> str:
    return json.dumps([result_to_dict(r) for r in results], indent=2, allow_nan=False)


def render_csv(results: list[CheckResult]) -> str:
    fields = ["slug", "title", "status", "observed", "threshold", "metric", "reference",
              "statement", "note"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for r in results:
        writer.writerow(result_to_dict(r))
    return buffer.getvalue()


def _markdown_cell(value: object) -> str:
    return "n/a" if value is None else str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(results: list[CheckResult]) -> str:
    lines = [
        "# ChainBench benchmark report", "",
        "Deterministic numerical consistency checks for public, published results.", "",
        "| Check | Status | Observed | Threshold | Metric |",
        "|---|---|---:|---:|---|",
    ]
    for r in results:
        threshold = "n/a" if r.threshold is None else f"{r.threshold:.7g}"
        cells = [r.slug, result_status(r), f"{r.observed:.7g}", threshold, r.metric]
        lines.append("| " + " | ".join(_markdown_cell(c) for c in cells) + " |")
    lines.extend([
        "", "A consistent row means the bundled finite experiment satisfies its stated",
        "numerical condition. It is not a mathematical proof of the cited result.",
        "INFO rows are observations without a pass/fail threshold. See docs/SOURCE_MAP.md.", "",
    ])
    return "\n".join(lines)


def render_report(results: list[CheckResult], format_name: str) -> str:
    renderers = {"markdown": render_markdown, "csv": render_csv, "json": render_json}
    if format_name not in renderers:
        raise ValueError(f"unknown report format: {format_name}")
    return renderers[format_name](results)
