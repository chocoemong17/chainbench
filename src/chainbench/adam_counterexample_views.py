"""Offline views of the stored online-loss paths; no browser-side optimizer."""
from __future__ import annotations

import json
from html import escape
from io import StringIO

from ._adam_cycles import CYCLE_SCRIPT, block_panel, cycle_section
from ._pages import bi, page

COLORS = {'adam': '#2563eb', 'amsgrad': '#0f766e'}


def _record_json(data):
    # A single multi-megabyte text line exceeds Chromium's layout extent when
    # the native details is opened. Group only JSON's structural line breaks;
    # escaped newlines inside string values stay untouched. Avoid millions of
    # one-number lines too, while retaining the full accessible/download text.
    output, width = StringIO(), 0
    for line in StringIO(json.dumps(data,ensure_ascii=False,indent=0,separators=(',',':'),allow_nan=False)):
        token = line.rstrip('\n')
        if width+len(token)>240:
            output.write('\n')
            width = 0
        output.write(token)
        width += len(token)
    return output.getvalue()


def _number(value):
    return 'undefined / 미정의' if value is None else f'{value:.8e}'


def path_svg(case, metric):
    """All computed points, a declared linear scale and scoped reference dots."""
    point = metric == 'x'
    values = [v for run in case['runs'].values() for v in run['series'][metric]]
    reference = case['source_reference']['average_regret_lower']
    low, high = (-1.1, 1.1) if point else (min(0., min(values)), max(reference, max(values))*1.05)
    steps = case['inputs']['steps']
    title = 'Position after each update' if point else 'Average online regret'
    ylabel = 'x_(k+1) · blue Adam / green AMSGrad' if point else 'R_t / t · blue Adam / green AMSGrad'
    body = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 310" role="img" aria-label="{title}" '
            f'data-adam-chart="{metric}" data-low="{low!r}" data-high="{high!r}">'
            '<rect width="800" height="310" rx="12" fill="#f7fafb"/>'
            f'<text x="85" y="25" font-size="16">{title}</text><text x="85" y="46" font-size="12">{ylabel}</text>'
            '<rect x="85" y="65" width="655" height="180" fill="white" stroke="#c6d2df"/>')
    py = lambda v: 245-180*(v-low)/(high-low)  # noqa: E731
    px = lambda t: 85+655*t/steps  # noqa: E731
    for f in (0, .25, .5, .75, 1):
        v = low+(high-low)*f
        body += f'<path d="M85 {py(v)} H740" stroke="#e4eaf0"/><text x="77" y="{py(v)+4}" text-anchor="end" font-size="11">{v:.3g}</text>'
    for method, run in case['runs'].items():
        ys = run['series'][metric]
        xs = range(len(ys)) if point else range(1, steps+1)
        points = ' '.join(f'{px(t):.3f},{py(v):.3f}' for t, v in zip(xs, ys))
        body += f'<polyline data-adam-path="{method}" points="{points}" fill="none" stroke="{COLORS[method]}" stroke-width="1.5"/>'
        if not point and steps == 1:
            body += f'<circle cx="{px(1):.3f}" cy="{py(ys[0]):.3f}" r="3" fill="{COLORS[method]}"/>'
    if not point:
        for t in case['source_reference']['rounds']:
            body += f'<circle data-adam-bound="{t}" cx="{px(t):.3f}" cy="{py(reference):.3f}" r="1.7" fill="#b45309"/>'
    for t in sorted({0, steps//2, steps}):
        body += f'<text x="{px(t)}" y="264" text-anchor="middle" font-size="12">{t}</text>'
    label = 'completed updates k · k=0 is the initial x₁' if point else 'round t · orange lower reference: Adam, t=3,6,… only · no value at t=0'
    return body + f'<text x="400" y="291" text-anchor="middle" font-size="11">{label}</text></svg>'


def stage_values(case, method, t):
    s, j = case['runs'][method]['series'], t-1
    return {
        'round': t, 'gradient': case['gradients'][j], 'before': s['x'][j],
        'loss': s['loss'][j], 'v_before': s['second_moment'][j-1] if j else 0.,
        'v': s['second_moment'][j], 'memory': s['denominator_memory'][j],
        'alpha_t': case['step_sizes'][j], 'effective_rate': s['effective_rate'][j],
        'inverse_change': s['inverse_rate_difference'][j], 'proposal': s['proposal'][j],
        'after': s['x'][j+1], 'projection': s['projection_correction'][j],
        'regret_increment': s['regret_increment'][j], 'average_regret': s['average_regret'][j],
    }


def _stage_svg(case, method, t):
    v = stage_values(case, method, t)
    # Fixed domain includes every proposal: |eta_t g_t| <= alpha/sqrt(1-beta2) < 1.
    px = lambda x: 70+165*(x+2)  # noqa: E731
    body = ('<svg viewBox="0 0 800 235" role="img" aria-label="Actual proposal and projection; second-moment memory">'
            '<rect width="800" height="235" rx="12" fill="#f7fafb"/>'
            '<text x="70" y="26" font-size="15">Actual round: incur loss → normalize → propose → project</text>'
            '<rect x="235" y="48" width="330" height="54" fill="#e6f3ee"/>'
            '<path d="M70 75 H730" stroke="#607086"/>')
    for x in (-2,-1,0,1,2):
        body += f'<text x="{px(x)}" y="121" text-anchor="middle" font-size="12">{x}</text>'
    for name, color, y, fill in (('before','#2563eb',65,'#2563eb'),('proposal','#b45309',75,'white'),('after','#0f766e',85,'#0f766e')):
        body += f'<circle data-adam-marker="{name}" cx="{px(v[name]):.6f}" cy="{y}" r="6" fill="{fill}" stroke="{color}" stroke-width="2"/>'
    body += (f'<path data-adam-projection d="M{px(v["proposal"]):.6f} 95 H{px(v["after"]):.6f}" stroke="#b45309" stroke-width="3"/>'
             '<text x="70" y="146" font-size="11">Blue: x_t · hollow amber: proposal · green: x_(t+1) · pale region: [−1,1]</text>')
    for name, y, color in (('v',164,'#2563eb'),('memory',192,'#0f766e')):
        width = 540*v[name]/case['inputs']['C']**2
        body += f'<text x="70" y="{y+12}" font-size="12">{name}/C²</text><rect x="170" y="{y}" width="540" height="16" fill="#e1e7ef"/><rect data-adam-memory="{name}" x="170" y="{y}" width="{width:.6f}" height="16" fill="{color}"/>'
    return body + '<text x="170" y="226" font-size="11">Fixed [0,1] scale · v is an exponential mean of g², not a centered variance</text></svg>'


SCRIPT = r"""(()=>{
 const data=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 const select=document.querySelector('[data-adam-select]'),slider=document.querySelector('[data-adam-round]');
 CYCLE_SCRIPT_PLACEHOLDER
 const number=v=>v===null?'undefined / 미정의':v.toExponential(8);
 const update=()=>{
  const c=data.cases.find(c=>c.id===select.value),t=Number(slider.value),j=t-1;
  document.querySelector('[data-adam-label]').textContent='t='+t+' / '+slider.max;
  document.querySelector('[data-adam-inputs]').textContent=c.id+' · C='+c.inputs.C+' · α='+c.inputs.alpha+' · β₂='+c.inputs.beta2;
  updateCycle(c,t);
  for(const panel of document.querySelectorAll('[data-adam-method]')){
   const s=c.runs[panel.dataset.adamMethod].series;
   const v={round:t,gradient:c.gradients[j],before:s.x[j],loss:s.loss[j],v_before:j?s.second_moment[j-1]:0,
    v:s.second_moment[j],memory:s.denominator_memory[j],alpha_t:c.step_sizes[j],effective_rate:s.effective_rate[j],
    inverse_change:s.inverse_rate_difference[j],proposal:s.proposal[j],after:s.x[j+1],projection:s.projection_correction[j],
    regret_increment:s.regret_increment[j],average_regret:s.average_regret[j]};
   for(const node of panel.querySelectorAll('[data-adam-value]')){
    const value=v[node.dataset.adamValue];node.textContent=number(value);node.dataset.raw=value===null?'null':String(value);
   }
   const px=x=>70+165*(x+2);
   for(const node of panel.querySelectorAll('[data-adam-marker]'))node.setAttribute('cx',px(v[node.dataset.adamMarker]).toFixed(6));
   panel.querySelector('[data-adam-projection]').setAttribute('d',`M${px(v.proposal).toFixed(6)} 95 H${px(v.after).toFixed(6)}`);
   for(const node of panel.querySelectorAll('[data-adam-memory]'))node.setAttribute('width',(540*v[node.dataset.adamMemory]/c.inputs.C**2).toFixed(6));
  }
 };
 slider.addEventListener('input',update);select.addEventListener('change',update);
 document.querySelector('[data-cycle-select]').addEventListener('change',e=>{select.value=e.target.value;update();});
 document.querySelector('[data-cycle-block]').addEventListener('input',e=>{slider.value=String(3*(Number(e.target.value)-1)+1);update();});
 for(const action of ['first','next','last'])document.querySelector('[data-adam-'+action+']').addEventListener('click',()=>{
  slider.value=action==='first'?'1':action==='last'?slider.max:String(Math.min(Number(slider.max),Number(slider.value)+1));update();
 });
 update();document.documentElement.classList.add('adam-js');
})();""".replace('CYCLE_SCRIPT_PLACEHOLDER', CYCLE_SCRIPT)


def adam_counterexample_html(result, lang='en'):
    first, steps = result['cases'][0], result['parameters']['steps']
    body = '''<style>
 .adam-controls{display:none;gap:10px;align-items:center;flex-wrap:wrap}.adam-js .adam-controls{display:flex}
 .adam-controls label{min-width:0;max-width:100%}.adam-controls select,.adam-controls input{max-width:100%}
 .adam-controls input{width:230px}.adam-flow{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
 .adam-flow article{padding:16px;background:#edf4fa;border-radius:12px}.adam-readout{font-family:monospace;overflow-wrap:anywhere}
 .adam-figure{overflow:auto;margin:16px 0}.adam-figure svg{display:block;width:100%;min-width:640px;height:auto}
 .adam-values{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.adam-values div{padding:10px;background:#f1f5f9;border-radius:8px;overflow-wrap:anywhere}
 .adam-values dt{font-size:12px}.adam-values dd{margin:0;font:12px monospace}.adam-inputs{overflow-wrap:anywhere}
 #chainbench-evidence{max-height:32rem;overflow:auto}
 @media(max-width:700px){.adam-flow{grid-template-columns:1fr 1fr}.adam-values{grid-template-columns:1fr 1fr}}
 </style><section><span class="badge">Reddi · Kale · Kumar / ICLR 2018 / Theorem 1</span><h2>'''
    body += bi('기억이 짧으면, 어느 쪽으로 움직일까?', 'When memory fades, which way do we move?') + '</h2><p>' + bi(
        '큰 양의 기울기 한 번과 작은 음의 기울기 두 번이 반복됩니다. 양의 기울기는 왼쪽으로, 음의 기울기는 오른쪽으로 움직이게 합니다. Adam은 큰 기울기의 기억을 빠르게 잊어 다음 두 걸음을 크게 만들 수 있습니다. AMSGrad는 분모에 쓰는 기억의 최댓값을 유지합니다.',
        'One large positive gradient is followed by two small negative gradients. Positive gradients move left; negative gradients move right. Adam can quickly forget the large squared gradient, enlarging the next two steps. AMSGrad retains the largest denominator memory.') + '</p>'
    body += '<div class="formula">F=[−1,1] · x₁=1 · gₜ=C if t≡1 (mod 3), otherwise −1\nfₜ(x)=gₜx · β₁=0 · β₂=1/(1+C²) · αₜ=α/√t\nC∈{3,10,100} · α / √(1−β₂)∈{0.1,0.5,0.9}</div><p class="callout caution">' + bi(
        '논문의 분석용 변형입니다: 편향 보정 없음, ε=0, 구간으로 투영. 정리 1의 입력군을 9개 설정으로 실행하며, 별도의 101주기 Figure 1 실험이나 신경망 학습을 재현하는 화면이 아닙니다.',
        'Paper analysis variant: no moment debiasing, ε=0, interval projection. These nine declared inputs instantiate Theorem 1, distinct from the period-101 Figure 1 experiment or neural-network training.') + '</p><div class="adam-flow">'
    for title, ko, en in (
        ('1 · LOSS','갱신 전 xₜ에서 gₜxₜ를 지불합니다.','Incur gₜxₜ at the pre-update point.'),
        ('2 · MEMORY','vₜ=β₂vₜ₋₁+(1−β₂)gₜ². AMSGrad는 max(v̂ₜ₋₁,vₜ).','vₜ=β₂vₜ₋₁+(1−β₂)gₜ². AMSGrad uses max(v̂ₜ₋₁,vₜ).'),
        ('3 · PROPOSE','분모의 제곱근으로 보폭을 나누고 −gₜ 방향으로 이동합니다.','Divide the step size by the memory square root and move along −gₜ.'),
        ('4 · PROJECT','제안이 [−1,1] 밖이면 가장 가까운 끝점으로 옮깁니다.','Clip an infeasible proposal to the nearest interval endpoint.'),
    ):
        body += f'<article><h3>{title}</h3><p>{bi(ko,en)}</p></article>'
    body += '</div></section><section><h2>' + bi('손실을 하나의 목적함수로 읽지 않기', 'Changing losses and the fixed comparator') + '</h2><p>' + bi(
        '매 시점마다 함수가 바뀝니다. 모든 접두 구간의 기울기 합은 양수이므로, 미리 하나만 정해 계속 쓰는 최선의 점은 −1입니다. 누적 regret은 그 점보다 지불한 손실의 차이입니다. 한 회의 차이는 음수일 수 있으며, T=0의 평균은 미정의입니다.',
        'The function changes each round. Every prefix has a positive gradient sum, so the best single fixed point in hindsight is −1. Regret measures excess cumulative loss over that comparator. One round can contribute negatively; the average at T=0 is undefined.') + '</p><div class="formula">R_T = Σₜ gₜxₜ − minₓ Σₜ gₜx = Σₜ gₜ(xₜ+1)\nAdam: R_(3j)/(3j) ≥ 2(C−2)/3 &gt; 0 · complete blocks only</div><p>' + bi(
        '논문은 이 조건에서 Adam의 regret 평균이 0으로 가지 않는 반례를 증명합니다. 아래 유한 실행의 확인은 그 증명을 대신하지 않습니다. AMSGrad의 유한 경로와 이 하한을 혼동하지 마세요. 기본 3,000회에서도 C=3, 비율 0.1인 AMSGrad는 아직 −1에서 멉니다.',
        'The paper proves non-vanishing average regret for Adam under these conditions. Checking finite paths does not replace that proof. The lower reference does not apply to AMSGrad. At the default 3,000 rounds, AMSGrad with C=3 and fraction 0.1 is still far from −1.') + '</p></section>'
    body += '<section id="round-inspector"><h2>' + bi('같은 입력에서 두 기억을 나란히 보기', 'Inspect both memories on the same input') + '</h2><p>' + bi(
        '선택기는 저장된 계산값을 표시합니다. 그래프의 수평축은 항상 [−2,2]이고, 막대는 C²로 나눈 같은 척도입니다. 좁은 화면에서는 그림 안을 좌우로 스크롤하세요. 아래 기본 표와 원본 JSON은 스크립트 없이도 읽을 수 있습니다.',
        'Controls display stored computed values. Number lines always span [−2,2]; memory bars share a C²-normalized scale. Scroll inside figures on narrow screens. Native tables and the full JSON remain readable without scripts.') + '</p><div class="adam-controls"><label>' + bi('사례','Case') + ' <select data-adam-select aria-label="Counterexample case">'
    for c in result['cases']:
        body += f'<option value="{c["id"]}">{c["id"]}</option>'
    body += '</select></label><button data-adam-first>1</button><label>t <input data-adam-round type="range" min="1" max="' + str(steps) + '" value="1" aria-label="Online loss round"></label><output data-adam-label>t=1</output><button data-adam-next>+1</button><button data-adam-last>' + bi('마지막','Last') + '</button></div>'
    body += f'<p class="adam-inputs" data-adam-inputs>{first["id"]} · C={first["inputs"]["C"]} · α={first["inputs"]["alpha"]} · β₂={first["inputs"]["beta2"]}</p>'
    for method in COLORS:
        body += f'<article data-adam-method="{method}"><h3>{method.upper()}</h3><div class="adam-figure" tabindex="0">{_stage_svg(first,method,1)}</div><dl class="adam-values">'
        for key, value in stage_values(first, method, 1).items():
            raw = 'null' if value is None else repr(value)
            body += f'<div><dt>{key}</dt><dd data-adam-value="{key}" data-raw="{raw}">{_number(value)}</dd></div>'
        body += '</dl></article>'
    body += '<p class="small">' + bi(
        'inverse_change = √memoryₜ/αₜ − √memoryₜ₋₁/αₜ₋₁. 첫 회는 이전 학습률이 없어 미정의입니다. 음수이면 정규화된 학습률이 증가한 것입니다. proposal과 after의 차이가 투영 보정입니다.',
        'inverse_change = √memoryₜ/αₜ − √memoryₜ₋₁/αₜ₋₁. Round 1 has no previous learning rate and is undefined. A negative value means the effective learning rate increased. The difference between proposal and after is the projection correction.') + '</p></section>'
    body += cycle_section(result)
    body += '<section><h2>' + bi('9개 설정을 모두 비교하기','Compare all nine settings') + '</h2><p>' + bi(
        '각 그래프는 모든 계산점을 포함합니다. x 그래프의 k=0은 초기점이고 regret 그래프에는 t=0이 없습니다. 두 방법은 같은 사례 안에서 같은 축을 씁니다. 사례별 regret 세로축 범위는 표시된 눈금으로 확인하세요. 주황 점은 완성된 3회 묶음에만 놓입니다.',
        'Every computed point is included. Position includes initial k=0; regret has no t=0. Both methods share axes within each case. Read the regret ticks for each case’s range. Orange reference dots appear only at completed three-round blocks.') + '</p>'
    for case in result['cases']:
        body += f'<details data-adam-case="{case["id"]}"><summary>{case["id"]} · α={case["inputs"]["alpha"]:.6g} · β₂={case["inputs"]["beta2"]:.6g}</summary>'
        body += '<details data-adam-native-cycle><summary>' + bi('첫 묶음의 세 걸음 · 스크립트 없이 읽기','First-block steps · native view without scripts') + '</summary>'
        body += ''.join(block_panel(case,method) for method in COLORS) + '</details>'
        for metric in ('x','average_regret'):
            body += '<div class="adam-figure" tabindex="0">' + path_svg(case, metric) + '</div>'
        body += '<div class="scroll"><table><caption>' + bi('선택한 실제 회차의 기본 표 · 전체 회차는 원본 JSON','Native selected-round table · all rounds are in the full JSON') + '</caption><tr><th>method</th><th>t</th><th>g</th><th>xₜ</th><th>gₜxₜ</th><th>memory</th><th>proposal</th><th>xₜ₊₁</th><th>Rₜ/t</th></tr>'
        for method in COLORS:
            for t in case['native_rounds']:
                v = stage_values(case,method,t)
                body += f'<tr data-adam-native="{method}:{t}"><td>{method}</td><td>{t}</td>' + ''.join(f'<td>{_number(v[k])}</td>' for k in ('gradient','before','loss','memory','proposal','after','average_regret')) + '</tr>'
        body += '</table></div><details><summary>' + bi('입력과 유한 관측','Inputs and finite observations') + '</summary><pre>' + escape(json.dumps({'inputs':case['inputs'],'input_sha256':case['input_sha256'],'observations':{m:r['observations'] for m,r in case['runs'].items()}},ensure_ascii=False,indent=2)) + '</pre></details></details>'
    body += '</section><section><h2>' + bi('출처와 재현 범위','Source and reproduction scope') + '</h2><p><a href="' + result['source']['url'] + '">Reddi, Kale &amp; Kumar · On the Convergence of Adam and Beyond</a> · ICLR 2018 · arXiv v1 (2019-04-19)</p><p>' + bi(
        'Algorithm 1·각주 1(p.3), 정리 1(p.4), 부록 A(pp.10–11), AMSGrad Algorithm 2(p.5). C·α 비율·유한 예산은 여기서 선언한 입력입니다. 모든 사례를 유지하며, 최신 Adam 기본값이나 일반적 우열에 대한 결론을 내리지 않습니다.',
        'Algorithm 1 and footnote 1 (p.3), Theorem 1 (p.4), Appendix A (pp.10–11), AMSGrad Algorithm 2 (p.5). C, alpha fractions and finite budgets are declared inputs. All cases remain visible; no conclusion about modern Adam defaults or universal method rankings follows.') + '</p><div class="formula">chainbench reproduce reddi-2018 --steps ' + str(steps) + ' --lang ko --output adam.html</div></section>'
    # Compact raw arrays keep the maximum-budget offline file bounded. The same
    # visible pre element is the no-JS fallback, download source and UI record.
    raw = escape(_record_json(result))
    body += '<details class="panel"><summary>' + bi('전체 수치·설정·환경','All samples, settings and environment') + '</summary><button data-download="chainbench-evidence" data-filename="adam-counterexample.json">JSON</button><pre id="chainbench-evidence">' + raw + '</pre></details>'
    html = page('Adam · Memory and regret',bi('공개 반례의 계산을 한 회씩 따라가기','Follow a published counterexample one round at a time'),body,lang=lang)
    return html.replace('</body>','<script>'+SCRIPT+'</script></body>')
