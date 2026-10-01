"""Offline walkthrough of a recorded, fixed-penalty ADMM LASSO computation."""
from __future__ import annotations

import json
from html import escape

from ._admm_figures import dual_svg, objective_svg, primal_svg, residual_svg
from ._admm_overview import CSS as OVERVIEW_CSS
from ._admm_overview import SCRIPT as OVERVIEW_SCRIPT
from ._admm_overview import native_id, overview
from ._admm_subproblems import MODEL_UPDATE, subproblem_section
from ._pages import bi, evidence, page
from .admm_geometry import SOURCE

FIELDS = (
    ('x_target', 'z_old − u_old'), ('x_rhs', 'Aᵀb + ρ(z_old − u_old)'),
    ('x', 'x'), ('x_equation_residual', '(AᵀA+ρI)x − rhs'),
    ('shrink_input', 'x + u_old'), ('z', 'z'), ('u', 'u'), ('y', 'y = ρu'),
    ('primal_residual', 'r = x − z'), ('dual_residual', 's = −ρ(z − z_old)'),
    ('primal_norm', '||r||₂'), ('eps_primal', 'ε_primal'),
    ('dual_norm', '||s||₂'), ('eps_dual', 'ε_dual'),
    ('stopping_passed', '||r||₂ ≤ ε_primal AND ||s||₂ ≤ ε_dual'),
    ('objective_z', 'F(z)'), ('split_objective', 'f(x) + g(z)'),
    ('stable_gap_z', 'F(z) − F* (stable)'), ('split_minus_optimum', 'f(x) + g(z) − F*'),
    ('dual_identity_residual', '∇f(x) + y − s'), ('dual_box_excess', '|y| − λ'),
)


def formatted(value):
    if value is None:
        return '—'
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list):
        return '('+', '.join(formatted(v) for v in value)+')'
    return f'{value:.6e}'


def _figure(svg):
    return '<div class="admm-figure" tabindex="0" aria-label="Scrollable figure / 좌우로 이동하는 그림">'+svg+'</div>'


def _case(case, radius, primary):
    ip, opt = case['inputs'], case['optimum']
    body = f'<details class="admm-case" data-admm-case="{case["id"]}"'+(' open' if primary else '')+'><summary>'
    body += f'{case["family"]} · λ/λ_max={ip["lambda_fraction"]:g} · {case["start_name"]} · ρ={ip["rho"]:g}</summary>'
    body += '<p class="small"><a data-admm-overview-return href="#admm-overview">'+bi('36개 결과로 돌아가기','Return to all 36 outcomes')+'</a></p>'
    body += f'<p class="formula">A={ip["A"]} · b={ip["b"]}<br>λ={ip["lambda"]:.8g} · λ_max={ip["lambda_max"]:.8g} · ρ={ip["rho"]:g}<br>'
    body += f'z₀={ip["z0"]} · u₀={ip["u0"]} · x₀=undefined<br>w*={formatted(opt["point"])} · F*={opt["value"]:.8g}</p>'
    body += '<div class="visual-grid">'+_figure(primal_svg(case,radius))+_figure(primal_svg(case,radius,surface=True))+'</div>'
    body += '<p class="small">'+bi('전체 경로는 계산한 모든 반복을 보여줍니다. 큰 점과 황색 선분은 선택한 k의 상태입니다. 표면 높이는 원래 목적함수 F의 간극이며, 3D 선분은 곡면을 따라 움직이는 연속 경로가 아닙니다.',
        'Full paths show every computed iterate. Large markers and the amber segment show the selected k. Surface height is the original F gap; 3D segments are not continuous motion along the surface.')+'</p>'
    body += subproblem_section(case,radius,formatted)
    body += '<h3>'+bi('선택한 상태', 'Selected state')+' · <span data-admm-k>k = 1</span></h3>'
    body += '<p class="small">'+bi('—는 이 단계에서 정의되지 않는 값입니다. 0으로 채우지 않습니다. 아래 표의 true는 두 잔차 조건을 모두 만족한다는 뜻입니다.',
        '— means undefined at this stage. It is not filled with zero. In the table, true means both residual tests pass.')+'</p>'
    body += '<div class="scroll" tabindex="0" aria-label="Selected numerical state / 선택한 수치"><table><thead><tr><th>Quantity</th><th>Stored value</th></tr></thead><tbody>'
    for key,label in FIELDS:
        body += f'<tr><th scope="row">{escape(label)}</th><td data-admm-field="{key}">{formatted(case["rows"][1][key])}</td></tr>'
    body += '</tbody></table></div><div class="visual-grid">'+_figure(dual_svg(case))+'<div>'
    body += '<h3>'+bi('불일치를 기억하는 변수', 'A variable that remembers disagreement')+'</h3><p>'+bi(
        'u는 매번 x−z를 더해 기억합니다. 다음 x 단계는 z−u를 향한 이차 벌점을, z 단계는 x+u에 대한 축소를 사용합니다. 같은 잔차를 두 번 더하는 방식이 아닙니다.',
        'u accumulates x−z. The next x step uses a quadratic penalty toward z−u; the z step shrinks x+u. The memory affects the two subproblems differently.')+'</p>'
    body += '<p class="formula">k≥1: y=ρu ∈ ∂(λ||z||₁)<br>zᵢ≠0 ⇒ yᵢ=λ sign(zᵢ)<br>zᵢ=0 ⇒ |yᵢ|≤λ</p><p>'+bi(
        '이는 축소를 마친 k≥1 단계의 정확한 산술에서 성립하는 z 최적성 조건입니다. 초기 기억 y₀는 이 조건을 만족할 필요가 없습니다. 원시 부동소수점 y와 |y|−λ를 그대로 기록합니다. 이 그림의 y는 특성 좌표의 변수이며, 측정 잔차로 만든 쌍대 하계 인증서가 아닙니다.',
        'These are exact-arithmetic z optimality conditions after a completed shrink step, k≥1. Initial memory y₀ need not satisfy them. Raw floating-point y and |y|−λ are retained. This y is in feature coordinates, not a measurement-residual certificate of a dual lower bound.')+'</p>'
    body += '<p>'+bi('검은 점은 원래 문제의 KKT 조건으로 얻은 y*=λ·s*입니다. 모든 경로는 결과를 선별하지 않고 표시합니다.',
        'The black point is y*=λ·s*, obtained from the original KKT system. Every recorded path is retained.')+'</p></div></div>'
    body += '<div class="visual-grid">'+_figure(objective_svg(case))+_figure(residual_svg(case))+'</div>'
    first = case['first_residual_pass']
    body += '<p data-admm-first-pass="'+str(first)+'">'+bi(
        f'잔차 조건의 최초 동시 만족: {first if first is not None else "예산 안에서 없음"}. 이 기록은 조기 종료하지 않고 {ip["steps"]}회 모두 계산합니다.',
        f'First simultaneous residual pass: {first if first is not None else "none within budget"}. The record computes all {ip["steps"]} updates without early stopping.')+'</p>'
    body += '<details class="admm-native"><summary>'+bi('스크립트 없이 읽는 대표 반복', 'Selected iterations readable without scripts')+'</summary>'
    body += '<div class="scroll" tabindex="0" aria-label="Native iteration table / 반복 수치 표"><table><thead><tr><th>k</th><th>x</th><th>z</th><th>y</th><th>F(z)−F*</th><th>||r|| / ε_r</th><th>||s|| / ε_s</th><th>pass</th></tr></thead><tbody>'
    for k in case['native_iterations']:
        row = case['rows'][k]
        body += f'<tr id="{native_id(case["id"],k)}" data-admm-native="{k}"><td>{k}</td>'
        values = [row[key] for key in ('x','z','y','stable_gap_z')]
        values += [None if k==0 else row[name+'_norm']/row['eps_'+name] for name in ('primal','dual')]
        values += [row['stopping_passed']]
        body += ''.join('<td>'+formatted(v)+'</td>' for v in values)+'</tr>'
    body += '</tbody></table></div></details><p class="small">input SHA-256: <code>'+case['input_sha256']+'</code></p></details>'
    return body


SCRIPT = r"""
(()=>{'use strict';
 const record=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 const selector=document.getElementById('admm-case'), slider=document.getElementById('admm-step');
 const cases=Array.from(document.querySelectorAll('[data-admm-case]'));
 const byId=new Map(record.cases.map(c=>[c.id,c]));
 const frameCache=new Map(Array.from(document.querySelectorAll('[data-frames]')).map(el=>[el,JSON.parse(el.dataset.frames)]));
 const format=v=>v===null?'—':typeof v==='boolean'?String(v):Array.isArray(v)?'('+v.map(format).join(', ')+')':Number(v).toExponential(6).replace(/e([+-])(\d)$/, 'e$10$2');
 const update=()=>{
  const id=selector.value,k=Number(slider.value),c=byId.get(id),row=c.rows[k];
  document.getElementById('admm-step-label').textContent='k = '+k;
  document.querySelectorAll('[data-admm-overview-link]').forEach(a=>{
   if(a.dataset.admmOverviewLink===id&&k===Number(slider.max))a.setAttribute('aria-current','true');
   else a.removeAttribute('aria-current');
  });
  cases.forEach(el=>{
   el.hidden=el.dataset.admmCase!==id;
   if(el.hidden)return;
   el.open=true;
   el.querySelector('[data-admm-k]').textContent='k = '+k;
   el.querySelectorAll('[data-admm-field]').forEach(e=>e.textContent=format(row[e.dataset.admmField]));
   el.querySelectorAll('[data-admm-marker]').forEach(e=>{
    const p=frameCache.get(e)[k];e.style.display=p===null?'none':'';
    if(p){e.setAttribute('cx',p[0]);e.setAttribute('cy',p[1]);}
   });
   el.querySelectorAll('[data-admm-primal]').forEach(svg=>{
    const x=frameCache.get(svg.querySelector('[data-admm-marker="x"]'))[k];
    const z=frameCache.get(svg.querySelector('[data-admm-marker="z"]'))[k];
    const chord=svg.querySelector('[data-admm-residual-chord]');chord.style.display=x===null?'none':'';
    if(x)chord.setAttribute('d',`M${x[0]} ${x[1]} L${z[0]} ${z[1]}`);
   });
"""+MODEL_UPDATE+r"""
  });
 };
 document.documentElement.classList.add('admm-js');
 selector.addEventListener('change',update);slider.addEventListener('input',update);
 document.querySelectorAll('[data-admm-move]').forEach(b=>b.addEventListener('click',()=>{
  const move=b.dataset.admmMove;
  slider.value=move==='first'?'0':move==='last'?slider.max:String(Math.min(Number(slider.max),Number(slider.value)+1));update();
 }));
"""+OVERVIEW_SCRIPT+r"""
 update();
})();
"""


def admm_html(result: dict, lang: str = 'en') -> str:
    if result.get('kind') != 'chainbench.admm-lasso-geometry':
        raise ValueError('not an ADMM LASSO geometry record')
    json.dumps(result,allow_nan=False)
    steps = result['parameters']['steps']
    primary = 'coupled-lambda0.1-zero-rho1'
    body = '<style>'+OVERVIEW_CSS+'''.admm-controls{display:none}.admm-js .admm-controls{display:flex}
    .admm-controls select{max-width:100%}.admm-controls input{min-width:120px;flex:1}
    .admm-step-controls{position:sticky;top:8px;z-index:5;background:#f8fafc;border:1px solid #dbe4ee;border-radius:12px;padding:8px}
    .admm-models th{text-transform:none;letter-spacing:normal}
    .admm-case{scroll-margin-top:150px;padding:18px 0;border-top:1px solid #dbe4ee}.admm-case>summary{overflow-wrap:anywhere}
    .admm-case .visual-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
    .admm-figure{overflow:auto;min-width:0;margin:10px 0}.admm-figure svg{display:block;width:100%;min-width:600px;height:auto}
    .admm-case td,.admm-case th{white-space:nowrap;font-variant-numeric:tabular-nums}
    .admm-figure:focus-visible,.scroll:focus-visible{outline:3px solid #ef9f47;outline-offset:3px}
    @media(max-width:1100px){.admm-case .visual-grid{grid-template-columns:minmax(0,1fr)}}
    @media print{.admm-controls{display:none!important}.admm-case[hidden]{display:block!important}}
    </style>'''
    body += '<div class="evidence-banner"><span class="evidence-tag">CONTROLLED ADMM GEOMETRY</span>'+bi(
        '2개 행렬 × 3개 규제 강도 × 2개 시작점 × 3개 벌점. 새 2차원 예제 36개이며 원문의 대규모 실험 재현은 아닙니다.',
        '2 matrices × 3 regularization strengths × 2 starts × 3 penalties. All 36 are new 2D examples, not reproductions of the source’s large experiment.')+'</div>'
    body += '<section><h2>'+bi('하나의 해를 두 변수가 나누어 찾기', 'Two variables work toward one solution')+'</h2><p>'+bi(
        '데이터에 잘 맞추는 일과 좌표를 0으로 만드는 일을 나눕니다. x는 이차 문제를 풀고, z는 좌표별로 축소합니다. 둘이 같아져야 원래 LASSO 문제의 한 점이 됩니다. u는 그동안의 불일치를 기억합니다.',
        'Split fitting the data from making coordinates zero. x solves a quadratic problem; z shrinks coordinates. They must agree to form one feasible point of the original LASSO problem. u remembers their accumulated disagreement.')+'</p>'
    body += '<p class="formula">F(w)=½||Aw−b||₂²+λ||w||₁<br>min f(x)+g(z), subject to x−z=0<br>λ_max=||Aᵀb||∞ · λ/λ_max∈{0.1,0.6,1.1} · ρ∈{0.1,1,10}</p>'
    body += '<div class="deep-grid"><article><h3>1 · '+bi('이차 문제 풀기', 'Solve the quadratic')+'</h3><p class="formula">(AᵀA+ρI)x_new<br>= Aᵀb+ρ(z_old−u_old)</p></article>'
    body += '<article><h3>2 · '+bi('좌표별 축소', 'Shrink coordinates')+'</h3><p class="formula">z_new=soft(x_new+u_old,λ/ρ)<br>soft(v,τ)=sign(v)max(|v|−τ,0)</p></article>'
    body += '<article><h3>3 · '+bi('불일치 누적', 'Accumulate disagreement')+'</h3><p class="formula">u_new=u_old+x_new−z_new<br>y_new=ρu_new</p></article></div>'
    body += '<p>'+bi('ρ는 해 자체를 바꾸는 λ와 역할이 다릅니다. ρ는 두 하위 문제의 결합 강도를 바꾸며, 이 화면에서는 실행 내내 고정합니다. 과완화나 적응형 ρ는 사용하지 않습니다.',
        'ρ has a different role from λ, which changes the solution. ρ controls the coupling of the subproblems and stays fixed throughout each run. There is no over-relaxation or adaptive penalty.')+'</p></section>'
    body += '<section><h2>'+bi('값이 낮다고 두 변수가 합의한 것은 아닙니다', 'A low value does not establish agreement')+'</h2>'
    body += '<p class="callout caution">'+bi(
        'F(z)는 하나의 점에서 계산한 원래 목적함수입니다. f(x)+g(z)는 서로 다른 두 점을 섞은 값이므로 x≠z이면 F*보다 작을 수 있습니다. 그 값을 원래 문제의 오차나 인증된 하계로 읽으면 안 됩니다.',
        'F(z) evaluates the original objective at one point. f(x)+g(z) combines two different points and can be below F* when x≠z. It is neither an original-primal gap nor a certified lower bound.')+'</p>'
    body += '<p>'+bi('λ/λ_max=1.1, zero 시작에서는 z=0이 이미 원래 문제의 해입니다. 그런데 첫 x 단계와 z가 다르므로 원래 간극이 0이어도 두 잔차 검사를 모두 통과하지 않습니다. 이 조합도 선택해 비교하세요.',
        'With λ/λ_max=1.1 and the zero start, z=0 already solves the original problem. Yet x and z differ after the first update: a zero original gap does not pass both residual tests. Select this case too.')+'</p>'
    body += '<p class="formula">r=x−z · s=−ρ(z−z_old)<br>ε_primal=√2·10⁻⁴+0.01 max(||x||₂,||z||₂)<br>ε_dual=√2·10⁻⁴+0.01||y||₂<br>pass ⇔ ||r||₂≤ε_primal AND ||s||₂≤ε_dual</p><p>'+bi(
        f'최초 통과를 기록하지만 {steps}회 고정 예산을 모두 실행합니다. 이 허용오차는 유한 정지 진단이며 정확도 정리가 아닙니다. k=0에는 x나 잔차 검사를 만들어 넣지 않습니다.',
        f'We record the first pass but run all {steps} fixed-budget updates. These tolerances are finite stopping diagnostics, not an accuracy theorem. No x or residual test is invented at k=0.')+'</p></section>'
    body += overview(result,formatted)
    body += '<section><h2>'+bi('36개 조합과 모든 반복', 'All 36 combinations, every iterate')+'</h2><p class="small">'+bi(
        '작은 화면에서는 그림과 표를 좌우로 밀어 보세요. 키보드로 영역에 초점을 맞춘 뒤 화살표 키로도 이동할 수 있습니다. 스크립트가 없으면 모든 조합을 펼쳐 첫 단계와 대표 반복을 읽을 수 있습니다.',
        'On small screens, scroll figures and tables sideways. Keyboard users can focus each region and use arrow keys. Without scripts, expand every case to read its first update and selected iterations.')+'</p>'
    body += '<div class="controls admm-controls"><label for="admm-case">'+bi('조합', 'Case')+'</label><select id="admm-case">'
    for case in result['cases']:
        body += '<option value="'+case['id']+'"'+(' selected' if case['id']==primary else '')+'>'+case['id']+'</option>'
    body += '</select></div><div class="controls admm-controls admm-step-controls" role="group" aria-label="Recorded iteration / 기록된 반복"><button type="button" data-admm-move="first">k=0</button>'
    body += '<button type="button" data-admm-move="next">+1</button><button type="button" data-admm-move="last">'+bi('마지막', 'Last')+'</button>'
    body += '<label for="admm-step">'+bi('반복', 'Iteration')+'</label>'+f'<input id="admm-step" type="range" min="0" max="{steps}" value="1"><strong id="admm-step-label" aria-live="polite">k = 1</strong></div>'
    radius = result['geometry']['primal_bounds'][1]
    for case in result['cases']:
        body += _case(case,radius,case['id']==primary)
    body += '</section><section><h2>'+bi('원문과 이 실험의 경계', 'Source and experiment scope')+'</h2><p><a href="'+SOURCE+'">Boyd, Parikh, Chu, Peleato &amp; Eckstein (2011)</a> · §6.4, printed p.43 / PDF 46; §3.1.1 / Eqs. (3.5)–(3.7), printed p.15 / PDF 18; §3.3, printed pp.18–19 / PDF 21–22.</p>'
    body += '<p>'+bi('이 논문은 1970년대부터 이어진 ADMM을 정리한 리뷰입니다. 여기서는 §6.4의 LASSO 갱신과 식 (3.12)의 ≤ 잔차 조건을 구현했습니다. 원문의 1,500×5,000 행렬, 난수열, 최적값, 실행 시간, 15회 종료를 재현했다고 주장하지 않습니다.',
        'This is a review of ADMM, whose origins are in the 1970s. We implement the §6.4 LASSO updates and the ≤ residual test of Eq. (3.12). We do not reproduce the original 1,500×5,000 matrix, RNG stream, optimum, timing or 15-update stop.')+'</p>'
    body += '<p>'+bi('원문 그림 11.2는 F(z)를 평가합니다. 저자의 MATLAB 예제는 이와 달리 f(x)+g(z)를 명시적으로 기록합니다. 여기서는 둘을 각각 이름 붙여 남깁니다. 두 AᵀA의 고윳값은 모두 1과 9이며, 해는 9개 부호 패턴과 KKT 조건으로 검사합니다. 전형적인 밀집 LASSO의 닫힌 해를 주장하는 것이 아닙니다.',
        'Figure 11.2 evaluates F(z); the author’s MATLAB example explicitly records f(x)+g(z). We retain both under separate names. Both AᵀA spectra are {1,9}; the optimum is checked over nine sign patterns using KKT conditions. This is not a closed-form claim for general dense LASSO.')+'</p>'
    body += '<p><a href="https://web.stanford.edu/~boyd/papers/admm/lasso/lasso.html">Author’s LASSO code and objective convention</a></p>'
    body += f'<pre>python -m chainbench geometry admm-lasso --steps {steps} --lang ko --output admm.html\npython -m chainbench geometry admm-lasso --steps {steps} --format json --output admm.json</pre></section>'
    body += evidence(result,'admm-lasso-geometry.json')+'<script>'+SCRIPT+'</script>'
    return page('Fit. Shrink. Agree.',bi('ADMM · 데이터를 맞추고, 좌표를 줄이고, 두 변수를 일치시키기',
        'ADMM · fit the data, shrink coordinates, bring two variables into agreement'),body,lang=lang)
