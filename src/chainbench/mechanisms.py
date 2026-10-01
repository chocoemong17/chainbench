"""Symbolic reading aids, separate from the computed numerical evidence."""
from __future__ import annotations

from html import escape

from ._pages import bi

# Each step is (Korean label, English label, symbolic operation).
MAPS = {
    'gd-baseline': {
        'steps': [('현재점 읽기', 'Read the current point', 'xₖ'),
                  ('기울기 계산', 'Evaluate the gradient', 'gₖ = ∇f(xₖ)'),
                  ('곡률에 맞춘 이동', 'Take a curvature-scaled step', 'xₖ₊₁ = xₖ − gₖ/L')],
        'needs': ('기울기와 올바른 L', 'Gradient and a valid L'),
        'state': ('현재점 x', 'Current point x'),
        'work': ('기울기 평가와 벡터 갱신', 'Gradient evaluation and vector update'),
        'distinct': ('기억 항이나 prox 없이 현재 기울기를 사용합니다.', 'Uses the current gradient without a memory term or prox.'),
        'related': [('nesterov-1983', '외삽점에서 기울기를 계산하면?', 'What if the gradient is evaluated after extrapolation?'),
                    ('ista-vs-fista', '미분 불가능한 항을 추가하면?', 'What if a nonsmooth term is added?')],
    },
    'nesterov-1983': {
        'steps': [('외삽점 읽기', 'Read the extrapolated point', 'yₖ, tₖ'),
                  ('그 위치에서 기울기 이동', 'Step from that point', 'xₖ₊₁ = yₖ − ∇f(yₖ)/L'),
                  ('계수 갱신', 'Update the coefficient', 'tₖ₊₁ = (1+√(1+4tₖ²))/2'),
                  ('다음 외삽점', 'Form the next extrapolation', 'yₖ₊₁ = xₖ₊₁ + ((tₖ−1)/tₖ₊₁)(xₖ₊₁−xₖ)')],
        'needs': ('기울기와 올바른 L; 실제 구현은 smooth FISTA', 'Gradient and valid L; implemented as smooth FISTA'),
        'state': ('현재·이전 점, 외삽점 y, 계수 t', 'Current/previous points, extrapolated y and coefficient t'),
        'work': ('외삽점의 기울기 평가와 벡터 갱신', 'Gradient at the extrapolated point and vector updates'),
        'distinct': ('1983은 역사적 이름이며 갱신식은 2009 fixed-L FISTA의 g=0 특수 경우입니다.', 'The historical 1983 label uses the g=0 specialization of fixed-L FISTA (2009).'),
        'related': [('beck-teboulle-2009', 'g를 다시 넣으면?', 'What if g is restored?'),
                    ('polyak-1964', 'heavy-ball의 기억 항과 어떻게 다른가?', 'How does this differ from heavy-ball memory?')],
    },
    'polyak-1964': {
        'steps': [('현재점과 이전점', 'Read two points', 'xₖ, xₖ₋₁'),
                  ('현재 기울기', 'Use the current gradient', 'gₖ = Qxₖ − b'),
                  ('고정 운동량 더하기', 'Add fixed momentum', 'xₖ₊₁ = xₖ − αgₖ + β(xₖ−xₖ₋₁)')],
        'needs': ('SPD 이차함수와 μ,L에 맞춘 α,β', 'SPD quadratic and α,β tuned from μ,L'),
        'state': ('현재점과 이전점', 'Current and previous points'),
        'work': ('행렬-벡터 곱과 운동량 갱신', 'Matrix-vector product and momentum update'),
        'distinct': ('기울기는 현재점에서 계산하며, 이 구현의 운동량 계수는 고정됩니다. 8% 비교는 경험적입니다.', 'Evaluates the gradient at the current point with fixed coefficients. The 8% comparison is empirical.'),
        'related': [('nesterov-1983', '기울기를 외삽점에서 평가하는 방식과 비교', 'Compare with evaluating the gradient at an extrapolated point'),
                    ('hestenes-stiefel-1952', '같은 SPD 문제의 다른 방향 선택', 'A different direction choice for SPD problems')],
    },
    'hestenes-stiefel-1952': {
        'steps': [('잔차와 탐색 방향', 'Read residual and direction', 'r = b−Qx, p'),
                  ('방향별 길이', 'Choose a directional step', 'α = (rᵀr)/(pᵀQp)'),
                  ('점과 잔차 갱신', 'Update point and residual', 'x_next=x+αp; r_next=r−αQp'),
                  ('켤레 방향 유지', 'Form the next conjugate direction', 'β = ||r_next||²/||r||²; p_next = r_next+βp')],
        'needs': ('SPD 선형계와 행렬-벡터 곱', 'SPD linear system and matrix-vector products'),
        'state': ('보정점, 잔차, 탐색 방향', 'Correction point, residual and search direction'),
        'work': ('방향 계산과 실제 잔차 재계산에 행렬-벡터 곱 사용', 'Matrix-vector products for direction and true-residual checks'),
        'distinct': ('위는 정확한 산술의 방향 구조입니다. 실제 코드는 크기를 조정한 보정 방정식을 풀고 실제 잔차로 종료를 확인합니다.', 'This is the exact-arithmetic direction structure. Code solves a scaled correction equation and checks the true residual for stopping.'),
        'related': [('gd-baseline', '매번 최급 방향을 택하는 방식과 비교', 'Compare with choosing the steepest direction each time'),
                    ('rockafellar-1976', '선형계를 갱신마다 푸는 암시적 방법', 'An implicit method that solves a system each update')],
    },
    'jaggi-2013': {
        'steps': [('현재 실행 가능한 점', 'Read a feasible point', 'xₖ ∈ D; gₖ=∇f(xₖ)'),
                  ('선형 오라클', 'Call the linear oracle', 'sₖ ∈ argmin_s∈D ⟨gₖ,s⟩'),
                  ('선분 위 갱신', 'Move along a feasible segment', 'xₖ₊₁=(1−γₖ)xₖ+γₖsₖ; γₖ=2/(k+2)')],
        'needs': ('볼록 제약 집합 위 선형 최소화 오라클', 'Linear minimization oracle over a convex feasible set'),
        'state': ('현재 실행 가능한 점과 선택한 원자', 'Current feasible point and selected atom'),
        'work': ('기울기 평가, 선형 오라클, 볼록 결합', 'Gradient, linear oracle and convex combination'),
        'distinct': ('투영 대신 선형 오라클을 사용합니다. 이 고정 보폭은 선 탐색이 아닙니다.', 'Uses a linear oracle in place of projection. The scheduled step is not line search.'),
        'related': [('rockafellar-1976', '선형 오라클과 prox 하위 문제 비교', 'Compare a linear oracle with a proximal subproblem'),
                    ('gd-baseline', '제약 없이 기울기 방향으로 움직인다면?', 'What changes without constraints?')],
    },
    'rockafellar-1976': {
        'steps': [('현재점과 c', 'Read the point and parameter', 'xₖ, c>0'),
                  ('하위 문제를 정확히 풀기', 'Solve the subproblem exactly', '(I+cQ)xₖ₊₁ = xₖ+cb'),
                  ('새 점 채택', 'Accept the implicit point', 'xₖ₊₁ = prox_cf(xₖ)')],
        'needs': ('정확히 풀 수 있는 SPD 이차 하위 문제', 'An exactly solvable SPD quadratic subproblem'),
        'state': ('현재점 x와 고정된 Q,c', 'Current point x and fixed Q,c'),
        'work': ('갱신마다 선형계 풀이; 기울기 한 번과 같은 비용이 아닙니다.', 'A linear solve per update; not the same cost as one gradient.'),
        'distinct': ('전체 이차함수를 prox 안에서 풉니다. FISTA는 smooth 항을 선형화하고 nonsmooth 항에 prox를 적용합니다.', 'Proxes the whole quadratic. FISTA linearizes the smooth term and proxes the nonsmooth term.'),
        'related': [('gd-baseline', '명시적 이동과 암시적 풀이', 'Explicit step versus implicit solve'),
                    ('beck-teboulle-2009', '전체 prox와 분할된 proximal gradient', 'Whole-objective prox versus proximal gradient splitting')],
    },
    'beck-teboulle-2009': {
        'steps': [('외삽점에서 기울기', 'Evaluate at the extrapolated point', 'z = yₖ−∇f(yₖ)/L'),
                  ('nonsmooth 항의 prox', 'Apply the nonsmooth prox', 'xₖ₊₁=prox_(g/L)(z); L1: soft(z,λ/L)'),
                  ('가속 계수 갱신', 'Update acceleration', 'tₖ₊₁=(1+√(1+4tₖ²))/2'),
                  ('다음 외삽점', 'Prepare the next extrapolation', 'yₖ₊₁=xₖ₊₁+((tₖ−1)/tₖ₊₁)(xₖ₊₁−xₖ)')],
        'needs': ('L-smooth f의 기울기와 convex g의 정확한 prox', 'Gradient of L-smooth f and exact prox of convex g'),
        'state': ('현재·이전 점, 외삽점, 가속 계수', 'Current/previous points, extrapolation and acceleration coefficient'),
        'work': ('기울기 평가와 prox; 여기서는 좌표별 soft threshold', 'Gradient and prox; coordinate soft threshold in this fixture'),
        'distinct': ('prox는 정확한 수학 연산입니다. FISTA의 오차가 매번 감소한다고 가정하지 않습니다.', 'The prox is a mathematical operation. FISTA does not promise monotonic objective gaps.'),
        'related': [('ista-vs-fista', '외삽을 제거한 ISTA와 비교', 'Compare with ISTA after removing extrapolation'),
                    ('nesterov-1983', 'g=0이면 smooth FISTA', 'Set g=0 to obtain smooth FISTA')],
    },
    'ista-vs-fista': {
        'steps': [('같은 입력·시작점·예산', 'Use the same inputs and budget', '(problem, x₀, N)'),
                  ('두 경로 실행', 'Run both paths', 'ISTA: y=x; FISTA: extrapolated y'),
                  ('최종 오차 비교', 'Compare final gaps', 'gap_FISTA / gap_ISTA, when denominator is resolved')],
        'needs': ('동일한 composite 문제와 측정 가능한 비교 분모', 'Same composite problem and a resolved comparison denominator'),
        'state': ('비교를 위한 두 개의 독립 실행', 'Two independent runs for comparison'),
        'work': ('동일 반복 수를 비교하며 실행시간 순위는 측정하지 않습니다.', 'Compares equal iterations, without measuring a runtime ranking.'),
        'distinct': ('새 알고리즘이나 통과 정리가 아니라 INFO 비교입니다. 고정 검사는 바닥값 분모를 거부하고 stress는 unresolved로 보존합니다.', 'An INFO comparison, not a new algorithm or theorem test. The fixed check rejects floor denominators; stress retains them as unresolved.'),
        'related': [('beck-teboulle-2009', '가속 갱신식과 그 상계', 'The accelerated recurrence and its envelope'),
                    ('gd-baseline', 'g=0인 ISTA는 GD', 'ISTA with g=0 is gradient descent')],
    },
}

CSS = '''.method-flow{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px}
.method-flow li{position:relative;padding:16px;border:1px solid #dbe3ed;border-radius:14px;background:#f8fafc;min-width:0}
.method-flow li+li:before{content:'→';position:absolute;left:-13px;top:42%;color:#557694}
.method-flow strong{display:block;font-size:14px;margin-bottom:10px}.method-flow code{font-size:13px;line-height:1.7;display:block;overflow-wrap:anywhere}
.symbolic-label{font-size:10px;letter-spacing:.12em;color:#536d85;font-weight:750;margin-top:20px}
.comparison-controls{display:none;gap:16px;flex-wrap:wrap;margin:18px 0}.maps-js .comparison-controls{display:flex}
.comparison-controls label{flex:1;min-width:220px}.comparison-controls select{display:block;width:100%;margin-top:8px}
.comparison-controls select:focus-visible{outline:3px solid #ef9f47;outline-offset:3px}
.mechanism-compare{display:grid;grid-template-columns:1fr 1fr;gap:16px}.mechanism-card{min-width:0;background:#f8fafc;border:1px solid #dbe3ed;border-radius:16px;padding:20px}
.mechanism-card dt{font-size:11px;color:#58738f;font-weight:750;margin-top:14px}.mechanism-card dd{margin:4px 0;font-size:14px}
.related-methods{padding:12px 16px;border-radius:12px;background:#eef4f8;margin:16px 0;font-size:13px}
.related-methods a{font-weight:650}.related-methods p:last-child{margin-bottom:0}
@media(max-width:760px){.mechanism-compare{grid-template-columns:1fr}.method-flow{grid-template-columns:1fr}.method-flow li+li:before{content:'↓';left:50%;top:-20px}}
@media print{.comparison-controls{display:none!important}.mechanism-card[hidden]{display:block!important}}'''


def flow_html(slug):
    body = '<div class="symbolic-label">'+bi('기호로 읽는 갱신 흐름 · 수치 궤적과 구분',
        'SYMBOLIC UPDATE FLOW · separate from numerical trajectories')+'</div><ol class="method-flow">'
    for i, (ko, en, formula) in enumerate(MAPS[slug]['steps'], 1):
        body += '<li><strong>'+str(i)+' · '+bi(ko, en)+'</strong><code>'+escape(formula)+'</code></li>'
    return body+'</ol>'


def related_html(slug, available, names):
    body = '<aside class="related-methods"><strong>'+bi('이 아이디어를 다른 방법과 연결하기',
        'Connect this idea to another method')+'</strong>'
    for target, ko, en in MAPS[slug]['related']:
        body += '<p>'+bi(ko, en)+'<br>'
        if target in available:
            body += f'<a href="#{target}" data-lesson-link="{target}">'+escape(names[target])+'</a>'
        else:
            body += '<code>chainbench learn --focus '+target+' --output related.html</code>'
        body += '</p>'
    return body+'</aside>'


def comparison_html(slugs, names):
    if len(slugs) < 2:
        return ''
    body = '<section id="mechanism-comparison"><h2>'+bi('무엇을 계산하고, 무엇을 기억할까?',
        'What does each method compute and remember?')+'</h2><p>'+bi(
        '두 방법의 필요한 연산과 상태를 나란히 봅니다. 문제 계열과 한 단계의 비용이 달라 수렴 속도 순위표로 쓰지 않습니다.',
        'Compare the required operations and state. Problem families and per-step work differ, so this is not a convergence-speed ranking.')+'</p>'
    body += '<div class="comparison-controls">'
    for side, default in (('left', slugs[0]), ('right', 'beck-teboulle-2009' if 'beck-teboulle-2009' in slugs else slugs[1])):
        body += '<label>'+bi('첫 번째 방법' if side == 'left' else '두 번째 방법',
                            'First method' if side == 'left' else 'Second method')+f'<select data-compare="{side}">'
        for slug in slugs:
            body += f'<option value="{slug}"'+(' selected' if slug == default else '')+'>'+escape(names[slug])+'</option>'
        body += '</select></label>'
    body += '</div><div class="mechanism-compare" aria-live="polite">'
    for slug in slugs:
        body += f'<article class="mechanism-card" data-mechanism="{slug}"><h3>'+escape(names[slug])+'</h3><dl>'
        for key, ko, en in (('needs', '필요한 정보', 'Required information'),
                            ('state', '기억하는 상태', 'State'), ('work', '한 갱신의 핵심 작업', 'Work per update')):
            body += '<dt>'+bi(ko, en)+'</dt><dd>'+bi(*MAPS[slug][key])+'</dd>'
        body += '</dl><p class="small">'+bi(*MAPS[slug]['distinct'])+'</p>'
        body += f'<a href="#{slug}" data-lesson-link="{slug}">'+bi('질문·가정·실제 곡선 읽기', 'Read assumptions and the computed curve')+'</a></article>'
    return body+'</div></section>'


SCRIPT = '''(() => {
 document.documentElement.classList.add('maps-js');
 const left=document.querySelector('[data-compare="left"]'),right=document.querySelector('[data-compare="right"]');
 const update=changed=>{
  if(left.value===right.value){const other=changed===left?right:left;other.value=Array.from(other.options).find(o=>o.value!==changed.value).value;}
  document.querySelectorAll('[data-mechanism]').forEach(card=>{
   card.hidden=card.dataset.mechanism!==left.value&&card.dataset.mechanism!==right.value;
   card.style.order=card.dataset.mechanism===left.value?'0':'1';
  });
 };
 if(left&&right){left.addEventListener('change',()=>update(left));right.addEventListener('change',()=>update(right));update(left);}
 document.querySelectorAll('[data-lesson-link]').forEach(a=>a.addEventListener('click',()=>{
  const filter=document.getElementById('lesson-filter');if(filter&&filter.value){filter.value='';filter.dispatchEvent(new Event('input'));}
 }));
})();'''


def mechanism_record(slugs):
    return {'kind': 'symbolic-process-maps', 'notation': 'zero-based updates; initial t=1',
            'purpose': 'conceptual update structure, not computed samples or historical derivation',
            'topics': {slug: MAPS[slug] for slug in slugs}}
