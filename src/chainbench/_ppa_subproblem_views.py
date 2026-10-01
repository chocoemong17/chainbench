"""Local contours and gradient balance for the last completed quadratic PPA solve."""
from __future__ import annotations

import json
from html import escape

import numpy as np

from ._pages import bi
from ._ppa_subproblem import SOURCE


def _label(x,y,text,size=11,anchor='start'):
    return f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" text-anchor="{anchor}" fill="#334155">{escape(str(text))}</text>'


def _frame(record, row, visible):
    reference, point, previous = (np.array(row[key]) for key in ('reference','next','previous'))
    c = record['parameter']
    # Work in local offsets so adding tiny vectors to an absolute coordinate does
    # not erase them before the displayed, declared zoom is applied.
    ends = {'previous': previous-reference, 'next': point-reference, 'reference': np.zeros(2),
            'objective': point-reference+c*np.array(row['objective_gradient']),
            'penalty': point-reference+c*np.array(row['penalty_gradient'])}
    radius = 1. if row['unchanged_iterate'] else max(float(np.linalg.norm(v)) for v in ends.values())
    radius = radius or 1.
    unit = 2.6*radius/320
    hessian = np.array(record['hessian'])
    eigenvalues, eigenvectors = np.linalg.eigh(hessian)
    error = previous-reference
    base_level = float(.5*error@hessian@error) or float(.5*eigenvalues[0]*radius**2)
    levels = [base_level*v for v in (.25,.5,1.,2.)]
    axes = {'reference': reference.tolist(), 'radius': radius, 'units_per_pixel': unit,
            'center': [310.,240.], 'levels': levels,
            'coordinate': 'u minus the floating reference; equal coordinate scales',
            'energy': '0.5*(u-reference)^T*H*(u-reference)',
            'zoom': 'unit radius for unchanged iterate; otherwise actual point and scaled-gradient extents'}
    def project(offset):
        return 310+offset[0]/unit, 240-offset[1]/unit
    hidden = '' if visible else ' hidden="hidden"'
    body = [f'<g data-ppa-frame="{row["completed_update"]}" data-axes="{escape(json.dumps(axes),quote=True)}"{hidden}>',
            '<rect width="620" height="490" fill="#fbfaf7" rx="16"/>',
            _label(20,27,f'PPA · {row["completed_update"]-1} → {row["completed_update"]} · c={c:g}',16),
            _label(20,48,'Shifted problem contours · orange: c∇f(next) · blue: next−previous',11),
            _label(20,66,'Coordinates are local offsets from the floating reference solve.',11),
            '<rect x="70" y="80" width="480" height="320" fill="white" stroke="#cbd5df"/>',
            '<g clip-path="url(#ppa-subproblem-clip)">']
    angles = np.linspace(0,2*np.pi,97)
    for level in levels:
        radii = np.sqrt(2*level/eigenvalues)
        points = (eigenvectors@np.vstack((radii[0]*np.cos(angles),radii[1]*np.sin(angles)))).T
        line = ' '.join(','.join(f'{v:.3f}' for v in project(p)) for p in points)
        body.append(f'<polyline data-ppa-level="{level:.17g}" points="{line}" fill="none" stroke="#c1cad5"/>')
    body.append('</g>')
    for value in (-radius,0.,radius):
        x,y = project(np.array([value,value]))
        body.extend([f'<line x1="{x}" x2="{x}" y1="80" y2="400" stroke="#edf0f3"/>',
                     f'<line x1="70" x2="550" y1="{y}" y2="{y}" stroke="#edf0f3"/>',
                     _label(x,419,f'{value:.3g}',11,'middle'),_label(62,y+4,f'{value:.3g}',11,'end')])
    for key,color in [('objective','#d97706'),('penalty','#2563eb')]:
        x,y = project(ends['next'])
        a,b = project(ends[key])
        body.append(f'<line data-ppa-arrow="{key}" x1="{x:.3f}" y1="{y:.3f}" x2="{a:.3f}" y2="{b:.3f}" '
                    f'stroke="{color}" stroke-width="2.8" marker-end="url(#ppa-arrow-{key})"/>')
    for key,color,radius_px in [('reference','#172238',8),('previous','#64748b',5),('next','#13856a',4)]:
        x,y = project(ends[key])
        fill = 'none' if key == 'reference' else color
        body.append(f'<circle data-ppa-point="{key}" cx="{x:.3f}" cy="{y:.3f}" r="{radius_px}" fill="{fill}" stroke="{color}" stroke-width="1.8"/>')
    body.extend([_label(310,442,'Δu₁ → · Δu₂ ↑ · previous grey / next green / reference ring',11,'middle'),
                 _label(20,461,'Unchanged iterate: unit radius; residuals remain in the readout.' if row['unchanged_iterate']
                        else f'Common local scale: {unit:.4g} coordinate units / pixel; zoom can magnify roundoff.',10),
                 _label(20,480,'Quadratic-error contour levels: '+', '.join(f'{v:.3g}' for v in levels),10),'</g>'])
    return ''.join(body)


def subproblem_svg(record, problem=None):
    body = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 490" role="img" aria-label="Quadratic PPA subproblem and actual gradient balance" data-ppa-view="">'
    body += '<metadata>'+escape(json.dumps({'kind':'chainbench.ppa-subproblem-projection',
        'problem':problem,'subproblems':record},allow_nan=False))+'</metadata>'
    body += '<defs><clipPath id="ppa-subproblem-clip"><rect x="70" y="80" width="480" height="320"/></clipPath>'
    for key,color in [('objective','#d97706'),('penalty','#2563eb')]:
        body += f'<marker id="ppa-arrow-{key}" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7 Z" fill="{color}"/></marker>'
    body += '</defs>'
    body += ''.join(_frame(record,r,r['completed_update']==len(record['rows'])) for r in record['rows'])
    return body+'</svg>'


SCRIPT = '''(() => {
 const panel=document.querySelector('[data-ppa-panel]');if(!panel)return;
 let data=null;
 document.addEventListener('chainbench:trajectory',event=>{
  if(!data)data=JSON.parse(document.getElementById('chainbench-evidence').textContent).proximal_subproblems;
  const k=Math.min(event.detail.step,data.rows.length),initial=k===0;
  panel.querySelector('[data-ppa-initial]').hidden=!initial;
  panel.querySelector('[data-ppa-current]').hidden=initial;
  if(initial)return;
  panel.querySelectorAll('[data-ppa-frame]').forEach(frame=>frame.toggleAttribute('hidden',Number(frame.dataset.ppaFrame)!==k));
  const r=data.rows[k-1],fmt=v=>Number(v.toPrecision(6)),vec=x=>x.map(fmt).join(', ');
  panel.querySelector('[data-ppa-readout]').textContent=`PPA ${k-1} → ${k} · reference=(${vec(r.reference)}) · ||gradient balance||₂=${fmt(r.balance_norm)} · denominator=${fmt(r.balance_denominator)} · relative=${r.relative_balance===null?'undefined (zero denominator)':fmt(r.relative_balance)} · unchanged iterate: ${r.unchanged_iterate}`;
 });
})();'''


def subproblem_html(result):
    if 'proximal_subproblems' not in result:
        return ''
    record = result['proximal_subproblems']
    row = record['rows'][-1]
    relative = 'undefined (zero denominator)' if row['relative_balance'] is None else f'{row["relative_balance"]:.6g}'
    body = '<section data-ppa-panel class="ppa-panel"><style>[data-ppa-frame][hidden]{display:none}.ppa-panel{border:1px solid #d7e0e8;border-radius:16px;padding:22px;background:#f8fafc}.ppa-figure{max-width:720px;margin:16px auto}.ppa-figure svg{display:block;width:100%;height:auto}.ppa-panel .small{overflow-wrap:anywhere}@media(max-width:700px){.ppa-panel{padding:12px}}</style>'
    body += '<h2>'+bi('PPA: 다음 점에서 두 기울기가 균형을 이룹니다', 'PPA: two gradients balance at the next point')+'</h2>'
    p = result['problem']
    body += f'<p class="small">n=2 · κ={p["actual_condition_number"]:.6g} · angle={p["angle_degrees"]:g}° · x₀={p["start"]} · budget={result["steps"]} · no seed</p>'
    body += '<p>'+bi('원래 목적함수에 현재점에서 멀어지는 비용을 더한 보조문제를 풉니다. 그 해에서는 원래 함수의 기울기와 거리 벌점의 기울기가 반대 방향으로 균형을 이룹니다. 화면 위의 반복 슬라이더로 마지막으로 완료한 보조문제를 선택하세요.',
        'Solve the original objective plus a cost for moving away from the current point. At the solution, the original gradient and distance-penalty gradient balance in opposite directions. Use the iteration slider above to inspect the last completed subproblem.')+'</p>'
    body += '<div class="formula">φ_k(u)=f(u)+||u−x_k||²/(2c)<br>(Q+I/c)x_next=b+x_k/c<br>∇f(x_next)+(x_next−x_k)/c=0 · c=1</div>'
    body += '<p data-ppa-initial hidden>'+bi('k=0: 시작점만 있습니다. 완료한 PPA 보조문제가 아직 없습니다.', 'k=0: only the initial point exists. No PPA subproblem has been completed.')+'</p><div data-ppa-current>'
    body += '<div class="ppa-figure">'+subproblem_svg(record,p)+'</div>'
    body += f'<p class="small" data-ppa-readout>PPA {len(record["rows"])-1} → {len(record["rows"])} · reference={row["reference"]} · ||gradient balance||₂={row["balance_norm"]:.6g} · denominator={row["balance_denominator"]:.6g} · relative={relative} · unchanged iterate: {str(row["unchanged_iterate"]).lower()}</p></div>'
    body += '<p class="small">'+bi('검은 원은 수치적으로 구한 보조문제의 기준 해, 초록 점은 기존 solver가 계산한 실제 다음 점입니다. 두 점은 보통 화면에서 겹칩니다. 등고선은 그 기준 해를 중심으로 한 이차 오차 ½(u−û)ᵀ(Q+I/c)(u−û)이며, 정확한 산술에서는 φ의 최솟값과의 차이입니다. 수치 잔차를 표에 그대로 남깁니다.',
        'The ring marks a floating reference solve; green is the next point from the existing solver. They usually overlap on screen. Contours show the quadratic error ½(u−û)ᵀ(Q+I/c)(u−û) about that reference, equal to the subproblem gap in exact arithmetic. Floating residuals remain in the table.')+'</p>'
    body += '<p>'+bi('좌표는 기준 해에 대한 상대 위치이며, 두 축과 두 화살표에 같은 배율을 씁니다. 화살표는 다음 점에서의 기울기이며 반복점의 이동 경로가 아닙니다. 점이 그대로인 단계는 고정 범위로 표시합니다. 작은 잔차끼리 나눈 상대값은 커질 수 있으므로 분모와 절대 잔차를 함께 보세요. 이 화면은 일반적인 비정확 단조 연산자 이론이나 실행 시간 비교가 아닙니다.',
        'Coordinates are offsets from the reference, with one scale for both axes and arrows. Arrows are gradients at the next point, not iterate trajectories. An unchanged iterate uses a fixed range. Relative residuals can be large when dividing tiny values; read the denominator and absolute residual together. This is not the general inexact monotone-operator theory or a timing comparison.')+'</p>'
    body += '<p class="small"><a href="'+SOURCE+'">Rockafellar (1976), Eqs. (1.7)–(1.9), p.878 / PDF 2; Eq. (1.16), p.880 / PDF 4</a></p>'
    body += '<details><summary>'+bi('모든 PPA 보조문제의 값과 잔차', 'Values and residuals of every PPA subproblem')+'</summary><div class="scroll"><table><tr><th>k−1 → k</th><th>f(previous)−f*</th><th>f(next)−f*</th><th>distance penalty</th><th>φ(next)−f*</th><th>balance norm</th><th>denominator</th><th>relative</th><th>unchanged</th></tr>'
    for r in record['rows']:
        body += f'<tr><td>{r["completed_update"]-1} → {r["completed_update"]}</td>'
        body += ''.join(f'<td>{r[key]:.8g}</td>' for key in ('previous_objective_gap','next_objective_gap','penalty_value','subproblem_value_above_f_star','balance_norm','balance_denominator'))
        body += '<td>'+('undefined' if r['relative_balance'] is None else f'{r["relative_balance"]:.8g}')+f'</td><td>{str(r["unchanged_iterate"]).lower()}</td></tr>'
    return body+'</table></div></details></section><script>'+SCRIPT+'</script>'
