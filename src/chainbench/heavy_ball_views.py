"""Offline geometry and state inspection of the published heavy-ball cycle."""

from __future__ import annotations

import json
from html import escape

from ._pages import bi, evidence, page
from .heavy_ball_cycle import CYCLE, PiecewiseCycleProblem
from .visuals import ChartSpec, LineSeries, render_line_chart

COLORS = {'heavy-ball': '#ad6813', 'gd': '#287698'}


def _points(points):
    return ' '.join(f'{x:.3f},{y:.3f}' for x, y in points)


def cycle_svg(case, landscape, *, view='objective'):
    phase, history = view == 'phase', view == 'history'
    lo, hi = landscape['x'][0], landscape['x'][-1]
    xmin, xmax = (0, case['runs']['heavy-ball']['updates']) if history else (lo, hi)
    ymin, ymax = (lo, hi) if phase or history else (0, max(landscape['objective'])*1.04)
    left, top, width, height = (65, 75, 780, 190) if history else (80, 80, 400, 400)
    vw, vh = (900, 335) if history else (560, 555)
    def project(x, y):
        return left+width*(x-xmin)/(xmax-xmin), top+height-height*(y-ymin)/(ymax-ymin)
    def text(x, y, value, size=12, anchor='start'):
        return f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" text-anchor="{anchor}" fill="#334155">{escape(value)}</text>'
    title = {'objective': 'Actual iterates on the objective', 'phase': 'Two-state plane: previous and current',
             'history': 'Signed iterate history · published setup / declared variation'}[view]
    xlabel = 'iteration k' if history else 'previous iterate x[k−1]' if phase else 'iterate x'
    ylabel = 'current x[k]' if phase or history else 'f(x), with f*=0'
    axes = {'xmin': xmin, 'xmax': xmax, 'ymin': ymin, 'ymax': ymax,
            'left': left, 'top': top, 'width': width, 'height': height}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" '
             f'data-cycle-view="{view}" data-axes="{escape(json.dumps(axes), quote=True)}" '
             f'role="img" aria-label="{title}">',
             f'<rect width="{vw}" height="{vh}" rx="16" fill="#fbfaf7"/>',
             text(24, 28, title, 16), text(24, 51, ylabel, 12)]
    def ticks(low, high, integer=False):
        values = [low+(high-low)*j/4 for j in range(5)]
        if low < 0 < high:
            values[min(range(5), key=lambda i: abs(values[i]))] = 0.
        return sorted(set(round(v) if integer else v for v in values))
    for value in ticks(ymin, ymax):
        yy = project(xmin, value)[1]
        parts += [f'<line x1="{left}" x2="{left+width}" y1="{yy:.3f}" y2="{yy:.3f}" stroke="#dde3e7"/>',
                  text(left-9, yy+4, f'{value:.3g}', 11, 'end')]
    for value in ticks(xmin, xmax, integer=history):
        parts.append(text(project(value, ymin)[0], top+height+21, f'{value:.3g}', 11, 'middle'))
    parts.append(text(left+width/2, top+height+46, xlabel, 13, 'middle'))
    for join in (1., 2.):
        if not history:
            xx = project(join, ymin)[0]
            parts.append(f'<line x1="{xx:.3f}" x2="{xx:.3f}" y1="{top}" y2="{top+height}" stroke="#bc8989" stroke-dasharray="5 4"/>')
        if phase or history:
            yy = project(xmin, join)[1]
            parts.append(f'<line x1="{left}" x2="{left+width}" y1="{yy:.3f}" y2="{yy:.3f}" stroke="#bc8989" stroke-dasharray="5 4"/>')
    if not phase and not history:
        curve = [project(x, y) for x, y in zip(landscape['x'], landscape['objective'])]
        parts.append(f'<polyline points="{_points(curve)}" fill="none" stroke="#9cabb8" stroke-width="2" data-objective-curve=""/>')
    if phase:
        cycle = [(CYCLE[2], CYCLE[0]), (CYCLE[0], CYCLE[1]), (CYCLE[1], CYCLE[2])]
        points = [project(*v) for v in cycle]
        parts.append(f'<polygon points="{_points(points)}" fill="none" stroke="#192b43" stroke-dasharray="4 4" data-cycle-reference=""/>')
    else:
        points = [] if history else [project(x, PiecewiseCycleProblem.value([x])) for x in CYCLE]
    for x, y in points:
        parts.append(f'<rect x="{x-3:.3f}" y="{y-3:.3f}" width="6" height="6" fill="#192b43"/>')
    for name, run in case['runs'].items():
        points = [project(r['iteration'] if history else r['previous'] if phase else r['x'],
                          r['x'] if phase or history else r['objective']) for r in run['rows']]
        encoded = '|'.join(f'{x:.3f},{y:.3f}' for x, y in points)
        color = COLORS[name]
        parts.append(f'<polyline data-cycle-history="{name}" data-points="{encoded}" points="{_points(points)}" '
                     f'fill="none" stroke="{color}" stroke-width="2" '+('stroke-dasharray="5 3" ' if name == 'gd' else '')+'/>')
        x, y = points[0]
        parts.append(f'<circle data-cycle-marker="{name}" data-points="{encoded}" cx="{x:.3f}" cy="{y:.3f}" '
                     f'r="{6 if name == "gd" else 8}" fill="{"white" if name == "gd" else color}" stroke="{color}" stroke-width="2"/>')
    parts.append(text(24, vh-10, 'Amber: heavy-ball · blue dashed: GD · dark squares: source cycle' if not history
                      else 'Dashed horizontal lines: gradient-piece boundaries x=1 and x=2', 11))
    parts.append('</svg>')
    return ''.join(parts)


SCRIPT = """(()=>{
 const data=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 document.documentElement.classList.add('cycle-js');
 document.querySelectorAll('[data-cycle-case]').forEach(panel=>{
  const c=data.cases.find(c=>c.id===panel.dataset.cycleCase),slider=panel.querySelector('input'),button=panel.querySelector('[data-cycle-play]');let timer=null;
  const fmt=v=>v===null?'—':Number(v).toExponential(5);
  const update=()=>{
   const k=Number(slider.value);panel.querySelector('[data-cycle-step]').textContent='k = '+k;
   panel.querySelectorAll('[data-cycle-marker]').forEach(el=>{const v=el.dataset.points.split('|')[k].split(',');el.setAttribute('cx',v[0]);el.setAttribute('cy',v[1]);});
   panel.querySelectorAll('[data-cycle-history]').forEach(el=>{if(el.closest('svg').dataset.cycleView!=='history')el.setAttribute('points',el.dataset.points.split('|').slice(0,k+1).join(' '));});
   for(const name of ['heavy-ball','gd']){
    const row=c.runs[name].rows[k];
    panel.querySelector('[data-cycle-readout="'+name+'"]').textContent=name+' · x='+fmt(row.x)+' · f='+fmt(row.objective)+' · |grad|='+fmt(row.stationarity)+' · |x[k]−x[k−3]|='+fmt(row.three_step_difference);
   }
   const row=c.runs['heavy-ball'].rows[k],next=c.runs['heavy-ball'].rows[k+1];
   panel.querySelector('[data-cycle-update]').textContent=next?'HB: '+fmt(row.x)+' + gradient step '+fmt(row.gradient_step)+' + momentum '+fmt(row.momentum_step)+' = '+fmt(next.x):'Budget end / 예산 끝: no next update';
  };
  const stop=()=>{clearInterval(timer);timer=null;button.textContent='▶';button.setAttribute('aria-pressed','false');};
  slider.addEventListener('input',()=>{stop();update();});
  button.addEventListener('click',()=>{if(timer){stop();return;}if(+slider.value===+slider.max)slider.value='0';button.textContent='Ⅱ';button.setAttribute('aria-pressed','true');update();timer=setInterval(()=>{if(+slider.value>=+slider.max){stop();return;}slider.value=String(+slider.value+1);update();},500);});
  const details=panel.closest('details');if(details)details.addEventListener('toggle',()=>{if(!details.open)stop();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});update();
 });
})();"""


def _case_html(case, result):
    steps, cid = result['parameters']['steps'], case['id']
    body = f'<div data-cycle-case="{cid}"><p class="formula">x[-1] = x[0] = {case["start"]} · {steps} updates · α=1/9 · β=4/9 · GD step=1/25</p>'
    body += '<div class="cycle-geometry">'+cycle_svg(case, result['landscape'])+cycle_svg(case, result['landscape'], view='phase')+'</div>'
    body += '<p class="small">'+bi('좌표와 높이는 실제 반복점입니다. 직선 연결은 샘플 순서를 나타내며, 연속 시간의 궤적이나 곡면 위 이동을 뜻하지 않습니다. 위상 평면에서는 같은 x라도 이전 점이 다르면 다음 점이 달라지는 기억 효과를 볼 수 있습니다.', 'Coordinates and heights come from actual iterates. Chords show sample order, not continuous-time or surface motion. The state plane exposes memory: the same current x with a different previous x can produce a different next point.')+'</p>'
    body += f'<div class="cycle-player"><button type="button" data-cycle-play aria-pressed="false" aria-label="Play or pause / 재생·정지">▶</button><label for="cycle-{cid}">'+bi('반복점', 'Iterate')+f'</label><input id="cycle-{cid}" type="range" min="0" max="{steps}" value="0"><b data-cycle-step>k = 0</b></div>'
    body += '<div class="cycle-readout" aria-live="polite">'
    for name, run in case['runs'].items():
        row = run['rows'][0]
        body += f'<p data-cycle-readout="{name}">{name} · x={row["x"]:.6g} · f={row["objective"]:.6g} · |grad|={row["stationarity"]:.6g}</p>'
    row, nxt = case['runs']['heavy-ball']['rows'][:2]
    body += f'<p data-cycle-update>HB: {row["x"]:.6g} + gradient step {row["gradient_step"]:.6g} + momentum {row["momentum_step"]:.6g} = {nxt["x"]:.6g}</p></div>'
    body += '<div class="cycle-history">'+cycle_svg(case, result['landscape'], view='history')+'</div>'
    body += '<div class="cycle-geometry">'
    for field, title, label in [('objective', 'Computed objective gap; f*=0', 'f(x_k) − f*'),
                                ('stationarity', 'Stationarity is separate from repeating', '|gradient f(x_k)|')]:
        series = tuple(LineSeries(name, tuple(r['iteration'] for r in run['rows']), tuple(r[field] for r in run['rows'])) for name, run in case['runs'].items())
        body += '<div class="plot">'+render_line_chart(ChartSpec(title, 'iteration k', label, series), colors=tuple(COLORS.values()))+'</div>'
    body += '</div><details><summary>'+bi('모든 반복점과 갱신 항', 'Every iterate and update term')+'</summary><div class="scroll"><table><tr><th>method</th><th>k</th><th>x[k−1]</th><th>x[k]</th><th>f</th><th>gradient</th><th>gradient step</th><th>momentum</th><th>distance to cycle set</th><th>three-step difference</th></tr>'
    for name, run in case['runs'].items():
        for row in run['rows']:
            body += f'<tr><td>{name}</td>'
            for key in ('iteration', 'previous', 'x', 'objective', 'gradient', 'gradient_step', 'momentum_step', 'distance_to_cycle_set', 'three_step_difference'):
                value = row[key]
                body += '<td>'+('—' if value is None else f'{value:.8g}')+'</td>'
            body += '</tr>'
    body += '</table></div></details><p class="small">input SHA-256: <code>'+case['input_sha256']+'</code></p></div>'
    return body


def heavy_ball_cycle_html(result, lang='en'):
    if result.get('kind') != 'chainbench.heavy-ball-cycle':
        raise ValueError('not a heavy-ball counterexample record')
    json.dumps(result, allow_nan=False)
    steps = result['parameters']['steps']
    body = '<style>.cycle-geometry{display:grid;grid-template-columns:1fr 1fr;gap:22px}.cycle-geometry svg,.cycle-history svg{width:100%;height:auto;display:block}.cycle-player{display:none;align-items:center;gap:14px;flex-wrap:wrap;margin:18px 0}.cycle-js .cycle-player{display:flex}.cycle-player input{flex:1;min-width:120px;padding:0}.cycle-readout{font-family:monospace;font-size:13px;padding:16px;background:#edf4f7;border-radius:12px;overflow-wrap:anywhere}.cycle-readout p{margin:6px 0}.cycle-case{margin:18px 0;border-top:1px solid #ddd;padding-top:16px}@media(max-width:720px){.cycle-geometry{grid-template-columns:1fr}}@media print{.cycle-player{display:none!important}}</style>'
    body += '<div class="evidence-banner">'+bi('공개 반례 재현: 원문 시작점 3.3. 추가 8개 시작점과 GD 비교는 별도 설명용 변형입니다.', 'Published counterexample: original start 3.3. Eight extra starts and the GD comparison are separate controlled additions.')+'</div>'
    body += '<section><h2>'+bi('강볼록인데도, 최적해 대신 주기 궤도로 향합니다', 'Strong convexity alone does not save this tuning')+'</h2>'
    body += '<p>'+bi('Lessard–Recht–Packard의 이 함수는 매끄럽고 강볼록이지만 전체가 하나의 이차함수는 아닙니다. 이차함수에 맞춘 heavy-ball 매개변수를 그대로 사용하면 원문 시작점에서 세 점을 반복하는 궤도로 향합니다. 이전의 성공적인 이차함수 예시가 보장하는 범위를 보여주는 공개 반례입니다.', 'This Lessard–Recht–Packard function is smooth and strongly convex, but not a single quadratic. Heavy-ball with its quadratic-optimal parameters approaches a three-cycle from the published start. The counterexample marks a boundary of what successful quadratic examples establish.')+'</p>'
    body += '<div class="formula">f′(x) = 25x (x&lt;1); x+24 (1≤x&lt;2); 25x−24 (x≥2)<br>f(x) = 12.5x²; 0.5x²+24x−12; 12.5x²−24x+36<br>μ=1 · L=25 · κ=25 · x*=0 · f*=0 · n=1 · no seed<br>HB: x[k+1] = x[k] − (1/9) f′(x[k]) + (4/9)(x[k]−x[k−1])</div>'
    body += '<p>'+bi('기울기는 두 경계에서 연속이며 기울기의 기울기는 1 또는 25입니다. 따라서 gradient는 Lipschitz이고 강볼록성도 유지됩니다. f는 C¹이지만 경계 1, 2에서 두 번 미분 가능하지 않습니다. 비볼록 함수의 반례가 아닙니다.', 'The gradient is continuous at both joins, with slopes 1 or 25. It is Lipschitz and the function remains strongly convex. The objective is C1 but is not twice differentiable at 1 and 2. This is not a nonconvex example.')+'</p>'
    body += f'<p class="small"><a href="{result["source"]["url"]}#page=23">§4.6 / Eq. (4.11) · Figures 6–7</a> · <a href="{result["source"]["url"]}#page=39">Appendix B / Eqs. (B.1)–(B.3)</a> · budget={steps} · '+bi('원문 그림의 k=0…50 범위' if steps == 50 else '원문 50회와 다른 예산', 'Source-figure range k=0…50' if steps == 50 else 'Different budget from the source 50-update plot')+'</p></section>'
    body += '<section><h2>'+bi('먼저 원문의 시작점에서 따라가기', 'Follow the published start first')+'</h2>'+_case_html(result['cases'][0], result)+'</section>'
    body += '<section><h2>'+bi('반복한다고 최적해는 아닙니다', 'Repeating is different from being stationary')+'</h2><div class="formula">p=792/1225 · q=−2208/1225 · r=2592/1225<br>x[3n]→p, x[3n+1]→q, x[3n+2]→r for the published start</div>'
    body += '<p>'+bi('위 세 값은 원문의 해석적 주기이며 관측값에 맞춰 구한 값이 아닙니다. 주기 근처에서는 |x[k]−x[k−3]|가 작아지지만 기울기는 0이 아닙니다. 반면 고정점도 세 단계 차이가 0이므로, 이 차이만으로 주기 또는 수렴 여부를 판정하지 않습니다. 원문 Appendix B는 주기의 존재와 이 시작점에서의 끌림을 설명하며, 이 화면의 유한 계산은 그 수치 동작을 확인합니다.', 'These are the paper’s analytical cycle values, not a fit to the observations. Near the cycle, |x[k]−x[k−3]| becomes small while the gradient remains nonzero. A fixed point also has zero three-step difference, so that diagnostic alone does not establish a cycle or convergence. Appendix B supplies the cycle and attraction argument; this finite run checks the computed behavior.')+'</p></section>'
    body += '<section><h2>'+bi('추가한 시작점도 전부 보기', 'Inspect every added starting point')+'</h2><p>'+bi('0.5부터 4.0까지 0.5 간격인 8개 시작점을 미리 정하고 모두 포함했습니다. 결과에 따라 골라낸 표본이 아니며 대표 무작위 표본도 아닙니다. 같은 시작점의 GD(1/L)는 ChainBench의 비교 추가입니다. 반복 수가 실제 실행 시간 순위를 뜻하지는 않습니다.', 'All eight starts on the declared 0.5:0.5:4.0 grid are included without outcome filtering. They are controlled variations, not representative random sampling. GD at 1/L is a ChainBench comparison addition; iteration counts are not a runtime ranking.')+'</p><div class="scroll"><table><tr><th>start</th><th>HB final x</th><th>HB |gradient|</th><th>HB distance to cycle set</th><th>GD |gradient|</th></tr>'
    for case in result['cases']:
        hb, gd = case['runs']['heavy-ball']['rows'][-1], case['runs']['gd']['rows'][-1]
        body += f'<tr><td>{case["start"]}</td><td>{hb["x"]:.6g}</td><td>{hb["stationarity"]:.6g}</td><td>{hb["distance_to_cycle_set"]:.6g}</td><td>{gd["stationarity"]:.6g}</td></tr>'
    body += '</table></div>'
    for case in result['cases'][1:]:
        body += f'<details class="cycle-case" id="{case["id"]}"><summary>x₀={case["start"]} · '+bi('추가 통제 예시 열기', 'Open controlled variation')+'</summary>'+_case_html(case, result)+'</details>'
    body += '</section><section><h2>'+bi('연구 맥락과 재현 범위', 'Research context and scope')+'</h2><p>'+bi('이 논문은 최적화 알고리즘을 동적 시스템으로 보고 IQC와 작은 준정부호 문제로 안정성을 분석합니다. 여기서는 공개 반례의 함수와 기존 heavy-ball 갱신을 재계산합니다. IQC 행렬 문제, 안정성 영역 탐색 또는 논문 전체 실험을 구현한 것은 아닙니다. 다른 heavy-ball 매개변수나 모든 비이차함수가 실패한다는 주장도 아닙니다.', 'The paper studies optimization algorithms as dynamical systems using IQCs and small semidefinite problems. This workflow recomputes its public counterexample using the existing heavy-ball update. It does not implement the IQC programs, stability-region searches or all experiments, and makes no claim that every heavy-ball tuning or nonquadratic problem fails.')+'</p><ul>'
    body += ''.join('<li>'+escape(x)+'</li>' for x in result['differences'])+'</ul>'
    body += f'<pre>python -m chainbench reproduce lessard-2016 --steps {steps} --lang ko --output cycle.html\npython -m chainbench reproduce lessard-2016 --steps {steps} --format json --output cycle.json</pre></section>'
    body += evidence(result, 'heavy-ball-cycle.json')+'<script>'+SCRIPT+'</script>'
    return page('When momentum settles into a cycle.', bi('공개 heavy-ball 반례 · 실제 함수, 기억 상태와 모든 반복점', 'Published heavy-ball counterexample · objective, memory state and actual iterates'), body, lang=lang)
