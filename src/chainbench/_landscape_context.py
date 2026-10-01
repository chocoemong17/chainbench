"""Visible calculation context and actual-step readouts for the shared landscape."""
from __future__ import annotations

import json
from html import escape

from ._pages import bi

CSS = '''.landscape-context{padding:18px;border:1px solid #d7e2ed;border-radius:14px;background:#f3f7fb}
.landscape-context pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}
.landscape-context td,.landscape-values td{white-space:nowrap}
.landscape-readouts{padding:12px 18px;border-radius:14px;background:#f3f7fb;overflow-wrap:anywhere;font-size:13px;font-variant-numeric:tabular-nums}
.landscape-readouts p{margin:8px 0}.landscape-controls{display:none}
.trajectory-enabled .landscape-controls{display:flex}'''


def context_html(result, colors):
    p = result['problem']
    body = '<style>'+CSS+'</style><section class="landscape-context" id="calculation"><h2>'+bi(
        '이 경로를 만든 실제 계산', 'The actual calculation behind these paths')+'</h2>'
    body += '<p>f(x)=½xᵀQx−bᵀx · z=f(x)−f* · n=2 · '
    body += f'L={p["L"]:.8g} · μ={p["mu"]:.8g} · κ={p["actual_condition_number"]:.8g}</p>'
    body += '<p>'+bi('회전', 'Rotation')+f'={p["angle_degrees"]:g}° · x₀={p["start"]} · x*={p["x_star"]} · '
    body += f'f*={p["f_star"]:.8g} · '+bi('최대 갱신', 'Update budget')+f'={result["steps"]}</p>'
    body += '<p>'+bi('결정론적 이차함수 · 난수·정규화 항 없음 · CG만 실제 잔차로 조기 종료합니다.',
                    'Deterministic quadratic; no randomness or regularizer. Only CG stops early by its true residual.')+'</p>'
    body += '<pre>'+escape(json.dumps({'Q': p['Q'], 'b': p['b'], 'c': p['c']}, ensure_ascii=False))+'</pre>'
    body += '<div class="scroll"><table><thead><tr><th>method / source</th><th>actual settings</th>'
    body += '<th>updates</th><th>termination</th></tr></thead><tbody>'
    for method in result['methods']:
        run = result['runs'][method]
        source = result['sources'][method]
        body += '<tr><td><a style="color:'+colors[method]+'" href="'+escape(source['url'], quote=True)+'">'+method+'</a></td><td>'
        body += escape(json.dumps(result['method_parameters'][method], ensure_ascii=False))+f'</td><td>{run["updates"]}</td>'
        body += '<td>'+escape(run['termination'])+'</td></tr>'
    body += '</tbody></table></div>'
    for method in result['methods']:
        body += '<p class="small">'+escape(method+': '+result['sources'][method]['scope'])+'</p>'
    body += '<p class="small">'+bi(
        'fixed_budget는 수렴 판정이 아닙니다. 반복 수는 동일 작업량·시간 비교가 아닙니다. 정확한 이차 PPA는 매회 선형계를 풀며, CG는 스케일 조정과 실제 잔차 검사를 사용합니다.',
        'fixed_budget is not a convergence decision. Iteration counts do not compare equal work or time. Exact quadratic PPA solves a linear system per update; CG uses scaling and true-residual checks.')+'</p>'
    body += '<details><summary>'+bi('입력 해시·실행 환경', 'Input fingerprint and environment')+'</summary><p><code>'
    body += result['input_sha256']+'</code></p><p class="small">'+escape(result['input_hash_format'])+'</p><pre>'
    body += escape(json.dumps(result['environment'], indent=2))+'</pre></details></section>'
    return body


def readouts_html(result):
    body = '<div class="landscape-readouts" aria-live="polite">'
    for method in result['methods']:
        k = result['runs'][method]['updates']
        body += f'<p data-landscape-readout="{method}">{method} · k={k} · x={result["traces"][method][k]} '
        body += f'· f−f*={result["gaps"][method][k]:.6g} · ||r||₂={result["runs"][method]["residual_norms"][k]:.6g}</p>'
    return body+'</div><p class="small">'+bi(
        '종료한 방법은 마지막 계산점에 머뭅니다. 경로의 선분은 저장된 점을 연결하며 연속시간 궤적이나 곡면 위의 이동이 아닙니다.',
        'A stopped method holds its last computed point. Chords connect saved samples; they are not continuous-time trajectories or paths on the surface.')+'</p>'


def values_html(result):
    body = '<section class="landscape-values"><h2>'+bi('모든 실제 반복점', 'Every computed iterate')+'</h2>'
    for method in result['methods']:
        body += '<details><summary>'+method+'</summary><div class="scroll"><table><thead><tr>'
        body += '<th>k</th><th>x₁</th><th>x₂</th><th>f−f*</th><th>||r||₂</th></tr></thead><tbody>'
        for k, x in enumerate(result['traces'][method]):
            body += f'<tr><td>{k}</td>'+''.join(f'<td>{v:.8g}</td>' for v in (
                *x, result['gaps'][method][k], result['runs'][method]['residual_norms'][k]))+'</tr>'
        body += '</tbody></table></div></details>'
    return body+'</section>'
