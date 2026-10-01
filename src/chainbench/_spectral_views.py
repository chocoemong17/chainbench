"""Source polynomial curves beside observations from the saved CG iterates."""
from __future__ import annotations

from html import escape

from ._pages import bi

CSS = """
.spectral-details [hidden]{display:none}.spectral-legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px}
.spectral-details .spectral-readout{font-variant-numeric:tabular-nums;overflow-wrap:anywhere;font-size:13px}
.spectral-details td{white-space:nowrap}
.spectral-controls{display:none;gap:12px;align-items:center;margin:12px 0}
.repro-js .spectral-controls{display:flex}
"""

SCRIPT = """
   const cg=c.runs.cg, sr=cg.rows[Math.min(k,cg.updates)].spectral;
   panel.querySelector('[data-spectral-select]').value=String(Math.min(k,cg.updates));
   panel.querySelectorAll('[data-spectral-degree]').forEach(el=>{
    el.toggleAttribute('hidden',Number(el.dataset.spectralDegree)!==sr.reference_degree);
   });
   sr.component_ratios.forEach((value,j)=>{
    const marker=panel.querySelector(`[data-spectral-marker="${j}"]`);
    marker.setAttribute('visibility',value===null?'hidden':'visible');
    if(value!==null)marker.setAttribute('cy',186.25-85*value);
    panel.querySelector(`[data-spectral-bar="${j}"]`).setAttribute('width',360*sr.normalized_energy_squared[j]);
   });
   const number=v=>v===null?'undefined (initial component zero)':v.toExponential(4);
   panel.querySelector('[data-spectral-readout]').textContent=
    `CG k=${Math.min(k,cg.updates)}${k>cg.updates?' (last computed / 마지막 계산점)':''}`
    + ` · c₂/c₂,₀=${number(sr.component_ratios[0])} · c₇/c₇,₀=${number(sr.component_ratios[1])}`
    + ` · ||e||A/||e₀||A=${number(sr.energy_ratio)}`;
   panel.querySelector('[data-spectral-energy]').textContent=
    `λ=2: ${number(sr.normalized_energy_squared[0])} · λ=7: ${number(sr.normalized_energy_squared[1])}`
    + ` · sum=${number(sr.normalized_energy_squared.reduce((a,b)=>a+b,0))}`;
"""


def _text(x, y, label, size=12, anchor='start'):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="#334155" '
            f'text-anchor="{anchor}">{escape(label)}</text>')


def _open(kind, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 490" '
            f'data-spectral-view="{kind}" role="img" aria-label="{label}">'
            '<rect width="560" height="490" rx="16" fill="#fbfaf7"/>')


def polynomial_svg(case, spectral):
    row = case['runs']['cg']['rows'][-1]['spectral']
    body = _open('polynomials', 'Source comparison curves and actual CG component ratios at eigenvalues')
    body += _text(24, 28, 'Source curves · actual values at λ=2,7', 16)
    body += _text(24, 51, 'Same A, b and chosen start as the paths above', 12)
    body += _text(64, 72, 'P(λ), Q(λ), or observed c/c₀', 11)
    body += '<rect x="64" y="80" width="448" height="340" fill="white" stroke="#d6d1c7"/>'
    body += '<rect x="176" y="80" width="280" height="340" fill="#eff4f8"/>'
    for value in (-2, -1, 0, 1):
        y = 186.25-85*value
        body += f'<path d="M64 {y}H512" stroke="#d5dde3"/>' + _text(54, y+4, str(value), anchor='end')
    for value in (0, 2, 4, 6, 7, 8):
        x = 64+56*value
        body += _text(x, 442, str(value), anchor='middle')
        if value in (2, 7):
            body += f'<path d="M{x} 80V420" stroke="#8899aa" stroke-dasharray="3 4"/>'
    for p in spectral['polynomials']:
        hidden = '' if p['degree'] == row['reference_degree'] else ' hidden="hidden"'
        body += f'<g data-spectral-degree="{p["degree"]}"{hidden}>'
        for field, color, dash in [('interval', '#29816f', '6 4'), ('finite_spectrum', '#64748b', '')]:
            points = ' '.join(f'{64+56*x:.3f},{186.25-85*y:.3f}'
                              for x, y in zip(p['abscissae'], p[field]))
            body += f'<polyline data-spectral-curve="{field}" points="{points}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{dash}"/>'
        body += '</g>'
    for j, (lam, value) in enumerate(zip(spectral['eigenvalues'], row['component_ratios'])):
        y = 186.25-85*value if value is not None else 186.25
        body += f'<circle data-spectral-marker="{j}" cx="{64+56*lam}" cy="{y:.3f}" r="6" fill="#bc541d" stroke="white" stroke-width="2" visibility="{"visible" if value is not None else "hidden"}"/>'
    body += _text(280, 468, 'λ · shaded interval [2,7]', 13, 'middle')
    return body + '</svg>'


def energy_svg(case):
    row = case['runs']['cg']['rows'][-1]['spectral']
    body = _open('energy', 'Each eigenmode contribution to squared energy, normalized by initial total energy')
    body += _text(24, 28, 'What the actual CG step minimizes', 16)
    body += _text(24, 51, 'λⱼ cⱼ² / ||e₀||A² · bar sums = squared norm ratio', 12)
    for value in (0, .25, .5, .75, 1):
        x = 128+360*value
        body += f'<path d="M{x} 82V378" stroke="#d5dde3"/>' + _text(x, 405, f'{value:g}', anchor='middle')
    for j, lam in enumerate((2, 7)):
        y = 114+142*j
        body += _text(24, y+8, f'λ = {lam}', 15)
        body += _text(115, y+6, 'initial', 11, 'end')
        body += _text(115, y+45, 'current', 11, 'end')
        body += f'<rect x="128" y="{y-10}" width="{360*case["spectral_initial"]["energy_weights"][j]:.6f}" height="25" fill="#b3bec9"/>'
        body += f'<rect data-spectral-bar="{j}" x="128" y="{y+29}" width="{360*row["normalized_energy_squared"][j]:.6f}" height="25" fill="#176b91"/>'
    body += _text(280, 438, 'Same normalization for every step', 13, 'middle')
    body += _text(280, 463, 'Initial weights change with the selected start', 12, 'middle')
    return body + '</svg>'


def spectral_section(case, spectral):
    row = case['runs']['cg']['rows'][-1]
    data = row['spectral']
    body = '<details class="spectral-details" open><summary>'+bi(
        '두 고유값에서 오차를 줄이기: 상계의 곡선과 실제 CG',
        'Reduce error at two eigenvalues: bound curves and actual CG')+'</summary>'
    source = 'https://www.cs.cmu.edu/~quake-papers/painless-conjugate-gradient.pdf'
    body += f'<p class="small"><a href="{source}#page=40">Shewchuk §9.1 · Eq. (50) · Figure 31(a–c)</a> · <a href="{source}#page=42">§9.2 · Figure 33</a></p>'
    body += '<p>'+bi(
        '같은 오차를 고유벡터 방향의 계수 c₂, c₇로 분해합니다. 정확한 산술에서 CG는 현재 Krylov 탐색 공간에서 2c₂²+7c₇²를 최소화합니다. 회색·초록 곡선은 원문의 상계 비교 다항식이고, 주황 점은 저장된 반복점에서 측정한 계수 비율입니다. 주황 점 사이의 곡선을 추정하지 않습니다.',
        'Split the same error into coefficients c₂ and c₇ along the eigenvectors. In exact arithmetic CG minimizes 2c₂²+7c₇² over its current Krylov search space. Gray/green curves are source comparison polynomials for bounds; orange points are coefficient ratios measured from saved iterates. No curve is fitted between the observations.')+'</p>'
    body += '<div class="spectral-legend"><span style="color:#64748b">━ '+bi('유한 스펙트럼 {2,7}', 'Finite spectrum {2,7}')+'</span><span style="color:#29816f">┄ '+bi('전체 구간 [2,7]', 'Whole interval [2,7]')+'</span><span style="color:#bc541d">● '+bi('실제 CG 계수 비율', 'Actual CG coefficient ratio')+'</span></div>'
    body += '<p class="small">'+bi('k=0,1에서는 두 비교 곡선이 겹칩니다. 막대는 초기 전체 에너지로 나눈 각 성분의 기여도입니다.',
        'The comparison curves coincide at k=0,1. Bars show each contribution divided by the initial total squared energy.')+'</p>'
    control = 'spectral-select-'+case['id']
    body += f'<div class="spectral-controls"><label for="{control}">'+bi('CG 단계 선택', 'Select CG step')+f'</label><select id="{control}" data-spectral-select>'
    for r in case['runs']['cg']['rows']:
        selected = ' selected' if r['iteration'] == row['iteration'] else ''
        body += f'<option value="{r["iteration"]}"{selected}>k = {r["iteration"]}</option>'
    body += '</select></div>'
    body += '<div class="geometry">'+polynomial_svg(case, spectral)+energy_svg(case)+'</div>'
    def number(v):
        return 'undefined (initial component zero)' if v is None else f'{v:.4e}'
    body += f'<p class="spectral-readout" data-spectral-readout>CG k={row["iteration"]} · c₂/c₂,₀={number(data["component_ratios"][0])} · c₇/c₇,₀={number(data["component_ratios"][1])} · ||e||A/||e₀||A={number(data["energy_ratio"])}</p>'
    body += '<p class="spectral-readout" data-spectral-energy>'+f'λ=2: {number(data["normalized_energy_squared"][0])} · λ=7: {number(data["normalized_energy_squared"][1])} · sum={number(sum(data["normalized_energy_squared"]))}</p>'
    body += '<p class="callout">'+bi(
        '한 걸음의 회색 곡선은 1−2λ/9로, 두 고유값에서 크기가 같은 5/9입니다. 원 시작점의 실제 CG는 1−(13/75)λ를 사용합니다. 한 고유값의 비율이 더 커도 가중 제곱합은 더 작을 수 있습니다. 이 화면에서 k=1을 선택해 비교하세요.',
        'At one step the gray curve is 1−2λ/9, with equal magnitude 5/9 at both eigenvalues. Actual CG from the published start uses 1−(13/75)λ. One component ratio can be larger while the weighted sum of squares is smaller. Select k=1 here to compare.')+'</p>'
    body += '<details><summary>'+bi('원문 다항식과 모든 실제 계수', 'Source polynomials and every actual coefficient')+'</summary><div class="scroll"><table><tr><th>degree</th><th>{2,7}: comparison P(λ)</th><th>factor</th><th>[2,7]: comparison Q(λ)</th><th>factor</th></tr>'
    for p, pf, qf in zip(spectral['polynomials'], spectral['finite_formulas'], spectral['interval_formulas']):
        body += f'<tr><td>{p["degree"]}</td><td>{escape(pf)}</td><td>{p["finite_envelope_factor"]:.8g}</td><td>{escape(qf)}</td><td>{p["interval_envelope_factor"]:.8g}</td></tr>'
    body += '</table><table><tr><th>CG k</th><th>c₂</th><th>c₇</th><th>c₂/c₂,₀</th><th>c₇/c₇,₀</th><th>2c₂²</th><th>7c₇²</th><th>||e||A/||e₀||A</th></tr>'
    for r in case['runs']['cg']['rows']:
        s = r['spectral']
        values = s['coefficients']+s['component_ratios']+s['energy_squared']+[s['energy_ratio']]
        body += f'<tr><td>{r["iteration"]}</td>'+''.join('<td>'+('— (initial zero)' if v is None else f'{v:.8g}')+'</td>' for v in values)+'</tr>'
    body += '</table></div></details><p class="small">'+bi(
        '모든 비교 다항식은 P(0)=1입니다. 두 고유값에서는 2차로 정확히 0에 닿지만 구간 전체의 2차 상계는 25/137입니다. 이는 정확한 산술의 설명입니다. 반올림 오차를 0으로 바꾸지 않으며, 초기 계수가 0인 성분의 비율은 정의하지 않습니다. 종료된 CG는 마지막 계산점에 머뭅니다.',
        'All comparison polynomials satisfy P(0)=1. Degree two vanishes at the two eigenvalues, while the whole-interval degree-two factor is 25/137. These are exact-arithmetic statements. Roundoff is retained and ratios for zero initial components are undefined. Stopped CG holds its last computed state.')+'</p></details>'
    return body
