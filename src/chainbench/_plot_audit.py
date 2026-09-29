"""Bind the fixed-suite presentation to the plotted samples, not a second story."""
from __future__ import annotations

import math
import platform
from dataclasses import asdict

import numpy as np


def chart_metric(slug, chart) -> float:
    a, b = (np.asarray(s.y, dtype=float) for s in chart.series)
    if slug == "polyak-1964":
        return float(abs(np.median(a[-20:]) - b[-1]) / b[-1])
    if slug == "ista-vs-fista":
        return float(b[-1] / a[-1])
    if slug == "rockafellar-1976":
        valid = a[:-1] > 1e-12
        q = b[1] / b[0]
        return float(np.max(a[1:][valid] / (q * a[:-1][valid])))
    if slug == "hestenes-stiefel-1952":
        a, b = a[1:], b[1:]  # The check excludes k=0, though the figure shows it.
    return float(np.max(a / b))


def validate_chart_result(result, chart) -> None:
    measured = chart_metric(result.slug, chart)
    if not math.isfinite(measured) or not math.isclose(
            measured, result.observed, rel_tol=1e-9, abs_tol=1e-12):
        raise ValueError("visual samples disagree with the supplied fixed-suite result")
    threshold = None if result.slug == "ista-vs-fista" else (
        .08 if result.slug == "polyak-1964" else 1.)
    verdict = None if threshold is None else measured <= threshold + (
        0. if result.slug == "polyak-1964" else 1e-10)
    if result.threshold != threshold or result.consistent is not verdict:
        raise ValueError("visual verdict disagrees with the plotted metric")


def evidence_record(results, charts) -> dict:
    from . import __version__

    return {
        "kind": "chainbench.visual_report", "schema_version": 1,
        "environment": {"chainbench": __version__, "python": platform.python_version(),
                        "numpy": np.__version__, "os": platform.system()},
        "results": [asdict(r) for r in results],
        "charts": {slug: asdict(chart) for slug, chart in charts.items()},
        "notice": "Fixed synthetic demonstrations, not whole-paper reproductions or proofs. "
                  "SVG metadata retains unclipped samples. Zeros are never positive log values.",
    }
