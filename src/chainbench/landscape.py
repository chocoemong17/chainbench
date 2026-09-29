"""Geometry-first two-dimensional visualizations for supported optimization methods."""
from __future__ import annotations

import json
import math
from html import escape

import numpy as np

from ._pages import bi, evidence, page
from .methods import accelerated_gradient, conjugate_gradient, gradient_descent, heavy_ball, proximal_point
from .problems import QuadraticProblem
from .visuals import ChartSpec, LineSeries, render_line_chart

METHODS = ("gd", "smooth-fista", "heavy-ball", "cg", "proximal-point")
COLORS = {
    "gd": "#2563eb",
    "smooth-fista": "#7c3aed",
    "heavy-ball": "#dc2626",
    "cg": "#059669",
    "proximal-point": "#d97706",
}


def _problem(condition_number: float, angle_degrees: float) -> QuadraticProblem:
    if not math.isfinite(condition_number) or not 1.01 <= condition_number <= 10000:
        raise ValueError("condition_number must be between 1.01 and 10000")
    if not math.isfinite(angle_degrees) or not -85 <= angle_degrees <= 85:
        raise ValueError("angle_degrees must be between -85 and 85")
    theta = math.radians(angle_degrees)
    r = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
    q = r @ np.diag([1.0 / condition_number, 1.0]) @ r.T
    x_star = np.array([1.0, -0.8])
    return QuadraticProblem.from_reference(q, x_star)


def _traces(problem: QuadraticProblem, steps: int, methods: tuple[str, ...]) -> dict[str, list[list[float]]]:
    if isinstance(steps, bool) or not isinstance(steps, int) or not 2 <= steps <= 80:
        raise ValueError("steps must be an integer between 2 and 80")
    if not methods or any(method not in METHODS for method in methods) or len(set(methods)) != len(methods):
        raise ValueError("methods must be unique supported quadratic methods")
    x0 = np.array([-1.55, 1.45])
    out = {}
    for method in methods:
        if method == "gd":
            trace = gradient_descent(problem, steps, x0=x0)
        elif method == "smooth-fista":
            trace = accelerated_gradient(problem, steps, x0=x0)
        elif method == "heavy-ball":
            trace = heavy_ball(problem, steps, x0=x0)[0]
        elif method == "cg":
            trace = conjugate_gradient(problem, steps, x0=x0)
        else:
            trace = proximal_point(problem, steps, 1.0, x0=x0)
        out[method] = [x.tolist() for x in trace.iterates]
    return out


def run_landscape(condition_number: float = 20.0, angle_degrees: float = 32.0,
                  steps: int = 18, methods: tuple[str, ...] = METHODS) -> dict:
    p = _problem(condition_number, angle_degrees)
    traces = _traces(p, steps, methods)
    values = {}
    for method, points in traces.items():
        values[method] = [p.gap(np.asarray(point)) for point in points]
    return {
        "kind": "chainbench.landscape",
        "schema_version": 1,
        "problem": {
            "kind": "rotated-2d-quadratic",
            "condition_number": condition_number,
            "angle_degrees": angle_degrees,
            "Q": p.Q.tolist(),
            "x_star": p.x_star.tolist(),
            "start": [-1.55, 1.45],
        },
        "steps": steps,
        "methods": list(methods),
        "traces": traces,
        "gaps": values,
        "notice": (
            "This is a deliberately chosen 2D geometric teaching problem, not evidence that one "
            "method dominates on all objectives. Use stress sampling for many-case evidence."
        ),
    }


def _bounds(result: dict):
    points = [np.asarray(p) for trace in result["traces"].values() for p in trace]
    points.append(np.asarray(result["problem"]["x_star"]))
    xs = np.asarray([p[0] for p in points])
    ys = np.asarray([p[1] for p in points])
    pad_x = max(.55, .2 * (xs.max() - xs.min()))
    pad_y = max(.55, .2 * (ys.max() - ys.min()))
    return float(xs.min() - pad_x), float(xs.max() + pad_x), float(ys.min() - pad_y), float(ys.max() + pad_y)


def _gap(result: dict, x: float, y: float) -> float:
    q = np.asarray(result["problem"]["Q"])
    star = np.asarray(result["problem"]["x_star"])
    e = np.asarray([x, y]) - star
    return float(.5 * e @ q @ e)


def _trajectory_attr(points: list[tuple[float, float]]) -> str:
    return escape("|".join(f"{x:.2f},{y:.2f}" for x, y in points), quote=True)


def contour_svg(result: dict, width: int = 720, height: int = 500, methods: tuple[str, ...] | None = None) -> str:
    xmin, xmax, ymin, ymax = _bounds(result)
    q = np.asarray(result["problem"]["Q"])
    star = np.asarray(result["problem"]["x_star"])
    eig, vec = np.linalg.eigh(q)
    corner = max(_gap(result, x, y) for x in (xmin, xmax) for y in (ymin, ymax))
    levels = np.geomspace(max(corner * 0.01, 1e-4), corner * .9, 8)
    left, right, top, bottom = 58., 24., 42., 52.
    pw, ph = width - left - right, height - top - bottom
    sx = lambda x: left + (x - xmin) / (xmax - xmin) * pw
    sy = lambda y: top + (ymax - y) / (ymax - ymin) * ph
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Contour trajectories">',
             '<rect width="100%" height="100%" rx="18" fill="#fbfaf7"/>',
             '<text x="58" y="27" font-size="17" font-weight="700" fill="#172238">Contour map: where each method moves</text>']
    for level in levels:
        t = np.linspace(0, 2 * np.pi, 180)
        radii = np.sqrt(2 * level / eig)
        local = np.vstack((radii[0] * np.cos(t), radii[1] * np.sin(t)))
        pts = (vec @ local).T + star
        path = ' '.join(f'{sx(float(x)):.2f},{sy(float(y)):.2f}' for x, y in pts)
        parts.append(f'<polyline points="{path}" fill="none" stroke="#d6d1c7" stroke-width="1.2"/>')
    selected = tuple(result["methods"]) if methods is None else methods
    for method in selected:
        pts = result["traces"][method]
        screen = [(sx(p[0]), sy(p[1])) for p in pts]
        path = ' '.join(f'{x:.2f},{y:.2f}' for x, y in screen)
        encoded = _trajectory_attr(screen)
        color = COLORS[method]
        parts.append(f'<polyline data-trajectory-line data-trajectory-points="{encoded}" points="{path}" '
                     f'fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round"/>')
        for i, (x, y) in enumerate(screen[:min(8, len(screen))]):
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.5" fill="{color}" fill-opacity=".45"><title>{escape(method)} k={i}</title></circle>')
        x, y = screen[-1]
        parts.append(f'<circle data-trajectory-marker data-trajectory-points="{encoded}" cx="{x:.2f}" cy="{y:.2f}" '
                     f'r="6" fill="{color}" stroke="white" stroke-width="2"><title>{escape(method)} current iterate</title></circle>')
    parts.append(f'<circle cx="{sx(star[0]):.2f}" cy="{sy(star[1]):.2f}" r="6" fill="#111827"/><text x="{sx(star[0])+9:.2f}" y="{sy(star[1])-8:.2f}" font-size="12" fill="#111827">optimum</text>')
    legend_y = height - 18
    x = left
    for method in selected:
        parts.append(f'<line x1="{x}" x2="{x+24}" y1="{legend_y}" y2="{legend_y}" stroke="{COLORS[method]}" stroke-width="3"/><text x="{x+30}" y="{legend_y+4}" font-size="11" fill="#334155">{escape(method)}</text>')
        x += 120
    parts.append('</svg>')
    return ''.join(parts)


def surface_svg(result: dict, width: int = 720, height: int = 500) -> str:
    xmin, xmax, ymin, ymax = _bounds(result)
    nx = 15
    xs = np.linspace(xmin, xmax, nx)
    ys = np.linspace(ymin, ymax, nx)
    zmax = max(_gap(result, float(x), float(y)) for x in xs for y in ys) or 1.0

    def raw(x, y, z):
        xn = (x - xmin) / (xmax - xmin) * 2 - 1
        yn = (y - ymin) / (ymax - ymin) * 2 - 1
        zn = z / zmax
        return xn - yn, .48 * (xn + yn) - 1.55 * zn

    raw_grid = [raw(float(x), float(y), _gap(result, float(x), float(y))) for x in xs for y in ys]
    rx = [p[0] for p in raw_grid]; ry = [p[1] for p in raw_grid]
    margin_x, margin_y = 55., 58.
    scale_x = (width - 2 * margin_x) / (max(rx) - min(rx))
    scale_y = (height - 2 * margin_y) / (max(ry) - min(ry))
    scale = min(scale_x, scale_y)
    cx = width / 2 - scale * (max(rx) + min(rx)) / 2
    cy = height / 2 - scale * (max(ry) + min(ry)) / 2 + 12

    def proj(x, y, z):
        a, b = raw(x, y, z)
        return cx + scale * a, cy + scale * b

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="3D objective surface">',
             '<rect width="100%" height="100%" rx="18" fill="#fbfaf7"/>',
             '<text x="40" y="27" font-size="17" font-weight="700" fill="#172238">3D surface: same trajectories on objective height</text>']
    for y in ys:
        pts = [proj(float(x), float(y), _gap(result, float(x), float(y))) for x in xs]
        parts.append('<polyline points="' + ' '.join(f'{a:.2f},{b:.2f}' for a,b in pts) + '" fill="none" stroke="#ccd4df" stroke-width="1"/>')
    for x in xs:
        pts = [proj(float(x), float(y), _gap(result, float(x), float(y))) for y in ys]
        parts.append('<polyline points="' + ' '.join(f'{a:.2f},{b:.2f}' for a,b in pts) + '" fill="none" stroke="#ccd4df" stroke-width="1"/>')
    for method in result["methods"]:
        pts = [proj(p[0], p[1], _gap(result, p[0], p[1])) for p in result["traces"][method]]
        encoded = _trajectory_attr(pts)
        path = ' '.join(f'{a:.2f},{b:.2f}' for a, b in pts)
        parts.append(f'<polyline data-trajectory-line data-trajectory-points="{encoded}" points="{path}" '
                     f'fill="none" stroke="{COLORS[method]}" stroke-width="3"/>')
        for i, (a, b) in enumerate(pts[:min(8, len(pts))]):
            parts.append(f'<circle cx="{a:.2f}" cy="{b:.2f}" r="2.5" fill="{COLORS[method]}" fill-opacity=".45"><title>{escape(method)} k={i}</title></circle>')
        a, b = pts[-1]
        parts.append(f'<circle data-trajectory-marker data-trajectory-points="{encoded}" cx="{a:.2f}" cy="{b:.2f}" '
                     f'r="6" fill="{COLORS[method]}" stroke="white" stroke-width="2"><title>{escape(method)} current iterate</title></circle>')
    parts.append('</svg>')
    return ''.join(parts)


def landscape_html(result: dict, lang: str = "en") -> str:
    if result.get("kind") != "chainbench.landscape":
        raise ValueError("not a landscape result")
    series = []
    for method in result["methods"]:
        y = tuple(result["gaps"][method])
        series.append(LineSeries(method, tuple(range(len(y))), y))
    convergence = render_line_chart(ChartSpec(
        "Objective gap along the same geometric run", "iteration k", "objective gap", tuple(series), "log"
    ))
    body = (
        '<div class="evidence-banner"><span class="evidence-tag">GEOMETRIC ILLUSTRATION</span>'
        + bi(
            '이 화면은 일부러 길쭉하고 회전된 2차원 bowl을 골라 각 방법의 이동 방향을 눈으로 이해하기 위한 예시입니다. 대표성 증거가 아니라 기하 직관용입니다.',
            'This deliberately elongated, rotated 2D bowl is chosen to make update geometry visible. It is for intuition, not representative evidence.',
        ) + '</div>'
        + '<div class="trajectory-player" data-trajectory-player><button type="button" data-trajectory-play aria-label="play or pause trajectory">▶</button>'
        + '<span>' + bi('반복을 직접 움직여 보기', 'Scrub or animate the iterations') + '</span>'
        + f'<input data-trajectory-slider type="range" min="0" max="{max(len(v) for v in result["traces"].values()) - 1}" value="{max(len(v) for v in result["traces"].values()) - 1}">'
        + f'<strong data-trajectory-label>k = {max(len(v) for v in result["traces"].values()) - 1}</strong></div>'
        + '<section><h2>' + bi('먼저 전체 지형과 3D 높이를 함께 보기', 'First: the shared contour map and 3D height') + '</h2><p class="small">'
        + bi('재생 버튼이나 슬라이더를 움직이면 contour와 3D의 현재점이 같은 반복 번호로 함께 이동합니다.', 'The play button and slider move the current iterate on the contour and 3D views in sync.') + '</p><div class="visual-grid"><div>' + contour_svg(result) + '</div><div>' + surface_svg(result) + '</div></div></section>'
        + '<section><h2>' + bi('방법별 경로를 같은 contour에서 따로 보기', 'Then separate each method on the same contour geometry') + '</h2><div class="deep-grid">'
        + ''.join('<article><h3>' + escape(method) + '</h3><div class="plot">' + contour_svg(result, 430, 330, (method,)) + '</div></article>' for method in result['methods']) + '</div></section>'
        + '<section><h2>' + bi('같은 실행을 loss 곡선으로 보면', 'The same run as a convergence chart') + '</h2><div class="plot">' + convergence + '</div></section>'
        + '<section><h2>' + bi('왜 경로가 다르게 보이나?', 'Why do the paths differ?') + '</h2><div class="deep-grid">'
        + '<article><h3>GD</h3><p>' + bi('가장 가파른 방향을 반복해서 따라가므로 길쭉한 골짜기에서 지그재그가 보일 수 있습니다.', 'Repeated steepest directions can zig-zag across a narrow valley.') + '</p></article>'
        + '<article><h3>Momentum / acceleration</h3><p>' + bi('이전 이동을 기억해 좁은 방향의 왕복을 줄이거나, 반대로 과도하게 지나칠 수 있습니다.', 'Memory of prior motion can reduce zig-zagging or create overshoot.') + '</p></article>'
        + '<article><h3>CG</h3><p>' + bi('2차원 SPD 문제에서는 Q-켤레 방향 때문에 매우 적은 단계로 끝날 수 있습니다. 이것은 일반 비선형 목적함수의 보장이 아닙니다.', 'On this 2D SPD quadratic, Q-conjugate directions can finish in very few steps; that is not a general nonlinear guarantee.') + '</p></article>'
        + '<article><h3>Proximal point</h3><p>' + bi('한 번의 업데이트가 선형계를 푸는 비싼 단계라서, 경로가 매끈해 보여도 반복 수만으로 비용을 비교하면 안 됩니다.', 'Each update solves a linear system, so a smooth-looking path is not an equal-cost comparison.') + '</p></article></div></section>'
        + '<p class="callout caution">' + bi(
            '이 그림이 보기 좋다고 해서 그 방법이 모든 문제에서 더 좋다는 뜻은 아닙니다. 대표성은 stress 표본에서, worst-case는 공개 tight construction에서 따로 확인하세요.',
            'A visually attractive path is not a universal ranking. Use seeded stress sampling for breadth and a published tight construction for worst-case claims.',
        ) + '</p>' + evidence(result, 'landscape-evidence.json')
    )
    return page(
        'See the optimization path, not only the loss',
        bi('같은 수치 실행을 contour, 3D surface, loss 세 시점에서 연결합니다.', 'Connect the same numerical run through contour, 3D surface and loss views.'),
        body,
        lang=lang,
    )
