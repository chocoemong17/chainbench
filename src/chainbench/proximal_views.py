"""Offline projections of actual ISTA/FISTA points and proximal stage annotations."""
from __future__ import annotations

import json
from html import escape

import numpy as np

from ._pages import bi, evidence, page
from .proximal_geometry import SOURCE, A, B
from .visuals import ChartSpec, LineSeries, render_line_chart

COLORS = {'ista': '#236e9a', 'fista': '#bd4c34'}
LEVELS = (.05, .2, .8, 2., 5., 12., 25.)


def _gaps(x, case):
    x = np.asarray(x, dtype=float)
    a, b = np.array(A), np.array(B)
    error = a*(x-np.array(case['x_star']))
    subgradient = np.clip(a*b/case['lambda'], -1, 1)
    return .5*np.sum(error*error, axis=-1)+case['lambda']*np.sum(np.abs(x)-subgradient*x, axis=-1)


def _contour(case, level):
    angles = np.linspace(0, 2*np.pi, 257)
    direction = np.column_stack((np.cos(angles), np.sin(angles)))
    lo, hi = np.zeros(len(angles)), np.full(len(angles), 32.)
    star = np.array(case['x_star'])
    for _ in range(48):
        mid = (lo+hi)/2
        inside = _gaps(star+mid[:, None]*direction, case) < level
        lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
    return star+((lo+hi)/2)[:, None]*direction


def _project(x, gap=0., surface=False):
    a, b = x
    return (310+70*a+45*b, 380-15*a+24*b-5*gap) if surface else (310+100*a, 260-100*b)


def _text(x, y, value, size=12, anchor='start'):
    return (f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="#334155">{escape(str(value))}</text>')


def _points(points):
    return ' '.join(','.join(f'{v:.3f}' for v in p) for p in points)


def _frames(points):
    return '|'.join(','.join(f'{v:.3f}' for v in p) for p in points)


def proximal_svg(case, *, surface=False):
    def project(x):
        return _project(x, float(_gaps(x, case)), surface)
    title = 'Composite objective height F − F*' if surface else 'Composite contours · equal coordinate scales'
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 530" '
             f'role="img" aria-label="{title}"><rect width="620" height="530" rx="16" fill="#fbfaf7"/>',
             _text(22, 28, title, 16)]
    if surface:
        for first in (True, False):
            for fixed in np.linspace(-2.5 if first else -2, 2.5 if first else 2, 17):
                points = [project([fixed, free] if first else [free, fixed])
                          for free in np.linspace(-2 if first else -2.5, 2 if first else 2.5, 65)]
                parts.append('<polyline points="'+_points(points)+'" fill="none" stroke="#c8d4db"/>')
        for end, name in (([2.5, -2], 'x₁'), ([-2.5, 2], 'x₂')):
            start = _project([-2.5, -2], 0, True)
            finish = _project(end, 0, True)
            parts.append(f'<line x1="{start[0]}" y1="{start[1]}" x2="{finish[0]}" y2="{finish[1]}" stroke="#64748b"/>')
            parts.append(_text(finish[0]+8, finish[1], name, 14))
        x, y = _project([-2.5, -2], 0, True)
        parts.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y-100}" stroke="#64748b"/>')
        parts.append(_text(x+3, y-106, 'z=20', 11))
        parts.append(_text(22, 480, 'z = F(x) − F*; both the quadratic and L1 terms are included', 12))
    else:
        clip = 'prox-clip-'+case['id']
        parts.append(f'<defs><clipPath id="{clip}"><rect x="60" y="60" width="500" height="400"/></clipPath></defs>')
        parts.append('<rect x="60" y="60" width="500" height="400" fill="white" stroke="#cbd5df"/>')
        parts.append(f'<g clip-path="url(#{clip})">')
        for level in LEVELS:
            points = [project(x) for x in _contour(case, level)]
            parts.append(f'<polyline data-level="{level}" points="'+_points(points)
                         +'" fill="none" stroke="#b8cbd5"><title>F−F*='+str(level)+'</title></polyline>')
        parts.append('</g>')
        for value in (-2, -1, 0, 1, 2):
            x, y = _project([value, 0])
            parts.append(f'<line x1="{x}" y1="60" x2="{x}" y2="460" stroke="#edf0f3"/>')
            parts.append(_text(x, 478, value, 12, 'middle'))
            x, y = _project([0, value])
            parts.append(f'<line x1="60" y1="{y}" x2="560" y2="{y}" stroke="#edf0f3"/>')
            parts.append(_text(50, y+4, value, 12, 'end'))
        parts.append('<path d="M310 60 V460 M60 260 H560" stroke="#7f8d9d" fill="none" stroke-dasharray="4 4"/>')
        parts += [_text(574, 265, 'x₁', 14), _text(310, 50, 'x₂', 14, 'middle'),
                  _text(22, 505, 'Contour gaps: .05, .2, .8, 2, 5, 12, 25; axes mark L1 kinks', 12)]
    star = project(case['x_star'])
    parts.append(f'<circle cx="{star[0]:.3f}" cy="{star[1]:.3f}" r="5" fill="#172238"/>')
    parts.append(_text(star[0]+8, star[1]-10, 'x*', 13))
    for method, run in case['runs'].items():
        points = [project(r['x']) for r in run['rows']]
        parts.append(f'<polyline data-prox-path="{method}" data-points="{_frames(points)}" '
                     f'points="{_points(points)}" fill="none" stroke="{COLORS[method]}" '
                     f'stroke-width="2.6" stroke-dasharray="{"none" if method == "ista" else "8 4"}"/>')
    for name, first, last, color, dash in (('extrapolate', 'x', 'y', '#8454a6', '3 3'),
                                           ('gradient', 'y', 'z', '#ce8b20', '6 3'),
                                           ('shrink', 'z', 'next_x', '#13856a', 'none')):
        frames = {m: [(*project(r[first]), *project(r[last])) for r in run['stages']]
                  for m, run in case['runs'].items()}
        v = frames['fista'][0]
        parts.append(f'<line data-stage="{name}" data-prox-attrs="x1,y1,x2,y2" '
                     f'data-ista="{_frames(frames["ista"])}" data-fista="{_frames(frames["fista"])}" '
                     f'x1="{v[0]:.3f}" y1="{v[1]:.3f}" x2="{v[2]:.3f}" y2="{v[3]:.3f}" '
                     f'stroke="{color}" stroke-width="3.5" stroke-dasharray="{dash}"/>')
    for field, color, radius in (('x', '#172238', 4), ('y', '#8454a6', 6),
                                 ('z', '#ce8b20', 7), ('next_x', '#13856a', 5)):
        frames = {m: [project(r[field]) for r in run['stages']] for m, run in case['runs'].items()}
        x, y = frames['fista'][0]
        parts.append(f'<circle data-point="{field}" data-prox-attrs="cx,cy" '
                     f'data-ista="{_frames(frames["ista"])}" data-fista="{_frames(frames["fista"])}" '
                     f'cx="{x:.3f}" cy="{y:.3f}" r="{radius}" fill="{color}" stroke="white" stroke-width="1.3"/>')
    parts.append(_text(22, 523, 'Paths: ISTA blue / FISTA red · stages: y purple → z amber → next green', 11))
    parts.append('</svg>')
    return ''.join(parts)


SCRIPT = '''(() => {
 document.documentElement.classList.add('prox-js');
 const data=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 document.querySelectorAll('[data-prox-case]').forEach(panel=>{
  const c=data.cases.find(c=>c.id===panel.dataset.proxCase),slider=panel.querySelector('input[type=range]');
  const select=panel.querySelector('select'),button=panel.querySelector('[data-play]');let timer=null;
  const fmt=x=>x.map(v=>Number(v.toPrecision(6))).join(', ');
  const update=()=>{
   const k=Number(slider.value),m=select.value,s=c.runs[m].stages[k];
   panel.querySelector('[data-step]').textContent=`${m.toUpperCase()} · k = ${k} → ${k+1}`;
   panel.querySelectorAll('[data-prox-attrs]').forEach(el=>{
    const values=el.dataset[m].split('|')[k].split(',');
    el.dataset.proxAttrs.split(',').forEach((name,i)=>el.setAttribute(name,values[i]));
   });
   panel.querySelectorAll('[data-prox-path]').forEach(el=>
    el.setAttribute('points',el.dataset.points.split('|').slice(0,k+1).join(' ')));
   panel.querySelector('[data-y]').textContent=`x = (${fmt(s.x)}) → y = (${fmt(s.y)}) · β = ${s.momentum.toPrecision(5)}`;
   panel.querySelector('[data-z]').textContent=`∇f(y) = (${fmt(s.gradient)}) → z = (${fmt(s.z)})`;
   panel.querySelector('[data-next]').textContent=`τ = ${s.threshold.toPrecision(5)} → x_next = (${fmt(s.next_x)})`;
   panel.querySelector('[data-zero]').textContent=s.z.map((v,i)=>
    `coordinate ${i+1}: |z|=${Math.abs(v).toPrecision(5)} ${s.zeroed[i]?'≤':'>'} τ → ${s.zeroed[i]?'0':s.next_x[i].toPrecision(5)}`).join(' · ');
  };
  const stop=()=>{clearInterval(timer);timer=null;button.textContent='▶';button.setAttribute('aria-pressed','false');};
  slider.addEventListener('input',()=>{stop();update();});select.addEventListener('change',()=>{stop();update();});
  button.addEventListener('click',()=>{if(timer){stop();return;}if(+slider.value===+slider.max)slider.value='0';
   button.textContent='Ⅱ';button.setAttribute('aria-pressed','true');update();
   timer=setInterval(()=>{if(+slider.value>=+slider.max){stop();return;}slider.value=String(+slider.value+1);update();},750);
  });
  const details=panel.closest('details');if(details)details.addEventListener('toggle',()=>{if(!details.open)stop();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});update();
 });
})();'''


def _case_html(case):
    first = case['runs']['fista']['stages'][0]
    body = f'<div data-prox-case="{case["id"]}"><p class="formula">λ={case["lambda"]} · x₀={case["start"]}'
    body += f' · x*={case["x_star"]} · F*={case["f_star"]:.6g} · R²={case["radius_squared"]:.6g}</p>'
    body += '<div class="visual-grid"><div class="prox-figure">'+proximal_svg(case)+'</div>'
    body += '<div class="prox-figure">'+proximal_svg(case, surface=True)+'</div></div>'
    body += '<p class="small">'+bi('좌표 등고선과 3D 높이는 모두 F−F*입니다. 3D 선분은 표본 사이의 공간 선분이며 곡면을 따라 흐르는 연속 운동이 아닙니다.',
        'Contours and 3D heights both show F−F*. The 3D segments join sampled points in space; they are not continuous motion along the surface.')+'</p>'
    body += '<div class="prox-player"><label>'+bi('방법', 'Method')+'<select aria-label="Method / 방법"><option value="fista">FISTA</option><option value="ista">ISTA</option></select></label>'
    body += '<button type="button" data-play aria-pressed="false" aria-label="Play or pause / 재생·정지">▶</button>'
    body += f'<label for="prox-{case["id"]}">'+bi('단계', 'Step')+'</label>'
    body += f'<input id="prox-{case["id"]}" type="range" min="0" max="{len(case["runs"]["fista"]["stages"])-1}" value="0"><strong data-step>FISTA · k = 0 → 1</strong></div>'
    body += '<div class="deep-grid prox-stages" aria-live="polite"><article><h3>1 · '+bi('외삽점 y', 'Extrapolate y')+'</h3>'
    body += f'<p data-y>x={first["x"]} → y={first["y"]} · β=0</p></article>'
    body += '<article><h3>2 · '+bi('기울기 이동 z', 'Gradient step z')+'</h3>'
    body += f'<p data-z>∇f(y)={first["gradient"]} → z={first["z"]}</p></article>'
    body += '<article><h3>3 · Soft threshold</h3>'
    body += f'<p data-next>τ={first["threshold"]:.6g} → x_next={first["next_x"]}</p></article></div>'
    body += '<p class="prox-zero" data-zero>'+bi('각 좌표는 |zᵢ|≤τ일 때 정확히 0으로 설정됩니다.',
        'A coordinate is set to exactly zero when |z_i|≤τ.')+'</p>'
    series = []
    for method, run in case['runs'].items():
        series.append(LineSeries(method.upper()+' gap', tuple(r['iteration'] for r in run['rows']),
                                 tuple(r['gap'] for r in run['rows'])))
    body += '<div class="plot">'+render_line_chart(ChartSpec('Actual composite objective gaps',
        'completed updates k', 'F(x_k) − F*', tuple(series)), colors=tuple(COLORS.values()))+'</div>'
    for method in ('ista', 'fista'):
        series.append(LineSeries(method.upper()+' envelope', tuple(case['bounds']['iterations']),
                                 tuple(case['bounds'][method]), 'bound'))
    body += '<details><summary>'+bi('정리 3.1·4.4의 상계와 함께 보기', 'Compare the envelopes from Theorems 3.1 and 4.4')+'</summary><div class="plot">'
    body += render_line_chart(ChartSpec('Measured gaps and fixed-step theorem envelopes',
        'completed updates k', 'F(x_k) − F*', tuple(series)), colors=('#236e9a', '#bd4c34', '#698eaa', '#bc9389'))+'</div></details>'
    body += '<details><summary>'+bi('모든 갱신 단계와 수치', 'Every update stage and value')+'</summary><div class="scroll"><table>'
    body += '<tr><th>method</th><th>k → k+1</th><th>y</th><th>z</th><th>x_next</th><th>next gap</th></tr>'
    for method, run in case['runs'].items():
        for k, stage in enumerate(run['stages']):
            values = ['('+', '.join(f'{v:.5g}' for v in stage[key])+')' for key in ('y', 'z', 'next_x')]
            body += f'<tr><td>{method.upper()}</td><td>{k} → {k+1}</td>'
            body += ''.join('<td>'+v+'</td>' for v in values)+f'<td>{run["rows"][k+1]["gap"]:.6g}</td></tr>'
    body += '</table></div></details><p class="small">input SHA-256: <code>'+case['input_sha256']+'</code></p></div>'
    return body


def proximal_html(result: dict, lang: str = 'en') -> str:
    if result.get('kind') != 'chainbench.proximal-geometry':
        raise ValueError('not a proximal geometry result')
    json.dumps(result, allow_nan=False)
    body = '''<style>.prox-figure svg{width:100%;height:auto;display:block}
    .prox-player{display:none;gap:12px;align-items:center;flex-wrap:wrap;margin:18px 0}
    .prox-js .prox-player{display:flex}.prox-player input{flex:1;min-width:140px;padding:0}
    .prox-player select{margin-left:8px}.prox-stages{font-size:13px;overflow-wrap:anywhere}
    .prox-stages article:nth-child(1){border-top:3px solid #8454a6}
    .prox-stages article:nth-child(2){border-top:3px solid #ce8b20}
    .prox-stages article:nth-child(3){border-top:3px solid #13856a}
    .prox-zero{padding:12px 16px;background:#eaf5f0;border-radius:12px;font-size:13px;overflow-wrap:anywhere}
    .prox-case{padding:14px 0;border-top:1px solid #ddd}@media print{.prox-js .prox-player{display:none}}</style>'''
    body += '<div class="evidence-banner"><span class="evidence-tag">CONTROLLED PROXIMAL GEOMETRY</span>'
    body += bi('3개 λ × 3개 시작점 × 두 방법. 원 논문의 영상 복원 실험을 재현한 그림이 아닙니다.',
               '3 regularization strengths × 3 starts × two methods. These do not reproduce the paper’s deblurring figures.')+'</div>'
    body += '<section><h2>'+bi('미분 가능한 부분과, 모서리가 있는 부분', 'A smooth term and a term with corners')+'</h2>'
    body += '<div class="formula">F(x)=½||diag(1,3)x−(1.4,−2.4)||₂²+λ||x||₁ · x∈R²<br>'
    body += 'L=9 · μ_smooth=1 · κ_smooth=9 · step=1/9 · τ=λ/9<br>'
    body += f'λ∈{{0.1,0.8,1.8}} · budget={result["parameters"]["steps"]} · no seed</div>'
    body += '<p>'+bi('ISTA는 현재점에서 기울기를 계산합니다. FISTA는 이전 두 점의 이동을 섞어 만든 외삽점 y에서 계산합니다. 두 방법 모두 z=y−∇f(y)/L 뒤에 soft-thresholding을 적용합니다.',
        'ISTA evaluates the gradient at the current point. FISTA evaluates it at an extrapolated point y formed from two iterates. Both take z=y−∇f(y)/L and then apply soft thresholding.')+'</p>'
    body += '<p class="formula">x_next,i = sign(zᵢ) max(|zᵢ|−λ/L,0)</p><p>'+bi(
        '이것은 좌표를 0에 가깝게 반올림하는 과정이 아니라, λ||x||₁+(L/2)||x−z||²의 정확한 최소화입니다. |zᵢ|≤λ/L 구간에서는 최솟값이 0에 놓입니다.',
        'This is the exact minimizer of λ||x||₁+(L/2)||x−z||², not rounding small coordinates to zero. In the interval |z_i|≤λ/L, the minimizer is zero.')+'</p>'
    body += '<p class="small"><a href="'+SOURCE+'">Beck–Teboulle (2009), Eq. (1.5), Eqs. (2.5)–(2.6), (3.1), (4.1)–(4.3)</a></p></section>'
    primary = next(c for c in result['cases'] if c['id'] == 'lambda-2-opposite')
    body += '<section><h2>'+bi('한 단계 안에서 무슨 일이 일어날까?', 'What happens inside one update?')+'</h2>'+_case_html(primary)+'</section>'
    body += '<section><h2>'+bi('λ가 바뀌면 해도 바뀝니다', 'Changing λ changes the solution')+'</h2><div class="scroll"><table>'
    body += '<tr><th>λ</th><th>x*</th><th>τ=λ/L</th><th>nonzero coordinates</th></tr>'
    for c in result['cases'][::3]:
        body += f'<tr><td>{c["lambda"]}</td><td>{[round(v, 6) for v in c["x_star"]]}</td><td>{c["lambda"]/9:.6g}</td><td>{sum(v != 0 for v in c["x_star"])}</td></tr>'
    body += '</table></div><p>'+bi('대각 문제에서는 x*=soft(a·b,λ)/a²로 해를 독립적으로 계산합니다. λ=1.8에서는 첫 좌표가 0이 됩니다. 이는 일반적인 밀집 LASSO의 닫힌 형태 해를 주장하는 것이 아닙니다.',
        'For this diagonal problem, x*=soft(a·b,λ)/a² is independently known. At λ=1.8 the first coordinate becomes zero. This is not a closed-form solution claim for general dense LASSO.')+'</p>'
    body += '<p class="callout caution">'+bi('올바른 고정 L에서 ISTA의 목적함수는 감소하지만 FISTA는 매번 감소하지 않을 수 있습니다. 더 빠른 상계가 모든 반복에서 작은 오차를 보장하지는 않습니다. 첫 번째 FISTA 갱신은 ISTA와 같고, 이후 t와 외삽 계수가 달라집니다.',
        'With valid fixed L, ISTA is nonincreasing, while FISTA need not be. A faster envelope does not guarantee smaller error at every iterate. The first FISTA update matches ISTA; the t sequence then changes extrapolation.')+'</p></section>'
    body += '<section><h2>'+bi('9개 조합 모두 열기', 'Inspect all nine combinations')+'</h2><p class="small">'+bi(
        'λ=0.8, opposite 시작은 위에 표시했습니다. 나머지 여덟 조합도 모두 포함합니다.',
        'The λ=0.8 / opposite-start case appears above. All eight remaining combinations follow.')+'</p>'
    for c in result['cases']:
        if c['id'] != primary['id']:
            body += f'<details class="prox-case" id="{c["id"]}"><summary>λ={c["lambda"]} · {c["start_name"]} · x₀={c["start"]}</summary>'+_case_html(c)+'</details>'
    body += '</section><section><h2>'+bi('가정, 단위, 범위', 'Assumptions, scaling and scope')+'</h2><p>'
    body += bi('f는 볼록하고 L-smooth, g=λ||x||₁은 볼록하며 prox를 정확히 계산합니다. k≥1에서 ISTA 상계는 LR²/(2k), FISTA 상계는 2LR²/(k+1)²입니다. R=||x₀−x*||이며 유한 곡선은 정리의 증명이 아닙니다.',
        'The smooth term is convex and L-smooth; g=λ||x||₁ is convex with an exact prox. For k≥1, the ISTA envelope is LR²/(2k) and FISTA’s is 2LR²/(k+1)², where R=||x0−x*||. Finite curves do not prove the theorems.')+'</p><p>'
    body += bi('원문의 식 (1.3)은 제곱 오차에 ½이 없습니다. 여기서는 ½을 사용하므로 ∇f=Aᵀ(Ax−b), L=9입니다. 원문 일반 모델의 고정 L 알고리즘을 이 관례에 적용하며, 행렬·영상 데이터를 재현했다고 주장하지 않습니다.',
        'Equation (1.3) in the paper uses an unhalved squared loss. Here the ½ convention gives ∇f=Aᵀ(Ax−b), L=9. We apply the paper’s general fixed-L model under this convention, without claiming its matrix or image experiment.')+'</p><pre>'
    body += f'python -m chainbench geometry ista-fista --steps {result["parameters"]["steps"]} --lang ko --output proximal.html\n'
    body += f'python -m chainbench geometry ista-fista --steps {result["parameters"]["steps"]} --format json --output proximal.json</pre></section>'
    body += evidence(result, 'proximal-geometry.json')+'<script>'+SCRIPT+'</script>'
    return page('Extrapolate. Step. Shrink.', bi('ISTA / FISTA · 같은 계산을 좌표와 높이로 읽기',
        'ISTA / FISTA · read the same computation in coordinates and objective height'), body, lang=lang)
