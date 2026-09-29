"""Auditable Frank–Wolfe motion on a triangular probability simplex.

Jaggi (2013), Algorithm 1 / Eq. (2) / Theorem 1, exact oracle (delta=0).
The fixtures are controlled geometric illustrations, not original-paper figures.
"""
from __future__ import annotations

import hashlib
import json
import platform
from html import escape

import numpy as np

from . import __version__
from ._pages import bi, evidence, page
from .methods import frank_wolfe
from .problems import SimplexQuadraticProblem
from .visuals import ChartSpec, LineSeries, render_line_chart

TARGETS = {'interior': (.2, .3, .5), 'edge': (.7, .3, 0.), 'near-vertex': (.84, .10, .06)}
STARTS = {'e1': (1., 0., 0.), 'e2': (0., 1., 0.), 'e3': (0., 0., 1.),
          'center': (1/3, 1/3, 1/3)}
SOURCE = 'https://proceedings.mlr.press/v28/jaggi13.pdf'


def run_simplex_geometry(steps: int = 18) -> dict:
    if type(steps) is not int or not 1 <= steps <= 60:
        raise ValueError('steps must be an integer between 1 and 60')
    cases = []
    for target_name, target in TARGETS.items():
        problem = SimplexQuadraticProblem(np.array(target))
        for start_name, start in STARTS.items():
            trace = frank_wolfe(problem, steps, x0=np.array(start))
            rows = []
            for k, x in enumerate(trace.iterates):
                gradient = problem.grad(x)
                vertex = problem.linear_minimizer(gradient)
                rows.append({'iteration': k, 'x': x.tolist(), 'gap': problem.gap(x),
                             'gradient': gradient.tolist(), 'vertex': vertex.tolist(),
                             'vertex_index': int(np.argmax(vertex)),
                             'dual_gap': float(gradient @ (x - vertex)),
                             'gamma': 2/(k+2) if k < steps else None,
                             'support': int(np.count_nonzero(x > 0))})
            actual = np.array([*target, *start], dtype='<f8').tobytes()
            cases.append({'id': f'{target_name}-{start_name}', 'target_name': target_name,
                          'target': list(target), 'start_name': start_name, 'start': list(start),
                          'input_sha256': hashlib.sha256(actual).hexdigest(), 'rows': rows,
                          'termination': 'fixed_budget', 'updates': steps})
    result = {
        'kind': 'chainbench.simplex-geometry', 'schema_version': 1,
        'evidence_level': 'controlled-geometric-illustrations',
        'source': {'author': 'Martin Jaggi', 'year': 2013, 'url': SOURCE,
                   'recurrence': 'Algorithm 1, PDF page 1',
                   'dual_gap': 'Eq. (2), Section 2, PDF page 2',
                   'bound': 'Theorem 1, Section 3, PDF page 3; exact oracle delta=0'},
        'problem': {'objective': 'f(x)=0.5||x-target||_2^2',
                    'domain': 'x in R^3; x_i >= 0; sum(x_i)=1', 'dimension': 3,
                    'affine_dimension': 2, 'L': 1., 'mu': 1., 'curvature': 2.,
                    'f_star': 0., 'seed': None, 'regularizer': None},
        'parameters': {'steps': steps, 'step_rule': 'gamma_k=2/(k+2)',
                       'oracle': 'basis vector at first minimum gradient coordinate',
                       'stopping': 'fixed budget; no tolerance-based early termination'},
        'design': 'all 3 named targets x all 4 named starts; no performance filtering',
        'input_hash_encoding': 'SHA-256 of little-endian float64 target then start',
        'bound': {'iterations': list(range(1, steps+1)),
                  'values': [4/(k+2) for k in range(1, steps+1)]},
        'cases': cases,
        'environment': {'chainbench': __version__, 'numpy': np.__version__,
                        'python': platform.python_version()},
        'limits': ['Not a reproduction of an original-paper numerical figure.',
                   'Twelve controlled cases, one 3D simplex family; not representative sampling.',
                   'Fixed step schedule is not line search and need not decrease every step.',
                   'Finite plots do not prove the theorem or certify worst-case optimality.'],
    }
    json.dumps(result, allow_nan=False)
    return result


def _plane(x):
    return x[1] + .5*x[2], np.sqrt(3)/2*x[2]


def _project(x, gap=0, surface=False):
    u, v = _plane(x)
    return (90+380*u-80*v, 435-170*v-240*gap) if surface else (70+420*u, 440-420*v)


def _text(x, y, value, size=12, anchor='start'):
    return (f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="#334155">{escape(str(value))}</text>')


def _points(points):
    return ' '.join(f'{x:.3f},{y:.3f}' for x, y in points)


def _frames(points):
    return '|'.join(','.join(f'{value:.3f}' for value in point) for point in points)


def simplex_svg(case: dict, *, surface: bool = False) -> str:
    target = np.array(case['target'])
    vertices = np.eye(3)
    def project(x):
        return _project(x, float(.5*np.sum((np.array(x)-target)**2)), surface)
    corners = [project(x) for x in vertices]
    title = 'Objective height on the feasible set' if surface else 'Feasible triangle · weights sum to one'
    clip = 'fw-clip-' + case['id'] + ('-surface' if surface else '')
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 530" '
             f'role="img" aria-label="{title}"><rect width="560" height="530" rx="16" '
             'fill="#fbfaf7"/>', _text(24, 28, title, 16)]
    if surface:
        for i in range(16):
            fixed = i/15
            for swap in (False, True):
                points = []
                for free in np.linspace(0, 1-fixed, 40):
                    x = [1-fixed-free, free, fixed] if swap else [1-fixed-free, fixed, free]
                    points.append(project(x))
                parts.append('<polyline points="' + _points(points)
                             + '" fill="none" stroke="#c4d2d8"/>')
        base = [_project(x, 0, True) for x in vertices]
        parts.append('<polygon points="' + _points(base) + '" fill="none" stroke="#9faeba"/>')
        ox, oy = base[0]
        parts.append(f'<line x1="{ox}" y1="{oy}" x2="{ox}" y2="{oy-240}" stroke="#64748b"/>')
        parts.append(_text(ox, oy-250, 'z = 1', 11, 'middle'))
        parts.append(_text(25, 500, 'z = f(x) − f* = ½||x−target||²; f* = 0'))
    else:
        parts.append(f'<defs><clipPath id="{clip}"><polygon points="{_points(corners)}"/>'
                     '</clipPath></defs><polygon points="' + _points(corners)
                     + '" fill="white" stroke="#8a9daa" stroke-width="1.5"/>')
        tx, ty = project(target)
        parts.append(f'<g clip-path="url(#{clip})">')
        # The equilateral embedding has gap = squared planar distance.
        for level in (.005, .02, .05, .10, .20, .40, .70):
            parts.append(f'<circle cx="{tx:.3f}" cy="{ty:.3f}" r="{420*np.sqrt(level):.3f}" '
                         f'fill="none" stroke="#d2dbdd"><title>f−f*={level}</title></circle>')
        parts.append('</g>')
        parts.append(_text(25, 500, 'Contours: f−f* = .005, .02, .05, .10, .20, .40, .70', 11))
    for i, (x, y) in enumerate(corners):
        parts.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="4" fill="#64748b"/>')
        parts.append(_text(x, y-13 if i == 2 else y+23,
                           f'e{i+1} = ' + ('(1,0,0)', '(0,1,0)', '(0,0,1)')[i], 12, 'middle'))
    tx, ty = project(target)
    parts.append(f'<circle cx="{tx:.3f}" cy="{ty:.3f}" r="5" fill="#172238"/>')
    parts.append(_text(tx+8, ty-12, 'target = x*', 12))
    points = [project(row['x']) for row in case['rows']]
    encoded = _frames(points)
    parts.append(f'<polyline data-fw-history="" data-points="{encoded}" points="{_points(points)}" '
                 'fill="none" stroke="#287698" stroke-width="2.6"/>')
    transitions = case['rows'][:-1]
    oracle = [project(row['vertex']) for row in transitions]
    segments = [(*a, *b) for a, b in zip(points[:-1], oracle)]
    first = segments[0]
    parts.append(f'<line data-fw-attrs="x1,y1,x2,y2" data-frames="{_frames(segments)}" '
                 f'x1="{first[0]:.3f}" y1="{first[1]:.3f}" x2="{first[2]:.3f}" '
                 f'y2="{first[3]:.3f}" stroke="#d38c20" stroke-dasharray="7 4" stroke-width="2"/>')
    for name, locations, color, radius in (('current', points[:-1], '#287698', 6),
                                           ('oracle', oracle, '#d38c20', 8),
                                           ('next', points[1:], '#148365', 5)):
        x, y = locations[0]
        parts.append(f'<circle data-marker="{name}" data-fw-attrs="cx,cy" '
                     f'data-frames="{_frames(locations)}" cx="{x:.3f}" cy="{y:.3f}" '
                     f'r="{radius}" fill="{color}" stroke="white" stroke-width="1.5"/>')
    parts.append(_text(25, 519, 'Blue: x_k · amber: oracle s_k · green: x_(k+1)', 11))
    parts.append('</svg>')
    return ''.join(parts)


SCRIPT = """
(() => {
 document.documentElement.classList.add('fw-js');
 const data=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 document.querySelectorAll('[data-fw-case]').forEach(panel=>{
  const c=data.cases.find(c=>c.id===panel.dataset.fwCase);
  const slider=panel.querySelector('input'),button=panel.querySelector('[data-play]');
  let timer=null;
  const update=()=>{
   const k=Number(slider.value),row=c.rows[k],next=c.rows[k+1];
   panel.querySelector('[data-step]').textContent=`k = ${k} → ${k+1}`;
   panel.querySelectorAll('[data-fw-attrs]').forEach(el=>{
    const values=el.dataset.frames.split('|')[k].split(',');
    el.dataset.fwAttrs.split(',').forEach((attr,i)=>el.setAttribute(attr,values[i]));
   });
   panel.querySelectorAll('[data-fw-history]').forEach(el=>
    el.setAttribute('points',el.dataset.points.split('|').slice(0,k+1).join(' ')));
   const fmt=x=>x.map(v=>Number(v.toPrecision(5))).join(', ');
   panel.querySelector('[data-oracle]').textContent=
    `∇f(x_k) = (${fmt(row.gradient)}) → s_k = e${row.vertex_index+1} = (${fmt(row.vertex)})`;
   panel.querySelector('[data-update]').textContent=
    `γ = ${row.gamma.toPrecision(5)} · x_k = (${fmt(row.x)}) → x_(k+1) = (${fmt(next.x)})`;
   panel.querySelector('[data-values]').textContent=
    `f(x_k)−f* = ${row.gap.toExponential(4)} · g_FW(x_k) = ${row.dual_gap.toExponential(4)}`
    + ` · f(x_(k+1))−f* = ${next.gap.toExponential(4)}`;
  };
  const stop=()=>{clearInterval(timer);timer=null;button.textContent='▶';button.setAttribute('aria-pressed','false');};
  slider.addEventListener('input',()=>{stop();update();});
  button.addEventListener('click',()=>{
   if(timer){stop();return;}if(+slider.value===+slider.max) slider.value='0';
   button.textContent='Ⅱ';button.setAttribute('aria-pressed','true');update();
   timer=setInterval(()=>{if(+slider.value>=+slider.max){stop();return;}
    slider.value=String(+slider.value+1);update();},750);
  });
  const details=panel.closest('details');
  if(details) details.addEventListener('toggle',()=>{if(!details.open) stop();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden) stop();});update();
 });
})();
"""


def _case_html(case: dict, bound: dict) -> str:
    rows = case['rows']
    k = tuple(row['iteration'] for row in rows)
    chart = render_line_chart(ChartSpec('Objective gap and oracle certificate',
        'completed updates k', 'gap / upper bound', (
            LineSeries('objective gap', k, tuple(r['gap'] for r in rows)),
            LineSeries('FW dual gap (certificate)', k, tuple(r['dual_gap'] for r in rows)),
            LineSeries('4/(k+2) · Theorem 1', tuple(bound['iterations']), tuple(bound['values']), 'bound'),
        )), colors=('#287698', '#d38c20', '#64748b'))
    cid = case['id']
    text = f'<div data-fw-case="{cid}"><p class="formula">target = {case["target"]} · x₀ = {case["start"]}</p>'
    text += '<div class="visual-grid"><div class="fw-figure">' + simplex_svg(case) + '</div>'
    text += '<div class="fw-figure">' + simplex_svg(case, surface=True) + '</div></div>'
    text += '<p class="small">' + bi(
        '좌표 그림의 점선은 가능한 선분입니다. 3D 점선은 두 끝점을 잇는 공간 선분이므로 곡면 위 경로가 아닙니다. 초록 점은 실제 다음 반복점의 목적함수 높이에 놓입니다.',
        'The triangle’s dashed line is the feasible segment. The 3D dashed line joins the endpoints in space, not along the curved surface. The green point has the actual next iterate’s objective height.') + '</p>'
    text += '<div class="fw-player"><button type="button" data-play aria-pressed="false" aria-label="Play or pause / 재생·정지">▶</button>'
    text += f'<label for="fw-{cid}">' + bi('갱신 단계', 'Update step') + '</label>'
    text += f'<input id="fw-{cid}" type="range" min="0" max="{len(rows)-2}" value="0"><strong data-step>k = 0 → 1</strong></div>'
    first = rows[0]
    text += '<div class="fw-readout" aria-live="polite"><p data-oracle>'
    text += f'∇f(x₀) = {first["gradient"]} → s₀ = e{first["vertex_index"]+1}</p>'
    text += f'<p data-update>γ₀ = 1 · x₁ = {rows[1]["x"]}</p>'
    text += f'<p data-values>f(x₀)−f* = {first["gap"]:.5g} · g_FW(x₀) = {first["dual_gap"]:.5g}</p></div>'
    text += '<div class="plot">' + chart + '</div>'
    text += '<details><summary>' + bi('모든 반복점·오라클·갱신 비율', 'All iterates, oracle choices and step sizes')
    text += '</summary><div class="scroll"><table><tr><th>k</th><th>x</th><th>f−f*</th><th>g_FW</th><th>s</th><th>γ</th></tr>'
    for row in rows:
        text += f'<tr><td>{row["iteration"]}</td><td>{", ".join(f"{x:.6g}" for x in row["x"])}</td>'
        text += f'<td>{row["gap"]:.6g}</td><td>{row["dual_gap"]:.6g}</td><td>e{row["vertex_index"]+1}</td>'
        text += f'<td>{row["gamma"] if row["gamma"] is not None else "—"}</td></tr>'
    text += '</table></div><p class="small">input SHA-256: <code>' + case['input_sha256'] + '</code></p></details></div>'
    return text


def simplex_html(result: dict, lang: str = 'en') -> str:
    if result.get('kind') != 'chainbench.simplex-geometry':
        raise ValueError('not a simplex geometry result')
    json.dumps(result, allow_nan=False)
    body = '''<style>.fw-figure svg{width:100%;height:auto;display:block}
    .fw-player{display:none;align-items:center;gap:14px;flex-wrap:wrap;margin:20px 0}
    .fw-js .fw-player{display:flex}.fw-player input{flex:1;min-width:120px;padding:0}
    .fw-readout{padding:12px 16px;background:#edf4f7;border-radius:12px;font-size:14px;overflow-wrap:anywhere}
    .fw-readout p{margin:5px 0}.fw-case{border-top:1px solid #ddd;padding:14px 0}
    @media print{.fw-js .fw-player{display:none}}</style>'''
    body += '<div class="evidence-banner"><span class="evidence-tag">GEOMETRIC ILLUSTRATIONS</span>'
    body += bi('3개 목표점 × 4개 시작점. 논문 그림 재현이 아닌 공개 알고리즘의 통제된 설명용 예시입니다.',
               '3 targets × 4 starts. Controlled explanations of a published algorithm, not reproduced paper figures.') + '</div>'
    body += '<section><h2>' + bi('투영 없이, 삼각형 안에서 움직이기', 'Move inside the triangle without projection') + '</h2>'
    body += '<div class="formula">min ½||x−target||₂² · xᵢ≥0 · x₁+x₂+x₃=1<br>'
    body += 'n=3 (affine dimension 2) · L=μ=1 · C_f=2 · x*=target · f*=0<br>'
    body += f'budget={result["parameters"]["steps"]} updates · γₖ=2/(k+2) · no seed / no regularizer</div>'
    body += '<div class="deep-grid">'
    for title, ko, en in (
        ('1 · Linear oracle', '기울기의 가장 작은 좌표에 해당하는 꼭짓점 eᵢ를 고릅니다. 동률이면 가장 앞의 좌표를 선택합니다. 심플렉스 위 선형함수는 꼭짓점에서 최솟값을 가집니다.',
         'Choose the basis vertex at the smallest gradient coordinate; exact ties use the first index. A linear function on the simplex attains its minimum at a vertex.'),
        ('2 · Convex combination', 'x새=(1−γ)x+γs. 0≤γ≤1이므로 두 실행 가능한 점을 잇는 선분에서도 제약을 지킵니다. 비싼 투영 대신 선형 오라클을 호출한다는 것이 핵심입니다.',
         'x_new=(1−γ)x+γs. With 0≤γ≤1, the segment between feasible points stays feasible. The key trade is a linear oracle in place of projection.'),
        ('3 · Certificate', 'g_FW=⟨∇f(x),x−s⟩는 볼록성에 의해 f(x)−f*의 상계입니다. 최적값을 모르더라도 오라클로 계산할 수 있습니다. 이 예제에서는 target이 해라 실제 오차와 직접 대조합니다.',
         'Convexity gives f(x)−f* ≤ g_FW=⟨∇f(x),x−s⟩. The oracle computes this certificate without knowing f*. Here the known optimum target lets us compare it to the actual gap.'),
    ):
        body += '<article><h3>' + title + '</h3><p>' + bi(ko, en) + '</p></article>'
    body += '</div><p class="small"><a href="' + SOURCE + '">Jaggi (2013), Algorithm 1 · Eq. (2) · Theorem 1</a></p></section>'
    body += '<section><h2>' + bi('한 걸음의 구조를 먼저 보기', 'Inspect one update first') + '</h2>'
    body += _case_html(result['cases'][0], result['bound']) + '</section>'
    body += '<section><h2>' + bi('항상 내려가는 것은 아닙니다', 'A scheduled step need not decrease the objective') + '</h2>'
    example = next(c for c in result['cases'] if c['id'] == 'interior-center')
    body += '<p class="callout caution">' + bi(
        f'내부 목표점과 무게중심 시작점에서 첫 gap은 {example["rows"][0]["gap"]:.5g}이고 첫 갱신 뒤 {example["rows"][1]["gap"]:.5g}입니다. γ₀=1은 꼭짓점까지 이동합니다. 이 고정 규칙을 선 탐색이나 매번 감소하는 방법으로 설명하면 안 됩니다.',
        f'With the interior target and barycenter start, the gap changes from {example["rows"][0]["gap"]:.5g} to {example["rows"][1]["gap"]:.5g} on the first update. γ₀=1 goes all the way to a vertex. This schedule is neither line search nor a promise of monotonic decrease.') + '</p>'
    body += '<p>' + bi(
        'compact convex 제약, 볼록·미분가능 목적함수, 유한 곡률과 정확한 오라클에서 정리 1은 k≥1에 대해 f(xₖ)−f*≤2C_f/(k+2)=4/(k+2)를 줍니다. 이 곡선은 g_FW의 매 반복 상계가 아닙니다.',
        'For a compact convex domain, convex differentiable objective, finite curvature and exact oracle, Theorem 1 gives f(x_k)−f*≤2C_f/(k+2)=4/(k+2) for k≥1. This curve is not a pointwise upper bound on g_FW.') + '</p>'
    body += '<p>' + bi(
        'Frank–Wolfe(1956)의 아이디어를 Jaggi(2013)는 dual gap·희소 원자·다양한 제약 집합의 관점에서 연결했습니다. 꼭짓점에서 시작하면 한 번에 원자 하나를 더할 수 있습니다. 무게중심 시작은 이미 세 원자를 사용하므로 희소한 시작으로 부르지 않습니다.',
        'Jaggi (2013) connects Frank–Wolfe (1956) to dual gaps, sparse atoms and varied constraint sets. A vertex start can add at most one atom per step. The barycenter already uses three atoms, so it is not labelled a sparse start.') + '</p></section>'
    body += '<section><h2>' + bi('12개 조합을 모두 확인하기', 'Inspect all twelve combinations') + '</h2><div class="scroll"><table>'
    body += '<tr><th>case</th><th>target</th><th>start</th><th>final f−f*</th><th>final g_FW</th></tr>'
    for case in result['cases']:
        last = case['rows'][-1]
        body += f'<tr><td>{case["id"]}</td><td>{case["target"]}</td><td>{case["start_name"]}</td>'
        body += f'<td>{last["gap"]:.6g}</td><td>{last["dual_gap"]:.6g}</td></tr>'
    body += '</table></div><p class="small">' + bi(
        '첫 조합은 위에 표시했습니다. 나머지 11개도 선택적으로 제외하지 않고 모두 포함합니다.',
        'The first combination appears above; all eleven remaining combinations are included below.') + '</p>'
    for case in result['cases'][1:]:
        body += f'<details class="fw-case" id="{case["id"]}"><summary>{case["id"]} · '
        body += bi('경로·갱신 열기', 'Open path and updates') + '</summary>'
        body += _case_html(case, result['bound']) + '</details>'
    body += '</section><section><h2>' + bi('무엇까지 설명하는가', 'Scope and trade-offs') + '</h2><p>'
    body += bi('이 화면은 하나의 심플렉스 이차함수 계열에서 이동·오라클·gap을 연결합니다. 고차원·실제 데이터의 대표 표본이나 원 논문의 응용 실험 재현은 아닙니다. 투영을 피하는 장점은 있지만 좁은 면 근처의 지그재그와 오라클 비용은 별도로 살펴야 합니다.',
               'This connects motion, oracle and gaps in one simplex quadratic family. It is not representative high-dimensional data or a reproduction of the paper’s application experiments. Avoiding projection is useful, while zig-zagging near faces and oracle cost remain trade-offs.')
    body += '</p><pre>python -m chainbench geometry frank-wolfe --steps '
    body += str(result['parameters']['steps']) + ' --lang ko --output simplex.html\n'
    body += 'python -m chainbench geometry frank-wolfe --steps '
    body += str(result['parameters']['steps']) + ' --format json --output simplex.json</pre></section>'
    body += evidence(result, 'simplex-geometry.json') + '<script>' + SCRIPT + '</script>'
    return page('Choose a vertex. Stay feasible.',
                bi('Frank–Wolfe · 심플렉스, 선형 오라클, 실제 반복점',
                   'Frank–Wolfe · simplex, linear oracle and actual iterates'), body, lang=lang)
