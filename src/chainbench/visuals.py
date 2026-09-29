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


def render_line_chart(spec: ChartSpec, width: int = 760, height: int = 400,
                      *, colors: tuple[str, ...] | None = None) -> str:
    """Render finite samples without inventing positive values for logarithmic zeros."""
    import json
    import re
    import textwrap
    from dataclasses import asdict

    if (type(width) is not int or type(height) is not int
            or not 380 <= width <= 2400 or not 260 <= height <= 1600):
        raise ValueError("chart dimensions must be bounded integers")
    if spec.y_scale not in ("linear", "log") or not spec.series:
        raise ValueError("chart needs series and a linear or log y_scale")
    if colors is not None and (len(colors) != len(spec.series)
                              or any(not re.fullmatch(r"#[0-9a-fA-F]{6}", c) for c in colors)):
        raise ValueError("colors must supply one six-digit hex color per series")
    for series in spec.series:
        _series(series.label, series.x, series.y, series.role)
        if any(b <= a for a, b in zip(series.x, series.x[1:])):
            raise ValueError("chart x samples must be strictly increasing")
        if series.role not in ("observed", "bound", "reference", "samples"):
            raise ValueError("unknown chart series role")
    all_x = np.asarray([v for s in spec.series for v in s.x], dtype=float)
    all_y = np.asarray([v for s in spec.series for v in s.y], dtype=float)
    xmin, xmax = float(all_x.min()), float(all_x.max())
    if not math.isfinite(xmax - xmin):
        raise ValueError("chart x range exceeds floating point")
    if xmax == xmin:
        xmin, xmax = xmin - .5, xmax + .5
    title_lines = textwrap.wrap(spec.title, max(24, (width - 100) // 8)) or [""]
    columns = max(1, (width - 95) // 235)
    legend_rows = math.ceil(len(spec.series) / columns)
    top = 30 * len(title_lines) + 24 * legend_rows + 15
    height = max(height, top + 230)
    left, right, bottom = 82., 22., 72.
    plot_w, plot_h = width - left - right, height - top - bottom
    positive = all_y[all_y > 0]
    use_log = spec.y_scale == "log" and bool(positive.size)
    zeros = int(np.count_nonzero(all_y == 0))
    if use_log:
        ymin, ymax = float(np.log10(positive.min())), float(np.log10(positive.max()))
        if ymin == ymax:
            ymin, ymax = ymin - .5, ymax + .5
        note = "Log10 y-axis."
        if zeros:
            note += f" {zeros} zero samples shown as triangles at baseline, not positive values."
        def sy(value):
            return top + (ymax - math.log10(value)) / (ymax - ymin) * plot_h
        ticks = [(v, f"10^{v:.1f}") for v in np.linspace(ymin, ymax, 5)]
        # Prefer integral powers when the range permits them.
        powers = list(range(math.ceil(ymin), math.floor(ymax) + 1))
        if len(powers) >= 2:
            powers = powers[::max(1, math.ceil(len(powers) / 6))]
            ticks = [(float(v), f"10^{v}") for v in powers]
    else:
        scale = float(all_y.max()) or 1.
        ymin, ymax = 0., 1.
        note = "Linear y-axis. All recorded values are zero." if not positive.size else "Linear y-axis."
        def sy(value):
            return top + (1 - value / scale) * plot_h
        ticks = [(float(v), _fmt(float(v) * scale)) for v in np.linspace(0, 1, 5)]
    def sx(value):
        return left + (value - xmin) / (xmax - xmin) * plot_w
    def text(x, y, value, size=12, anchor="start", weight=400):
        return (f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" '
                f'fill="#334155" font-size="{size}" font-weight="{weight}">{escape(str(value))}</text>')
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
             f'role="img" aria-label="{escape(spec.title)}" font-family="system-ui,sans-serif">',
             f'<title>{escape(spec.title)}</title><desc>{escape(note)}</desc>',
             '<metadata>' + escape(json.dumps(asdict(spec), allow_nan=False)) + '</metadata>',
             f'<rect width="{width}" height="{height}" rx="12" fill="white"/>']
    for i, line in enumerate(title_lines):
        parts.append(text(left, 24 + 27 * i, line, 16, weight=650))
    for tick in np.linspace(xmin, xmax, 5):
        x = sx(float(tick))
        parts.append(f'<path d="M{x:.2f},{top} V{top + plot_h}" stroke="#e2e8f0"/>')
        parts.append(text(x, top + plot_h + 20, _fmt(float(tick)), anchor="middle"))
    for value, label in ticks:
        y = top + (ymax - value) / (ymax - ymin) * plot_h
        parts.append(f'<path d="M{left},{y:.2f} H{left + plot_w}" stroke="#e2e8f0"/>')
        parts.append(text(left - 10, y + 4, label, anchor="end"))
    parts.append(f'<path d="M{left},{top} V{top + plot_h} H{left + plot_w}" '
                 'fill="none" stroke="#64748b"/>')
    parts.append(text(left + plot_w / 2, height - 31, spec.x_label, 13, "middle"))
    parts.append(f'<text transform="translate(18 {top + plot_h / 2}) rotate(-90)" '
                 f'text-anchor="middle" fill="#334155" font-size="12">{escape(spec.y_label)}</text>')
    palette = colors or ("#2563eb", "#dc2626", "#059669", "#7c3aed", "#d97706", "#0891b2")
    patterns = ("", "7 4", "2 3", "9 3 2 3", "12 4", "4 2")
    for i, series in enumerate(spec.series):
        color = palette[i % len(palette)]
        pattern = "8 5" if series.role in ("bound", "reference") else patterns[i % len(patterns)]
        dash = f' stroke-dasharray="{pattern}"' if pattern else ""
        segments, segment = [], []
        for x, y in zip(series.x, series.y):
            if use_log and y == 0:
                if segment:
                    segments.append(segment)
                    segment = []
                px, py = sx(x), top + plot_h
                parts.append(f'<path d="M{px-4:.2f},{py-7:.2f} L{px+4:.2f},{py-7:.2f} '
                             f'L{px:.2f},{py:.2f} Z" fill="{color}"><title>'
                             f'{escape(series.label)}: k={x:g}, value=0</title></path>')
            elif series.role == "samples":
                px, py = sx(x), sy(y)
                parts.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="4.1" fill="{color}" '
                             f'fill-opacity=".83" stroke="white" stroke-width="1.2"><title>'
                             f'{escape(series.label)}: sample={x:g}, value={y:.8g}</title></circle>')
            else:
                segment.append((sx(x), sy(y)))
        if segment:
            segments.append(segment)
        for segment in segments:
            points = " ".join(f"{x:.2f},{y:.2f}" for x, y in segment)
            parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" '
                         f'stroke-width="2.3"{dash}/>')
            if len(segment) == 1:
                x, y = segment[0]
                parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}"/>')
        lx = left + (i % columns) * ((width - left - right) / columns)
        ly = 30 * len(title_lines) + 12 + (i // columns) * 24
        if series.role == "samples":
            parts.append(f'<circle cx="{lx+10:.2f}" cy="{ly:.2f}" r="4" fill="{color}"/>')
        else:
            parts.append(f'<path d="M{lx},{ly} h24" stroke="{color}" stroke-width="2.3"{dash}/>')
        parts.append(text(lx + 30, ly + 4, series.label))
    for i, line in enumerate(textwrap.wrap(note, max(24, (width - 95) // 5))):
        parts.append(text(left, height - 20 + 11 * i, line, 10))
    parts.append('</svg>')
    return ''.join(parts)


def render_check_svg(slug: str) -> str:
    return render_line_chart(build_check_chart(slug))
