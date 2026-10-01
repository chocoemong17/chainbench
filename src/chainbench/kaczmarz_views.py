"""Offline row projections, exact expectations and all finite trial observations."""

from __future__ import annotations

import itertools
import json
import math
from html import escape

from ._kaczmarz_proof_views import CSS as PROOF_CSS
from ._kaczmarz_proof_views import SCRIPT as PROOF_SCRIPT
from ._kaczmarz_proof_views import proof_html
from ._pages import bi, evidence, page

COLORS = ("#2563eb", "#b45309", "#0f766e", "#7c3aed", "#be185d", "#475569", "#0891b2", "#4d7c0f")
CSS = """
html{scroll-behavior:auto}.rk-controls{display:none;gap:12px;flex-wrap:wrap;align-items:center;background:#172238;color:#fff;padding:18px;border-radius:16px}.rk-enabled .rk-controls{display:flex}.rk-controls input[type=range]{min-width:140px;flex:1}.rk-controls select{max-width:100%}.rk-visual svg{width:100%;height:auto;display:block}.rk-readout{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.9 monospace;background:#eef5f6;padding:16px;border-radius:12px}.rk-grid{display:grid;grid-template-columns:1fr 1.3fr;gap:18px}.rk-step-flow{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.rk-step-flow>div{padding:14px;border-radius:12px;background:#f0f4fa}.rk-step-flow b{display:block}.rk-table{max-height:420px;overflow:auto}.rk-chart{overflow:auto}.rk-chart svg{min-width:640px}.rk-prob{max-width:800px;margin:auto}@media(max-width:850px){.rk-grid,.rk-step-flow{grid-template-columns:1fr}}@media print{.rk-controls{display:none!important}[data-rk-case]{display:block!important}.rk-table{max-height:none}}
"""
SCRIPT = r"""(()=>{
 const record=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 const choice=document.querySelector('[data-rk-select]'),seed=document.querySelector('[data-rk-seed]'),slider=document.querySelector('[data-rk-slider]'),camera=document.querySelector('[data-rk-camera]'),play=document.querySelector('[data-rk-play]');
 document.documentElement.classList.add('rk-enabled');let timer=null;
 const stop=()=>{if(timer)clearInterval(timer);timer=null;play.textContent='▶';play.setAttribute('aria-pressed','false');};
 const project=x=>{const a=Number(camera.value)*Math.PI/180,e=25*Math.PI/180;return[230+130*(Math.cos(a)*x[0]-Math.sin(a)*x[1]),260-130*(Math.sin(e)*(Math.sin(a)*x[0]+Math.cos(a)*x[1])+Math.cos(e)*x[2])];};
 const pts=xs=>xs.map(project).map(p=>p.join(',')).join(' ');
 const update=()=>{
  const c=record.cases.find(c=>c.id===choice.value),s=Number(seed.value),k=Number(slider.value),run=c.runs[s];
  document.querySelectorAll('[data-rk-case]').forEach(p=>p.hidden=p.dataset.rkCase!==c.id);
  const panel=document.querySelector('[data-rk-case="'+c.id+'"]'),row=k===0?null:run.row_indices[k-1],axis=row===null?null:c.inputs.A[row].indexOf(1),x=run.iterates[k];
  document.querySelector('[data-rk-step]').textContent='k = '+k;
  document.querySelector('[data-rk-angle]').textContent='yaw '+camera.value+'° · elevation 25°';
  camera.disabled=c.id!=='cube';
  panel.querySelector('[data-rk-readout]').textContent='seed='+s+' · k='+k+' · selected row (0-based)='+(row===null?'none / 초기':row)+'\n'+(axis===null?'initial point / 초기점':'project onto x'+(axis+1)+'=0 · row probability='+c.inputs.row_probabilities[row])+'\n'+(k?'previous=['+run.iterates[k-1].join(', ')+'] → ':'')+'x=['+x.join(', ')+']\n||x−x*||²='+run.squared_errors[k]+' · exact E='+c.exact_expectation[k].toExponential(6)+' · batch mean='+c.empirical_mean[k].toExponential(6)+'\nfirst zero='+(run.first_zero===null?'not reached within budget / 예산 내 미도달':run.first_zero)+' · zero trials='+c.zero_counts[k]+'/'+record.parameters.trials;
  const chart=panel.querySelector('[data-rk-chart]'),h=c.exact_expectation[0],cp=(v,i)=>[65+630*i/record.parameters.steps,335-260*v/h];
  chart.querySelector('[data-rk-selected]').setAttribute('points',run.squared_errors.map(cp).map(p=>p.join(',')).join(' '));
  const p=cp(run.squared_errors[k],k),marker=chart.querySelector('[data-rk-current]');marker.setAttribute('cx',p[0]);marker.setAttribute('cy',p[1]);
  chart.querySelector('[data-rk-cursor]').setAttribute('x1',p[0]);chart.querySelector('[data-rk-cursor]').setAttribute('x2',p[0]);
  chart.setAttribute('data-current-seed',s);chart.setAttribute('data-current-step',k);
  if(c.id==='cube'){
   const svg=panel.querySelector('[data-rk-cube]');svg.setAttribute('data-current-step',k);svg.setAttribute('data-current-seed',s);svg.setAttribute('data-yaw',camera.value);
   svg.querySelectorAll('[data-rk-coordinates]').forEach(el=>el.setAttribute('points',pts(JSON.parse(el.dataset.rkCoordinates))));
   svg.querySelectorAll('[data-rk-axis-label]').forEach(el=>{const p=project(JSON.parse(el.dataset.rkAxisLabel));el.setAttribute('x',p[0]+8);el.setAttribute('y',p[1]);});
   svg.querySelectorAll('[data-rk-plane]').forEach(el=>{el.style.display=Number(el.dataset.rkPlane)===axis?'':'none';});
   svg.querySelector('[data-rk-path]').setAttribute('points',pts(run.iterates.slice(0,k+1)));
   for(const [name,point] of [['previous',run.iterates[Math.max(0,k-1)]],['current',x]]){const p=project(point),el=svg.querySelector('[data-rk-point="'+name+'"]');el.setAttribute('cx',p[0]);el.setAttribute('cy',p[1]);}
  }else{
   const marker=panel.querySelector('[data-rk-state]');marker.setAttribute('cx',x[0]===1?110:365);marker.setAttribute('data-state',x[0]);
  }
  document.dispatchEvent(new CustomEvent('chainbench:kaczmarz',{detail:{caseRecord:c,run,step:k}}));
 };
 for(const el of [choice,seed,slider,camera])el.addEventListener(el.tagName==='SELECT'?'change':'input',()=>{stop();update();});
 play.addEventListener('click',()=>{if(timer){stop();return;}if(Number(slider.value)===Number(slider.max))slider.value='0';play.textContent='❚❚';play.setAttribute('aria-pressed','true');update();timer=setInterval(()=>{if(Number(slider.value)>=Number(slider.max)){stop();return;}slider.value=String(Number(slider.value)+1);update();},450);});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});update();
})();"""


def _text(x, y, value, size=13, extra=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="#334155" {extra}>{escape(str(value))}</text>'


def _svg(width, height, label, attr=""):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(label, quote=True)}" {attr}><rect width="{width}" height="{height}" rx="16" fill="#f7f9fc"/>'


def project_cube(x, yaw=35):
    a, e = math.radians(yaw), math.radians(25)
    return (230 + 130 * (math.cos(a)*x[0] - math.sin(a)*x[1]),
            260 - 130 * (math.sin(e)*(math.sin(a)*x[0]+math.cos(a)*x[1]) + math.cos(e)*x[2]))


def _poly(points, attrs):
    pixels = " ".join(f"{x:.7f},{y:.7f}" for x, y in map(project_cube, points))
    return f'<polyline data-rk-coordinates="{escape(json.dumps(points), quote=True)}" points="{pixels}" {attrs}/>'


def cube_svg():
    svg = _svg(480, 365, "Actual coordinates x1, x2, x3; selected coordinate plane and projection", 'data-rk-cube="" data-current-step="0" data-current-seed="0" data-yaw="35"')
    svg += '<metadata>'+escape(json.dumps(dict(kind="chainbench.kaczmarz-cube", coordinates="x1,x2,x3; not objective height", projection="orthographic yaw 35 degrees, elevation 25 degrees, scale 130; origin=(230,260)", range=[0,1], initial_iteration=0)))+'</metadata>'
    svg += _text(20, 28, "3D coordinates · orange = selected run", 15)
    for axis in range(3):
        others = [j for j in range(3) if j != axis]
        plane = []
        for u, v in ((0,0),(1,0),(1,1),(0,1),(0,0)):
            point = [0,0,0]
            point[others[0]], point[others[1]] = u, v
            plane.append(point)
        svg += _poly(plane, f'data-rk-plane="{axis}" style="display:none" fill="{COLORS[axis]}" fill-opacity=".16" stroke="{COLORS[axis]}"')
        for bits in itertools.product((0, 1), repeat=2):
            p = [0,0,0]
            p[others[0]], p[others[1]] = bits
            q = p.copy()
            q[axis] = 1
            svg += _poly([p,q], 'fill="none" stroke="#c0cbd9"')
        endpoint = [0,0,0]
        endpoint[axis] = 1.15
        svg += _poly([[0,0,0],endpoint], f'fill="none" stroke="{COLORS[axis]}" stroke-width="2"')
        x,y = project_cube(endpoint)
        svg += _text(x+8,y,f"x{axis+1}",14,f'data-rk-axis-label="{json.dumps(endpoint)}"')
    svg += '<polyline data-rk-path="" points="" fill="none" stroke="#d97706" stroke-width="4"/>'
    x,y = project_cube([1,1,1])
    for name,color,size in (("previous","#64748b",9),("current","#d97706",6)):
        svg += f'<circle data-rk-point="{name}" cx="{x:.7f}" cy="{y:.7f}" r="{size}" fill="{color}"/>'
    return svg + _text(20,338,"x*=(0,0,0) · cube edges have coordinate length 1",12) + '</svg>'


def state_svg(case):
    m, r = case["inputs"]["equations"], min(case["inputs"]["direction_counts"])
    svg = _svg(480,365,"Two exact states: wait at e1 until a row in direction e1 is selected")
    svg += _text(22,32,"Actual state: e1 or the zero vector",15)
    svg += '<path d="M140,170 H335 l-12,-7 m12,7 l-12,7" fill="none" stroke="#0f766e" stroke-width="3"/>'
    svg += _text(164,147,f"hit e1: p={r}/{m}",14)
    svg += '<path d="M89,145 C30,72 187,70 131,145" fill="none" stroke="#64748b" stroke-width="2"/>'
    svg += _text(35,72,f"wait: 1−p={m-r}/{m}",13)
    for x,label in ((110,"e1"),(365,"0")):
        svg += f'<circle cx="{x}" cy="170" r="29" fill="white" stroke="#94a3b8"/>' + _text(x-9,176,label,18)
    svg += '<circle data-rk-state="" data-state="1" cx="110" cy="170" r="36" fill="none" stroke="#d97706" stroke-width="4"/>'
    svg += _text(26,250,"After the first hit: stay at 0, continue sampling.",13)
    svg += _text(26,280,"All n coordinates are retained in the readout / JSON.",12)
    return svg + '</svg>'


def probability_svg(case):
    inputs = case["inputs"]
    m, counts = inputs["equations"], inputs["direction_counts"]
    svg = _svg(780,200,"Uniform probability per row; direction probability depends on multiplicity")
    svg += _text(20,26,f"m={m} unit rows · each row probability 1/{m}",15)
    offset = 0
    for axis,count in enumerate(counts):
        for index in range(offset, offset+count):
            svg += f'<rect x="{25+730*index/m:.5f}" y="47" width="{730/m-1:.5f}" height="35" fill="{COLORS[axis]}"><title>row {index}: e{axis+1}, probability 1/{m}</title></rect>'
        width = 730*count/m
        svg += f'<rect x="{25+730*offset/m:.5f}" y="117" width="{width:.5f}" height="32" fill="{COLORS[axis]}"/>'
        svg += _text(25+730*offset/m+width/2,174,f"e{axis+1}: {count}/{m}",11,'text-anchor="middle"')
        offset += count
    svg += _text(25,103,"Aggregate by direction (same color)",12)
    return svg+'</svg>'


def expectation_svg(case, steps):
    height = case["exact_expectation"][0]
    def points(values):
        return ' '.join(f'{65+630*k/steps:.7f},{335-260*v/height:.7f}' for k,v in enumerate(values))
    svg = _svg(750,400,"Squared error: every trial, selected trial, finite batch mean and exact expectation", 'data-rk-chart="" data-current-step="0" data-current-seed="0"')
    svg += '<metadata>'+escape(json.dumps(dict(kind="chainbench.kaczmarz-expectation-chart", case=case["id"], x="completed row projections k", y="squared Euclidean error; linear axis including zero", all_seeds=[r["seed"] for r in case["runs"]], exact_expectation=case["exact_expectation"], empirical_mean=case["empirical_mean"])))+'</metadata>'
    svg += _text(65,27,"||x[k]−x*||² · linear scale",15)
    for value in (0,height/2,height):
        y = 335-260*value/height
        svg += f'<path d="M65,{y} H695" stroke="#d8e0e8"/>'+_text(30,y+4,f'{value:g}',12)
    for k in sorted({0,steps//2,steps}):
        svg += _text(65+630*k/steps,360,k,12,'text-anchor="middle"')
    for run in case["runs"]:
        svg += f'<polyline data-rk-trial="{run["seed"]}" points="{points(run["squared_errors"])}" fill="none" stroke="#94a3b8" opacity=".14"/>'
    for field,color,dash in (("empirical_mean","#2563eb",""),("exact_expectation","#0f766e",'stroke-dasharray="7 4"')):
        svg += f'<polyline data-rk-series="{field}" points="{points(case[field])}" fill="none" stroke="{color}" stroke-width="3" {dash}/>'
    svg += f'<polyline data-rk-selected="" points="{points(case["runs"][0]["squared_errors"])}" fill="none" stroke="#d97706" stroke-width="2.5"/>'
    svg += '<line data-rk-cursor="" x1="65" x2="65" y1="65" y2="335" stroke="#475569" stroke-dasharray="3 4"/><circle data-rk-current="" cx="65" cy="75" r="6" fill="#d97706"/>'
    return svg + _text(380,387,"completed updates k",12,'text-anchor="middle"') + '</svg>'


def _case(case, steps):
    inputs = case["inputs"]
    m,n = inputs["equations"], inputs["dimension"]
    body = f'<section data-rk-case="{case["id"]}"><h2>{case["id"]} · m={m}, n={n}</h2>'
    body += '<div class="formula">A: '+escape(str(inputs["direction_counts"]))+' rows per direction · b=0\nx0='+escape(str(inputs["start"]))+f'\nκ_scaled²={case["scaled_condition_squared"]:g} · κ_spectral²={case["spectral_condition_squared"]:g}\nE||x[k]−x*||² = {case["exact_expectation"][0]:g} × ({case["contraction_numerator"]}/{m})^k</div>'
    body += '<div class="rk-prob rk-visual">'+probability_svg(case)+'</div>'
    body += '<p class="small">'+bi('행 하나를 균등하게 고릅니다. 같은 방향의 행이 여러 개 있으므로 방향별 확률은 다를 수 있습니다.','Each row is equally likely. Repeated rows make some directions more likely than others.')+'</p>'
    body += '<div class="rk-grid"><div class="rk-visual">'+(cube_svg() if case["id"]=='cube' else state_svg(case))+'</div><div class="rk-chart rk-visual">'+expectation_svg(case,steps)+'</div></div>'
    body += '<p class="small">'+bi('회색: 선언한 모든 시드 · 주황: 선택한 실행 · 파랑: 유한 표본 평균 · 초록 점선: 정확한 기대값(이 입력에서 정리의 상계와 같음). 선분은 정수 반복점들을 연결합니다.','Gray: every declared seed · orange: selected run · blue: finite batch mean · green dashed: exact expectation (equal to the theorem upper bound here). Segments connect integer iterations.')+'</p>'
    body += '<div class="rk-readout" data-rk-readout>'+escape(f'seed=0 · k=0 · no selected row\nx={inputs["start"]} · squared error={case["exact_expectation"][0]}')+'</div>'
    if 'conditional_projection' in case:
        body += proof_html(case)
    body += '<details><summary>'+bi('모든 반복의 평균·도달 시점 분포','Every iteration: mean and first-zero distribution')+'</summary><div class="rk-table"><table><thead><tr><th>k</th><th>Exact E / upper</th><th>Batch mean</th><th>Zero by k</th><th>First zero at k</th></tr></thead><tbody>'
    for k in range(steps+1):
        body += f'<tr><td>{k}</td><td>{case["exact_expectation"][k]:.12g}</td><td>{case["empirical_mean"][k]:.12g}</td><td>{case["zero_counts"][k]}</td><td>{case["first_zero_counts"][k]}</td></tr>'
    body += f'</tbody></table></div><p>Unresolved at k={steps}: {case["unresolved_trials"]}. '+bi('미도달 실행도 모두 포함합니다.','Unresolved trials remain in all summaries.')+'</p></details>'
    body += '<details><summary>'+bi('전체 시드·행 선택·실제 좌표 (JavaScript 없이 열람)','All seeds, row choices and actual coordinates (works without JavaScript)')+'</summary>'
    for run in case["runs"]:
        first = 'unresolved' if run["first_zero"] is None else str(run["first_zero"])
        body += f'<details data-rk-run="{run["seed"]}"><summary>seed={run["seed"]} · first zero={first}</summary><div class="rk-table"><table><thead><tr><th>k</th><th>Row (0-based)</th><th>x[k]</th><th>||x−x*||²</th></tr></thead><tbody>'
        for k,(x,error) in enumerate(zip(run["iterates"],run["squared_errors"])):
            row = '—' if k==0 else str(run["row_indices"][k-1])
            body += f'<tr><td>{k}</td><td>{row}</td><td>{escape(str(x))}</td><td>{error:g}</td></tr>'
        body += '</tbody></table></div></details>'
    return body+'</details></section>'


def kaczmarz_html(result, lang="en"):
    if lang not in ("en", "ko"):
        raise ValueError("lang must be en or ko")
    params = result["parameters"]
    body = '<style>'+CSS+PROOF_CSS+'</style><section><h2>'+bi('평균은 줄어도 한 실행은 기다릴 수 있습니다','An average can shrink while a single run waits')+'</h2>'
    body += '<p>'+bi('연립방정식 Ax=0을 한 행씩 해결합니다. 선택한 행의 평면으로 현재 점을 수직 투영합니다. 세 좌표 예제에서는 정육면체 위의 실제 점이 좌표 평면으로 이동합니다.','Solve Ax=0 one row at a time by projecting the current point onto the selected row hyperplane. In the three-coordinate example, actual cube vertices move onto coordinate planes.')+'</p>'
    body += '<div class="rk-step-flow"><div><b>1 · '+bi('행 선택','Choose a row')+'</b>pᵢ=||aᵢ||²/||A||F²</div><div><b>2 · '+bi('잔차 계산','Read its residual')+'</b>rᵢ=bᵢ−aᵢ·x</div><div><b>3 · '+bi('수직 투영','Project')+'</b>x ← x+(rᵢ/||aᵢ||²)aᵢ</div></div>'
    body += '<div class="callout caution">'+bi('기대값 보장은 개별 실행이나 유한 표본 평균의 상계가 아닙니다. 모든 시드를 유지하며, 평균이 선 위로 올라가도 실패 판정을 하지 않습니다. 무작위 표본에서 가장 늦은 실행을 수학적 최악 사례라고 부르지 않습니다.','The expectation bound does not bound each path or its finite sample mean. Every declared seed is retained; a mean above the curve is not a failed theorem check. The latest sampled run is not a mathematical worst case.')+'</div>'
    body += '<p>'+bi('출처: Strohmer–Vershynin, 2009 (2007 프리프린트), Algorithm 1, Theorem 2, §3.2. 여섯 입력은 논문의 상계 달성 구성을 구체화한 것이며 원 논문의 실험 데이터가 아닙니다.','Source: Strohmer–Vershynin, 2009 (2007 preprint), Algorithm 1, Theorem 2, §3.2. The six inputs instantiate its sharp construction; they are not the paper’s experimental datasets.')+' <a href="'+result["source"]["url"]+'">PDF pp.4,9</a></p>'
    body += '<details><summary>'+bi('기대값이 상계와 같아지는 이유·원문 표기','Why equality holds; source notation')+'</summary><p>'+bi('A=I₃이면 각 좌표가 한 번도 선택되지 않을 확률이 (2/3)^k이므로 오차 제곱의 기대값은 3(2/3)^k입니다. 나머지 입력은 x0=e₁에서 시작하며 e₁ 행을 만날 때까지 그대로 있다가 0으로 이동합니다. 그 확률이 p=r/m이므로 기대 오차는 (1−p)^k입니다.','For A=I₃ each initial unit coordinate survives with probability (2/3)^k, so expected squared error is 3(2/3)^k. Other inputs start at e₁, wait until a row e₁ is drawn, then jump to 0. With hit probability p=r/m, expected squared error is (1−p)^k.')+'</p><p>'+bi('프리프린트 §3.2 마지막 식의 왼쪽에는 x₀가 인쇄되어 있습니다. 여기서는 Theorem 2와 직전 설명에 맞춰 해 x*=0까지의 오차를 사용합니다.','The last display in preprint §3.2 prints x₀ on the left. This implementation uses error to the solution x*=0, consistent with Theorem 2 and the preceding construction.')+'</p></details>'
    body += '<p class="small">'+escape(f'{params["trials"]} trials per case · seeds 0…{params["trials"]-1} · {params["steps"]} projections per trial · PCG64')+' · '+bi('해에 도달해도 예산 끝까지 추출합니다. 같은 시드를 입력마다 재사용하므로 입력 사이 표본은 독립이라고 간주하지 않습니다.','Sampling continues after reaching zero. Seeds are reused across cases; do not pool cases as independent samples.')+'</p></section>'
    body += '<div class="rk-controls"><label>'+bi('입력','Case')+' <select data-rk-select="">'+''.join(f'<option value="{c["id"]}">{c["id"]}</option>' for c in result["cases"])+'</select></label><label>seed <select data-rk-seed="">'+''.join(f'<option>{s}</option>' for s in params["seeds"])+'</select></label><button data-rk-play="" aria-label="Play or pause recorded projections" aria-pressed="false">▶</button><input data-rk-slider="" type="range" min="0" max="'+str(params["steps"])+'" value="0" aria-label="Completed projections"><strong data-rk-step="">k=0</strong><label>'+bi('3D 회전','3D rotation')+' <input data-rk-camera="" type="range" min="-180" max="180" value="35" aria-label="Cube yaw in degrees"></label><span data-rk-angle=""></span></div>'
    body += ''.join(_case(c,params["steps"]) for c in result["cases"])
    body += evidence(result,"kaczmarz-expectation.json")+'<script>'+PROOF_SCRIPT+SCRIPT+'</script>'
    return page('Randomized Kaczmarz · expectation and actual runs',
                bi('무작위 투영: 논문의 상계 달성 예제와 모든 시드',
                   'Published expectation attainment, actual projections and every seed'),
                body, lang=lang)
