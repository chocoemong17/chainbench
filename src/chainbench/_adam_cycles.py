"""Three-round reading of stored paths, without recomputing the optimizer."""
from ._pages import bi

FIELDS = ('gradient', 'memory', 'effective_rate', 'displacement', 'projection', 'regret_increment')


def block_values(case, method, t):
    start = 3*((t-1)//3)
    stop = min(start+3, case['inputs']['steps'])
    run = case['runs'][method]
    s = run['series']
    rows = [dict(round=j+1, before=s['x'][j], proposal=s['proposal'][j], after=s['x'][j+1],
                 gradient=case['gradients'][j], memory=s['denominator_memory'][j],
                 effective_rate=s['effective_rate'][j], displacement=s['displacement'][j],
                 projection=s['projection_correction'][j], regret_increment=s['regret_increment'][j])
            for j in range(start, stop)]
    complete = run['complete_cycles'][start//3] if stop-start == 3 else None
    summary = dict(start_x=s['x'][start], end_x=s['x'][stop],
                   regret=complete['regret'] if complete else None,
                   source_lower=complete['source_lower'] if complete else None)
    return rows, summary


def _number(value):
    return 'not applicable / 해당 없음' if value is None else f'{value:.8e}'


def _cell(key, value):
    raw = 'null' if value is None else repr(value)
    return f'<span data-cycle-value="{key}" data-raw="{raw}">{_number(value)}</span>'


def block_panel(case, method, t=1):
    rows, summary = block_values(case, method, t)
    px = lambda x: 85+155*(x+2)  # noqa: E731
    body = f'<article data-adam-cycle-method="{method}"><h3>{method.upper()}</h3>'
    body += ('<div class="adam-figure" tabindex="0"><svg viewBox="0 0 800 310" role="img" '
             'aria-label="Three stored updates on the same fixed position axis">'
             '<rect width="800" height="310" rx="12" fill="#f7fafb"/>'
             '<text x="85" y="24" font-size="15">Stored block · shared position axis x</text>'
             '<rect x="240" y="47" width="310" height="192" fill="#e6f3ee"/>')
    for i in range(3):
        row = rows[i] if i < len(rows) else None
        v = row or dict(before=0., proposal=0., after=0.)
        y = 76+64*i
        hidden = '' if row else ' style="display:none"'
        body += f'<g data-cycle-step="{i}"{hidden}><rect data-cycle-highlight x="36" y="{y-25}" width="725" height="49" fill="#dce8fa" opacity="{.55 if row and row["round"] == t else 0}"/>'
        body += f'<text data-cycle-round x="77" y="{y+4}" text-anchor="end" font-size="12">t={row["round"] if row else ""}</text>'
        body += f'<path d="M85 {y} H705" stroke="#c6d2df"/>'
        body += f'<path data-cycle-move d="M{px(v["before"]):.6f} {y} H{px(v["after"]):.6f}" stroke="#334155" stroke-width="4"/>'
        body += f'<path data-cycle-clip d="M{px(v["proposal"]):.6f} {y+12} H{px(v["after"]):.6f}" stroke="#b45309" stroke-width="3"/>'
        for key, color, fill, dy in (('before','#2563eb','#2563eb',-6),('proposal','#b45309','white',0),('after','#0f766e','#0f766e',6)):
            body += f'<circle data-cycle-marker="{key}" cx="{px(v[key]):.6f}" cy="{y+dy}" r="5" stroke="{color}" fill="{fill}" stroke-width="2"/>'
        body += '</g>'
    for x in (-2,-1,0,1,2):
        body += f'<text x="{px(x)}" y="260" text-anchor="middle" font-size="12">{x}</text>'
    body += ('<text x="85" y="284" font-size="11">Blue: before · hollow amber: proposal · green: after · amber segment: clip</text>'
             '<text x="85" y="300" font-size="11">Dark segment: actual move · shaded interval: [−1,1] · highlighted row: selected t</text></svg></div>')
    body += '<div class="scroll" tabindex="0"><table style="white-space:nowrap;font-variant-numeric:tabular-nums"><caption>' + bi('각 회차의 부호와 실제 이동','Signed contributions and actual movement') + '</caption>'
    body += '<thead><tr><th>t</th><th>gₜ</th><th>memory</th><th>ηₜ</th><th>Δx</th><th>clip</th><th>ΔR</th></tr></thead><tbody>'
    for i in range(3):
        row = rows[i] if i < len(rows) else None
        hidden = '' if row else ' hidden'
        body += f'<tr data-cycle-row="{i}"{hidden}><th data-cycle-round>{row["round"] if row else ""}</th>'
        body += ''.join('<td>'+_cell(key, row[key] if row else None)+'</td>' for key in FIELDS) + '</tr>'
    body += '</tbody></table></div><dl class="adam-values">'
    for key, value in summary.items():
        body += f'<div><dt>{key}</dt><dd>{_cell(key,value)}</dd></div>'
    return body + '</dl></article>'


def cycle_section(result):
    first = result['cases'][0]
    stop = min(3, result['parameters']['steps'])
    body = '<section id="cycle-inspector"><h2>' + bi('세 걸음을 합치면 어디로 돌아올까?', 'Where do the three steps take us?') + '</h2><p>' + bi(
        '위의 사례·회차 선택기와 연결됩니다. 선택한 회차가 속한 세 회차 묶음을 보여 주며, 예산 안에서 이미 계산된 뒤 회차도 함께 표시합니다. 파란 강조 행이 선택 회차입니다. 두 방법과 모든 묶음의 위치축은 [−2,2]로 같습니다.',
        'Linked to the case and round controls above. This shows the block containing the selected round, including later rounds already computed within the budget. The blue highlight marks the selected round. Both methods and every block share the position axis [−2,2].') + '</p><p><a href="#round-inspector">' + bi('사례·회차 선택기로 이동','Go to case and round controls') + '</a></p>'
    body += '<p class="callout">' + bi(
        'g의 합이 양수라는 사실만으로 실제 이동의 방향을 알 수는 없습니다. ηₜ=αₜ/√memoryₜ가 회차마다 달라지기 때문입니다. Δx는 투영 후 이동, clip은 after−proposal, ΔR=gₜ(xₜ+1)은 이동 전에 지불한 regret 기여분입니다. 음의 ΔR도 그대로 보존합니다.',
        'A positive gradient sum alone does not determine the actual displacement: ηₜ=αₜ/√memoryₜ changes each round. Δx is the move after projection; clip is after−proposal; ΔR=gₜ(xₜ+1) is incurred before moving. Negative regret contributions remain visible.') + '</p>'
    body += '<div class="adam-controls"><label>' + bi('사례','Case') + ' <select data-cycle-select aria-label="Three-round block case">'
    body += ''.join(f'<option value="{c["id"]}">{c["id"]}</option>' for c in result['cases'])
    body += '</select></label><label>' + bi('묶음','Block') + f' <input data-cycle-block type="range" min="1" max="{(result["parameters"]["steps"]+2)//3}" value="1" aria-label="Three-round block"></label></div>'
    body += '<p class="small">' + bi('좁은 화면에서는 그림과 표 안을 좌우로 넘겨 전체를 읽으세요. 키보드로 초점을 맞춘 뒤 화살표 키로도 이동할 수 있습니다.', 'On narrow screens, scroll sideways inside each diagram and table. Focus a scroll region and use the arrow keys with a keyboard.') + '</p>'
    body += f'<p class="adam-inputs" data-cycle-label>{first["id"]} · t=1…{stop} · {stop}/3</p>'
    for method in ('adam','amsgrad'):
        body += block_panel(first, method)
    body += '<p class="small">' + bi(
        'regret은 저장된 완성 묶음의 세 기여분 합입니다. source_lower=2C−4는 Adam의 완성 묶음에만 적용됩니다. AMSGrad 또는 미완성 묶음은 해당 없음입니다. 아래 각 사례에는 스크립트 없이 읽는 첫 묶음도 있습니다.',
        'regret is the stored sum of the three contributions in a complete block. source_lower=2C−4 applies only to complete Adam blocks. It is not applicable to AMSGrad or incomplete blocks. Each case below also contains a native first-block view.') + '</p></section>'
    return body


CYCLE_SCRIPT = r"""
 const cyclePanels=[...document.querySelectorAll('#cycle-inspector [data-adam-cycle-method]')].map(p=>({
  method:p.dataset.adamCycleMethod,
  steps:[...p.querySelectorAll('[data-cycle-step]')].map(g=>({g,label:g.querySelector('[data-cycle-round]'),
   highlight:g.querySelector('[data-cycle-highlight]'),move:g.querySelector('[data-cycle-move]'),clip:g.querySelector('[data-cycle-clip]'),
   markers:[...g.querySelectorAll('[data-cycle-marker]')]})),
  rows:[...p.querySelectorAll('[data-cycle-row]')].map(r=>({r,label:r.querySelector('[data-cycle-round]'),values:[...r.querySelectorAll('[data-cycle-value]')]})),
  summary:[...p.querySelectorAll('dl [data-cycle-value]')]
 }));
 let lastCycle='';
 const cycleNumber=v=>v===null?'not applicable / 해당 없음':v.toExponential(8);
 const updateCycle=(c,t)=>{
  const start=3*Math.floor((t-1)/3),stop=Math.min(start+3,c.inputs.steps),key=c.id+':'+start;
  document.querySelector('[data-cycle-select]').value=c.id;
  document.querySelector('[data-cycle-block]').value=String(start/3+1);
  if(key!==lastCycle){
   document.querySelector('[data-cycle-label]').textContent=c.id+' · t='+(start+1)+'…'+stop+' · '+(stop-start)+'/3';
   for(const p of cyclePanels){
    const run=c.runs[p.method],s=run.series,cycle=stop-start===3?run.complete_cycles[start/3]:null;
    const summary={start_x:s.x[start],end_x:s.x[stop],regret:cycle?cycle.regret:null,source_lower:cycle?cycle.source_lower:null};
    for(const node of p.summary){const v=summary[node.dataset.cycleValue];node.dataset.raw=v===null?'null':String(v);node.textContent=cycleNumber(v);}
    for(let i=0;i<3;i++){
     const j=start+i,g=p.steps[i],row=p.rows[i],visible=j<stop;
     g.g.style.display=visible?'':'none';row.r.hidden=!visible;
     if(!visible)continue;
     g.label.textContent='t='+(j+1);row.label.textContent=String(j+1);
     const v={gradient:c.gradients[j],memory:s.denominator_memory[j],effective_rate:s.effective_rate[j],
      displacement:s.displacement[j],projection:s.projection_correction[j],regret_increment:s.regret_increment[j],
      before:s.x[j],proposal:s.proposal[j],after:s.x[j+1]};
     for(const node of row.values){const value=v[node.dataset.cycleValue];node.dataset.raw=String(value);node.textContent=cycleNumber(value);}
     const px=x=>85+155*(x+2),y=76+64*i;
     for(const node of g.markers)node.setAttribute('cx',px(v[node.dataset.cycleMarker]).toFixed(6));
     g.move.setAttribute('d',`M${px(v.before).toFixed(6)} ${y} H${px(v.after).toFixed(6)}`);
     g.clip.setAttribute('d',`M${px(v.proposal).toFixed(6)} ${y+12} H${px(v.after).toFixed(6)}`);
    }
   }
   lastCycle=key;
  }
  for(const p of cyclePanels)for(let i=0;i<3;i++)p.steps[i].highlight.setAttribute('opacity',start+i+1===t?'.55':'0');
 };
"""
