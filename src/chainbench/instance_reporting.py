"""Bilingual offline reading of the exact numeric-instance workflow."""
from __future__ import annotations

import json
from dataclasses import replace
from html import escape

from ._pages import bi, evidence, page
from .instances import validate_instance_report
from .visuals import experiment_chart, render_line_chart


def instance_html(result: dict, lang: str = "en", *, replay: dict | None = None) -> str:
    validate_instance_report(result)
    instance, fixture = result["instance"], result["fixture"]
    settings = instance["run"]
    intro = bi('이 곡선의 출발점은 저장된 실제 숫자입니다. 입력을 확인하고, 궤적을 읽고, 같은 입력으로 다시 검증하세요.',
               'These curves start from stored numbers. Inspect the input, read the trajectories, then rerun the same inputs.')
    body = '<nav class="panel">' + ''.join(
        f'<a href="#{key}">{bi(ko, en)}</a>' for key, ko, en in [
            ('instance-context', '1. 실제 입력', '1. Stored inputs'),
            ('instance-curves', '2. 계산 궤적', '2. Trajectories'),
            ('instance-methods', '3. 방법과 한계', '3. Methods and limits')]) + '</nav>'
    if replay is not None:
        body += ('<section id="instance-replay"><h2>' + escape(replay['status']) + '</h2><p>'
                 + bi('설정으로 예제를 새로 만들지 않고 저장된 행렬·벡터·시작점을 사용했습니다.',
                      'The rerun used the stored arrays and start; it did not regenerate data from the seed.')
                 + f'</p><p>rtol={replay["rtol"]:g} · atol={replay["atol"]:g} · '
                 + bi('대조한 수치', 'Numeric samples') + f': {replay["numeric_samples_compared"]} · '
                 + bi('차이', 'Mismatches') + f': {replay["mismatch_count"]} · '
                 + bi('환경 변경', 'Environment changed') + f': {replay["environment_changed"]}</p>'
                 + '<pre>' + escape(json.dumps(replay['first_mismatches'], indent=2)) + '</pre>'
                 + '<p class="callout caution">' + bi('MATCH는 표시된 오차 범위에서 이 재실행과 일치한다는 뜻입니다. 원본 작성자나 이론의 참을 인증하지 않습니다.',
                     'MATCH is agreement with this rerun at the stated tolerances. It does not authenticate the original author or certify a theorem.') + '</p></section>')
    formulas = {
        'quadratic': ('f(x) = ½ xᵀQx − bᵀx', '||Qx − b||₂',
                      'Q는 대칭 준정부호이고 Qx*=b를 수치적으로 확인합니다. CG·heavy-ball은 양의 정부호가 필요합니다.',
                      'Q is symmetric PSD and Qx*=b is checked numerically. CG and classical heavy-ball require positive definiteness.'),
        'diagonal-lasso': ('F(x) = ½ ||a ⊙ x − b||₂² + λ||x||₁', '||L[x − soft(x − ∇f(x)/L, λ/L)]||₂',
                           '대각 a는 0이 아니고 λ≥0입니다. 해석적 soft-threshold 해가 기준점입니다.',
                           'Diagonal entries a are nonzero and λ≥0. The reference is the analytic soft-threshold solution.'),
        'simplex': ('f(x) = ½ ||x − target||₂², x ≥ 0, Σx = 1', '∇f(x)ᵀ(x − argminᵥ ∇f(x)ᵀv)',
                    'target과 시작점은 확률 단체 위에 있습니다. 기준점은 target이며 선형 오라클은 꼭짓점을 선택합니다.',
                    'Target and start are on the probability simplex. The reference is target; the linear oracle chooses a vertex.'),
    }
    formula, metric, ko, en = formulas[fixture['kind']]
    body += ('<section id="instance-context"><h2>' + bi('저장된 실제 문제', 'The stored problem')
             + '</h2><p class="formula">' + escape(formula) + '</p><p>' + bi(ko, en) + '</p>'
             + f'<p>{escape(fixture["kind"])} · d={fixture["dimension"]} · L={fixture["L"]:.8g} · '
             + bi('요청한 업데이트', 'Requested updates') + f'={settings["steps"]}</p>'
             + '<p class="small">input SHA-256: <code>' + instance['input_sha256'] + '</code><br>'
             + 'manifest SHA-256: <code>' + instance['manifest_sha256'] + '</code></p>'
             + '<p class="callout">' + bi('입력 해시는 시작점을 포함한 float64 바이트를 묶습니다. 매니페스트 해시는 방법 설정과 선언된 출처도 묶습니다. 시드는 설명용 메타데이터이며 재실행은 저장된 숫자를 읽습니다.',
                  'The input hash binds float64 bytes including the start. The manifest hash also binds method settings and declared origin. The seed is descriptive metadata; rerun authority is the stored numbers.')
             + '</p><details><summary>' + bi('행렬·벡터·시작점·기준점과 설정 펼치기', 'Expand arrays, start, reference and settings')
             + '</summary><pre>' + escape(json.dumps({'instance': instance, 'reference': fixture['x_star'],
                                                     'environment': result['environment']}, indent=2))
             + '</pre></details></section>')
    body += '<section id="instance-curves"><h2>' + bi('계산된 궤적 읽기', 'Read the computed trajectories') + '</h2>'
    body += '<p>' + bi('k=0은 저장된 시작점이고 k는 완료한 업데이트 수입니다. CG는 잔차 조건에서 먼저 멈출 수 있습니다. 로그 축에서 0은 양의 작은 수로 바꾸지 않습니다.',
                      'k=0 is the stored start; k counts completed updates. CG may stop early at its true-residual criterion. Log scale does not replace zeros with small positive numbers.') + '</p>'
    body += '<p class="small">' + bi('기준점 거리는 0부터 시작하는 선형 축입니다. 작은 화면에서는 그래프를 가로로 스크롤하거나 그래프에 초점을 두고 방향키를 누르세요.',
        'Reference distance uses a linear axis starting at zero. On small screens, scroll each plot horizontally or focus it and use the arrow keys.') + '</p>'
    body += ('<div class="panel" id="instance-inspector"><h3>' + bi('한 업데이트의 실제 숫자', 'Inspect one computed update')
             + '</h3><div id="instance-inspector-controls" class="controls" hidden><label>'
             + bi('방법', 'Method') + ' <select id="instance-method">'
             + ''.join(f'<option>{escape(run["method"])}</option>' for run in result['runs'])
             + '</select></label><label>' + bi('완료한 업데이트', 'Completed update')
             + ' <input id="instance-step" type="range" min="0" max="0" value="0"></label></div>'
             + '<p class="small">' + bi('각 방법에서 실제로 계산된 행만 선택합니다. 브라우저에서 알고리즘을 다시 실행하지 않습니다.',
                  'Select only rows actually computed by that method. The browser does not rerun an algorithm.')
             + '</p><pre id="instance-sample" aria-live="polite">'
             + escape(json.dumps(result['runs'][0]['rows'][0], indent=2)) + '</pre></div>')
    for field, title, label, note_ko, note_en in [
        ('gap', 'Objective gap', 'F(x) − F*', '안정적인 공식으로 계산한 기준 최적값과의 차이입니다.', 'The gap uses the existing stable formulas relative to the validated reference.'),
        ('stationarity', fixture['stationarity_metric'], fixture['stationarity_metric'],
         '정지성 척도는 문제군마다 정의가 다릅니다. 다른 문제군 사이의 같은 이름의 순위가 아닙니다.',
         'Stationarity has a family-specific definition; its numerical scale is not a cross-family ranking.'),
        ('distance_to_reference', 'Distance to the reference', '||x − x*||₂',
         '준정부호 문제에서는 최적해가 여러 개일 수 있어 이 거리가 0이 되지 않아도 gap은 0일 수 있습니다.',
         'For PSD quadratics, the solution may be nonunique: zero gap does not require zero distance to this particular reference.'),
    ]:
        chart = experiment_chart(result, field, title, label)
        if field == 'distance_to_reference':
            chart = replace(chart, y_scale='linear')
        body += ('<h3>' + escape(title) + '</h3><p>' + bi(note_ko, note_en) + '</p>'
                 + (f'<p class="formula">{escape(metric)}</p>' if field == 'stationarity' else '')
                 + f'<div class="plot" data-instance-chart="{field}" tabindex="0" role="region" aria-label="{escape(title)}">'
                 + render_line_chart(chart) + '</div>')
    body += '</section><section id="instance-methods"><h2>' + bi('방법의 실제 설정', 'Actual method settings') + '</h2>'
    descriptions = {
        'gd': ('기울기 반대 방향으로 1/L만큼 이동합니다.', 'Move against the gradient with step 1/L.'),
        'smooth-fista': ('g=0인 고정 L FISTA입니다. Nesterov의 역사적 아이디어와 실제 점화식을 구별합니다.', 'Fixed-L FISTA with g=0; distinguish the implemented recurrence from historical Nesterov attribution.'),
        'heavy-ball': ('직전 이동을 기억하며 이차함수의 μ·L로 α·β를 정합니다.', 'Retain the previous movement, using quadratic μ,L tuning for α,β.'),
        'cg': ('공액 방향을 갱신하고 실제 잔차로 종료를 확인합니다. rtol의 기준은 초기 잔차입니다.', 'Update conjugate directions and recheck the true residual. rtol is relative to the initial residual.'),
        'proximal-point': ('매 업데이트마다 (I+cQ)x[k+1]=x[k]+cb를 풉니다.', 'Solve (I+cQ)x[k+1]=x[k]+cb at every update.'),
        'ista': ('기울기 이동 다음에 soft-threshold를 적용합니다.', 'Apply soft thresholding after a gradient step.'),
        'fista': ('외삽점에서 기울기 이동과 soft-threshold를 적용합니다.', 'Apply the gradient/proximal step at an extrapolated point.'),
        'frank-wolfe': ('선형 오라클이 고른 꼭짓점으로 γ[k]=2/(k+2)만큼 이동합니다.', 'Move toward the oracle vertex with γ[k]=2/(k+2).'),
    }
    for run in result['runs']:
        ko, en = descriptions[run['method']]
        body += ('<article data-instance-method="' + run['method'] + '"><h3>' + escape(run['method'])
                 + '</h3><p>' + bi(ko, en) + '</p><pre>'
                 + escape(json.dumps({k: run[k] for k in ('parameters', 'updates', 'termination')}, indent=2))
                 + '</pre></article>')
    body += ('<p class="callout caution">' + bi('이 입력의 유한한 수치 관측입니다. 동일한 업데이트 수는 동일한 연산량이 아닙니다. 해시를 다시 계산한 기록은 작성자나 생성 이력을 증명하지 않습니다.',
              'These are finite observations on this input. Equal updates are not equal work. Recomputed hashes do not prove the author or generation history.')
             + '</p><p><a href="https://github.com/chocoemong17/chainbench/blob/v0.7.0/docs/SOURCE_MAP.md">'
             + bi('기존 점화식·논문 출처·유한 검사의 대응', 'Implemented recurrences, paper sources and finite-check scope')
             + '</a></p></section>' + evidence(result if replay is None else replay,
                                                'instance-result.json' if replay is None else 'instance-replay.json'))
    document = page('Stored inputs · exact replay', intro, body, lang=lang)
    script = """<script>
(() => {
 const saved=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 const record=saved.kind==='chainbench.instance-replay'?saved.replayed:saved;
 const select=document.getElementById('instance-method'), slider=document.getElementById('instance-step');
 const sample=document.getElementById('instance-sample');
 function update(){
   const run=record.runs.find(r=>r.method===select.value);
   slider.max=String(run.rows.length-1);
   slider.value=String(Math.min(Number(slider.value),run.rows.length-1));
   slider.setAttribute('aria-valuetext','k = '+slider.value);
   sample.textContent=JSON.stringify(run.rows[Number(slider.value)],null,2);
 }
 select.addEventListener('change',update);slider.addEventListener('input',update);
 document.getElementById('instance-inspector-controls').hidden=false;update();
})();
</script>"""
    return document.replace('</body>', script + '</body>')
