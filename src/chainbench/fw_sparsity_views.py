"""Actual atom weights and a sharp support floor; never a fitted hard instance."""

from __future__ import annotations

import json
from html import escape

import numpy as np

from ._pages import bi, evidence, page
from .visuals import ChartSpec, LineSeries, render_line_chart

BLUE, GREEN = "#287698", "#0f766e"
CSS = ".sparse-controls{display:none;gap:14px;flex-wrap:wrap;align-items:center;padding:18px;background:#172238;color:white;border-radius:14px}.sparse-enabled .sparse-controls{display:flex}.sparse-controls input{flex:1;min-width:160px}.sparse-readout{font:13px/1.8 monospace;overflow-wrap:anywhere;background:#eef5f6;padding:16px;border-radius:12px}.sparse-bars svg,.sparse-space svg{display:block;width:100%;height:auto}.sparse-bars{overflow:auto}.sparse-bars svg{min-width:600px}.sparse-space{max-width:700px;margin:auto}.sparse-proof{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:650px){.sparse-proof{grid-template-columns:1fr}}@media print{.sparse-controls{display:none!important}[data-sparse-case]{display:block!important}}"
SCRIPT = """(()=>{
 const record=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 const select=document.querySelector('[data-sparse-select]'),slider=document.querySelector('[data-sparse-slider]'),play=document.querySelector('[data-sparse-play]');
 document.documentElement.classList.add('sparse-enabled');let timer=null;
 const stop=()=>{if(timer)clearInterval(timer);timer=null;play.textContent='▶';play.setAttribute('aria-pressed','false');};
 const update=()=>{
  const k=Number(slider.value),n=Number(select.value);
  document.querySelector('[data-sparse-step]').textContent='k = '+k;
  for(const c of record.cases){
   const panel=document.querySelector('[data-sparse-case="'+c.dimension+'"]');panel.hidden=c.dimension!==n;
   const r=c.rows[k],upper=1.15*Math.max(...r.x);
   for(const kind of ['actual','balanced']){
    const values=kind==='actual'?r.x:r.balanced,baseline=kind==='actual'?175:355;
    panel.querySelectorAll('[data-sparse-bar="'+kind+'"]').forEach((bar,i)=>{const h=130*values[i]/upper;bar.setAttribute('height',h);bar.setAttribute('y',baseline-h);bar.querySelector('title').textContent='i='+i+' · x_i='+values[i].toPrecision(9);});
   }
   panel.querySelectorAll('[data-sparse-ymax]').forEach(t=>t.textContent=upper.toPrecision(5));
   const marker=panel.querySelector('[data-sparse-support-current]');marker.setAttribute('cx',75+610*(r.support-1)/(c.dimension-1));marker.setAttribute('cy',60+270*Math.log(1/r.objective)/Math.log(c.dimension));
   panel.querySelector('[data-sparse-readout]').textContent='k='+k+' · support s='+r.support+'/'+c.dimension+' · f='+r.objective.toExponential(6)+' · support minimum 1/s='+r.minimum_with_support.toExponential(6)+' · excess='+r.excess_over_support_minimum.toExponential(6)+' · primal gap='+r.primal_gap.toExponential(6)+' · dual gap='+r.dual_gap.toExponential(6)+' · dual floor='+(r.dual_support_floor===null?'not applicable (s=n) / 적용 안 됨':r.dual_support_floor.toExponential(6));
   if(c.dimension===3){
    const project=x=>{const u=x[1]+.5*x[2],v=Math.sqrt(3)/2*x[2],f=x.reduce((s,a)=>s+a*a,0);return[120+360*u-70*v,360-120*v-190*f];};
    const pts=c.rows.slice(0,k+1).map(row=>project(row.x));panel.querySelector('[data-sparse-path]').setAttribute('points',pts.map(p=>p.join(',')).join(' '));
    for(const [kind,x] of [['actual',r.x],['balanced',r.balanced]]){const p=project(x),el=panel.querySelector('[data-sparse-point="'+kind+'"]');el.setAttribute('cx',p[0]);el.setAttribute('cy',p[1]);}
   }
  }
 };
 select.addEventListener('change',()=>{stop();update();});slider.addEventListener('input',()=>{stop();update();});
 play.addEventListener('click',()=>{if(timer){stop();return;}if(Number(slider.value)>=Number(slider.max))slider.value='0';play.textContent='❚❚';play.setAttribute('aria-pressed','true');update();timer=setInterval(()=>{if(Number(slider.value)>=Number(slider.max)){stop();return;}slider.value=String(Number(slider.value)+1);update();},450);});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});update();
})();"""


def _text(x, y, text, size=12, anchor="start", extra=""):
    return f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" text-anchor="{anchor}" fill="#334155" {extra}>{escape(str(text))}</text>'


def weights_svg(case, k):
    n, row = case["dimension"], case["rows"][k]
    upper = 1.15 * max(row["x"])
    width = 660 / n
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 400" role="img" aria-label="Actual Frank-Wolfe weights and equal weights on the same support"><rect width="760" height="400" rx="16" fill="#f7f9fc"/>'
    svg += (
        "<metadata>"
        + escape(
            json.dumps(
                {
                    "dimension": n,
                    "initial_iteration": k,
                    "projection": "bar height=130*x_i/(1.15*max(actual x)); equal scale for both panels at each k; scale changes with k",
                }
            )
        )
        + "</metadata>"
    )
    for kind, values, baseline, color, title in [
        ("actual", row["x"], 175, BLUE, "Computed FW weights"),
        ("balanced", row["balanced"], 355, GREEN, "Equal weights on the SAME active coordinates"),
    ]:
        svg += _text(65, baseline - (148 if kind == "actual" else 134), title, 15)
        svg += f'<path d="M65,{baseline - 130} V{baseline} H725" stroke="#64748b" fill="none"/>'
        svg += _text(58, baseline - 125, f"{upper:.5g}", 11, "end", 'data-sparse-ymax=""') + _text(
            58, baseline + 3, "0", 11, "end"
        )
        for i, value in enumerate(values):
            h = 130 * value / upper
            svg += f'<rect data-sparse-bar="{kind}" data-index="{i}" x="{65 + i * width + width * 0.08:.8f}" y="{baseline - h:.8f}" width="{width * 0.84:.8f}" height="{h:.8f}" fill="{color}"><title>i={i} · x_i={value:.9g}</title></rect>'
        for i in sorted({0, n // 2, n - 1}):
            svg += _text(65 + (i + 0.5) * width, baseline + 19, i, 11, "middle")
    svg += _text(725, 392, "coordinate index i (zero-based)", 11, "end") + "</svg>"
    return svg


def _project(x, height=None):
    u, v = x[1] + 0.5 * x[2], np.sqrt(3) / 2 * x[2]
    f = float(np.dot(x, x)) if height is None else height
    return (120 + 360 * u - 70 * v, 360 - 120 * v - 190 * f)


def _points(points):
    return " ".join(f"{x:.7f},{y:.7f}" for x, y in points)


def objective_svg(case, k):
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 430" role="img" aria-label="Three-coordinate simplex: actual objective height f=sum x_i squared"><rect width="600" height="430" rx="16" fill="#f7f9fc"/>'
    svg += (
        "<metadata>"
        + escape(
            json.dumps(
                {
                    "dimension": 3,
                    "height": "f=sum(x_i^2), not a gap",
                    "projection": "u=x1+x2/2; v=sqrt(3)*x2/2; screen=(120+360u-70v,360-120v-190f)",
                    "chords": "only computed endpoints lie on the surface; balanced marker is an analytical comparison, not an algorithm trajectory",
                }
            )
        )
        + "</metadata>"
    )
    svg += _text(22, 27, "n=3 · height is the source objective f(x)", 16)
    for fixed in np.linspace(0, 1, 16):
        for swap in (False, True):
            points = []
            for free in np.linspace(0, 1 - fixed, 35):
                x = (1 - fixed - free, free, fixed) if swap else (1 - fixed - free, fixed, free)
                points.append(_project(x))
            svg += '<polyline points="' + _points(points) + '" fill="none" stroke="#c6d3db"/>'
    base = [_project(x, 0) for x in np.eye(3)]
    svg += '<polygon points="' + _points(base) + '" fill="none" stroke="#94a3b8"/>'
    svg += '<path d="M120,360 V170" fill="none" stroke="#64748b"/>'
    for value in (0, 1 / 3, 1):
        y = 360 - 190 * value
        svg += f'<path d="M115,{y} h10" stroke="#64748b"/>' + _text(
            108, y + 4, f"{value:.3g}", 11, "end"
        )
    svg += _text(92, 145, "f", 13)
    for i, x in enumerate(np.eye(3)):
        a, b = _project(x)
        svg += _text(a, b - 12, f"e{i + 1}, f=1", 11, "middle")
    a, b = _project([1 / 3] * 3)
    svg += f'<circle cx="{a:.7f}" cy="{b:.7f}" r="3" fill="#172238"/>' + _text(
        a + 10, b + 18, "x*, f*=1/3", 11
    )
    svg += (
        '<polyline data-sparse-path="" points="'
        + _points([_project(r["x"]) for r in case["rows"][: k + 1]])
        + '" stroke="'
        + BLUE
        + '" stroke-width="2.5" fill="none"/>'
    )
    for kind, x, color, radius in [
        ("actual", case["rows"][k]["x"], BLUE, 6),
        ("balanced", case["rows"][k]["balanced"], GREEN, 4),
    ]:
        a, b = _project(x)
        svg += f'<circle data-sparse-point="{kind}" cx="{a:.7f}" cy="{b:.7f}" r="{radius}" fill="{color}" stroke="white" stroke-width="1.5"/>'
    svg += (
        _text(
            22, 402, "Blue: computed iterate · green: equal weights on its active coordinates", 11
        )
        + "</svg>"
    )
    return svg


def _readout(row, n):
    dual = (
        "not applicable (s=n) / 적용 안 됨"
        if row["dual_support_floor"] is None
        else f"{row['dual_support_floor']:.6e}"
    )
    return (
        f"k={row['iteration']} · support s={row['support']}/{n} · f={row['objective']:.6e}"
        f" · support minimum 1/s={row['minimum_with_support']:.6e} · excess={row['excess_over_support_minimum']:.6e}"
        f" · primal gap={row['primal_gap']:.6e} · dual gap={row['dual_gap']:.6e} · dual floor={dual}"
    )


def support_svg(case, k):
    n = case["dimension"]

    def project(s, value):
        return 75 + 610 * (s - 1) / (n - 1), 60 + 270 * np.log(1 / value) / np.log(n)

    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 400" role="img" aria-label="Objective versus actual support: all iterations, including repeated support counts"><rect width="760" height="400" rx="16" fill="#f7f9fc"/>'
    metadata = dict(
        kind="chainbench.support-scatter",
        x_label="actual support s",
        y_scale="log",
        rows=[
            dict(iteration=r["iteration"], support=r["support"], objective=r["objective"])
            for r in case["rows"]
        ],
        floor=[dict(support=r["support"], minimum=r["minimum"]) for r in case["construction"]],
        projection="X=75+610*(s-1)/(n-1); Y=60+270*log(1/f)/log(n)",
    )
    svg += (
        "<metadata>"
        + escape(json.dumps(metadata))
        + "</metadata>"
        + _text(22, 27, "Objective versus support · every computed iteration", 16)
    )
    svg += '<path d="M75,60 V330 H685" fill="none" stroke="#64748b"/>'
    for value in (1.0, 1 / np.sqrt(n), 1 / n):
        _, y = project(1, value)
        svg += f'<path d="M75,{y} H685" stroke="#dce3e9"/>' + _text(
            66, y + 4, f"{value:.4g}", 11, "end"
        )
    for s in (1, n // 2, n):
        x, _ = project(s, 1)
        svg += _text(x, 352, s, 12, "middle")
    svg += _text(75, 382, "f(x), log scale", 11) + _text(685, 382, "actual support s", 11, "end")
    svg += (
        '<polyline data-sparse-floor="" points="'
        + _points([project(s, 1 / s) for s in range(1, n + 1)])
        + '" stroke="'
        + GREEN
        + '" stroke-width="2" fill="none"/>'
    )
    for r in case["rows"]:
        x, y = project(r["support"], r["objective"])
        svg += f'<circle data-sparse-observation="{r["iteration"]}" cx="{x:.7f}" cy="{y:.7f}" r="3" fill="{BLUE}"><title>k={r["iteration"]}, s={r["support"]}, f={r["objective"]:.9g}</title></circle>'
    x, y = project(case["rows"][k]["support"], case["rows"][k]["objective"])
    svg += f'<circle data-sparse-support-current="" cx="{x:.7f}" cy="{y:.7f}" r="7" fill="none" stroke="{BLUE}" stroke-width="2"/>'
    return svg + _text(90, 50, "Blue: actual FW · green: sharp minimum 1/s", 11) + "</svg>"


def _case_html(case, k):
    n, rows = case["dimension"], case["rows"]
    body = (
        f'<section data-sparse-case="{n}"><h2>n = {n} · '
        + bi("한 번에 원자 하나 추가", "At most one new atom per update")
        + "</h2>"
    )
    body += (
        '<div class="sparse-readout" data-sparse-readout>'
        + _readout(rows[k], n)
        + '</div><div class="sparse-bars">'
        + weights_svg(case, k)
        + '</div><p class="small">'
        + bi(
            "위는 실제 FW 가중치, 아래는 같은 활성 좌표에 균등하게 배분한 값입니다. 두 막대 패널은 같은 반복점에서 같은 세로 척도를 쓰며 반복점을 바꾸면 척도도 바뀝니다. 아래 값은 비교용 구성이지 다른 최적화 알고리즘의 결과가 아닙니다.",
            "Top: actual FW weights. Bottom: equal weights on the same active coordinates. Both panels share the same vertical scale at each iteration; the scale changes with the iteration. The bottom vector is an analytical comparison, not another optimizer.",
        )
        + "</p>"
    )
    if n == 3:
        body += (
            '<div class="sparse-space">'
            + objective_svg(case, k)
            + '</div><p class="small">'
            + bi(
                "높이는 f=Σxᵢ²이며 최솟값은 1/3입니다. 파란 선분은 실제 계산점을 잇습니다. 선분 내부는 곡면 위 경로가 아닙니다. 초록 점은 같은 활성 좌표에 균등 배분한 비교점입니다. 고차원 사례는 위의 모든 좌표 막대로 읽습니다.",
                "Height is f=Σxᵢ², with minimum 1/3. Blue chords connect computed points; their interiors are not paths on the surface. Green is the equally weighted comparison on the same active coordinates. Higher dimensions use the complete coordinate bars above.",
            )
            + "</p>"
        )
    body += '<div class="plot">' + support_svg(case, k) + "</div>"
    chart_specs = [
        ChartSpec(
            "Iteration and support impose different statements",
            "iteration k",
            "primal gap f-f*",
            (
                LineSeries(
                    "actual primal gap",
                    tuple(r["iteration"] for r in rows),
                    tuple(r["primal_gap"] for r in rows),
                ),
                LineSeries(
                    "support floor 1/s(k)-1/n",
                    tuple(r["iteration"] for r in rows),
                    tuple(r["support_floor"] for r in rows),
                    "bound",
                ),
                LineSeries(
                    "Theorem 1 upper 8/(k+2)",
                    tuple(r["iteration"] for r in rows[1:]),
                    tuple(r["iteration_upper"] for r in rows[1:]),
                    "bound",
                ),
            ),
        ),
        ChartSpec(
            "Dual-gap floor only before full support",
            "iteration k",
            "FW dual gap",
            (
                LineSeries(
                    "actual dual gap",
                    tuple(r["iteration"] for r in rows),
                    tuple(r["dual_gap"] for r in rows),
                ),
                LineSeries(
                    "Lemma 4 lower 2/s (s<n only)",
                    tuple(r["iteration"] for r in rows if r["support"] < n),
                    tuple(r["dual_support_floor"] for r in rows if r["support"] < n),
                    "bound",
                ),
            ),
        ),
    ]
    for chart in chart_specs:
        body += (
            '<div class="plot">'
            + render_line_chart(chart, colors=(BLUE, GREEN, "#b45309")[: len(chart.series)])
            + "</div>"
        )
    body += (
        '<p class="small">'
        + bi(
            "상계 8/(k+2)는 k≥1에만 적용합니다. 하한 1/s−1/n은 실제 활성 좌표 수 s를 사용합니다. s=n일 때 두 번째 보조정리의 2/s 곡선은 종료합니다. 값 0을 대신 넣지 않습니다. 로그 축에서 0은 양수로 바꾸지 않으며 아래 표·JSON에 그대로 남습니다.",
            "The upper bound applies only for k≥1. The floor 1/s−1/n uses actual support s. At s=n, the Lemma 4 curve ends; no replacement zero is inserted. Log plots do not turn zero into a positive value; tables and JSON retain it.",
        )
        + "</p>"
    )
    body += (
        "<details><summary>"
        + bi("모든 반복의 실제 값", "Every actual iteration")
        + '</summary><div class="scroll"><table><thead><tr><th>k</th><th>s</th><th>f</th><th>1/s</th><th>f−f*</th><th>dual gap</th><th>dual floor</th></tr></thead><tbody>'
    )
    for r in rows:
        body += (
            "<tr>"
            + "".join(
                "<td>"
                + (
                    "— (s=n)"
                    if r[field] is None
                    else str(r[field])
                    if field in ("iteration", "support")
                    else f"{r[field]:.9g}"
                )
                + "</td>"
                for field in (
                    "iteration",
                    "support",
                    "objective",
                    "minimum_with_support",
                    "primal_gap",
                    "dual_gap",
                    "dual_support_floor",
                )
            )
            + "</tr>"
        )
    return body + "</tbody></table></div></details></section>"


def fw_sparsity_html(result, lang="en"):
    steps = result["parameters"]["steps"]
    initial = min(2, steps)
    body = (
        "<style>"
        + CSS
        + '</style><section><span class="badge">Jaggi (2013) · Lemmas 3–4 · Appendix C</span><h2>'
        + bi(
            "좌표를 적게 쓰면서 얼마나 정확해질 수 있을까?",
            "How accurate can a sparse convex combination be?",
        )
        + "</h2><p>"
        + bi(
            "Frank–Wolfe는 매 갱신에서 꼭짓점 하나를 고르고 기존 점과 섞습니다. 원자를 적게 저장할 수 있는 장점에는 어떤 정확도 한계가 있을까요? 논문이 제시한 함수와 그 하한을 달성하는 구성을 계산합니다.",
            "Frank–Wolfe selects one vertex per update and mixes it with the current point. What accuracy limit accompanies a representation using few atoms? This page computes the source function and its explicitly attaining construction.",
        )
        + '</p><div class="formula">min f(x)=Σ xᵢ², xᵢ≥0, Σxᵢ=1\nx*=(1/n,…,1/n), f*=1/n, C_f=4\nmin over support≤s: f(x)=1/s; primal gap≥1/s−1/n\nFW dual gap≥2/s ONLY when s&lt;n</div><p>'
        + bi(
            "원문은 희소성에 k를 쓰지만 여기서는 반복을 k, 활성 좌표 수를 s로 구분합니다. 네 차원 n=3,8,32,128은 모든 경우를 보여주도록 추가한 선택입니다. 논문의 실험 그림이나 대표 표본은 아닙니다.",
            "We use k for iteration and s for the number of active coordinates to keep them distinct. Dimensions n=3,8,32,128 are added examples and all are retained; they are not original-paper experiments or a representative sample.",
        )
        + "</p>"
    )
    body += (
        f'<div class="callout">{steps} updates · x₀=e₁ · γₖ=2/(k+2) · exact oracle · first minimum wins ties · no random seed</div></section><section><h2>'
        + bi(
            "같은 좌표에서 균등하게 나누면 하한에 닿는다",
            "Equal weights attain the floor on the same support",
        )
        + '</h2><div class="sparse-proof"><div><div class="formula">Σ_active (xᵢ−1/s)² = Σxᵢ²−1/s ≥ 0</div><p>'
        + bi(
            "s개 양수 가중치의 합이 1이면 평균은 1/s입니다. 평균에서 벗어난 제곱합만큼 목적함수가 커집니다. 모두 1/s일 때 제곱합이 0이므로 최소값 1/s를 실제로 달성합니다.",
            "If s positive weights sum to one, their mean is 1/s. The objective exceeds 1/s by the sum of squared deviations from that mean. Equal weights make this excess zero, attaining the minimum.",
        )
        + '</p></div><div><div class="formula">g_FW(x)=2(Σxᵢ²−min xᵢ)\ns&lt;n ⇒ min xᵢ=0 ⇒ g_FW(x)≥2/s</div><p>'
        + bi(
            "좌표가 하나라도 비어 있을 때만 min xᵢ=0을 쓸 수 있습니다. 모든 좌표를 쓰면 이 가정이 사라집니다. 균등한 최적점에서는 dual gap이 0이므로 2/n을 하한으로 연장할 수 없습니다.",
            "The minimum coordinate is zero only while some coordinate is unused. At full support this assumption no longer holds. The uniform optimum has zero dual gap, so 2/n cannot be carried forward as a lower bound.",
        )
        + '</p></div></div><p class="callout caution">'
        + bi(
            "하한을 달성하는 비교점과 FW의 실제 반복점은 다를 수 있습니다. 이 결과는 주어진 희소성에서의 최선값을 설명하며, FW가 매 반복 최악 사례 상수에 도달한다는 주장이 아닙니다. 첫 보폭 γ₀=1은 초기 원자를 교체하므로 반복 수와 활성 좌표 수가 같지 않습니다.",
            "The attaining comparison and actual FW iterate can differ. This is a sharp support-constrained minimum, not a claim that every FW iterate attains an exact worst-case iteration constant. The first step γ₀=1 replaces the initial atom, so iteration count and support are different.",
        )
        + "</p></section>"
    )
    body += (
        '<div class="sparse-controls"><label for="sparse-dimension">'
        + bi("차원 n", "Dimension n")
        + '</label><select id="sparse-dimension" data-sparse-select>'
        + "".join(
            f'<option value="{c["dimension"]}">{c["dimension"]}</option>' for c in result["cases"]
        )
        + '</select><button type="button" data-sparse-play aria-label="Play or pause iterations" aria-pressed="false">▶</button><label for="sparse-iteration">'
        + bi("반복 k", "Iteration k")
        + f'</label><input id="sparse-iteration" data-sparse-slider type="range" min="0" max="{steps}" value="{initial}"><strong data-sparse-step>k = {initial}</strong></div>'
    )
    body += "".join(_case_html(c, initial) for c in result["cases"])
    body += (
        "<section><h2>"
        + bi("출처와 검증 범위", "Source and scope")
        + '</h2><p><a href="'
        + escape(result["source"]["url"], quote=True)
        + '#page=12">Jaggi (2013), supplementary Appendix C · Lemmas 3–4</a></p><p>'
        + bi(
            "하한과 이를 달성하는 구성이 최선이라는 사실은 공개 증명에서 옵니다. 이 페이지의 계산은 그 특수 문제와 실제 구현을 확인합니다. 기존 단체 기하의 ½ 제곱손실과 달리 여기서는 원문의 전체 제곱노름 f=||x||²를 사용하므로 C_f=4입니다.",
            "The public proof establishes sharpness. The calculations here inspect that construction and the implemented updates. Unlike the half-squared-loss simplex illustration, this page uses the source’s full f=||x||², hence C_f=4.",
        )
        + "</p><ul>"
        + "".join("<li>" + escape(x) + "</li>" for x in result["limits"])
        + "</ul></section>"
    )
    body += evidence(result, "chainbench-fw-sparsity.json") + "<script>" + SCRIPT + "</script>"
    return page(
        "Frank–Wolfe · the cost of sparsity",
        bi(
            "논문의 명시적 하한 · 실제 가중치 · 같은 지지집합의 최선값",
            "Published sharp floor · actual weights · the best value on the same support",
        ),
        body,
        lang=lang,
    )
