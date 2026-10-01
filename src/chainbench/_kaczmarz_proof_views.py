"""Explain the conditional step of Theorem 2 using the current recorded update."""

from __future__ import annotations

import json
from html import escape

from ._pages import bi

CSS = """
.rk-proof{margin-top:24px;padding-top:24px;border-top:1px solid #d7e1ee}.rk-proof-grid{display:grid;grid-template-columns:1fr 1.4fr;gap:18px}.rk-proof svg{width:100%;height:auto;display:block}.rk-proof-candidates{overflow:auto}.rk-proof-candidates svg{min-width:640px}.rk-proof-status{font:13px/1.8 monospace;white-space:pre-wrap;overflow-wrap:anywhere;padding:16px;border-radius:12px;background:#f1f4fa}.rk-proof-table{overflow:auto;max-height:420px}@media(max-width:850px){.rk-proof-grid{grid-template-columns:1fr}}@media print{.rk-proof-table{max-height:none}}
"""
SCRIPT = r"""document.addEventListener('chainbench:kaczmarz',event=>{
 const {caseRecord:c,run,step:k}=event.detail,panel=document.querySelector('[data-rk-case="'+c.id+'"] [data-rk-proof]');
 if(!panel)return;
 const before=run.iterates[Math.max(0,k-1)],state=c.conditional_projection.states.find(s=>s.key===before.join(',')),index=k?run.row_indices[k-1]:null,outcome=index===null?null:state.outcomes[index],axis=index===null?null:c.inputs.A[index].indexOf(1);
 panel.setAttribute('data-current-step',k);panel.setAttribute('data-current-seed',run.seed);panel.setAttribute('data-state-key',state.key);
 const chart=panel.querySelector('[data-rk-candidates]'),max=c.exact_expectation[0];
 for(const [j,d] of state.directions.entries()){
  const bar=chart.querySelector('[data-rk-candidate="'+j+'"]'),height=200*d.squared_error/max;
  bar.setAttribute('y',270-height);bar.setAttribute('height',height);bar.setAttribute('fill',j===axis?'#d97706':'#2563eb');
  const dot=chart.querySelector('[data-rk-candidate-marker="'+j+'"]');dot.setAttribute('cy',270-height);dot.style.display=j===axis?'':'none';
 }
 const ey=270-200*state.conditional_squared_error/max;chart.querySelector('[data-rk-conditional-line]').setAttribute('y1',ey);chart.querySelector('[data-rk-conditional-line]').setAttribute('y2',ey);
 const triangle=panel.querySelector('[data-rk-triangle]');triangle.querySelector('[data-rk-triangle-initial]').style.display=k?'none':'';triangle.querySelector('[data-rk-triangle-active]').style.display=k?'':'none';
 if(outcome){
  const scale=215/Math.sqrt(max),a=Math.sqrt(outcome.squared_step),b=Math.sqrt(outcome.squared_error),o=[90,290],next=[90,290-scale*b],previous=[90+scale*a,290-scale*b];
  for(const [name,points] of [['old',[o,previous]],['remaining',[o,next]],['removed',[next,previous]]])triangle.querySelector('[data-rk-error-leg="'+name+'"]').setAttribute('points',points.map(p=>p.join(',')).join(' '));
  for(const [name,p] of [['solution',o],['next',next],['previous',previous]]){const el=triangle.querySelector('[data-rk-error-point="'+name+'"]');el.setAttribute('cx',p[0]);el.setAttribute('cy',p[1]);}
  const right=triangle.querySelector('[data-rk-right-angle]');right.style.display=a>0&&b>0?'':'none';right.setAttribute('d','M'+next[0]+','+(next[1]+12)+' h12 v-12');
  triangle.querySelector('[data-rk-triangle-note]').textContent=a===0||b===0?'zero-length leg / 길이 0인 변: 직각 표시 생략':'orthogonal error vectors / 두 오차 벡터가 직교';
 }
 panel.querySelector('[data-rk-proof-status]').textContent=(k?'completed projection k='+k+' · fix x['+(k-1)+']':'k=0 · before any draw / 아직 투영 전')+'=['+before.join(', ')+']\n'+(outcome?'actual row='+index+' · old²='+state.squared_error+' = remaining² '+outcome.squared_error+' + removed² '+outcome.squared_step+' · dot='+outcome.inner_product+'\n':'no selected row / 선택한 행 없음\n')+'conditional E(next error²)='+state.conditional_squared_error.toPrecision(9)+' · conditional upper='+state.theorem_conditional_upper.toPrecision(9)+'\nE(removed²)='+state.conditional_squared_step.toPrecision(9)+' = ||A·before−b||²/||A||F²='+state.residual_energy_over_frobenius.toPrecision(9)+'\nconditional ratio='+(state.conditional_ratio===null?'undefined at zero error / 오차 0에서 미정의':state.conditional_ratio.toPrecision(9));
});"""


def _text(x,y,text,size=13,extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="#334155" {extra}>{escape(str(text))}</text>'


def _triangle(initial_error):
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 460 360" role="img" aria-label="Orthogonal error triangle for the completed projection; equal coordinate scales" data-rk-triangle=""><rect width="460" height="360" rx="14" fill="#f7f9fc"/>'
    svg += '<metadata>'+escape(json.dumps(dict(kind="chainbench.kaczmarz-error-triangle", coordinate_basis="removed error horizontal, remaining error vertical; not the original x axes", pixels_per_unit=215/initial_error**.5, solution_pixel=[90,290], degeneracy="no right-angle mark if either error leg has zero length", initial_iteration=0)))+'</metadata>'
    svg += _text(20,28,'Pythagorean error triangle',15)
    svg += _text(20,51,'Gray: old · green: remaining · orange: removed',11)
    svg += '<g data-rk-triangle-initial="">'+_text(40,165,'k=0: no completed projection',16)+_text(40,193,'Inspect the possible choices on the right.',13)+'</g>'
    svg += '<g data-rk-triangle-active="" style="display:none">'
    for name,color in [('old','#64748b'),('remaining','#0f766e'),('removed','#d97706')]:
        svg += f'<polyline data-rk-error-leg="{name}" points="" fill="none" stroke="{color}" stroke-width="3"/>'
    for name,color,r in [('solution','#172238',5),('previous','#64748b',9),('next','#0f766e',5)]:
        svg += f'<circle data-rk-error-point="{name}" cx="90" cy="290" r="{r}" fill="{color}"/>'
    svg += '<path data-rk-right-angle="" d="" fill="none" stroke="#475569"/>'
    svg += _text(25,330,'',11,'data-rk-triangle-note=""')+'</g></svg>'
    return svg


def _candidates(case,state):
    n,max_error = case['inputs']['dimension'],case['exact_expectation'][0]
    width = 630/n
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 360" role="img" aria-label="Every possible row direction: next squared error and selection probability" data-rk-candidates=""><rect width="760" height="360" rx="14" fill="#f7f9fc"/>'
    svg += _text(65,27,'Possible next error² · fix the same input point',15)
    for v in [0,max_error/2,max_error]:
        y = 270-200*v/max_error
        svg += f'<path d="M65,{y} H695" stroke="#d5dfea"/>'+_text(30,y+4,f'{v:g}',12)
    for j,d in enumerate(state['directions']):
        h = 200*d['squared_error']/max_error
        x = 65+width*j
        count = len(d['row_indices'])
        svg += f'<rect data-rk-candidate="{j}" x="{x+width*.16}" y="{270-h}" width="{width*.68}" height="{h}" fill="#2563eb"/>'
        svg += f'<circle data-rk-candidate-marker="{j}" cx="{x+width/2}" cy="{270-h}" r="6" fill="#d97706" style="display:none"/>'
        svg += _text(x+width/2,292,f'e{j+1}',13,'text-anchor="middle"')
        svg += _text(x+width/2,313,f'p={count}/{case["inputs"]["equations"]}',11,'text-anchor="middle"')
    y = 270-200*state['conditional_squared_error']/max_error
    svg += f'<line data-rk-conditional-line="" x1="65" x2="695" y1="{y}" y2="{y}" stroke="#0f766e" stroke-width="2" stroke-dasharray="7 4"/>'
    return svg+_text(65,341,'Dashed: probability-weighted mean · orange: actual selected direction',12)+'</svg>'


def proof_html(case):
    proof = case['conditional_projection']
    initial = next(s for s in proof['states'] if s['x']==case['inputs']['start'])
    body = '<div class="rk-proof" data-rk-proof="" data-current-step="0" data-current-seed="0" data-state-key="'+initial['key']+'"><h3>'+bi('오차가 줄어드는 이유: 한 단계의 조건부 평균','Why error shrinks: one conditional average')+'</h3>'
    body += '<p>'+bi('k≥1에서는 방금 완료한 투영의 이전점을 고정합니다. 오른쪽은 그 점에서 각각의 행을 뽑았을 때 가능한 결과입니다. 주황은 실제로 선택한 방향이며 나머지는 가상 후보입니다. k=0에는 아직 선택한 행이 없습니다.','At k≥1, fix the input to the completed projection. The right chart enumerates possible outcomes from that same input; orange marks the actual selected direction. Other outcomes are hypothetical. At k=0, no row has been selected.')+'</p>'
    body += '<div class="rk-proof-grid"><div>'+_triangle(case['exact_expectation'][0])+'</div><div class="rk-proof-candidates">'+_candidates(case,initial)+'</div></div>'
    body += '<p class="small">'+bi('왼쪽은 실제 오차 벡터를 직교축으로 표현한 삼각형입니다. 가로는 제거된 오차, 세로는 남은 오차이며 두 축의 배율은 같습니다. 원래 x좌표 그림은 위에 있습니다. 길이 0인 변이 있으면 직각 표시를 생략합니다.','The left triangle uses orthogonal error coordinates: removed error horizontally and remaining error vertically, with equal scales. The original x-coordinate view is above. Zero-length legs suppress the right-angle mark.')+'</p>'
    body += '<div class="rk-proof-status" data-rk-proof-status>'+escape(f'k=0: input={initial["x"]}; no selected row\nconditional E(next error²)={initial["conditional_squared_error"]}; conditional upper={initial["theorem_conditional_upper"]}')+'</div>'
    body += '<div class="formula">||old error||² = ||remaining error||² + ||removed error||²\nE(removed² | before) = ||A·before−b||² / ||A||F²\nE(next error² | before) ≤ (1−σ_min²/||A||F²) · ||before−x*||²</div>'
    body += '<p>'+bi('초록 점선은 가능한 행 전체에 대한 한 단계의 조건부 평균입니다. 위의 여러 시드로 구한 표본 평균과 다릅니다. 이 공개 구성에서는 조건부 상계도 같아집니다. 이미 오차가 0이면 다음 오차는 모두 0이고 수축비는 미정의로 남깁니다.','The green dashed line is a one-step conditional mean over all possible rows. It differs from the finite-seed mean above. These published constructions also attain the conditional upper bound. At zero error all next errors are zero, while the contraction ratio remains undefined.')+'</p>'
    body += '<p class="small">'+bi('출처: Theorem 2 증명, 식 (8)–(9), 프리프린트 pp.5–6. 투영의 직교성 → 조건부 평균 → 전체 기대값의 반복 순서입니다. 다음 표의 후보는 추가로 실행한 궤도가 아닙니다.','Source: Theorem 2 proof, Eqs. (8)–(9), preprint pp.5–6. Orthogonal projection leads to a conditional average, then iteration of the full expectation. Candidate projections below are not additional sampled trajectories.')+'</p>'
    body += '<details><summary>'+bi('기록된 모든 입력 상태의 후보·확률·직교성','Every recorded input state: candidate rows, probabilities and orthogonality')+'</summary>'
    for state in proof['states']:
        body += '<details data-rk-proof-state="'+state['key']+'"><summary>x='+escape(str(state['x']))+' · E(next²)='+format(state['conditional_squared_error'],'.9g')+'</summary><div class="rk-proof-table"><table><thead><tr><th>Row</th><th>p</th><th>Candidate</th><th>Remaining²</th><th>Removed²</th><th>Dot</th></tr></thead><tbody>'
        for row in state['outcomes']:
            body += '<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in [row['row_index'],row['probability'],row['next'],row['squared_error'],row['squared_step'],row['inner_product']])+'</tr>'
        body += '</tbody></table></div></details>'
    return body+'</details></div>'
