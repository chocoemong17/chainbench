"""A public, horizon-specific GD extremal example, not a worst-case search engine."""
from __future__ import annotations

import math
import platform
from dataclasses import asdict

import numpy as np

from . import __version__
from ._pages import bi, evidence, page
from ._validation import count, scalar
from .visuals import ChartSpec, LineSeries, render_line_chart

SOURCE = "https://arxiv.org/pdf/1206.3209"


def gd_tight_case(horizon: int = 20, L: float = 1., R: float = 1., h: float = 1.) -> dict:
    """Drori--Teboulle preprint Thms 3.1/3.2, h in (0,1], in dimension one.

    The reference function is constructed for N, and held fixed throughout that run.
    Python loops implement GD; the analytic target is independently evaluated.
    """
    n = count(horizon, "horizon", minimum=1)
    if n > 500:
        raise ValueError("horizon must be <=500")
    L, R, h = (scalar(v, name) for v, name in ((L, "L"), (R, "R"), (h, "h")))
    if not (1e-6 <= L <= 1e6 and 1e-6 <= R <= 1e6 and 1e-4 <= h <= 1):
        raise ValueError("require L,R in [1e-6,1e6] and h in [1e-4,1]")
    a = R / (2*n*h + 1)
    def value(x):
        return L*(.5*x*x if abs(x) <= a else a*abs(x) - .5*a*a)
    def grad(x):
        return L*max(-a, min(a, x))
    x, rows = R, []
    for k in range(n + 1):
        rows.append({"iteration": k, "x": x, "gap": value(x), "gradient": grad(x),
                     "upper_bound": L*R*R/(4*k*h + 2)})
        if k < n:
            x -= (h/L)*grad(x)
    target = L*R*R/(4*n*h + 2)
    ratio = rows[-1]["gap"]/target
    if not math.isfinite(ratio):
        raise FloatingPointError("non-finite tightness observation")
    chart = ChartSpec("One fixed Huber instance: equality at the chosen horizon", "iteration k", "objective gap",
                      (LineSeries("GD on horizon-N instance", tuple(range(n+1)), tuple(r["gap"] for r in rows)),
                       LineSeries("published upper bound", tuple(range(n+1)), tuple(r["upper_bound"] for r in rows), "bound")))
    grid = np.linspace(-1.1*R, 1.1*R, 161)
    shape = ChartSpec("The constructed smooth convex objective", "x", "f(x)",
                      (LineSeries("quadratic centre, affine tails", tuple(float(x) for x in grid), tuple(value(float(x)) for x in grid)),), "linear")
    return {"kind": "chainbench.gd_tight_case", "schema_version": 1,
            "config": {"horizon": n, "L": L, "R": R, "h": h, "dimension": 1},
            "environment": {"chainbench": __version__, "python": platform.python_version(), "numpy": np.__version__, "os": platform.system()},
            "reference": {"url": SOURCE, "location": "arXiv:1206.3209, Theorems 3.1 and 3.2 (preprint numbering)", "publication": "Drori and Teboulle, Mathematical Programming 145 (2014), 451-482"},
            "transition": a, "formula": "L*x^2/2 for |x|<=a; L*a*|x|-L*a^2/2 otherwise; a=R/(2*N*h+1)",
            "step_size": h/L, "rows": rows, "target": target, "observed_ratio": ratio,
            "matches_target": abs(ratio - 1) <= 1e-9,
            "charts": {"gap": asdict(chart), "function": asdict(shape)},
            "scope": "GD only; convex C1 functions with L-Lipschitz gradient, ||x0-x*||<=R, fixed step h/L and 0<h<=1. Extremality is supplied by the cited theorem, not numerical search. N changes the constructed function; equality is asserted only at k=N."}


def case_html(result: dict, lang: str = "en") -> str:
    n, h = result["config"]["horizon"], result["config"]["h"]
    def chart(key):
        obj = result["charts"][key]
        return render_line_chart(ChartSpec(obj["title"], obj["x_label"], obj["y_label"], tuple(LineSeries(**s) for s in obj["series"]), obj["y_scale"]))
    intro = bi('랜덤으로 어려운 문제를 찾는 대신, 공개 정리에서 상계에 도달하는 함수를 직접 재현합니다.', 'Reproduce a public construction attaining the bound, rather than searching random hard instances.')
    body = ('<section><span class="badge">Drori–Teboulle · 2014</span><h2>'
            + bi('보장하는 상계와 실제로 도달하는 값', 'The upper bound and an instance attaining it')
            + '</h2><div class="formula">f(x_N) − f* ≤ L R² / (4 N h + 2)</div>'
            + '<p>' + bi('정리 3.1은 모든 허용 함수에 대한 상계, 정리 3.2는 이 상계에 도달하는 구성입니다. 여기서는 그 1차원 특수 경우를 계산합니다.', 'Theorem 3.1 bounds all admissible functions; Theorem 3.2 constructs a matching example. This page computes its one-dimensional specialization.')
            + f'</p><p><a href="{SOURCE}#page=12">Public source · preprint Thms 3.1 / 3.2</a></p>'
            + f'<div class="callout">N = {n} · h = {h:g} · '
            + bi('관측값 / 이론값', 'observed / target') + f' = {result["observed_ratio"]:.12g}</div>'
            + '<div class="plot">' + chart("gap") + '</div></section><section><h2>'
            + bi('왜 이 예제에서 느리게 진행하는가?', 'Why is progress slow here?')
            + '</h2><p>' + bi('N을 정하고 a=R/(2Nh+1)을 고정합니다. 시작점 R에서 N번 업데이트하는 동안 기울기는 L·a로 일정해서, 매번 h·a만큼 이동합니다. 마지막 목적함수 값이 이론 상계와 일치합니다.', 'Choose N, then fix a=R/(2Nh+1). During the first N updates from R, the gradient is L·a and each step moves h·a. The final objective equals the theoretical bound.')
            + '</p><div class="formula">xₖ = R − k h a\nf(x) = L x²/2 (|x| ≤ a); L a |x| − L a²/2 (|x| > a)</div>'
            + '<div class="plot">' + chart("function") + '</div><p class="callout caution">'
            + bi('N을 바꾸면 함수도 바뀝니다. 같은 함수가 모든 k에서 최악인 것은 아닙니다. 이 결과를 FISTA·CG나 임의의 비볼록 문제로 일반화하지 않습니다. 수치 일치는 정리의 증명이 아닙니다.', 'Changing N changes the function. This is not one function worst at every k, or a claim about FISTA, CG or nonconvex problems. Numerical agreement is not a proof.')
            + '</p></section>' + evidence(result, 'gd-tight-case.json'))
    return page('GD · a tight public example', intro, body, lang=lang)
