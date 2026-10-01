"""Offline inspection of the recorded 16-dimensional CG modes."""

import json
from html import escape

from ._pages import bi, page
from .visuals import ChartSpec, LineSeries, render_line_chart

SPECTRA = ("two-values", "two-clusters", "spread")
PROFILES = ("equal-coefficients", "equal-energy", "single-mode")
COLORS = ("#2563eb", "#b45309", "#7c3aed")


def _number(value):
    return "undefined / 초기 계수 0" if value is None else f"{value:.8e}"


def ratio_limits(case):
    values = [v for r in case["rows"] for v in r["component_ratios"] if v is not None]
    # The references on the displayed [0,8] interval lie in [-1,1]. Keep the
    # same scale at every stage, including negative observed mode ratios.
    return min(-1., min(values)) * 1.1, max(1., max(values)) * 1.1


def _axes(title, ylabel, low, high):
    body = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 330" '
            f'role="img" aria-label="{escape(title)}" data-low="{low!r}" data-high="{high!r}">'
            '<rect width="800" height="330" rx="12" fill="#f7fafb"/>'
            f'<text x="70" y="25" font-size="16">{escape(title)}</text>'
            f'<text x="70" y="47" font-size="12">{escape(ylabel)}</text>'
            '<rect x="70" y="70" width="680" height="200" fill="white" stroke="#bdccd8"/>')
    for fraction in (0, .25, .5, .75, 1):
        value = low + (high-low)*fraction
        y = 270-200*fraction
        body += (f'<path d="M70 {y} H750" stroke="#e2e9ee"/>'
                 f'<text x="63" y="{y+4}" text-anchor="end" font-size="11">{value:.3g}</text>')
    return body


def _points(xs, values, low, high):
    return " ".join(f"{70+85*x:.3f},{270-200*(v-low)/(high-low):.3f}" for x, v in zip(xs, values))


def ratio_svg(case, row, comparison):
    low, high = ratio_limits(case)
    body = _axes(f"Signed mode ratios · k={row['iteration']}",
                 "Dots: actual c_i(k)/c_i(0) · dashed: Eq. (51) comparison, not actual CG", low, high)
    body += ('<polyline data-cg-reference="" points="'
             + _points(comparison["abscissae"], comparison["values"], low, high)
             + '" fill="none" stroke="#778599" stroke-width="1.8" stroke-dasharray="6 4"/>')
    for i, (eigenvalue, ratio) in enumerate(zip(case["declared_eigenvalues"], row["component_ratios"])):
        if ratio is None:
            continue
        body += (f'<circle data-cg-ratio="{i}" cx="{70+85*eigenvalue:.3f}" '
                 f'cy="{270-200*(ratio-low)/(high-low):.3f}" r="4" fill="#2563eb" fill-opacity=".7">'
                 f'<title>mode {i} · lambda={eigenvalue:.9g} · ratio={ratio:.12e}</title></circle>')
    for x in (0, 2, 4, 6, 7, 8):
        body += f'<text x="{70+85*x}" y="291" font-size="12" text-anchor="middle">{x}</text>'
    return body + '<text x="410" y="317" text-anchor="middle" font-size="12">declared eigenvalue λ · repeated modes can overlap · inactive ratios omitted</text></svg>'


def energy_svg(case, row):
    high = 1.08 * max(v for r in case["rows"] for v in r["normalized_mode_energy"])
    body = _axes("Where the squared energy remains", "Bar i = λ_i c_i(k)² / sum_j λ_j c_j(0)² · fixed scale within this case", 0., high)
    body = body.replace('data-low="0.0"', 'data-cg-energy="" data-low="0.0"')
    for i, value in enumerate(row["normalized_mode_energy"]):
        height = 200*value/high
        body += (f'<rect data-cg-mode="{i}" x="{76+42*i}" y="{270-height:.3f}" '
                 f'width="28" height="{height:.3f}" fill="#b45309">'
                 f'<title>mode {i} · normalized energy={value:.12e}</title></rect>'
                 f'<text x="{90+42*i}" y="291" text-anchor="middle" font-size="12">{i}</text>')
    return body + '<text x="410" y="317" text-anchor="middle" font-size="12">all 16 mode indices · zero-height bars are zero, not missing modes</text></svg>'


def witness_svg(case):
    witness = case["quadratic_witness"]
    low, high = min(-.1, min(witness["values"])*1.1), max(witness["values"])*1.1
    body = _axes("A fixed degree-2 witness", "p(λ)=(1−λ/a)(1−λ/b) · roots a,b chosen from the input spectrum", low, high)
    body += ('<polyline data-cg-witness="" points="'
             + _points(witness["abscissae"], witness["values"], low, high)
             + '" fill="none" stroke="#7c3aed" stroke-width="2"/>')
    for i, (lam, value) in enumerate(zip(case["declared_eigenvalues"], witness["at_eigenvalues"])):
        body += (f'<circle data-cg-witness-node="{i}" cx="{70+85*lam:.3f}" '
                 f'cy="{270-200*(value-low)/(high-low):.3f}" r="3.5" fill="#b45309"/>')
    for x in (0, 2, 4, 6, 7, 8):
        body += f'<text x="{70+85*x}" y="291" font-size="12" text-anchor="middle">{x}</text>'
    return body + '<text x="410" y="317" text-anchor="middle" font-size="12">λ · values at declared eigenvalues determine the weighted witness factor</text></svg>'


SCRIPT = """(()=>{
 document.documentElement.classList.add('cg-spectrum-js');
 const select=document.querySelector('[data-cg-case-select]');
 const show=()=>{for(const p of document.querySelectorAll('[data-cg-case]'))p.classList.toggle('is-current',p.dataset.cgCase===select.value);};
 select.addEventListener('change',show);show();
 for(const panel of document.querySelectorAll('[data-cg-case]')){
  const slider=panel.querySelector('[data-cg-step]');
  const update=()=>{
   const k=slider.value;
   panel.querySelector('[data-cg-step-label]').textContent='k='+k+' / '+slider.max;
   for(const frame of panel.querySelectorAll('[data-cg-frame]')){
    const active=frame.dataset.cgFrame===k;frame.classList.toggle('is-current',active);if(active)frame.open=true;
   }
  };
  slider.addEventListener('input',update);
  panel.querySelector('[data-cg-first]').addEventListener('click',()=>{slider.value='0';update();});
  panel.querySelector('[data-cg-last]').addEventListener('click',()=>{slider.value=slider.max;update();});
  update();
 }
})();"""


def cg_spectrum_html(result, lang="en"):
    body = '''<style>
 .cg-controls{display:none;gap:12px;align-items:center;flex-wrap:wrap;padding:14px;background:#eef4f8;border-radius:12px}
 .cg-spectrum-js .cg-controls{display:flex}.cg-spectrum-js [data-cg-case]:not(.is-current),.cg-spectrum-js [data-cg-frame]:not(.is-current){display:none}
 .cg-controls label{min-width:0;max-width:100%}.cg-controls select{max-width:100%;min-width:0}.cg-controls input{width:220px;max-width:100%}
 .cg-figure{overflow:auto;margin:16px 0}.cg-figure svg{display:block;width:100%;min-width:600px;height:auto}
 .cg-readout{font-family:monospace;overflow-wrap:anywhere}.cg-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}
 .cg-cards article{padding:18px;border-radius:12px;background:#eef4f8}.cg-cards h3{margin-top:0}
 @media(max-width:700px){.cg-cards{grid-template-columns:1fr}}
 @media print{.cg-controls{display:none!important}}
 </style>'''
    body += '<section><span class="badge">Shewchuk · §9.1–9.2 · controlled spectral illustrations</span><h2>' + bi(
        "같은 조건수인데 왜 다른 속도로 수렴할까?", "Why can the same condition number give different convergence?") + '</h2><p>' + bi(
        "CG는 오차를 고유값별 성분으로 줄입니다. 가장 작은 값과 큰 값이 같아도, 중간 값이 두 곳에 모이는지 넓게 퍼지는지, 시작 오차가 어디에 놓이는지에 따라 경로가 달라집니다. 16차원에서 3가지 분포 × 2가지 좌표계 × 3가지 시작을 빠짐없이 비교합니다.",
        "CG reduces error across eigenmodes. Equal smallest and largest eigenvalues leave room for different clusters and initial error weights. Compare all 3 spectra × 2 coordinate bases × 3 starting profiles in 16 dimensions.") + '</p>'
    body += '<div class="formula">f(x)=½xᵀAx · x*=0 · ||x₀||₂=1 · λ∈[2,7] · κ=3.5</div><div class="cg-cards">'
    descriptions = (
        ("two-values", "2와 7에 각각 8개", "Eight modes at 2, eight at 7"),
        ("two-clusters", "[2,2.1]과 [6.9,7]에 각각 8개", "Eight in [2,2.1], eight in [6.9,7]"),
        ("spread", "[2,7]에 서로 다른 16개", "Sixteen distinct values across [2,7]"),
    )
    for name, ko, en in descriptions:
        body += f'<article><h3>{name}</h3><p>{bi(ko,en)}</p></article>'
    body += '</div><p>' + bi(
        "정확한 산술에서는 오차가 놓인 서로 다른 고유값마다 근을 갖는 다항식으로 소거를 설명할 수 있습니다. 아래는 실제 부동소수점 실행입니다. 참 잔차가 초기의 10⁻¹² 이하이면 멈추며, 멈춘 뒤의 점이나 정확한 0을 만들어 붙이지 않습니다.",
        "In exact arithmetic, a polynomial with roots at the distinct active eigenvalues explains finite termination. These are floating-point executions, stopped when the true residual is at most 10⁻¹² times its initial norm. No extra points or exact zeros are appended.") + '</p><p>' + bi(
        "논문 Figure 31(d)의 원래 입력은 명시되어 있지 않습니다. 여기의 행렬과 시작점은 공개된 설명을 탐색하기 위해 선언한 새 입력입니다.",
        "Figure 31(d) does not specify its original inputs. The matrices and starts here are declared new inputs for exploring the published explanation.") + '</p></section>'
    body += '<section><h2>' + bi("18개 경로, 같은 척도에서 비교하기", "Compare all 18 paths") + '</h2><p>' + bi(
        "세로축은 ||eₖ||A/||e₀||A입니다. 초기 계수가 같은 경우와 초기 에너지가 같은 경우는 다릅니다. 한 고유모드만 켜면 다른 15개는 시작 오차에 기여하지 않습니다. Hadamard 좌표계는 같은 고유값을 가진 비대각 행렬을 만듭니다.",
        "The vertical axis is ||eₖ||A/||e₀||A. Equal initial coefficients and equal initial energies differ. A single-mode start leaves the other 15 modes inactive. The Hadamard basis produces a non-diagonal matrix with the same declared eigenvalues.") + '</p><p>' + bi(
        "점선은 구간 전체에 대한 정확한 산술의 비교 상계입니다. 개별 성분의 상계나 부동소수점 인증이 아닙니다. 그래프마다 로그 축 범위를 명시하며, 정확한 0은 바닥의 삼각형으로 표시합니다.",
        "The dashed reference is an exact-arithmetic interval comparison bound, not a componentwise bound or floating-point certificate. Each logarithmic axis declares its range; exact zeros use baseline triangles.") + '</p>'
    for basis in ("diagonal", "hadamard"):
        for profile in PROFILES:
            cases = [next(c for c in result['cases'] if c['spectrum']==s and c['basis_name']==basis and c['start_profile']==profile) for s in SPECTRA]
            series = tuple(LineSeries(c['spectrum'], tuple(r['iteration'] for r in c['rows']), tuple(r['energy_ratio'] for r in c['rows'])) for c in cases)
            max_k = max(c['completed_updates'] for c in cases)
            reference = LineSeries('Eq. (51) interval envelope', tuple(range(max_k+1)), tuple(result['comparisons'][k]['interval_envelope'] for k in range(max_k+1)), 'reference')
            body += '<details data-cg-overview><summary>' + basis + ' · ' + profile + '</summary><div class="cg-figure" tabindex="0">' + render_line_chart(ChartSpec(basis+' · '+profile, 'completed updates k', 'relative A-norm error', series+(reference,)), colors=COLORS+('#657588',)) + '</div></details>'
    body += '</section><section><h2>' + bi("고유모드 안에서 한 단계씩 보기", "Inspect each step in the eigenmodes") + '</h2><p class="small">' + bi(
        "좁은 화면에서는 그래프 안을 좌우로 스크롤하세요. 키보드로 그래프에 초점을 맞춘 뒤 방향키를 사용할 수도 있습니다.",
        "On narrow screens, scroll horizontally inside a graph. You can also focus it and use the arrow keys.") + '</p><p>' + bi(
        "파란 점은 실제 계산한 계수의 비율입니다. 회색 곡선은 같은 차수의 Chebyshev 비교 다항식이며, 점을 이은 실제 CG 다항식이 아닙니다. 초기 계수가 0이면 나눗셈은 미정의로 둡니다. 주황 막대는 각 성분의 제곱 에너지이며, 전체 합의 제곱근이 모드로 재구성한 상대 오차입니다.",
        "Blue dots are the actual coefficient ratios. The grey curve is the same-degree Chebyshev comparison polynomial, not a fitted actual CG polynomial. A zero initial coefficient leaves the ratio undefined. Orange bars are squared mode energies; the square root of their sum reconstructs the relative spectral error.") + '</p><div class="cg-controls"><label>' + bi("사례", "Case") + ' <select data-cg-case-select aria-label="CG spectrum case">'
    for case in result['cases']:
        body += f'<option value="{case["id"]}">{case["id"]}</option>'
    body += '</select></label></div></section>'
    for case in result['cases']:
        body += f'<section data-cg-case="{case["id"]}"><h2>{case["id"]}</h2><p class="cg-readout">'
        body += f"n=16 · declared κ=3.5 · measured κ={case['realized_condition_number']:.12g} · completed={case['completed_updates']} · stop={case['termination']}<br>"
        body += f"distinct declared eigenvalues={case['distinct_declared_eigenvalues']} · distinct initially active={len(case['active_declared_eigenvalues'])}<br>true residual tolerance={case['residual_tolerance']:.8e}</p>"
        body += '<div class="cg-controls"><button data-cg-first>' + bi('처음', 'First') + '</button><label>k <input data-cg-step type="range" min="0" max="' + str(case['completed_updates']) + '" value="0" aria-label="Completed CG updates"></label><output data-cg-step-label></output><button data-cg-last>' + bi('마지막', 'Last') + '</button></div>'
        for row in case['rows']:
            k = row['iteration']
            body += f'<details data-cg-frame="{k}"><summary>k={k} · relative A-norm error={row["energy_ratio"]:.8e}</summary>'
            body += f'<p class="cg-readout" data-cg-readout>k={k} · direct ratio={row["energy_ratio"]:.8e} · spectral ratio={row["spectral_energy_ratio"]:.8e}<br>direct energy − spectral energy={row["energy_identity_difference"]:.8e} · true residual={row["true_residual_norm"]:.8e}</p>'
            body += '<div class="cg-figure" tabindex="0">' + ratio_svg(case, row, result['comparisons'][k]) + '</div><div class="cg-figure" tabindex="0">' + energy_svg(case, row) + '</div>'
            body += '<details><summary>' + bi('16개 성분의 실제 수치', 'Actual values for all 16 modes') + '</summary><div class="scroll"><table><tr><th>i</th><th>λᵢ</th><th>cᵢ(k)</th><th>cᵢ(k)/cᵢ(0)</th><th>λᵢcᵢ(k)²</th><th>normalized energy</th></tr>'
            for i, lam in enumerate(case['declared_eigenvalues']):
                body += f'<tr><td>{i}</td><td>{lam:.9g}</td>' + ''.join('<td>'+_number(row[field][i])+'</td>' for field in ('coefficients','component_ratios','mode_energy','normalized_mode_energy')) + '</tr>'
            body += '</table></div></details></details>'
        w = case['quadratic_witness']
        body += '<details data-cg-witness-panel><summary>' + bi('두 개의 근으로 군집을 설명하기', 'Explain the clusters with two roots') + '</summary><p>' + bi(
            "정렬한 고유값 앞 8개와 뒤 8개의 평균을 두 근으로 고정했습니다. 이는 실제 CG 다항식이나 최적 다항식을 추정한 결과가 아닙니다. 아래 수치는 차수 2에 대한 별도 비교이며 위 단계 선택에 따라 변하지 않습니다.",
            "Fix the two roots at the mean of the first eight and last eight sorted eigenvalues. This is neither a fitted CG polynomial nor a claimed best polynomial. This separate degree-2 comparison does not change with the step selector.") + '</p><div class="cg-figure" tabindex="0">' + witness_svg(case) + '</div>'
        body += f'<p class="cg-readout">roots={w["roots"]}<br>max |p(λ)| over all modes={w["all_spectrum_factor"]:.8e}<br>max over initially active modes={w["active_spectrum_factor"]:.8e}<br>initial-energy-weighted factor={w["weighted_energy_factor"]:.8e}<br>'
        body += (f'actual k=2 A-norm ratio={case["rows"][2]["energy_ratio"]:.8e}' if case['completed_updates']>=2 else bi('실제 k=2 행 없음: 예산 또는 앞선 수렴으로 종료', 'No actual k=2 row: budget or earlier convergence')) + '</p><p>' + bi(
            "정확한 산술에서 CG의 k=2 상대 A-오차는 이 초기 에너지 가중 인자 이하입니다. 저장된 반올림 행렬과 부동소수점 경로에 대한 엄밀한 인증으로 해석하지 않습니다.",
            "In exact arithmetic, the k=2 relative CG A-error is at most this initial-energy-weighted factor. It is not a rigorous certificate for the rounded stored matrix and floating-point trajectory.") + '</p></details>'
        inputs = {key:case[key] for key in ('declared_eigenvalues','basis','basis_layout','A','b','x_star','start','declared_initial_coefficients','actual_initial_coefficients','input_sha256','basis_orthogonality_error_inf','eigen_equation_error_inf')}
        body += '<details><summary>' + bi('행렬·좌표계·시작점·반올림 잔차', 'Matrix, basis, start and rounding residuals') + '</summary><pre>' + escape(json.dumps(inputs,indent=2,allow_nan=False)) + '</pre></details></section>'
    body += '<section><h2>' + bi('원문과 검증 범위', 'Source and scope') + '</h2><p><a href="' + escape(result['source']['url'],quote=True) + '#page=39">Shewchuk (1994), §9.1 / Eq. (50), pp.33–35; §9.2 / Eqs. (51)–(52), p.36</a></p><ul>' + ''.join('<li>'+escape(s)+'</li>' for s in result['limits']) + '</ul><p class="formula">chainbench case-study cg-spectrum --steps 32 --lang ko --output cg-spectrum.html</p></section>'
    body += '<details><summary>' + bi('전체 입력과 모든 단계 JSON', 'Complete inputs and every recorded step') + '</summary><button data-download="chainbench-evidence" data-filename="chainbench-cg-spectrum.json">' + bi('JSON 저장', 'Save JSON') + '</button><pre id="chainbench-evidence">' + escape(json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':'))) + '</pre></details><script>' + SCRIPT + '</script>'
    return page('CG · same condition number, different spectra', bi('18개 선언된 사례 · 실제 고유모드 · 비교 다항식', '18 declared cases · actual eigenmodes · comparison polynomials'), body, lang=lang)
