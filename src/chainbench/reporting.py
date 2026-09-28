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
        "slug": result.slug,
        "title": result.title,
        "reference": result.reference,
        "statement": result.statement,
        "metric": result.metric,
        "observed": result.observed,
        "threshold": result.threshold,
        "status": result_status(result),
        "note": result.note,
    }


def render_json(results: list[CheckResult]) -> str:
    return json.dumps([result_to_dict(result) for result in results], indent=2)


def render_csv(results: list[CheckResult]) -> str:
    fieldnames = [
        "slug",
        "title",
        "status",
        "observed",
        "threshold",
        "metric",
        "reference",
        "statement",
        "note",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for result in results:
        writer.writerow(result_to_dict(result))
    return buffer.getvalue()


def _markdown_cell(value: object) -> str:
    if value is None:
        return "n/a"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(results: list[CheckResult]) -> str:
    lines = [
        "# ChainBench benchmark report",
        "",
        "Deterministic numerical consistency checks for public, published results.",
        "",
        "| Check | Status | Observed | Threshold | Metric |",
        "|---|---|---:|---:|---|",
    ]
    for result in results:
        threshold = "n/a" if result.threshold is None else f"{result.threshold:.8g}"
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_cell(result.slug),
                    _markdown_cell(result_status(result)),
                    f"{result.observed:.8g}",
                    threshold,
                    _markdown_cell(result.metric),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "A consistent row means the bundled finite experiment satisfies its stated",
            "numerical condition. It is not a mathematical proof of the cited result.",
            "",
        ]
    )
    return "\n".join(lines)


def render_report(results: list[CheckResult], format_name: str) -> str:
    if format_name == "markdown":
        return render_markdown(results)
    if format_name == "csv":
        return render_csv(results)
    if format_name == "json":
        return render_json(results)
    raise ValueError(f"unknown report format: {format_name}")
