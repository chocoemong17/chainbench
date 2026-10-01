"""Geometry-first two-dimensional visualizations for supported optimization methods."""
from __future__ import annotations

import json
import math
import platform
from html import escape

import numpy as np

from . import __version__
from ._landscape_context import context_html, readouts_html, values_html
from ._pages import bi, evidence, page
from ._ppa_subproblem import subproblem_record
from ._ppa_subproblem_views import subproblem_html
from ._sources import SOURCE_LINKS
from .methods import (
    Trace,
    accelerated_gradient,
    conjugate_gradient,
    gradient_descent,
    heavy_ball,
    proximal_point,
)
from .problems import QuadraticProblem
from .stress_cases import input_digest
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


def _traces(problem: QuadraticProblem, steps: int, methods: tuple[str, ...]) -> tuple[dict[str, Trace], dict]:
    if isinstance(steps, bool) or not isinstance(steps, int) or not 2 <= steps <= 80:
        raise ValueError("steps must be an integer between 2 and 80")
    if not methods or any(method not in METHODS for method in methods) or len(set(methods)) != len(methods):
        raise ValueError("methods must be unique supported quadratic methods")
    x0 = np.array([-1.55, 1.45])
    out, parameters = {}, {}
    for method in methods:
        if method == "gd":
            trace = gradient_descent(problem, steps, x0=x0)
            parameters[method] = {'step': 1/problem.L}
        elif method == "smooth-fista":
            trace = accelerated_gradient(problem, steps, x0=x0)
            parameters[method] = {'step': 1/problem.L, 't0': 1., 'y0': x0.tolist()}
        elif method == "heavy-ball":
            trace, alpha, beta = heavy_ball(problem, steps, x0=x0)
            parameters[method] = {'alpha': alpha, 'beta': beta, 'x_minus_1': x0.tolist()}
        elif method == "cg":
            trace = conjugate_gradient(problem, steps, x0=x0)
            parameters[method] = {'rtol': 1e-12, 'atol': 0.,
                                  'stopping': '||b-Qx|| <= max(atol, rtol*||b-Qx0||)',
                                  'implementation': 'scaled correction; recomputed true residual'}
        else:
            trace = proximal_point(problem, steps, 1.0, x0=x0)
            parameters[method] = {'proximal_parameter': 1., 'solve': '(I+cQ)x_next=x+c*b'}
        out[method] = trace
    return out, parameters


def run_landscape(condition_number: float = 20.0, angle_degrees: float = 32.0,
                  steps: int = 18, methods: tuple[str, ...] = METHODS) -> dict:
    p = _problem(condition_number, angle_degrees)
    computed, parameters = _traces(p, steps, methods)
    traces = {m: [x.tolist() for x in t.iterates] for m, t in computed.items()}
    values = {}
    for method, points in traces.items():
        values[method] = [p.gap(np.asarray(point)) for point in points]
    arrays = {'Q': p.Q.tolist(), 'b': p.b.tolist(), 'x_star': p.x_star.tolist(),
              'x0': next(iter(traces.values()))[0]}
    sources = {'gd': ('gd-baseline', 'ISTA with g=0; fixed step 1/L'),
               'smooth-fista': ('beck-teboulle-2009', 'fixed-L FISTA with g=0; not literal Nesterov 1983'),
               'heavy-ball': ('polyak-1964', 'classical quadratic tuning'),
               'cg': ('hestenes-stiefel-1952', 'linear SPD conjugate gradients'),
               'proximal-point': ('rockafellar-1976', 'exact quadratic resolvent specialization')}
    result = {
        "kind": "chainbench.landscape",
        "schema_version": 1,
        "problem": {
            "kind": "rotated-2d-quadratic",
            "condition_number": condition_number,
            "angle_degrees": angle_degrees,
            "Q": p.Q.tolist(),
            'b': p.b.tolist(), 'c': 0., 'dimension': p.dim,
            'L': p.L, 'mu': p.mu, 'actual_condition_number': p.L/p.mu,
            'f_star': p.f_star, 'lambda': None, 'seed': None,
            "x_star": p.x_star.tolist(),
            "start": [-1.55, 1.45],
        },
        "steps": steps,
        "methods": list(methods),
        "traces": traces,
        "gaps": values,
        'method_parameters': parameters,
        'runs': {m: {'updates': len(t.iterates)-1, 'termination': t.termination or 'fixed_budget',
                     'residual_norms': [float(np.linalg.norm(p.grad(x))) for x in t.iterates]}
                 for m, t in computed.items()},
        'sources': {m: {'url': SOURCE_LINKS[sources[m][0]], 'scope': sources[m][1]} for m in methods},
        'input_sha256': input_digest(arrays),
        'input_hash_format': 'sorted names + NUL + compact shape JSON + NUL + little-endian float64 C-order bytes; Q,b,x_star,x0',
        'environment': {'chainbench': __version__, 'numpy': np.__version__,
                        'python': platform.python_version(), 'os': platform.system()},
        "notice": (
            "This is a deliberately chosen 2D geometric teaching problem, not evidence that one "
            "method dominates on all objectives. Use stress sampling for many-case evidence."
        ),
    }
    if 'proximal-point' in computed:
        result['proximal_subproblems'] = subproblem_record(p, computed['proximal-point'],
            parameters['proximal-point']['proximal_parameter'])
    json.dumps(result, allow_nan=False)
    return result


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


def _svg_open(result, view, width, height, axes, selected, label):
    metadata = {'kind': 'chainbench.landscape-projection', 'view': view, 'axes': axes,
                'problem': result['problem'], 'steps': result['steps'],
                'methods': list(selected), 'method_parameters': result['method_parameters'],
                'input_sha256': result['input_sha256'], 'environment': result['environment']}
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="{label}" data-landscape-view="{view}" '
            f'data-projection="{escape(json.dumps(axes), quote=True)}">'
            '<metadata>'+escape(json.dumps(metadata, allow_nan=False))+'</metadata>'
            '<rect width="100%" height="100%" rx="18" fill="#fbfaf7"/>')


def _label(x, y, text, size=11, anchor='start'):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="#334155">{escape(text)}</text>')


def contour_svg(result: dict, width: int = 720, height: int = 500, methods: tuple[str, ...] | None = None) -> str:
    selected = tuple(result['methods']) if methods is None else methods
    columns = max(1, int((width-86)//120))
    legend_rows = math.ceil(len(selected)/columns)
    xmin, xmax, ymin, ymax = _bounds(result)
    q = np.asarray(result["problem"]["Q"])
    star = np.asarray(result["problem"]["x_star"])
    eig, vec = np.linalg.eigh(q)
    corner = max(_gap(result, x, y) for x in (xmin, xmax) for y in (ymin, ymax))
    levels = np.geomspace(max(corner * 0.01, 1e-4), corner * .9, 8)
    left, right, top, bottom = 60., 26., 50., 90.+18*(legend_rows-1)
    pw, ph = width - left - right, height - top - bottom
    # Pad the shorter coordinate span, never stretch one coordinate independently.
    unit = max((xmax-xmin)/pw, (ymax-ymin)/ph)
    cx, cy = (xmin+xmax)/2, (ymin+ymax)/2
    xmin, xmax, ymin, ymax = cx-pw*unit/2, cx+pw*unit/2, cy-ph*unit/2, cy+ph*unit/2
    axes = dict(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax,
                left=left, top=top, width=pw, height=ph, units_per_pixel=unit,
                contour_levels=levels.tolist())
    def sx(x):
        return left + (x - xmin) / (xmax - xmin) * pw

    def sy(y):
        return top + (ymax - y) / (ymax - ymin) * ph
    clip = 'landscape-clip-'+str(width)+'-'+'-'.join(selected)
    parts = [_svg_open(result, 'contour', width, height, axes, selected, 'Contour trajectories'),
             _label(left, 27, 'Contours · equal x₁/x₂ scales', 16),
             f'<defs><clipPath id="{clip}"><rect x="{left}" y="{top}" width="{pw}" height="{ph}"/></clipPath></defs>',
             f'<rect x="{left}" y="{top}" width="{pw}" height="{ph}" fill="white" stroke="#ccd4df"/>',
             f'<g clip-path="url(#{clip})">']
    for level in levels:
        t = np.linspace(0, 2 * np.pi, 180)
        radii = np.sqrt(2 * level / eig)
        local = np.vstack((radii[0] * np.cos(t), radii[1] * np.sin(t)))
        pts = (vec @ local).T + star
        path = ' '.join(f'{sx(float(x)):.2f},{sy(float(y)):.2f}' for x, y in pts)
        parts.append(f'<polyline points="{path}" fill="none" stroke="#d6d1c7" stroke-width="1.2">'
                     f'<title>f(x)−f*={level:.6g}</title></polyline>')
    for method in selected:
        pts = result["traces"][method]
        screen = [(sx(p[0]), sy(p[1])) for p in pts]
        path = ' '.join(f'{x:.2f},{y:.2f}' for x, y in screen)
        encoded = _trajectory_attr(screen)
        color = COLORS[method]
        parts.append(f'<polyline data-method="{method}" data-trajectory-line="" data-trajectory-points="{encoded}" points="{path}" '
                     f'fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round"/>')
        for i, (x, y) in enumerate(screen[:min(8, len(screen))]):
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.5" fill="{color}" fill-opacity=".45"><title>{escape(method)} k={i}</title></circle>')
        x, y = screen[-1]
        parts.append(f'<circle data-method="{method}" data-trajectory-marker="" data-trajectory-points="{encoded}" cx="{x:.2f}" cy="{y:.2f}" '
                     f'r="6" fill="{color}" stroke="white" stroke-width="2"><title>{escape(method)} current iterate</title></circle>')
    parts.append(f'<circle cx="{sx(star[0]):.2f}" cy="{sy(star[1]):.2f}" r="6" fill="#111827"/><text x="{sx(star[0])+9:.2f}" y="{sy(star[1])-8:.2f}" font-size="12" fill="#111827">optimum</text>')
    parts.append('</g>')
    for x in (xmin, (xmin+xmax)/2, xmax):
        parts.append(_label(sx(x), top+ph+20, f'{x:.3g}', anchor='middle'))
    for y in (ymin, (ymin+ymax)/2, ymax):
        parts.append(_label(left-8, sy(y)+4, f'{y:.3g}', anchor='end'))
    parts.extend([_label(left+pw/2, top+ph+42, 'x₁', 13, 'middle'),
                  _label(20, top-15, 'x₂', 13)])
    for index, method in enumerate(selected):
        x = left+(index % columns)*120
        legend_y = height-18-(legend_rows-1-index//columns)*18
        parts.append(f'<line x1="{x}" x2="{x+24}" y1="{legend_y}" y2="{legend_y}" stroke="{COLORS[method]}" stroke-width="3"/><text x="{x+30}" y="{legend_y+4}" font-size="11" fill="#334155">{escape(method)}</text>')
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

    axis_points = [(xmin, ymin, 0.), (xmax, ymin, 0.), (xmin, ymax, 0.), (xmin, ymin, zmax)]
    raw_grid = [raw(float(x), float(y), _gap(result, float(x), float(y))) for x in xs for y in ys]
    raw_grid.extend(raw(*p) for p in axis_points)
    rx = [p[0] for p in raw_grid]
    ry = [p[1] for p in raw_grid]
    margin_x, margin_y = 65., 76.
    scale_x = (width - 2 * margin_x) / (max(rx) - min(rx))
    scale_y = (height - 2 * margin_y) / (max(ry) - min(ry))
    scale = min(scale_x, scale_y)
    cx = width / 2 - scale * (max(rx) + min(rx)) / 2
    cy = height / 2 - scale * (max(ry) + min(ry)) / 2 + 12

    def proj(x, y, z):
        a, b = raw(x, y, z)
        return cx + scale * a, cy + scale * b

    axes = dict(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, zmax=zmax,
                scale=scale, cx=cx, cy=cy,
                formula='xn=2*(x-xmin)/(xmax-xmin)-1; yn likewise; zn=z/zmax; screen=(cx+s*(xn-yn),cy+s*(0.48*(xn+yn)-1.55*zn))')
    parts = [_svg_open(result, 'surface', width, height, axes, result['methods'], '3D objective surface'),
             _label(40, 27, '3D surface · actual height f(x)−f*', 17)]
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
        parts.append(f'<polyline data-method="{method}" data-trajectory-line="" data-trajectory-points="{encoded}" points="{path}" '
                     f'fill="none" stroke="{COLORS[method]}" stroke-width="3"/>')
        for i, (a, b) in enumerate(pts[:min(8, len(pts))]):
            parts.append(f'<circle cx="{a:.2f}" cy="{b:.2f}" r="2.5" fill="{COLORS[method]}" fill-opacity=".45"><title>{escape(method)} k={i}</title></circle>')
        a, b = pts[-1]
        parts.append(f'<circle data-method="{method}" data-trajectory-marker="" data-trajectory-points="{encoded}" cx="{a:.2f}" cy="{b:.2f}" '
                     f'r="6" fill="{COLORS[method]}" stroke="white" stroke-width="2"><title>{escape(method)} current iterate</title></circle>')
    ox, oy = proj(*axis_points[0])
    for point, label in zip(axis_points[1:], (f'x₁={xmax:.3g}', f'x₂={ymax:.3g}', f'gap={zmax:.3g}')):
        ex, ey = proj(*point)
        parts.append(f'<line x1="{ox:.2f}" y1="{oy:.2f}" x2="{ex:.2f}" y2="{ey:.2f}" stroke="#475569"/>')
        parts.append(_label(ex, ey+18 if point[2] == 0 else ey-12, label, 11,
                            'end' if ex > width/2 else 'start'))
    parts.append(_label(40, height-35, f'Axis origin: ({xmin:.3g}, {ymin:.3g}, 0)', 11))
    parts.append(_label(40, height-16, 'Oblique view; coordinates normalized separately; chords join samples', 11))
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
    ), colors=tuple(COLORS[m] for m in result['methods']))
    body = (
        '<div class="evidence-banner"><span class="evidence-tag">GEOMETRIC ILLUSTRATION</span>'
        + bi(
            '이 화면은 일부러 길쭉하고 회전된 2차원 bowl을 골라 각 방법의 이동 방향을 눈으로 이해하기 위한 예시입니다. 대표성 증거가 아니라 기하 직관용입니다.',
            'This deliberately elongated, rotated 2D bowl is chosen to make update geometry visible. It is for intuition, not representative evidence.',
        ) + '</div>'
        + context_html(result, COLORS)
        + '<div class="trajectory-player landscape-controls" data-trajectory-player><button type="button" data-trajectory-play aria-pressed="false" aria-label="play or pause trajectory">▶</button>'
        + '<span>' + bi('반복을 직접 움직여 보기', 'Scrub or animate the iterations') + '</span>'
        + f'<input data-trajectory-slider type="range" min="0" max="{max(len(v) for v in result["traces"].values()) - 1}" value="{max(len(v) for v in result["traces"].values()) - 1}">'
        + f'<strong data-trajectory-label>k = {max(len(v) for v in result["traces"].values()) - 1}</strong></div>'
        + readouts_html(result)
        + '<section><h2>' + bi('먼저 전체 지형과 3D 높이를 함께 보기', 'First: the shared contour map and 3D height') + '</h2><p class="small">'
        + bi('재생 버튼이나 슬라이더를 움직이면 contour와 3D의 현재점이 같은 반복 번호로 함께 이동합니다.', 'The play button and slider move the current iterate on the contour and 3D views in sync.') + '</p><div class="visual-grid"><div>' + contour_svg(result) + '</div><div>' + surface_svg(result) + '</div></div></section>'
        + subproblem_html(result)
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
        ) + '</p>' + values_html(result) + evidence(result, 'landscape-evidence.json')
    )
    return page(
        'See the optimization path, not only the loss',
        bi('같은 수치 실행을 contour, 3D surface, loss 세 시점에서 연결합니다.', 'Connect the same numerical run through contour, 3D surface and loss views.'),
        body,
        lang=lang,
    )
