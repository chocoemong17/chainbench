from __future__ import annotations

import csv
from html import escape
import io
import json

from .checks import CheckResult
from .stories import STORIES
from .visuals import build_check_chart, render_line_chart


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
    return json.dumps([result_to_dict(r) for r in results], indent=2, allow_nan=False)


def render_csv(results: list[CheckResult]) -> str:
    fields = [
        "slug", "title", "status", "observed", "threshold", "metric", "reference",
        "statement", "note",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for result in results:
        writer.writerow(result_to_dict(result))
    return buffer.getvalue()


def _markdown_cell(value: object) -> str:
    return "n/a" if value is None else str(value).replace("|", "\\|").replace("\n", " ")


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
        threshold = "n/a" if result.threshold is None else f"{result.threshold:.7g}"
        cells = [
            result.slug, result_status(result), f"{result.observed:.7g}", threshold, result.metric
        ]
        lines.append("| " + " | ".join(_markdown_cell(cell) for cell in cells) + " |")
    lines.extend([
        "",
        "A consistent row means the bundled finite experiment satisfies its stated",
        "numerical condition. It is not a mathematical proof of the cited result.",
        "INFO rows are observations without a pass/fail threshold. See docs/SOURCE_MAP.md.",
        "",
    ])
    return "\n".join(lines)


def _status_class(result: CheckResult) -> str:
    return {
        "CONSISTENT": "ok",
        "NOT CONSISTENT": "bad",
        "INFO": "info",
    }[result_status(result)]


def render_html(results: list[CheckResult]) -> str:
    if not results:
        raise ValueError("cannot render an empty visual report")
    missing = [result.slug for result in results if result.slug not in STORIES]
    if missing:
        raise ValueError(f"missing visual story metadata: {missing}")
    consistent = sum(result.consistent is True for result in results)
    info = sum(result.consistent is None for result in results)
    cards, sections, rows = [], [], []
    for result in results:
        story = STORIES[result.slug]
        status = result_status(result)
        threshold = "n/a" if result.threshold is None else f"{result.threshold:.7g}"
        cards.append(
            f'<a class="summary-card" href="#{escape(result.slug)}">'
            f'<span class="badge {_status_class(result)}">{escape(status)}</span>'
            f'<strong>{escape(result.title)}</strong>'
            f'<span>{escape(story.claim)}</span></a>'
        )
        chart = render_line_chart(build_check_chart(result.slug))
        sections.append(
            f'<section class="paper" id="{escape(result.slug)}">'
            f'<div class="paper-head"><div><p class="eyebrow">{escape(story.source)}</p>'
            f'<h2>{escape(result.title)}</h2></div>'
            f'<span class="badge {_status_class(result)}">{escape(status)}</span></div>'
            f'<div class="story-grid">'
            f'<article><h3>What the result says</h3><p>{escape(story.claim)}</p></article>'
            f'<article><h3>What ChainBench shows</h3><p>{escape(story.evidence)}</p></article>'
            f'<article><h3>What to notice</h3><p>{escape(story.takeaway)}</p></article>'
            f'</div><div class="chart">{chart}</div>'
            f'<p class="caveat"><strong>Limit:</strong> {escape(story.caveat)}</p>'
            f'<details><summary>Numerical check details</summary><dl>'
            f'<dt>Reference</dt><dd>{escape(result.reference)}</dd>'
            f'<dt>Measured statement</dt><dd>{escape(result.statement)}</dd>'
            f'<dt>Metric</dt><dd>{escape(result.metric)}</dd>'
            f'<dt>Observed</dt><dd>{result.observed:.9g}</dd>'
            f'<dt>Threshold</dt><dd>{escape(threshold)}</dd>'
            f'<dt>Implementation note</dt><dd>{escape(result.note)}</dd>'
            f'</dl></details></section>'
        )
        rows.append(
            "<tr>"
            f"<td>{escape(result.slug)}</td><td>{escape(status)}</td>"
            f"<td>{result.observed:.9g}</td><td>{escape(threshold)}</td>"
            f"<td>{escape(result.metric)}</td></tr>"
        )
    css = """
:root{font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",
sans-serif;color:#172033;background:#f6f8fb}*{box-sizing:border-box}body{margin:0}
main{max-width:1100px;margin:auto;padding:38px 22px 80px}.hero{background:linear-gradient(135deg,
#172554,#1e3a8a);color:white;padding:34px;border-radius:22px;box-shadow:0 16px 44px #17255422}
.hero h1{margin:0 0 8px;font-size:40px}.hero p{max-width:850px;line-height:1.6}.meta{display:flex;
gap:10px;flex-wrap:wrap;margin-top:18px}.pill,.badge{display:inline-block;border-radius:999px;
padding:6px 10px;font-size:12px;font-weight:700}.pill{background:#ffffff20}.badge.ok{
background:#dcfce7;color:#166534}.badge.info{background:#e0f2fe;color:#075985}.badge.bad{
background:#fee2e2;color:#991b1b}.summary-grid{display:grid;grid-template-columns:
repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:24px 0 32px}.summary-card{display:flex;
flex-direction:column;gap:9px;padding:17px;border:1px solid #e3e8ef;border-radius:16px;
background:white;color:inherit;text-decoration:none;box-shadow:0 5px 18px #0f172a0a}
.summary-card:hover{border-color:#93c5fd}.summary-card span:last-child{font-size:13px;
line-height:1.45;color:#526078}.paper{background:white;border:1px solid #e3e8ef;
border-radius:20px;padding:25px;margin:22px 0;box-shadow:0 7px 25px #0f172a0a}
.paper-head{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}
.paper h2{margin:2px 0 16px}.eyebrow{text-transform:uppercase;letter-spacing:.08em;
font-size:11px;font-weight:800;color:#64748b;margin:0}.story-grid{display:grid;
grid-template-columns:repeat(3,1fr);gap:12px}.story-grid article{background:#f8fafc;
border-radius:13px;padding:14px}.story-grid h3{font-size:13px;margin:0 0 7px;color:#334155}
.story-grid p{font-size:14px;line-height:1.5;margin:0}.chart{overflow-x:auto;margin:22px 0 12px}
.chart svg{display:block;min-width:660px;width:100%;height:auto}.caveat{font-size:13px;
line-height:1.55;background:#fff7ed;border-left:4px solid #fb923c;padding:10px 13px;
border-radius:8px}details{margin-top:14px}summary{cursor:pointer;font-weight:700}
dl{display:grid;grid-template-columns:170px 1fr;gap:7px 14px;font-size:13px}dt{font-weight:700}
dd{margin:0;color:#475569}table{width:100%;border-collapse:collapse;background:white}th,td{
padding:9px;border-bottom:1px solid #e5e7eb;text-align:left;font-size:12px}th{background:#f8fafc}
.appendix{background:white;border:1px solid #e3e8ef;border-radius:16px;padding:18px;
margin-top:26px}.note{color:#64748b;font-size:13px;line-height:1.55}@media(max-width:760px){
.story-grid{grid-template-columns:1fr}.hero h1{font-size:31px}.paper{padding:17px}}
"""
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>ChainBench visual report</title><style>' + css + '</style></head><body><main>'
        '<header class="hero"><h1>ChainBench visual report</h1>'
        '<p>Each section starts from the paper-level idea, shows the finite numerical evidence '
        'visually, and keeps raw numbers in an appendix. A green badge means only that this '
        'bundled experiment satisfied its stated numerical condition.</p>'
        f'<div class="meta"><span class="pill">{len(results)} checks</span>'
        f'<span class="pill">{consistent} quantitative conditions consistent</span>'
        f'<span class="pill">{info} informational comparison</span></div></header>'
        '<section><h2>At a glance</h2><p class="note">Choose a card to jump directly to the '
        'claim, plot and limitation.</p><div class="summary-grid">' + "".join(cards)
        + '</div></section>' + "".join(sections)
        + '<details class="appendix"><summary>Raw numerical appendix</summary>'
        '<p class="note">These values remain available for auditing and machine comparison; '
        'they are deliberately not the primary presentation.</p><div style="overflow:auto"><table>'
        '<thead><tr><th>Check</th><th>Status</th><th>Observed</th><th>Threshold</th>'
        '<th>Metric</th></tr></thead><tbody>' + "".join(rows)
        + '</tbody></table></div></details>'
        '<p class="note">For assumptions, formulas and public references, see '
        'docs/SOURCE_MAP.md and REFERENCES.md in the repository.</p></main></body></html>'
    )


def render_report(results: list[CheckResult], format_name: str) -> str:
    renderers = {
        "markdown": render_markdown,
        "csv": render_csv,
        "json": render_json,
        "html": render_html,
    }
    if format_name not in renderers:
        raise ValueError(f"unknown report format: {format_name}")
    return renderers[format_name](results)
