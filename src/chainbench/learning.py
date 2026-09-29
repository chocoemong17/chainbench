"""Bilingual, offline reading guide for selected public optimization results."""
from __future__ import annotations

import base64
from dataclasses import asdict
from html import escape

import numpy as np

from ._pages import bi, evidence, page
from ._plot_audit import evidence_record, validate_chart_result
from .checks import CHECKS, run_check
from .reporting import SOURCE_LINKS, result_status
from .stories import STORIES
from .visuals import ChartSpec, LineSeries, build_check_chart, render_line_chart

# These are explanatory notes, not new methods or transcriptions of entire papers.
# Formula/source mapping is independently documented in docs/SOURCE_MAP.md.
LESSONS = {
    'gd-baseline': {
        'name': 'Gradient descent', 'category': 'smooth',
        'question': ('기울기만 보고도 최적해에 가까워질 수 있을까?', 'Can gradients alone give a useful convergence guarantee?'),
        'mechanism': ('현재 기울기의 반대 방향으로 1/L만큼 이동합니다. 곡률 상한 L에 맞춘 보수적인 한 걸음이 기준선이 됩니다.', 'Move opposite the current gradient with step 1/L. A curvature-aware step provides the baseline.'),
        'assumptions': ('볼록하고 미분 가능한 f, L-Lipschitz 기울기, 최적해 존재, R=‖x₀−x*‖. 여기의 상계는 k≥1에 적용합니다.', 'Convex differentiable f with L-Lipschitz gradient and an optimizer; R=||x0-x*||. The displayed bound applies for k>=1.'),
        'recurrence': 'xₖ₊₁ = xₖ − ∇f(xₖ)/L',
        'formula': 'f(xₖ) − f* ≤ L R² / (2k)',
        'reason': ('매끄러움으로 한 단계의 감소량을 제어하고, 볼록성으로 그 감소를 최적해까지의 거리와 연결합니다. 이 관계를 반복해서 합칩니다.', 'Smoothness controls one-step decrease; convexity links it to distance from an optimizer. Summing the inequalities yields the bound.'),
        'reading': ('실선은 측정한 오차, 점선은 보장하는 상계입니다. 아래 비율 그래프에서 1 이하면 이 표본이 상계 안에 있습니다. 곡선의 기울기를 맞추는 회귀가 아닙니다.', 'The solid curve is the observed gap and the dashed curve an upper bound. A ratio <=1 satisfies that bound at this sample; no rate is fitted from the slope.'),
        'limit': ('이 기준 상계가 가장 타이트한 상계라는 뜻은 아닙니다. gd-tight 예제는 공개 문헌의 더 타이트한 별도 결과를 보여줍니다.', 'This baseline envelope is not claimed to be tight. The separate gd-tight case study illustrates a sharper public result.'),
        'command': 'chainbench case-study gd-tight --horizon 20 --lang ko --output tight.html',
    },
    'nesterov-1983': {
        'name': 'Nesterov-style acceleration', 'category': 'smooth',
        'question': ('이전 이동을 활용하면 일반적인 보장을 개선할 수 있을까?', 'Can extrapolation improve the general worst-case rate?'),
        'mechanism': ('현재점에서 바로 기울기를 쓰는 대신 이전 이동을 섞은 y에서 평가합니다. 실제 코드는 2009년 fixed-L FISTA의 g=0 특수 경우입니다.', 'Evaluate the gradient at an extrapolated point y. This implementation is the g=0 specialization of fixed-L FISTA (2009).'),
        'assumptions': ('볼록하고 L-smooth인 f, 고정된 올바른 L, 정확한 기울기. 시작 t₀=1, y₀=x₀. nesterov-1983은 역사적 명칭입니다.', 'Convex L-smooth f, valid fixed L and exact gradients. Start t0=1, y0=x0. nesterov-1983 is a historical label.'),
        'recurrence': 'xₖ₊₁ = yₖ − ∇f(yₖ)/L\ntₖ₊₁ = (1 + √(1 + 4tₖ²))/2\nyₖ₊₁ = xₖ₊₁ + ((tₖ−1)/tₖ₊₁)(xₖ₊₁−xₖ)',
        'formula': 'f(xₖ) − f* ≤ 2 L R² / (k+1)²',
        'reason': ('t의 재귀식이 만드는 가중치를 이용해 오차와 거리로 구성한 양을 제어합니다. 가중치가 k² 크기로 자라는 것이 보장의 핵심입니다.', 'The t recurrence supplies weights for an error-and-distance potential. Their quadratic growth in k is central to the guarantee.'),
        'reading': ('O(1/k²)는 모든 허용 함수에 대한 상계의 차수입니다. 이 한 그래프가 반드시 k⁻² 모양이어야 하는 것은 아닙니다.', 'O(1/k²) describes the bound over the admissible class. A particular curve need not have exactly a k^-2 slope.'),
        'limit': ('1983년 논문의 원래 알고리즘을 그대로 옮긴 것은 아닙니다. 각 반복에서 GD보다 항상 낫다는 보장도 아닙니다.', 'Not a literal transcription of the 1983 algorithm, nor a guarantee of beating GD at every iteration.'),
        'command': 'chainbench sweep --preset quadratic --parameter condition_number --values 10 100 1000 --methods gd smooth-fista --output sweep.html',
    },
    'polyak-1964': {
        'name': 'Polyak heavy-ball', 'category': 'quadratic',
        'question': ('이전 이동의 관성이 느린 방향의 수렴에 도움이 될까?', 'Can momentum accelerate slowly contracting modes?'),
        'mechanism': ('이전 이동량을 현재 기울기 단계에 더합니다. 이 실험은 강볼록 이차함수의 고유방향별 선형 재귀를 다룹니다.', 'Add the previous displacement to the gradient step. This experiment concerns linear recurrences in eigenmodes of an SPD quadratic.'),
        'assumptions': ('0<μ<L인 이차함수에 대한 고전적 튜닝입니다. 일반적인 비선형 강볼록 함수 전체로 확장하지 않습니다.', 'Classical tuning on a quadratic with 0<mu<L; not a blanket guarantee for nonlinear strongly convex functions.'),
        'recurrence': 'xₖ₊₁ = xₖ − α∇f(xₖ) + β(xₖ−xₖ₋₁)\nα = 4/(√L+√μ)²; β = ((√L−√μ)/(√L+√μ))²',
        'formula': 'ρ = (√L−√μ)/(√L+√μ)',
        'reason': ('각 고유방향에서 특성다항식의 근이 점근적인 거동을 제어합니다. 초반 과도현상·중근·진동 때문에 유한 단계의 오차비는 달라질 수 있습니다.', 'Characteristic roots control each eigenmode. Transients, repeated roots and oscillations can change finite-step error ratios.'),
        'reading': ('이 그래프는 오차 자체가 아니라 연속 오차의 비입니다. 이전 오차가 1e−10보다 큰 비율 중 마지막 최대 20개의 중앙값을 ρ와 비교합니다.', 'This is a consecutive-error ratio plot. The check compares rho with the median of up to 20 final ratios whose previous error exceeds 1e-10.'),
        'limit': ('허용오차 8%는 이 프로젝트의 경험적 회귀검사 기준이며 논문 정리의 상수가 아닙니다.', 'The 8% tolerance is this project’s empirical regression rule, not a theorem constant.'),
        'command': 'chainbench experiment --preset quadratic --methods gd heavy-ball --condition-number 100 --format html --output momentum.html',
    },
    'hestenes-stiefel-1952': {
        'name': 'Conjugate gradient', 'category': 'quadratic',
        'question': ('매번 같은 방향으로 내려가는 대신 이전 탐색을 활용할 수 있을까?', 'Can conjugate directions avoid repeating previous search work?'),
        'mechanism': ('Qx=b를 풀면서 잔차와 Q-켤레 탐색방향을 갱신합니다. 그래프의 오차는 유클리드 노름이 아니라 Q-에너지 노름입니다.', 'Solve Qx=b by updating residuals and Q-conjugate directions. The plotted error is the Q-energy norm, not Euclidean distance.'),
        'assumptions': ('대칭 양의 정부호 Q, κ=L/μ. 수렴 상계는 정확 산술 분석이고, 구현은 실제 잔차를 다시 확인하는 유한정밀도 연산입니다.', 'SPD Q, kappa=L/mu. The bound is an exact-arithmetic result; this finite-precision implementation rechecks the true residual.'),
        'recurrence': 'αₖ = (rₖᵀrₖ)/(pₖᵀQpₖ)\nxₖ₊₁ = xₖ + αₖpₖ; rₖ₊₁ = rₖ − αₖQpₖ\npₖ₊₁ = rₖ₊₁ + (‖rₖ₊₁‖²/‖rₖ‖²)pₖ',
        'formula': '‖xₖ−x*‖Q ≤ 2 ((√κ−1)/(√κ+1))ᵏ ‖x₀−x*‖Q',
        'reason': ('오차를 Q의 다항식으로 표현하고 스펙트럼 구간에서 그 다항식을 작게 만드는 분석을 사용합니다. 출처는 Shewchuk의 식 (52)입니다.', 'The error is represented by a polynomial in Q and bounded over its spectrum. The displayed envelope is Shewchuk’s equation (52).'),
        'reading': ('k=0의 비율은 항상 0.5이므로 검사 통계에서는 제외합니다. 작은 잔차와 작은 전방오차는 조건수가 크면 다른 의미입니다.', 'k=0 always gives ratio 0.5 and is excluded from the statistic. A small residual need not mean small forward error when conditioning is poor.'),
        'limit': ('정확 산술에서의 n단계 종료를 모든 실수 연산에서 보장하지 않습니다. 반복 수가 같아도 GD와 계산량이 같지는 않습니다.', 'No universal n-step termination promise in floating point; equal CG and GD update counts are not equal work.'),
        'command': 'chainbench sweep --preset quadratic --parameter condition_number --values 10 100 1000 --methods gd cg --output cg.html',
    },
    'jaggi-2013': {
        'name': 'Frank–Wolfe', 'category': 'constrained',
        'question': ('비싼 투영 대신 선형 문제 하나로 제약을 지킬 수 있을까?', 'Can a linear oracle replace projection while retaining feasibility?'),
        'mechanism': ('기울기에 대한 선형 최소점을 찾고 현재점과 볼록결합합니다. 심플렉스에서는 한 꼭짓점을 고르는 연산입니다.', 'Minimize the linearization, then take a convex combination with the current point. On the simplex the oracle chooses a vertex.'),
        'assumptions': ('컴팩트 볼록 집합, 볼록 미분가능 목적함수, 유한 곡률, 정확 선형 최소화. 여기서는 심플렉스 이차함수 C_f=2입니다.', 'Compact convex domain, differentiable convex objective, bounded curvature and exact linear oracle. Here the simplex quadratic has C_f=2.'),
        'recurrence': 'sₖ ∈ argminₛ∈D ⟨∇f(xₖ),s⟩\nxₖ₊₁ = (1−γₖ)xₖ + γₖsₖ; γₖ=2/(k+2)',
        'formula': 'f(xₖ) − f* ≤ 2 C_f/(k+2), k≥1',
        'reason': ('곡률은 선형 근사가 빗나가는 정도를 제어합니다. 선형 오라클의 gap은 볼록성으로 최적성 오차의 상계가 됩니다.', 'Curvature controls linearization error. Convexity makes the oracle dual gap an upper bound on suboptimality.'),
        'reading': ('Jaggi 논문의 더 큰 메시지는 투영 없는 최적화, dual gap, 희소·저랭크 구조입니다. 이 화면은 그중 primal-gap 상계만 선택했습니다.', 'Jaggi’s broader story includes projection-free updates, dual gaps, sparsity and low rank. This page selects the primal-gap bound.'),
        'limit': ('원 논문의 전체 응용·근사 오라클 실험을 재현한 것은 아닙니다.', 'Not a reproduction of all applications or approximate-oracle experiments in the paper.'),
        'command': 'chainbench sweep --preset simplex --parameter dimension --values 10 30 80 --output simplex.html',
    },
    'rockafellar-1976': {
        'name': 'Proximal point', 'category': 'quadratic',
        'question': ('멀리 이동하는 비용을 더해 하위문제를 풀면 어떻게 될까?', 'What happens when each step solves a regularized subproblem?'),
        'mechanism': ('f(z)+‖z−xₖ‖²/(2c)를 최소화합니다. 이차함수에서는 선형계를 정확히 푸는 한 번의 resolvent 단계가 됩니다.', 'Minimize f(z)+||z-xk||²/(2c). On a quadratic this is a resolvent step computed by solving a linear system.'),
        'assumptions': ('여기서는 μ>0인 이차함수, c>0, 정확한 하위문제 해를 사용합니다. Rockafellar의 일반 단조 연산자 이론 전체와는 다릅니다.', 'This demonstration uses an SPD quadratic, c>0 and exact subproblem solves, not the full monotone-operator theory.'),
        'recurrence': 'xₖ₊₁ = (I+cQ)⁻¹(xₖ+cb)',
        'formula': '‖xₖ₊₁−x*‖₂ ≤ q‖xₖ−x*‖₂; q=1/(1+cμ)',
        'reason': ('오차에 작용하는 (I+cQ)⁻¹의 가장 큰 고유값이 1/(1+cμ)입니다. 따라서 노름이 그 비율 이하로 줄어듭니다.', 'The largest eigenvalue of (I+cQ)^-1 is 1/(1+c*mu), giving the Euclidean contraction.'),
        'reading': ('큰 c가 반복 수를 줄여 보여도 선형계 풀이 비용을 공짜로 취급하면 안 됩니다. 아래 검사는 이전 오차가 1e−12를 넘는 단계만 사용합니다.', 'A larger c can improve iteration contraction, but the linear solve is not free. The ratio check uses only previous errors above 1e-12.'),
        'limit': ('근사 proximal 단계의 정확도나 일반 비선형 연산자에서 같은 실험을 했다는 뜻은 아닙니다.', 'No claim that this experiment covers inexact proximal steps or general nonlinear operators.'),
        'command': 'chainbench experiment --preset quadratic --methods gd proximal-point --format html --output proximal.html',
    },
    'beck-teboulle-2009': {
        'name': 'FISTA', 'category': 'composite',
        'question': ('희소성을 만드는 thresholding을 빠르게 할 수 있을까?', 'Can simple shrinkage-thresholding be accelerated?'),
        'mechanism': ('매끄러운 부분의 기울기 단계 뒤에 prox를 적용하고 이전 두 점으로 외삽합니다. L1 항의 prox는 soft thresholding입니다.', 'Apply a proximal map after a smooth gradient step, then extrapolate. For an L1 term, the proximal map is soft thresholding.'),
        'assumptions': ('F=f+g: f는 볼록 L-smooth, g는 볼록이고 prox 계산 가능, 최적해 존재. 여기서는 고정 L과 대각 LASSO를 사용합니다.', 'F=f+g with convex L-smooth f, convex proximable g and an optimizer. This uses fixed L and diagonal LASSO.'),
        'recurrence': 'xₖ₊₁ = prox_(g/L)(yₖ−∇f(yₖ)/L)\ntₖ₊₁=(1+√(1+4tₖ²))/2\nyₖ₊₁=xₖ₊₁+((tₖ−1)/tₖ₊₁)(xₖ₊₁−xₖ)',
        'formula': 'F(xₖ) − F* ≤ 2 L R²/(k+1)²',
        'reason': ('ISTA의 단순한 prox-gradient 연산을 유지하면서 외삽으로 더 빠른 일반 수렴 상계를 얻습니다. 단조 감소는 별도 보장이 아닙니다.', 'Extrapolation improves the general bound while retaining the simple proximal-gradient operation. Monotone objective decrease is not promised.'),
        'reading': ('합성 목적함수의 전체 gap을 봅니다. 대각 문제의 최적해를 soft thresholding으로 알 수 있어 다른 solver의 근사값을 정답으로 쓰지 않습니다.', 'Plot the full composite gap. The diagonal fixture has a soft-threshold optimizer, so another approximate solver is not used as ground truth.'),
        'limit': ('논문은 선형 역문제와 이미지 복원을 다룹니다. 여기의 대각 예제가 실제 이미지 복원 benchmark를 대신하지는 않습니다.', 'The paper addresses linear inverse problems and image restoration. This diagonal fixture is not a realistic deblurring benchmark.'),
        'command': 'chainbench sweep --preset diagonal-lasso --parameter lam --values 0.01 0.12 1 --methods ista fista --output sparsity.html',
    },
    'ista-vs-fista': {
        'name': 'ISTA ↔ FISTA', 'category': 'observation',
        'question': ('더 좋은 상계가 매 순간 더 좋은 실제 결과를 뜻할까?', 'Does a better bound imply a better iterate at every step?'),
        'mechanism': ('같은 문제·시작점·반복 예산에서 두 방법을 실행합니다. 그림은 직접 측정한 두 궤적이지 일반적인 우열 증명이 아닙니다.', 'Run both methods on the same problem, start and budget. The plot contains observations, not a universal ordering.'),
        'assumptions': ('한 개의 대각 LASSO와 같은 L을 사용합니다. 각 실행의 전체 목적함수 gap을 비교합니다.', 'One diagonal LASSO instance with the same L; compare full composite objective gaps.'),
        'recurrence': 'ISTA: gradient + prox\nFISTA: gradient + prox + extrapolation',
        'formula': 'Observed ratio = final FISTA gap / final ISTA gap',
        'reason': ('일반 상계의 개선과 특정 문제의 유한 단계 관측은 서로 다른 주장입니다. 따라서 이 항목은 통과·실패 판정 없이 INFO로 남깁니다.', 'An improved class-wide bound and finite observations on a particular problem are different claims. This item remains INFO rather than pass/fail.'),
        'reading': ('곡선이 교차하더라도 정리가 틀렸다는 뜻은 아닙니다. 같은 반복 수가 동일한 실행 시간이라는 주장도 하지 않습니다.', 'A curve crossing does not refute the rate theorem. Equal iteration counts do not establish equal runtime.'),
        'limit': ('한 예제를 근거로 모든 데이터셋·모든 반복에서 FISTA가 우세하다고 결론 내리지 않습니다.', 'Do not infer dominance for all datasets and all iterations from one example.'),
        'command': 'chainbench experiment --preset diagonal-lasso --lam 0.5 --format html --output compare.html',
    },
}


def ratio_chart(slug: str, chart: ChartSpec) -> ChartSpec | None:
    if slug in ('polyak-1964', 'ista-vs-fista'):
        return None  # Empirical tail statistic and informational ratio are not pointwise bounds.
    a, b = (np.asarray(s.y) for s in chart.series)
    x = np.asarray(chart.series[0].x)
    if slug == 'rockafellar-1976':
        valid = a[:-1] > 1e-12
        q = b[1]/b[0]
        ratios, x = a[1:][valid]/(q*a[:-1][valid]), x[1:][valid]
    else:
        start = 1 if slug == 'hestenes-stiefel-1952' else 0
        ratios, x = (a/b)[start:], x[start:]
    return ChartSpec('Observed / bound: at most 1 satisfies the sampled inequality', 'iteration k', 'normalized ratio',
                     (LineSeries('observed / bound', tuple(x), tuple(ratios)),
                      LineSeries('threshold 1', tuple(x), tuple(np.ones(len(x))), 'bound')), 'linear')


def learning_html(focus: str | None = None, lang: str = 'en') -> str:
    if focus is not None and focus not in LESSONS:
        raise ValueError('unknown learning topic')
    slugs = [focus] if focus else list(CHECKS)
    results = [run_check(slug) for slug in slugs]
    charts = {slug: build_check_chart(slug) for slug in slugs}
    ratios = {}
    cards, sections = [], []
    for result in results:
        slug = result.slug
        lesson, chart = LESSONS[slug], charts[slug]
        validate_chart_result(result, chart)
        svg = render_line_chart(chart)
        thumbnail = base64.b64encode(svg.encode()).decode()
        search = escape(' '.join((slug, lesson['name'], lesson['category'], *lesson['question'])), quote=True)
        cards.append(f'<a class="card" href="#{slug}" data-search="{search}"><span class="badge">'
                     + escape(lesson['category']) + '</span><h3>' + escape(lesson['name']) + '</h3><div>'
                     + bi(*lesson['question']) + f'</div><img alt="{escape(lesson["name"])} preview" src="data:image/svg+xml;base64,{thumbnail}"></a>')
        normalized = ratio_chart(slug, chart)
        ratio_html = ''
        if normalized is not None:
            ratios[slug] = asdict(normalized)
            ratio_html = '<details><summary>' + bi('상계와의 비율 보기: 1을 넘는가?', 'Inspect normalized ratio: does it exceed 1?') + '</summary><div class="plot">' + render_line_chart(normalized) + '</div></details>'
        sections.append(f'<section id="{slug}" data-search="{search}"><div class="eyebrow">'
                        + escape(STORIES[slug].source) + '</div><h2>' + bi(*lesson['question']) + '</h2>'
                        + '<p>' + bi(*lesson['mechanism']) + '</p><div class="pairs"><div><h3>'
                        + bi('어떤 조건에서?', 'Under which assumptions?') + '</h3><p>' + bi(*lesson['assumptions'])
                        + '</p></div><div><h3>' + bi('어떤 업데이트인가?', 'Which update?')
                        + '</h3><div class="formula">' + escape(lesson['recurrence']) + '</div></div></div>'
                        + '<div class="formula">' + escape(lesson['formula']) + '</div><div class="plot">' + svg + '</div>'
                        + '<p class="callout">' + bi(*lesson['reading']) + '</p>' + ratio_html
                        + '<p><span class="badge">' + result_status(result) + '</span> '
                        + bi('이 실행의 검사 통계', 'Statistic from this run') + f': {result.observed:.6g}</p>'
                        + '<details><summary>' + bi('왜 이런 결과가 나오는가?', 'Why does this result make sense?')
                        + '</summary><p>' + bi(*lesson['reason']) + '</p></details>'
                        + '<p class="callout caution">' + bi(*lesson['limit']) + '</p><details><summary>'
                        + bi('다음에 직접 바꿔볼 실험', 'A controlled experiment to try next') + '</summary><pre>'
                        + escape(lesson['command']) + '</pre></details><p class="small"><a href="'
                        + SOURCE_LINKS[slug] + '">' + escape(result.reference) + '</a></p></section>')
    record = evidence_record(results, charts)
    record['kind'] = 'chainbench.learning'
    record['normalized_charts'] = ratios
    record['source_map'] = {s: SOURCE_LINKS[s] for s in slugs}
    intro = bi('논문 이름이나 숫자보다 먼저 질문을 고르세요. 무엇이 달라지는지, 어떤 조건에서 보장되는지, 실제 곡선에서 무엇을 읽어야 하는지 연결합니다.', 'Start with a question, not a paper title or number. Connect the mechanism, its assumptions and the observation on the plot.')
    guide = ('<div class="callout">' + bi('읽는 순서: 질문 → 업데이트 → 보장 → 관측. 관측과 기준 곡선은 각 범례로 구분하세요. ISTA/FISTA 비교의 두 선은 모두 관측입니다. 이 페이지에서 새 최적화를 실행하지 않습니다.', 'Read: question → update → guarantee → observation. Use each legend to distinguish observations from reference curves. Both ISTA/FISTA curves are observations. This page does not run a new optimizer.') + '</div>'
             + '<div class="controls"><label for="lesson-filter">' + bi('방법·키워드 찾기', 'Find a method or keyword')
             + '</label><input id="lesson-filter" type="search" placeholder="FISTA / CG / 기울기"></div>')
    glossary = '<details class="panel"><summary>' + bi('처음 보는 용어', 'A small glossary') + '</summary><p>' + bi('gap: 현재 목적함수 값과 최적값의 차이. bound: 조건을 만족하는 문제들에 대한 보장 상계. κ: 이차함수의 최대/최소 곡률 비. residual: 방정식을 얼마나 만족하는지. INFO: 관측일 뿐, 통과 판정이 아님.', 'Gap: objective error relative to an optimum. Bound: guaranteed upper envelope under stated assumptions. Kappa: largest/smallest curvature ratio. Residual: equation error. INFO: observation without a pass/fail guarantee.') + '</p></details>'
    return page('From paper to understanding', intro, guide + '<div class="cards">' + ''.join(cards) + '</div>' + glossary + ''.join(sections) + evidence(record, 'learning-evidence.json'), lang=lang)
