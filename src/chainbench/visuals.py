from __future__ import annotations

import math
from dataclasses import dataclass
from html import escape

import numpy as np

from .methods import (
    accelerated_gradient,
    conjugate_gradient,
    fista,
    frank_wolfe,
    gradient_descent,
    heavy_ball,
    ista,
    proximal_point,
)
from .problems import (
    diagonal_lasso,
    simplex_quadratic,
    smooth_convex_quadratic,
    strongly_convex_quadratic,
)


@dataclass(frozen=True)
class LineSeries:
    label: str
    x: tuple[float, ...]
    y: tuple[float, ...]
    role: str = "observed"


@dataclass(frozen=True)
class ChartSpec:
    title: str
    x_label: str
    y_label: str
    series: tuple[LineSeries, ...]
    y_scale: str = "log"


def _series(label: str, x, y, role: str = "observed") -> LineSeries:
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)
    if xv.ndim != 1 or yv.ndim != 1 or xv.size != yv.size or not xv.size:
        raise ValueError("chart series must be nonempty one-dimensional vectors of equal length")
    if not np.all(np.isfinite(xv)) or not np.all(np.isfinite(yv)):
        raise ValueError("chart series must be finite")
    if np.any(yv < 0):
        raise ValueError("chart series cannot contain negative error values")
    return LineSeries(label, tuple(float(v) for v in xv), tuple(float(v) for v in yv), role)


def _gaps(problem, trace) -> np.ndarray:
    return np.asarray([problem.gap(x) for x in trace.iterates], dtype=float)


def build_check_chart(slug: str) -> ChartSpec:
    if slug == "gd-baseline":
        steps = 80
        p = smooth_convex_quadratic()
        t = gradient_descent(p, steps)
        k = np.arange(1, steps + 1, dtype=float)
        bound = p.L * float(p.x_star @ p.x_star) / (2 * k)
        return ChartSpec(
            "Observed gap vs O(1/k) envelope", "iteration k", "objective gap",
            (_series("observed gap", k, _gaps(p, t)[1:]),
             _series("O(1/k) envelope", k, bound, "bound")),
        )
    if slug == "nesterov-1983":
        steps = 80
        p = smooth_convex_quadratic()
        t = accelerated_gradient(p, steps)
        k = np.arange(1, steps + 1, dtype=float)
        bound = 2 * p.L * float(p.x_star @ p.x_star) / (k + 1) ** 2
        return ChartSpec(
            "Accelerated gap vs O(1/k^2) envelope", "iteration k", "objective gap",
            (_series("smooth FISTA gap", k, _gaps(p, t)[1:]),
             _series("O(1/k^2) envelope", k, bound, "bound")),
        )
    if slug == "polyak-1964":
        steps = 180
        p = strongly_convex_quadratic()
        t, _, _ = heavy_ball(p, steps)
        errors = np.asarray([np.linalg.norm(x - p.x_star) for x in t.iterates])
        valid = errors[:-1] > 1e-10
        idx = np.flatnonzero(valid) + 1
        ratios = errors[1:][valid] / errors[:-1][valid]
        rho = (np.sqrt(p.L) - np.sqrt(p.mu)) / (np.sqrt(p.L) + np.sqrt(p.mu))
        return ChartSpec(
            "Consecutive error ratios vs spectral prediction", "iteration k",
            "||e_k|| / ||e_(k-1)||",
            (_series("observed ratio", idx, ratios),
             _series("predicted rho", idx, np.full(idx.size, rho), "reference")),
            "linear",
        )
    if slug == "hestenes-stiefel-1952":
        steps = 20
        p = strongly_convex_quadratic(30, 0.1, 1.0)
        t = conjugate_gradient(p, steps)
        errors = np.sqrt(2 * _gaps(p, t))
        k = np.arange(errors.size, dtype=float)
        rho = (np.sqrt(p.L / p.mu) - 1) / (np.sqrt(p.L / p.mu) + 1)
        bound = 2 * rho ** k * errors[0]
        return ChartSpec(
            "CG energy error vs condition-number envelope", "iteration k", "Q-norm error",
            (_series("observed Q-norm error", k, errors),
             _series("classical envelope", k, bound, "bound")),
        )
    if slug == "jaggi-2013":
        steps = 80
        p = simplex_quadratic(50)
        t = frank_wolfe(p, steps)
        k = np.arange(1, steps + 1, dtype=float)
        bound = 2 * p.curvature_upper_bound / (k + 2)
        return ChartSpec(
            "Frank-Wolfe gap vs curvature envelope", "iteration k", "primal gap",
            (_series("observed primal gap", k, _gaps(p, t)[1:]),
             _series("curvature envelope", k, bound, "bound")),
        )
    if slug == "rockafellar-1976":
        steps = 30
        c = 1.0
        p = strongly_convex_quadratic(40, 0.1, 1.0)
        t = proximal_point(p, steps, c)
        errors = np.asarray([np.linalg.norm(x - p.x_star) for x in t.iterates])
        k = np.arange(errors.size, dtype=float)
        q = 1 / (1 + c * p.mu)
        bound = errors[0] * q ** k
        return ChartSpec(
            "Proximal-point error vs geometric contraction", "iteration k",
            "distance to optimizer",
            (_series("observed error", k, errors),
             _series("q^k envelope", k, bound, "bound")),
        )
    if slug == "beck-teboulle-2009":
        steps = 80
        p = diagonal_lasso()
        t = fista(p, steps)
        k = np.arange(1, steps + 1, dtype=float)
        bound = 2 * p.L * float(p.x_star @ p.x_star) / (k + 1) ** 2
        return ChartSpec(
            "FISTA composite gap vs O(1/k^2) envelope", "iteration k",
            "composite objective gap",
            (_series("observed FISTA gap", k, _gaps(p, t)[1:]),
             _series("O(1/k^2) envelope", k, bound, "bound")),
        )
    if slug == "ista-vs-fista":
        steps = 80
        p = diagonal_lasso()
        ti, tf = ista(p, steps), fista(p, steps)
        k = np.arange(steps + 1, dtype=float)
        return ChartSpec(
            "ISTA and FISTA on the same fixture", "iteration k", "objective gap",
            (_series("ISTA", k, _gaps(p, ti)), _series("FISTA", k, _gaps(p, tf))),
        )
    raise ValueError(f"unknown visual check: {slug}")


def experiment_chart(result: dict, field: str, title: str, y_label: str) -> ChartSpec:
    series = []
    for run in result["runs"]:
        x = [row["iteration"] for row in run["rows"]]
        y = [row[field] for row in run["rows"]]
        series.append(_series(run["method"], x, y))
    return ChartSpec(title, "iteration k", y_label, tuple(series), "log")


def _fmt(value: float) -> str:
    if value == 0:
        return "0"
    if abs(value) >= 1e4 or abs(value) < 1e-3:
        return f"{value:.1e}"
    return f"{value:.4g}"


def render_line_chart(spec: ChartSpec, width: int = 760, height: int = 360) -> str:
    if spec.y_scale not in ("linear", "log"):
        raise ValueError("chart y_scale must be linear or log")
    left, right, top, bottom = 76.0, 24.0, 48.0, 58.0
    plot_w, plot_h = width - left - right, height - top - bottom
    all_x = np.asarray([v for s in spec.series for v in s.x], dtype=float)
    all_y = np.asarray([v for s in spec.series for v in s.y], dtype=float)
    if not np.all(np.isfinite(all_x)) or not np.all(np.isfinite(all_y)):
        raise ValueError("chart contains non-finite values")
    xmin, xmax = float(all_x.min()), float(all_x.max())
    if xmax == xmin:
        xmax = xmin + 1.0

    if spec.y_scale == "log":
        positive = all_y[all_y > 0]
        if not positive.size:
            raise ValueError("log chart requires at least one positive value")
        floor = float(positive.min()) * 0.5
        transformed = np.log10(np.maximum(all_y, floor))
        ymin, ymax = float(transformed.min()), float(transformed.max())
        if ymax == ymin:
            ymin -= 0.5
            ymax += 0.5

        def ty(value: float) -> float:
            return math.log10(max(value, floor))

        def y_label(value: float) -> str:
            return _fmt(10 ** value)
    else:
        ymin, ymax = float(all_y.min()), float(all_y.max())
        pad = 0.05 * (ymax - ymin if ymax > ymin else max(abs(ymax), 1.0))
        ymin, ymax = ymin - pad, ymax + pad

        def ty(value: float) -> float:
            return value

        def y_label(value: float) -> str:
            return _fmt(value)

    def px(value: float) -> float:
        return left + (value - xmin) / (xmax - xmin) * plot_w

    def py(value: float) -> float:
        return top + (ymax - ty(value)) / (ymax - ymin) * plot_h

    palette = ("#2563eb", "#dc2626", "#059669", "#7c3aed", "#d97706", "#0891b2")
    x_ticks = np.linspace(xmin, xmax, 5)
    y_ticks = np.linspace(ymin, ymax, 5)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{escape(spec.title)}">',
        "<style>"
        ".bg{fill:#fff}.grid{stroke:#e5e7eb;stroke-width:1}.axis{stroke:#6b7280;stroke-width:1.2}"
        ".tick{fill:#4b5563;font:12px system-ui,sans-serif}.label{fill:#374151;"
        "font:13px system-ui,sans-serif}.title{fill:#111827;font:600 16px system-ui,sans-serif}"
        ".legend{fill:#374151;font:12px system-ui,sans-serif}</style>",
        f'<rect class="bg" width="{width}" height="{height}" rx="12"/>',
        f'<text class="title" x="{left}" y="24">{escape(spec.title)}</text>',
    ]
    for xt in x_ticks:
        x = px(float(xt))
        parts.append(
            f'<line class="grid" x1="{x:.2f}" x2="{x:.2f}" y1="{top}" y2="{top + plot_h}"/>'
        )
        parts.append(
            f'<text class="tick" x="{x:.2f}" y="{top + plot_h + 21}" '
            f'text-anchor="middle">{escape(_fmt(float(xt)))}</text>'
        )
    for yt in y_ticks:
        y = top + (ymax - float(yt)) / (ymax - ymin) * plot_h
        parts.append(
            f'<line class="grid" x1="{left}" x2="{left + plot_w}" y1="{y:.2f}" y2="{y:.2f}"/>'
        )
        parts.append(
            f'<text class="tick" x="{left - 10}" y="{y + 4:.2f}" '
            f'text-anchor="end">{escape(y_label(float(yt)))}</text>'
        )
    parts.extend([
        f'<line class="axis" x1="{left}" x2="{left + plot_w}" y1="{top + plot_h}" '
        f'y2="{top + plot_h}"/>',
        f'<line class="axis" x1="{left}" x2="{left}" y1="{top}" y2="{top + plot_h}"/>',
        f'<text class="label" x="{left + plot_w / 2:.2f}" y="{height - 12}" '
        f'text-anchor="middle">{escape(spec.x_label)}</text>',
        f'<text class="label" transform="translate(17 {top + plot_h / 2:.2f}) rotate(-90)" '
        f'text-anchor="middle">{escape(spec.y_label)}</text>',
    ])
    for index, series in enumerate(spec.series):
        color = palette[index % len(palette)]
        dash = ' stroke-dasharray="8 6"' if series.role in ("bound", "reference") else ""
        points = " ".join(f"{px(x):.2f},{py(y):.2f}" for x, y in zip(series.x, series.y))
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.3" '
            f'stroke-linejoin="round" stroke-linecap="round"{dash}/>'
        )
        lx = left + index * 185
        parts.append(
            f'<line x1="{lx}" x2="{lx + 25}" y1="39" y2="39" stroke="{color}" '
            f'stroke-width="2.3"{dash}/>'
        )
        parts.append(
            f'<text class="legend" x="{lx + 31}" y="43">{escape(series.label)}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def render_check_svg(slug: str) -> str:
    return render_line_chart(build_check_chart(slug))
