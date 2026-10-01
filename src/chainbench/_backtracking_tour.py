"""A reading bridge between fixed-L FISTA and recorded backtracking trials."""
from ._pages import bi


def backtracking_comparison():
    body = '''<style>
/* Settle native fragment returns from large reports before the next click. */
html{scroll-behavior:auto}
.bt-bridge .bt-flows{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:18px 0}
.bt-bridge .bt-flow{padding:18px;border:1px solid #d8e2ee;border-radius:14px;background:#f7faff}
.bt-bridge ol{padding-left:24px}.bt-bridge li{padding:6px 0}.bt-bridge code{white-space:normal}
.bt-bridge .scroll{border:1px solid #d8e2ee;border-radius:12px}.bt-bridge table{min-width:720px}
.bt-bridge th,.bt-bridge td{width:33.33%}.bt-bridge td:first-child{width:22%}
@media(max-width:760px){.bt-bridge .bt-flows{grid-template-columns:1fr}}
</style><div class="bt-bridge" data-backtracking-comparison>'''
    body += '<h3>'+bi('같은 축소 계산, 다른 이동 크기 선택', 'Shared shrinkage, different step selection')+'</h3>'
    body += '<p>'+bi('두 흐름 모두 FISTA의 외삽점 y_k에서 시작합니다. 고정 L 보고서의 FISTA 부분과 비교하며, 같은 보고서에 있는 ISTA에는 이 외삽이 없습니다. 아래 흐름은 기호 설명이고 실제 좌표는 각 보고서에 있습니다.',
        'Both flows start at FISTA’s extrapolated y_k. The comparison uses the FISTA part of the fixed-L report; its ISTA run has no extrapolation. These are symbolic flows; the reports retain the actual coordinates.')+'</p><div class="bt-flows">'
    flows = [
        ('fixed', '알려진 곡률로 한 번 계산', 'Compute once with a known curvature', [
            ('L=9', '매 단계 같은 곡률을 사용합니다.', 'Keep the same curvature at every update.'),
            ('z=y_k−∇f(y_k)/9', '외삽점에서 기울기 이동을 합니다.', 'Take a gradient step from the anchor.'),
            ('x_k=soft(z,λ/9)', '한 후보를 계산해 다음 점으로 씁니다.', 'Compute one candidate as the next iterate.'),
            ('t_next, y_next', '다음 외삽점을 만들고 L=9로 이어갑니다.', 'Form the next anchor and continue with L=9.')]),
        ('backtracking', '후보가 통과할 때까지 검사', 'Test candidates until one passes', [
            ('L=L_{k−1}', '이전 단계에서 채택한 곡률로 시작합니다.', 'Start with the previously accepted curvature.'),
            ('z=y_k−∇f(y_k)/L; q=soft(z,λ/L)', '현재 L로 이동과 축소를 계산합니다.', 'Compute the step and shrinkage at this L.'),
            ('F(q)≤Q_L(q,y_k)?', '거부되면 L←2L로 바꾸고 같은 y_k에서 다시 시도합니다.', 'On rejection, set L←2L and retry from the same y_k.'),
            ('x_k=q; L_k=L; t_next, y_next', '처음 통과한 후보와 L을 다음 단계로 넘깁니다.', 'Carry the first passing candidate and its L into the next update.')]),
    ]
    for name,ko,en,steps in flows:
        body += f'<div class="bt-flow" data-backtracking-flow="{name}"><h4>'+bi(ko,en)+'</h4><ol>'
        for formula,ko,en in steps:
            body += '<li><code>'+formula.replace('<','&lt;')+'</code><br>'+bi(ko,en)+'</li>'
        body += '</ol></div>'
    body += '</div><div class="scroll" tabindex="0" role="region" aria-label="Fixed L and backtracking FISTA comparison"><table><thead><tr>'
    for ko,en in [('읽을 항목','What to compare'),('고정 L 보고서의 FISTA','FISTA in the fixed-L report'),('Backtracking FISTA','Backtracking FISTA')]:
        body += '<th scope="col">'+bi(ko,en)+'</th>'
    body += '</tr></thead><tbody>'
    rows = [
        ('inputs',('입력','Inputs'),('λ 3종 × 시작점 3종 = 9개 FISTA 실행','3 λ values × 3 starts = 9 FISTA runs'),
            ('λ 3종 × 시작점 4종 × L₀ 3종 = 36개 실행','3 λ values × 4 starts × 3 L₀ guesses = 36 runs')),
        ('curvature',('곡률과 이동 크기','Curvature and step'),('L=9, 이동 크기 1/9','L=9, step size 1/9'),
            ('L₀∈{0.25,1,4}; 거부할 때 L을 2배, 이동 크기 1/L','L₀∈{0.25,1,4}; double L on rejection, step size 1/L')),
        ('threshold',('축소 문턱','Shrinkage threshold'),('λ/9','λ/9'),('λ/L','λ/L')),
        ('test',('채택 기준','Acceptance'),('9가 두 곡률 1,9를 덮으므로 별도 후보 탐색 없음','9 bounds both curvatures 1 and 9; no candidate search'),
            ('후보 q에서 F(q)≤Q_L(q,y)를 처음 만족','First candidate q with F(q)≤Q_L(q,y)')),
        ('carry',('다음 단계로 넘기는 L','Curvature carried forward'),('항상 9','Always 9'),
            ('채택한 L 유지; 다시 초기화하거나 줄이지 않음','Keep the accepted L; no reset or decrease')),
        ('envelope',('k≥1의 논문 상한','Source envelope for k≥1'),('18R²/(k+1)², α=1','18R²/(k+1)², α=1'),
            ('36R²/(k+1)², α=η=2, 모든 L₀≤9','36R²/(k+1)², α=η=2, all L₀≤9')),
        ('work',('갱신 수와 후보 수','Updates and trials'),('채택 갱신마다 후보 하나','One candidate per accepted update'),
            ('채택 갱신 안에 여러 거부 후보가 있을 수 있음','An accepted update may contain several rejected trials')),
    ]
    for key,label,fixed,adaptive in rows:
        body += f'<tr data-backtracking-meaning="{key}"><td>'+bi(*label)+'</td><td>'+bi(*fixed)+'</td><td>'+bi(*adaptive)+'</td></tr>'
    body += '</tbody></table></div><p class="small">'+bi('두 보고서의 목적함수는 같은 ½||diag(1,3)x−(1.4,−2.4)||²+λ||x||₁입니다. 첫 9개 목적함수·시작점 쌍이 겹치며, backtracking은 시작점 하나와 L₀ 추정치 세 가지를 더합니다. R은 각 실제 시작점에서 해당 최적해까지의 거리입니다.',
        'Both use ½||diag(1,3)x−(1.4,−2.4)||²+λ||x||₁. They share nine objective/start pairs; backtracking adds one start and three initial guesses. R is each actual start’s distance to its own optimum.')+'</p>'
    body += '<p class="callout">'+bi('후보에서의 통과는 함수 전체의 상한 인증이 아닙니다. FISTA는 이전 x보다 목적값이 커질 수 있습니다. 두 이론 곡선이나 같은 갱신 수를 실행 시간·방법의 우열로 읽지 마세요. 후보 수와 그림을 만드는 계산량도 실행 시간과는 다릅니다.',
        'Passing at one candidate is not a global upper-model certificate. FISTA may increase the objective relative to the previous x. Neither envelope nor equal update counts rank methods by runtime. Trial counts and work spent drawing figures also differ from timings.')+'</p>'
    body += '<p><a href="https://www.tau.ac.il/~becka/FISTA.pdf">Beck–Teboulle (2009): fixed-L Eqs. (4.1)–(4.3), p.193 / PDF 11; backtracking panel p.194 / PDF 12; Theorem 4.4, p.195 / PDF 13</a></p>'
    return body+'</div>'
