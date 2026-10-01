"""A complete fixed-budget overview of the existing ADMM factorial design."""
from __future__ import annotations

from html import escape
from itertools import product

from ._pages import bi

CSS = '''
html{scroll-behavior:auto}
.admm-overview-groups{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.admm-overview-group{min-width:0;border:1px solid #dbe4ee;border-radius:14px;padding:12px}
.admm-overview-group table{min-width:530px;font-size:12px}
.admm-overview-group caption{text-align:left;padding:4px 0 12px;font-weight:650}
.admm-overview-group th,.admm-overview-group td{padding:8px;vertical-align:top}
.admm-overview-group td{min-width:145px;font-variant-numeric:tabular-nums}
.admm-overview-group th[scope=row]{white-space:nowrap}
.admm-outcome-status{display:inline-block;padding:2px 7px;border-radius:5px;font-size:11px;font-weight:750}
[data-admm-outcome-pass=true] .admm-outcome-status{background:#dff5ec;color:#075e46}
[data-admm-outcome-pass=false] .admm-outcome-status{background:#fff0d6;color:#805313}
.admm-overview-group dl{margin:7px 0;font-size:11px}
.admm-overview-group dl div{display:flex;justify-content:space-between;gap:6px}
.admm-overview-group dt,.admm-overview-group dd{margin:0}
.admm-overview-group dd{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
.admm-first-pass{font-size:11px;margin:5px 0}
[data-admm-overview-link]{display:inline-block;font-size:12px;padding:3px 0}
[data-admm-overview-link][aria-current=true]{font-weight:800;text-decoration-thickness:3px}
@media(max-width:1100px){.admm-overview-groups{grid-template-columns:minmax(0,1fr)}}
@media print{.admm-overview-group{break-inside:avoid}}
'''

SCRIPT = r'''
 document.querySelectorAll('[data-admm-overview-link]').forEach(link=>link.addEventListener('click',event=>{
  event.preventDefault();
  selector.value=link.dataset.admmOverviewLink;
  slider.value=slider.max;
  update();
  const panel=cases.find(el=>el.dataset.admmCase===selector.value);
  panel.querySelector('summary').focus({preventScroll:true});
  panel.scrollIntoView({block:'start'});
 }));
'''


def native_id(case_id, iteration):
    return f'admm-{case_id}-k{iteration}'


def overview(result, formatted):
    parameters = result['parameters']
    steps = parameters['steps']
    families, starts = parameters['families'], parameters['starts']
    fractions, rhos = parameters['lambda_fractions'], parameters['rhos']
    keys = [(c['family'],c['start_name'],c['inputs']['lambda_fraction'],c['inputs']['rho'])
            for c in result['cases']]
    expected = list(product(families,starts,fractions,rhos))
    if len(keys)!=len(set(keys)) or set(keys)!=set(expected):
        raise ValueError('ADMM overview requires each declared case exactly once')
    cases = dict(zip(keys,result['cases']))
    body = '<section id="admm-overview"><h2>'+bi('36개 결과에서 경로 고르기', 'Choose a path from all 36 outcomes')+'</h2>'
    body += '<p>'+bi(
        f'모든 칸은 마지막 k={steps}의 기록입니다. 행은 문제의 규제 강도, 열은 고정 벌점 ρ입니다. 행렬과 시작점도 빠짐없이 나눠 보여줍니다. 사례를 선택하면 그 마지막 상태의 그림으로 이동합니다.',
        f'Every cell describes the final k={steps} record. Rows vary the problem’s regularization strength; columns vary fixed penalty ρ. Both matrices and starts remain visible. Choose a case to inspect its final geometric state.')+'</p>'
    body += '<p class="formula">R=||r||₂/ε_primal · S=||s||₂/ε_dual<br>'+bi(
        '마지막 잔차 통과 ⇔ R≤1 AND S≤1 · F 간극 = F(z)−F*',
        'Final residual pass ⇔ R≤1 AND S≤1 · F gap = F(z)−F*')+'</p>'
    body += '<p class="small">'+bi(
        '통과 표시는 반올림 전 기록으로 정합니다. 최초 통과와 마지막 통과는 서로 다른 정보이며, 예산 안에서 없으면 그대로 표시합니다. F 간극은 원래 목적함수의 안정된 대수식 값입니다.',
        'Pass labels use the unrounded record. First pass and final pass are distinct; absence within the budget stays explicit. F gap uses the stable algebraic original-objective gap.')+'</p>'
    body += '<div class="admm-overview-groups">'
    for family,start in product(families,starts):
        sample = cases[(family,start,fractions[0],rhos[0])]
        body += f'<div class="admm-overview-group" data-admm-overview-group="{escape(family)}-{escape(start)}">'
        body += '<div class="scroll" tabindex="0" aria-label="All penalty outcomes / 벌점별 모든 결과"><table><caption>'
        family_label = bi('대각 행렬','Diagonal matrix') if family=='diagonal' else bi('결합 행렬','Coupled matrix')
        start_label = bi('영벡터 시작','Zero start') if start=='zero' else bi('반대 방향 시작','Opposite start')
        body += family_label+' · '+start_label+f'<br>A={escape(str(sample["inputs"]["A"]))} · z₀={escape(str(sample["inputs"]["z0"]))}</caption>'
        body += '<thead><tr><th scope="col">λ/λ_max</th>'
        body += ''.join(f'<th scope="col">ρ={rho:g}</th>' for rho in rhos)+'</tr></thead><tbody>'
        for fraction in fractions:
            body += f'<tr><th scope="row">{fraction:g}</th>'
            for rho in rhos:
                case = cases[(family,start,fraction,rho)]
                row, first = case['rows'][-1], case['first_residual_pass']
                passed = row['stopping_passed']
                body += f'<td data-admm-outcome="{escape(case["id"])}" data-admm-outcome-pass="{str(passed).lower()}">'
                body += '<span class="admm-outcome-status">'+(bi('마지막 통과','Final pass') if passed else bi('마지막 미충족','Final unmet'))+'</span><dl>'
                values = [('R','primal_ratio',row['primal_norm']/row['eps_primal']),
                          ('S','dual_ratio',row['dual_norm']/row['eps_dual']),
                          ('F gap','gap',row['stable_gap_z'])]
                for label,key,value in values:
                    body += '<div><dt>'+label+'</dt><dd data-admm-outcome-value="'+key+'">'+formatted(value)+'</dd></div>'
                body += '</dl><p class="admm-first-pass">'+bi('최초 k: ','First k: ')
                body += '<span data-admm-outcome-first>'+(
                    bi('예산 안에서 없음','none within budget') if first is None else str(first))+'</span></p>'
                context = f'{family} · λ/λ_max={fraction:g} · {start} · ρ={rho:g} · k={steps}'
                body += '<a data-admm-overview-link="'+escape(case['id'])+'" aria-label="'+escape(context)+'" href="#'+native_id(case['id'],steps)+'">'+bi(
                    f'k={steps} 상태 보기',f'Inspect k={steps}')+'</a></td>'
            body += '</tr>'
        body += '</tbody></table></div></div>'
    body += '</div><p class="small">'+bi('좁은 화면에서는 각 표를 좌우로 이동하세요. 표에 초점을 맞추고 화살표 키를 사용할 수도 있습니다.',
        'On narrow screens, scroll each table sideways, or focus it and use the arrow keys.')+'</p><p class="callout caution">'+bi(
        '같은 반복 횟수는 같은 계산량이나 실행 시간을 뜻하지 않습니다. 이 36개 유한 기록의 잔차 만족 여부는 최적성 인증서나 일반적인 ρ 순위가 아닙니다. 낮은 F 간극과 두 변수의 합의도 구분해서 읽으세요.',
        'Equal iteration counts do not mean equal work or runtime. Residual attainment in these 36 finite records is not an optimality certificate or a general ranking of ρ. Read a small F gap separately from agreement of the two variables.')+'</p></section>'
    return body
