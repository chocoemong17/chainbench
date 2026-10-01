"""Offline signal reconstruction and row sampling from retained numerical data."""

import json
from html import escape

import numpy as np

from ._pages import bi, page
from ._sampling_projection_views import CSS as PROJECTION_CSS
from ._sampling_projection_views import response_html
from .visuals import ChartSpec, LineSeries, render_line_chart

COLORS = {"cyclic": "#657588", "uniform": "#2866b5", "weighted": "#bb5135"}
LABELS = {
    "cyclic": "Cyclic row order",
    "uniform": "Uniform random rows",
    "weighted": "Weighted random rows",
}


def _signal_limits(case):
    values = list(case["truth_signal"]["real"]) + list(case["observed_samples"]["real"])
    for run in case["runs"].values():
        for s in run["snapshots"]:
            values.extend(s["signal"]["real"])
            projection = s["last_projection"]
            if projection and "signal_update" in projection:
                values.extend(projection["signal_update"]["previous_signal"]["real"])
                values.extend(projection["signal_update"]["next_signal"]["real"])
    lo, hi = min(values), max(values)
    padding = 0.06 * (hi - lo or 1)
    return lo - padding, hi + padding


def _signal_points(grid, values, limits):
    lo, hi = limits
    return " ".join(
        f"{80 + 800 * t:.3f},{300 - 220 * (v - lo) / (hi - lo):.3f}" for t, v in zip(grid, values)
    )


def signal_svg(case, grid, method, k, *, interactive=True):
    limits = _signal_limits(case)
    lo, hi = limits
    s = next(s for s in case["runs"][method]["snapshots"] if s["iteration"] == k)
    body = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 370" role="img" aria-label="Actual bandlimited signal and stored reconstruction" data-signal-low="{lo!r}" data-signal-high="{hi!r}">'
    body += '<rect width="960" height="370" rx="16" fill="#f7fafb"/><text x="24" y="28" font-size="17">Real part of f(t): reference and stored reconstruction</text>'
    body += '<text x="24" y="50" font-size="12">Black dashed: reference · colored: reconstruction · shared vertical scale across all snapshots</text>'
    body += '<rect x="80" y="80" width="800" height="220" fill="white" stroke="#bdccd8"/>'
    for v in np.linspace(lo, hi, 5):
        y = 300 - 220 * (v - lo) / (hi - lo)
        body += f'<path d="M80 {y:.3f} H880" stroke="#e2e9ee"/><text x="70" y="{y + 4:.3f}" text-anchor="end" font-size="11">{v:.3f}</text>'
    for t in (0, 0.25, 0.5, 0.75, 1):
        x = 80 + 800 * t
        body += f'<path d="M{x} 80 V300" stroke="#e2e9ee"/><text x="{x}" y="322" text-anchor="middle" font-size="12">{t:g}</text>'
    if interactive:
        for t, v in zip(case["nodes"], case["observed_samples"]["real"]):
            body += f'<circle cx="{80 + 800 * t:.3f}" cy="{300 - 220 * (v - lo) / (hi - lo):.3f}" r="1.5" fill="#778c9c" opacity=".32"/>'
    body += (
        '<polyline points="'
        + _signal_points(grid, case["truth_signal"]["real"], limits)
        + '" fill="none" stroke="#172238" stroke-width="1.7" stroke-dasharray="6 4"/>'
    )
    body += (
        "<polyline "
        + ('data-sampling-prediction="" ' if interactive else "")
        + 'points="'
        + _signal_points(grid, s["signal"]["real"], limits)
        + f'" fill="none" stroke="{COLORS[method]}" stroke-width="2.2"/>'
    )
    if interactive:
        projection = s["last_projection"]
        i = projection["row"] if projection else 0
        x = 80 + 800 * case["nodes"][i]
        y = 300 - 220 * (case["observed_samples"]["real"][i] - lo) / (hi - lo)
        body += f'<circle data-picked-sample="" cx="{x:.3f}" cy="{y:.3f}" r="6" fill="none" stroke="#9d4f19" stroke-width="2" visibility="{"visible" if projection else "hidden"}"/>'
    body += '<text x="480" y="351" text-anchor="middle" font-size="12">t on the unit period [0,1] · lines connect 513 retained display samples</text></svg>'
    return body


def probability_svg(case):
    maximum = max(case["probabilities"]) * 1.08
    baseline = 280 - 190 / (700 * maximum)
    body = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 340" role="img" aria-label="Row selection probabilities at every actual sampling node">'
    body += '<rect width="960" height="340" rx="16" fill="#f7fafb"/><text x="24" y="28" font-size="17">Sampling density changes a row’s weight</text><text x="24" y="50" font-size="12">Blue stems: p_j = w_j / sum(w) · grey dashed: uniform probability 1/700</text>'
    for i, (t, p) in enumerate(zip(case["nodes"], case["probabilities"])):
        x, y = 80 + 800 * t, 280 - 190 * p / maximum
        body += f'<line data-sampling-probability="{i}" x1="{x:.3f}" x2="{x:.3f}" y1="280" y2="{y:.3f}" stroke="#2866b5" stroke-width="1.5"/>'
    body += f'<line x1="80" x2="880" y1="{baseline:.3f}" y2="{baseline:.3f}" stroke="#637387" stroke-dasharray="6 4"/>'
    for fraction in (0, 0.5, 1):
        body += f'<text x="72" y="{284 - 190 * fraction}" text-anchor="end" font-size="11">{maximum * fraction:.4f}</text>'
    body += '<path d="M80 90 V280 H880" fill="none" stroke="#8093a4"/><text x="80" y="302" font-size="12">0</text><text x="880" y="302" text-anchor="end" font-size="12">1</text><text x="480" y="325" text-anchor="middle" font-size="12">actual node t_j · cyclic order has no random selection probability</text></svg>'
    return body


SCRIPT = """(()=>{
 document.documentElement.classList.add('sampling-js');
 const d=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 const colors={cyclic:'#657588',uniform:'#2866b5',weighted:'#bb5135'};
 for(const panel of document.querySelectorAll('[data-sampling-case]')){
  const c=d.cases.find(c=>c.id===panel.dataset.samplingCase),method=panel.querySelector('[data-sampling-method]'),step=panel.querySelector('[data-sampling-step]');
  const svg=panel.querySelector('[data-signal-low]'),lo=Number(svg.dataset.signalLow),hi=Number(svg.dataset.signalHigh);
  const update=()=>{
   const m=method.value,k=Number(step.value),run=c.runs[m],s=run.snapshots.find(s=>s.iteration===k);
   const points=s.signal.real.map((v,i)=>(80+800*d.display_grid[i]).toFixed(3)+','+(300-220*(v-lo)/(hi-lo)).toFixed(3)).join(' ');
   panel.querySelector('[data-sampling-prediction]').setAttribute('points',points);
   panel.querySelector('[data-sampling-prediction]').setAttribute('stroke',colors[m]);
   const last=s.last_projection,marker=panel.querySelector('[data-picked-sample]');
   marker.setAttribute('visibility',last?'visible':'hidden');
   if(last){const i=last.row;marker.setAttribute('cx',(80+800*c.nodes[i]).toFixed(3));marker.setAttribute('cy',(300-220*(c.observed_samples.real[i]-lo)/(hi-lo)).toFixed(3));}
   panel.querySelector('[data-sampling-values]').textContent=m+' · completed k='+k+' · coefficient L2 error='+run.error_l2[k].toExponential(6)+' · weighted data residual='+s.weighted_residual_l2.toExponential(6);
   panel.querySelector('[data-sampling-row]').textContent=last?'Last row '+last.row+' · t='+last.node.toPrecision(7)+' · '+(last.probability===null?'deterministic cyclic order':'selection probability='+last.probability.toExponential(6)):'k=0: no completed projection';
   for(const frame of panel.querySelectorAll('[data-projection-frame]')){
    const active=frame.dataset.projectionFrame===m+'-'+k;
    frame.classList.toggle('is-current',active);if(active)frame.open=true;
   }
  };
  const first=panel.querySelector('[data-projection-first]');
  if(first)first.addEventListener('click',()=>{step.value='1';update();});
  method.addEventListener('change',update);step.addEventListener('change',update);update();
 }
})();"""


def nonuniform_html(result, lang="en"):
    p = result["parameters"]
    body = """<style>.sampling-controls{display:none;gap:18px;align-items:center;flex-wrap:wrap;padding:16px;background:#eef4f8;border-radius:12px}.sampling-js .sampling-controls{display:flex}.sampling-controls select{margin-left:8px}.sampling-figure{overflow:auto;margin:16px 0}.sampling-figure svg{display:block;width:100%;min-width:660px;height:auto}.sampling-values{overflow-wrap:anywhere;font-family:monospace}.sampling-case{margin:22px 0}.sampling-flow{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.sampling-flow p{padding:16px;background:#eef5f5;border-radius:12px}@media(max-width:700px){.sampling-flow{grid-template-columns:1fr}}@media print{.sampling-controls{display:none!important}}</style>"""
    body += "<style>" + PROJECTION_CSS + "</style>"
    body += (
        '<section><span class="badge">Strohmer–Vershynin · §4.1 / Figure 1 · declared-input protocol rerun</span><h2>'
        + bi("불규칙한 700개 샘플로 신호 되찾기", "Recover a signal from 700 irregular samples")
        + "</h2><p>"
        + bi(
            "같은 101개 Fourier 계수를 복원하되, 어떤 관측 행을 고르는지만 바꿉니다. 정렬된 순서대로, 모든 행을 같은 확률로, 또는 주변 샘플 간격에 비례한 확률로 선택합니다. 원문이 제공하지 않은 신호·좌표·시드는 아래에 명시한 새 입력입니다.",
            "Recover the same 101 Fourier coefficients while changing only which observation row is selected: sorted cyclic order, uniform random rows, or probabilities proportional to local sampling gaps. The source does not supply its exact signal, nodes or random stream; the declared inputs below are new.",
        )
        + "</p>"
    )
    body += (
        f'<div class="formula">r=50 · n=101 · m=700 · seeds=0,1,2 · {p["steps"]:,} projections / method / case<br>'
        + bi(
            "원문 그림의 15,000회 예산 전체"
            if p["full_paper_plot_budget"]
            else "축소한 미리보기 예산",
            "Full 15,000-projection source-plot budget"
            if p["full_paper_plot_budget"]
            else "Reduced preview budget",
        )
        + "</div>"
    )
    body += (
        '<div class="sampling-flow"><p><b>1 · '
        + bi("샘플과 가중치", "Nodes and weights")
        + "</b><br>wⱼ=(tⱼ₊₁−tⱼ₋₁)/2<br>"
        + bi(
            "주기 경계를 가로질러 이웃을 잇습니다. 덜 촘촘한 곳의 관측 한 개가 더 넓은 구간을 담당합니다.",
            "Neighbors wrap across the periodic boundary. One observation in a sparse region represents a wider interval.",
        )
        + "</p><p><b>2 · "
        + bi("행 선택", "Select a row")
        + "</b><br>pⱼ=wⱼ/Σw<br>"
        + bi(
            "가중 행의 제곱 노름은 n·wⱼ이므로 논문의 무작위 규칙이 이 확률을 줍니다.",
            "The weighted row has squared norm n·wⱼ, giving this probability under the source rule.",
        )
        + "</p><p><b>3 · "
        + bi("한 관측에 투영", "Project onto one observation")
        + "</b><br>x←x+(fⱼ−vⱼx)·conj(vⱼ)/‖vⱼ‖²<br>"
        + bi(
            "양의 가중치는 투영식에서 상쇄됩니다. 세 방법은 행을 고르는 규칙만 다릅니다.",
            "The positive row weight cancels from the projection. Only row selection differs between the three methods.",
        )
        + "</p></div></section>"
    )
    grid = result["display_grid"]
    for case in result["cases"]:
        body += (
            f'<section class="sampling-case" data-sampling-case="{case["id"]}"><h2>PCG64 seed {case["seed"]}</h2><p>'
            + bi(
                "영점 계수에서 시작합니다. 음·양 주파수 계수는 켤레 대칭으로 생성해 실제 신호가 실수가 되게 했으며, 계수 노름을 1로 정규화했습니다. 두 무작위 방법은 동일한 균등 난수를 각자의 선택 규칙에 적용합니다.",
                "All methods start from zero. Conjugate-symmetric coefficients give a real signal and are normalized to unit coefficient norm. The randomized methods use the same uniform draws with their respective selection rules.",
            )
            + "</p>"
        )
        body += (
            '<div class="sampling-controls"><label>'
            + bi("행 선택", "Row selection")
            + "<select data-sampling-method>"
        )
        for method in ("weighted", "uniform", "cyclic"):
            body += f'<option value="{method}">{LABELS[method]}</option>'
        body += (
            "</select></label><label>"
            + bi("저장한 반복점", "Stored iteration")
            + "<select data-sampling-step>"
        )
        for k in p["snapshot_iterations"]:
            body += (
                f'<option value="{k}"'
                + (" selected" if k == p["steps"] else "")
                + f">k={k}</option>"
            )
        body += "</select></label>"
        if "projection_geometry" in result:
            body += (
                '<button type="button" data-projection-first>'
                + bi("첫 투영 보기", "Show the first projection")
                + "</button>"
            )
        body += (
            '</div><div class="sampling-figure">'
            + signal_svg(case, grid, "weighted", p["steps"])
            + "</div>"
        )
        last = case["runs"]["weighted"]["snapshots"][-1]
        body += f'<p class="sampling-values" data-sampling-values>weighted · completed k={p["steps"]} · coefficient L2 error={case["runs"]["weighted"]["error_l2"][-1]:.6e} · weighted data residual={last["weighted_residual_l2"]:.6e}</p>'
        projection = last["last_projection"]
        caption = (
            f"Last row {projection['row']} · t={projection['node']:.7g} · selection probability={projection['probability']:.6e}"
            if projection
            else "k=0: no completed projection"
        )
        body += "<p data-sampling-row>" + caption + "</p>"
        body += (
            '<p class="small">'
            + bi(
                "표시 곡선은 복소 신호의 실수부입니다. 오차는 복소 계수 전체로 계산하며 허수부도 JSON에 남깁니다. 원은 마지막으로 투영한 관측 위치입니다. 세로 척도는 이 사례의 모든 저장점과 방법에 공통이며, 작은 화면에서는 그림을 가로로 스크롤할 수 있습니다.",
                "Waveforms show real parts; error uses the full complex coefficients, and imaginary values remain in JSON. The ring marks the last projected observation. One vertical scale covers all snapshots and methods in this case; figures scroll horizontally on small screens.",
            )
            + "</p>"
        )
        if "projection_geometry" in result:
            body += response_html(case, _signal_limits(case), p["steps"])
        chart = ChartSpec(
            f"Seed {case['seed']}: every projection, all three methods",
            "completed projections k",
            "coefficient error ||x_k−x_true||₂",
            tuple(
                LineSeries(
                    LABELS[m], tuple(range(p["steps"] + 1)), tuple(case["runs"][m]["error_l2"])
                )
                for m in ("cyclic", "uniform", "weighted")
            ),
        )
        body += (
            '<div class="plot">'
            + render_line_chart(chart, width=960, height=410, colors=tuple(COLORS.values()))
            + "</div><p>"
            + bi(
                "세로축은 오차의 제곱이 아니라 계수 L2 노름입니다. 그래프는 모든 갱신을 포함합니다. 단일 경로이며 기대값 곡선이 아닙니다. 부동소수점 바닥 부근의 작은 순위 차이는 속도 우열의 근거로 쓰지 않습니다.",
                "The vertical axis is the coefficient L2 error, not its square. Every update is retained. Each curve is one path, not an expectation. Tiny ordering differences near floating-point roundoff do not establish a speed ranking.",
            )
            + "</p>"
        )
        body += '<div class="sampling-figure">' + probability_svg(case) + "</div>"
        condition = case["conditioning"]
        bound = condition["theorem4_condition_upper"]
        body += (
            '<p class="formula">δ_max='
            + f"{condition['max_periodic_gap']:.9f} · 1/(2r)=0.01 · measured k(A)={condition['spectral_condition']:.6g}<br>"
        )
        body += (
            bi(
                "정리 4의 충분조건 미적용: 상계는 미정의로 남깁니다. 이 사실은 복원 실패를 뜻하지 않습니다.",
                "Theorem 4’s sufficient condition is inapplicable; its bound remains undefined. This does not imply failure of reconstruction.",
            )
            if bound is None
            else bi(
                f"정리 4의 조건 성립: k(A) ≤ {bound:.6g}. 위의 실제 조건수와 구분합니다.",
                f"Theorem 4’s condition holds: k(A) ≤ {bound:.6g}. This differs from the measured condition number above.",
            )
        ) + "</p>"
        body += (
            "<details data-sampling-gallery-list><summary>"
            + bi("모든 저장점의 복원 곡선과 수치", "Every stored waveform and error")
            + "</summary>"
        )
        for method, run in case["runs"].items():
            for s in run["snapshots"]:
                k = s["iteration"]
                body += (
                    f'<details data-sampling-gallery="{method}-{k}"><summary>{LABELS[method]} · k={k} · error={run["error_l2"][k]:.6e}</summary><div class="sampling-figure">'
                    + signal_svg(case, grid, method, k, interactive=False)
                    + "</div></details>"
                )
        body += (
            "</details><details><summary>"
            + bi(
                "700개 샘플과 전체 예산의 선택 횟수",
                "All 700 nodes and selection counts over the full budget",
            )
            + '</summary><p class="small">'
            + bi(
                "아래 횟수는 전체 예산 기준이며 위 저장점 선택에 따라 바뀌지 않습니다. 실제 빈도와 선택 확률은 다릅니다.",
                "Counts cover the full budget and do not change with the snapshot selector. Observed frequencies differ from selection probabilities.",
            )
            + '</p><div class="scroll"><table><tr><th>row</th><th>tⱼ</th><th>weighted pⱼ</th><th>cyclic count</th><th>uniform count</th><th>weighted count</th></tr>'
        )
        counts = {m: np.bincount(case["runs"][m]["rows"], minlength=700) for m in COLORS}
        for i, t in enumerate(case["nodes"]):
            body += (
                f"<tr><td>{i}</td><td>{t:.12f}</td><td>{case['probabilities'][i]:.12e}</td>"
                + "".join(f"<td>{counts[m][i]}</td>" for m in COLORS)
                + "</tr>"
            )
        body += "</table></div></details></section>"
    body += (
        "<section><h2>"
        + bi("원문과 추가한 선택을 구분하기", "Source protocol and declared additions")
        + '</h2><a href="'
        + escape(result["source"]["url"], quote=True)
        + '#page=10">Strohmer–Vershynin, arXiv:math/0702226v1, §4.1 / Eq. (18) / Figure 1</a><ul>'
        + "".join("<li>" + escape(s) + "</li>" for s in result["differences"] + result["limits"])
        + "</ul></section>"
    )
    body += (
        "<details><summary>"
        + bi(
            "전체 입력·모든 행 선택·곡선·저장점 JSON",
            "Complete inputs, every row choice, curves and snapshots",
        )
        + '</summary><button data-download="chainbench-evidence" data-filename="chainbench-nonuniform-sampling.json">'
        + bi("JSON 저장", "Save JSON")
        + '</button><pre id="chainbench-evidence">'
        + escape(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
        + "</pre></details><script>"
        + SCRIPT
        + "</script>"
    )
    return page(
        "Kaczmarz · nonuniform signal sampling",
        bi(
            "공개 실험 조건 · 새로 선언한 입력 · 모든 선택과 오차",
            "Published protocol · declared new inputs · every choice and error",
        ),
        body,
        lang=lang,
    )
