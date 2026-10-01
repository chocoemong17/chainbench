"""Offline navigation through every accepted update and rejected FISTA trial."""
from __future__ import annotations

import json
from html import escape

from ._backtracking_figures import model_svg, path_svg, proposal_svg
from ._pages import bi, evidence, page

STYLE = '''
html{scroll-behavior:auto}.bt-controls,.bt-shortcuts{display:none}.bt-enabled .bt-controls,.bt-enabled .bt-shortcuts{display:flex}
.bt-controls{position:sticky;top:0;z-index:4;padding:12px;background:#edf3fc;border:1px solid #c7d6eb;border-radius:12px;gap:10px;flex-wrap:wrap;align-items:center}
.bt-controls label{display:flex;gap:6px;align-items:center;font-size:13px}.bt-controls select{max-width:100%}
.bt-controls input{max-width:180px}.bt-figure{overflow-x:auto}.bt-figure svg{display:block;width:100%;min-width:580px}
.bt-flow{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;padding:0;list-style-position:inside}
.bt-flow li{padding:14px;background:#edf3fc;border-radius:12px}.bt-flow strong{display:block}
.bt-summary{overflow-wrap:anywhere}.bt-native table{min-width:1250px}.bt-native tr{scroll-margin-top:130px}.bt-native tr:target{background:#fff2d8}
@media(max-width:760px){.bt-flow{grid-template-columns:1fr}.bt-controls{position:static}.bt-controls label{flex-wrap:wrap}.bt-controls select{max-width:310px}}
@media print{.bt-controls{display:none!important}.bt-figure svg{min-width:0}.bt-native{overflow:visible}}
'''

SCRIPT = '''
'use strict';
const btRecord=JSON.parse(document.getElementById('chainbench-evidence').textContent);
const btCases=Array.from(document.querySelectorAll('[data-bt-case]'));
const btChoice=document.getElementById('bt-case'),btStep=document.getElementById('bt-step'),btTrial=document.getElementById('bt-trial');
const btCache=new Map();
btCases.forEach(el=>el.querySelectorAll('[data-bt-values],[data-bt-labels]').forEach(node=>{
 btCache.set(node,{values:node.dataset.btValues?JSON.parse(node.dataset.btValues):null,
  labels:node.dataset.btLabels?JSON.parse(node.dataset.btLabels):null});
}));
const btNumber=v=>Number(v).toPrecision(6),btVector=v=>'('+v.map(btNumber).join(', ')+')';
function btUpdate(resetTrial=false){
 const i=Number(btChoice.value),c=btRecord.cases[i],k=Number(btStep.value),s=c.stages[k-1];
 let j=resetTrial?0:Math.min(Number(btTrial.value)||0,s.trials.length-1);
 btTrial.replaceChildren(...s.trials.map((v,index)=>{const option=document.createElement('option');
  option.value=index;option.textContent=`${index+1} / ${s.trials.length} · L=${v.L} · ${v.accepted?'✓':'×'}`;return option;}));
 btTrial.value=j;
 const trial=s.trials[j],flat=c.stages.slice(0,k-1).reduce((n,v)=>n+v.trials.length,0)+j;
 btCases.forEach((el,n)=>{el.hidden=n!==i;});
 const el=btCases[i];el.dataset.btCurrentStep=k;el.dataset.btCurrentTrial=j;
 el.querySelectorAll('[data-bt-dynamic]').forEach(node=>{
  node.setAttribute(node.dataset.btAttribute,btCache.get(node).values[flat]);
  if(node.dataset.btLabels)node.textContent=btCache.get(node).labels[flat];
 });
 el.querySelectorAll('[data-bt-text]').forEach(node=>{node.textContent=btCache.get(node).values[flat];});
 el.querySelector('[data-bt-summary]').textContent=`k=${k} · trial=${j+1}/${s.trials.length} · carried L=${s.carried_L} · trial L=${trial.L} · 1/L=${btNumber(trial.step_size)} · λ/L=${btNumber(trial.threshold)}`;
 el.querySelector('[data-bt-vectors]').textContent=`y=${btVector(s.anchor)} → z=${btVector(trial.gradient_step)} → q=${btVector(trial.point)}`;
 el.querySelector('[data-bt-gate]').textContent=`F(q)−Q_L(q,y)=${btNumber(trial.stable_model_difference)} · raw F−Q=${btNumber(trial.raw_model_difference)} · ${trial.accepted?'채택 / accepted':'거부 / rejected'}`;
 el.querySelector('[data-bt-gate]').dataset.btAccepted=String(trial.accepted);
 el.querySelector('[data-bt-gaps]').textContent=`F(q)−F*=${btNumber(trial.stable_gap)} · Q_L(q,y)−F*=${btNumber(trial.stable_model_gap)} · F(y)−F*=${btNumber(s.anchor_gap)} · F(x_{k−1})−F*=${btNumber(s.previous_gap)}`;
 const native=el.querySelector('[data-bt-native-link]');native.href=`#bt-${c.id}-k${k}-j${j}`;
 document.getElementById('bt-step-label').textContent=`k=${k} / ${btRecord.parameters.steps}`;
 document.dispatchEvent(new CustomEvent('chainbench:backtracking',{detail:{caseId:c.id,step:k,trial:j}}));
}
btChoice.addEventListener('change',()=>btUpdate(true));
btStep.addEventListener('input',()=>btUpdate(true));
btTrial.addEventListener('change',()=>btUpdate());
document.querySelectorAll('[data-bt-jump]').forEach(button=>button.addEventListener('click',()=>{
 btStep.value=button.dataset.btJump;btUpdate(true);
 document.querySelector('[data-bt-case]:not([hidden]) [data-bt-summary]').focus();
}));
document.documentElement.classList.add('bt-enabled');btUpdate(true);
'''


def _numbers(values):
    return '('+', '.join(f'{v:.6g}' for v in values)+')'


def _native(case):
    body = '<details class="bt-native"><summary>'+bi('모든 단계·후보의 수치 표', 'Every step and trial, including rejections')+'</summary>'
    body += '<p class="small">'+bi('표는 가로로 스크롤할 수 있습니다. k는 채택된 갱신 번호, j는 그 안의 시도 번호입니다. y와 z, q는 서로 다른 점입니다.',
        'Scroll the table horizontally. k counts accepted updates; j counts trials within that update. y, z and q are distinct points.')+'</p>'
    body += '<div class="scroll" tabindex="0" role="region" aria-label="All recorded FISTA trial values"><table><caption>'+escape(case['id'])+'</caption><thead><tr>'
    body += ''.join('<th scope="col">'+v+'</th>' for v in ('k / j','L / 1/L','λ/L','y','z = y−∇f/L','q = soft(z,λ/L)','F(q)−Q','raw F−Q','decision','F(q)−F*','Q−F*'))+'</tr></thead><tbody>'
    for stage in case['stages']:
        for trial in stage['trials']:
            body += f'<tr id="bt-{case["id"]}-k{stage["iteration"]}-j{trial["attempt"]}" data-bt-native-row="">'
            values = [f'{stage["iteration"]} / {trial["attempt"]+1}',f'{trial["L"]:.8g} / {trial["step_size"]:.8g}',
                f'{trial["threshold"]:.8g}',_numbers(stage['anchor']),_numbers(trial['gradient_step']),_numbers(trial['point']),
                f'{trial["stable_model_difference"]:.8g}',f'{trial["raw_model_difference"]:.8g}',
                'accepted' if trial['accepted'] else 'rejected',f'{trial["stable_gap"]:.8g}',f'{trial["stable_model_gap"]:.8g}']
            body += ''.join('<td>'+escape(v)+'</td>' for v in values)+'</tr>'
    body += '</tbody></table></div></details>'
    body += '<details><summary>'+bi('채택된 경로와 이론 상한', 'Accepted path and source envelope')+'</summary><div class="scroll"><table><thead><tr>'
    body += ''.join('<th scope="col">'+v+'</th>' for v in ('k','x_k','F(x_k)−F*','raw F−F*','Δ gap','36 R²/(k+1)²'))+'</tr></thead><tbody>'
    for row in case['rows']:
        values = [str(row['iteration']),_numbers(row['x']),f'{row["stable_gap"]:.8g}',f'{row["raw_gap"]:.8g}',
            'undefined' if row['stable_gap_change'] is None else f'{row["stable_gap_change"]:.8g}',
            'not applied at k=0' if row['bound'] is None else f'{row["bound"]:.8g}']
        body += '<tr>'+''.join('<td>'+escape(v)+'</td>' for v in values)+'</tr>'
    return body+'</tbody></table></div></details>'


def _case(case):
    s,trial = case['stages'][0],case['stages'][0]['trials'][0]
    body = f'<section data-bt-case="{case["id"]}" id="case-{case["id"]}"><h2>'+escape(case['id'])+'</h2>'
    body += '<p class="formula">a=(1,3) · b=(1.4,−2.4) · λ='+str(case['inputs']['lambda'])+' · x₀='+_numbers(case['inputs']['x0'])+' · L₀='+str(case['inputs']['initial_L'])+' · η=2</p>'
    body += '<p class="small">x*='+_numbers(case['optimum']['point'])+f' · F*={case["optimum"]["value"]:.8g} · R²={case["radius_squared"]:.8g} · N={case["updates"]}'+'</p>'
    body += '<div class="callout bt-summary"><p tabindex="-1" data-bt-summary>'+f'k=1 · trial=1/{len(s["trials"])} · carried L={s["carried_L"]} · trial L={trial["L"]} · 1/L={trial["step_size"]:.6g} · λ/L={trial["threshold"]:.6g}</p>'
    body += '<p data-bt-vectors>y='+_numbers(s['anchor'])+' → z='+_numbers(trial['gradient_step'])+' → q='+_numbers(trial['point'])+'</p>'
    body += '<p data-bt-gate data-bt-accepted="'+str(trial['accepted']).lower()+'">'+f'F(q)−Q_L(q,y)={trial["stable_model_difference"]:.6g} · raw F−Q={trial["raw_model_difference"]:.6g} · '+('채택 / accepted' if trial['accepted'] else '거부 / rejected')+'</p>'
    body += '<p data-bt-gaps>'+f'F(q)−F*={trial["stable_gap"]:.6g} · Q_L(q,y)−F*={trial["stable_model_gap"]:.6g} · F(y)−F*={s["anchor_gap"]:.6g} · F(x_{{k−1}})−F*={s["previous_gap"]:.6g}'+'</p>'
    body += f'<a data-bt-native-link href="#bt-{case["id"]}-k1-j0">'+bi('선택한 후보의 원본 표로 이동', 'Open this trial in the native table')+'</a></div>'
    changes = [v for v in case['observations']['accepted_L_changes'] if v['iteration']>1]
    if changes:
        body += '<p class="bt-shortcuts"><button type="button" data-bt-jump="'+str(changes[0]['iteration'])+'">'+bi('처음으로 L을 다시 키운 단계 보기', 'First later increase of accepted L')+'</button></p>'
    increases = case['observations']['objective_increase_rounds']
    if increases:
        body += '<p class="bt-shortcuts"><button type="button" data-bt-jump="'+str(increases[0])+'">'+bi('채택된 목적값이 처음 증가한 단계 보기', 'First accepted objective increase')+'</button></p>'
    body += '<p>'+bi('초록 경로는 채택된 x만 잇습니다. 보라 점은 현재 단계의 외삽점 y입니다. 오른쪽 두 패널에서 거부된 후보까지 살펴보세요. 경로의 선분은 저장된 점 사이의 연결이며 연속 이동을 뜻하지 않습니다.',
        'Green paths join accepted x only; purple marks this step’s extrapolated y. Inspect rejected candidates in the proposal and model panels. Path chords connect saved points; they are not continuous motion.')+'</p>'
    body += '<div class="visual-grid">'+''.join('<div class="bt-figure">'+svg+'</div>' for svg in
        (path_svg(case),path_svg(case,surface=True),proposal_svg(case),model_svg(case)))+'</div>'
    body += '<p class="small">'+bi('경로 창은 두 좌표 모두 −3.5~3.5이며, 등고선만 창에서 잘립니다. 모든 경로 점과 외삽점은 창 안에 있습니다. 후보 그림은 모든 시도를 담도록 단계마다 축을 바꾸고, 모형 그림은 선택한 시도마다 높이 축을 바꿉니다. 겹친 후보 번호의 좌표는 아래 표에서 확인할 수 있습니다.',
        'The path window is [−3.5,3.5]²; only contours are clipped. All path and anchor points fit. The proposal axes refit per step to retain all attempts; model heights refit per trial. The table resolves overlapping proposal labels.')+'</p>'
    body += '<p>'+bi('이 실행의 전체 후보 수 / 거부 수:', 'Total trials / rejected trials in this run:')+f' {case["observations"]["total_trials"]} / {case["observations"]["rejected_trials"]}. '+bi('후보 수는 실행 시간이나 동일 비용의 반복 횟수가 아닙니다.', 'Trial counts are not timings or equal-cost iteration counts.')+'</p>'
    body += '<p class="small">'+bi('목적값 증가 이동 버튼은 gap 증가가 10⁻¹²보다 큰 첫 단계를 가리킵니다. 이 기준은 채택 판정에 사용하지 않습니다.',
        'The increase shortcut selects the first gap increase above 10⁻¹²; this display threshold never controls acceptance.')+'</p>'
    return body+_native(case)+'</section>'


def fista_backtracking_html(data: dict, lang: str = 'en') -> str:
    if data.get('kind')!='chainbench.fista-backtracking-geometry' or len(data.get('cases',[]))!=36:
        raise ValueError('expected all 36 FISTA backtracking runs')
    if len({c['id'] for c in data['cases']})!=36:
        raise ValueError('duplicate FISTA backtracking case')
    json.dumps(data,allow_nan=False)
    body = '<style>'+STYLE+'</style><section><h2>'+bi('어떤 이동 크기를 받아들일까?', 'Which trial step can we accept?')+'</h2>'
    body += '<p>'+bi('L을 크게 잡으면 이동 크기 1/L은 작아집니다. FISTA는 외삽점 y에서 후보 q를 계산하고, 실제 함수가 근사함수 Q_L 이하인지 검사합니다. 거부되면 같은 y에서 L을 두 배로 늘려 다시 시도합니다.',
        'Larger L means a smaller step 1/L. At the extrapolated y, FISTA computes a candidate q and checks whether its objective is at most its model Q_L. A rejection doubles L and retries from the same y.')+'</p>'
    flow = [('외삽점에서 시작','Start at the anchor','y_k'),('기울기만큼 이동','Gradient step','z=y_k−∇f(y_k)/L'),
        ('작은 좌표를 축소','Shrink coordinates','q=soft(z,λ/L)'),('실제 함수와 모형 비교','Test the candidate','F(q)≤Q_L(q,y_k)?'),
        ('채택하거나 다시 시도','Accept or retry','yes: x_k=q; no: L←2L')]
    body += '<ol class="bt-flow">'+''.join('<li><strong>'+bi(ko,en)+'</strong><code>'+escape(formula)+'</code></li>' for ko,en,formula in flow)+'</ol>'
    body += '<p class="formula">Q_L(u,y)=f(y)+∇f(y)ᵀ(u−y)+(L/2)||u−y||²+λ||u||₁<br>t_next=(1+√(1+4t²))/2<br>y_next=x_k+((t−1)/t_next)(x_k−x_{k−1})</p>'
    body += '<p>'+bi('채택한 L은 다음 단계로 이어집니다. 이 화면에서는 L을 다시 초기화하거나 줄이지 않습니다. 후보에서의 통과는 함수 전체의 상한 인증이나 이전 x보다 목적값이 작다는 뜻이 아닙니다.',
        'The accepted L is carried to the next step; it is never reset or decreased here. Passing at the candidate does not certify a global upper model or descent from the previous x.')+'</p>'
    body += '<div class="callout"><strong>'+bi('12개 입력 × 3개 초기 추정 = 36개 실행', '12 inputs × 3 initial guesses = 36 complete runs')+'</strong><p>'+bi('λ 3종과 시작점 4종의 모든 조합을, L₀=0.25,1,4에서 실행합니다. 처음 3개 시작점은 기존 ISTA/FISTA 설명과 같으며, low-mode는 추가 입력입니다. 어느 실행도 결과에 따라 제외하지 않습니다.',
        'Every combination of three λ values and four starts runs with L₀=0.25,1,4. The first three starts match the existing ISTA/FISTA illustrations; low-mode is an additional input. No outcome is filtered.')+'</p></div>'
    body += '<p>'+bi('이 이차 문제에서는 F(q)−Q_L(q,y)=½Σ(aᵢ²−L)(qᵢ−yᵢ)²로 판정합니다. 별도의 허용 오차를 더하지 않으며, 직접 뺀 raw F−Q도 보존합니다. 아주 작은 차이에서는 두 판정이 반올림 때문에 달라질 수 있습니다.',
        'For this quadratic, the gate uses F(q)−Q_L(q,y)=½Σ(aᵢ²−L)(qᵢ−yᵢ)² with no added tolerance. Directly subtracted raw F−Q is retained; roundoff can change its decision near zero.')+'</p>'
    body += '<p>'+bi('상한은 k≥1에서 2ηL(f)R²/(k+1)²=36R²/(k+1)²입니다. 모든 초기 추정은 L(f)=9 이하이고 η=2입니다. 이는 유한한 입력에서 검사하는 논문 상한이며 매 단계의 우열을 정하지 않습니다.',
        'For k≥1, the source envelope is 2ηL(f)R²/(k+1)²=36R²/(k+1)². All initial guesses are at most L(f)=9 and η=2. Checking this envelope on finite inputs does not rank every iterate.')+'</p>'
    body += '<p class="small">'+bi('새로 만든 대각 LASSO 설명용 입력이며 원 논문의 영상 실험이 아닙니다. 여기서는 ½||Ax−b||²를 쓰고, 논문의 식 (1.3)은 ½가 없는 손실입니다.',
        'These are declared diagonal LASSO illustrations, not the original image experiment. This fixture uses ½||Ax−b||²; source Eq. (1.3) uses unhalved loss.')+'</p>'
    body += '<p><a href="https://www.tau.ac.il/~becka/FISTA.pdf">Beck–Teboulle (2009): backtracking panel p.194 / PDF 12; model Eqs. (2.5)–(2.6), p.189 / PDF 7; Theorem 4.4, p.195 / PDF 13</a></p></section>'
    body += '<nav class="bt-controls" aria-label="FISTA backtracking navigation"><label for="bt-case">'+bi('사례','Case')+'<select id="bt-case">'
    body += ''.join(f'<option value="{i}">{escape(c["id"])}</option>' for i,c in enumerate(data['cases']))+'</select></label>'
    body += '<label for="bt-step">'+bi('채택 갱신','Accepted update')+f'<input id="bt-step" type="range" min="1" max="{data["parameters"]["steps"]}" value="1" step="1"></label><output id="bt-step-label" for="bt-step"></output>'
    body += '<label for="bt-trial">'+bi('후보 시도','Trial')+'<select id="bt-trial"></select></label></nav>'
    body += '<noscript><p class="callout">'+bi('스크립트가 꺼져 있습니다. 모든 사례의 첫 후보 그림과 모든 단계의 수치 표를 아래에서 읽을 수 있습니다.',
        'Scripts are off. Each case shows its first trial; native tables retain every step and trial.')+'</p></noscript>'
    body += ''.join(_case(case) for case in data['cases'])+evidence(data,'fista-backtracking.json')
    return page('FISTA · Backtracking',bi('거부된 후보에서 채택된 이동까지', 'From rejected candidates to accepted updates'),
        body,lang=lang).replace('</body>','<script>'+SCRIPT+'</script></body>')
