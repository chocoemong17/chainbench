"""Curated reading questions tied to bounded, existing CLI workflows."""
from __future__ import annotations

import copy
from html import escape

from ._pages import bi

CSS = """
html{scroll-behavior:auto}
.workflow-cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin:14px 0}
.workflow-cards article{border:1px solid #d7e0e8;border-radius:12px;padding:18px;min-width:0;background:#f8fafc}
.workflow-cards h4{font-size:17px;margin:9px 0}.workflow-cards p{font-size:14px;line-height:1.7}
.workflow-cards pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;line-height:1.6}
.workflow-cards .workflow-open{display:inline-block;font-weight:650;margin:6px 0}
.workflow-cards summary{font-size:13px}.workflow-cards .badge{font-size:10px;white-space:normal;overflow-wrap:anywhere;max-width:100%;line-height:1.6}
@media(max-width:700px){.workflow-cards{grid-template-columns:1fr}}
"""

WORKFLOWS = {
    'shewchuk': {
        'report': 'shewchuk.html', 'label': 'PUBLISHED SETUP + CONTROLLED STARTS',
        'question': ['같은 선형계에서 방향을 기억하면?', 'What does remembering directions change on one system?'],
        'scope': ['원문의 2×2 문제와 9개 추가 시작점. 실제 경로·내적·고유값별 오차를 연결합니다.',
                  'The published 2×2 problem and nine added starts. Connect actual paths, inner products and eigenmode errors.'],
        'command': ['reproduce', 'shewchuk-1994', '--steps', '12'],
    },
    'deblur': {
        'report': 'deblur.html', 'label': 'PUBLISHED IMAGE PROTOCOL · NO NOISE',
        'question': ['관측을 잘 맞추면 원본 영상도 복원될까?', 'Does fitting the observation recover the clean image?'],
        'scope': ['Figure 5의 64×64·λ=0 조건, 10,000회. 잔차와 원본 기준 RMSE를 구분합니다.',
                  'Figure 5 protocol: 64×64, lambda=0, 10,000 updates. Distinguish residual from clean-reference RMSE.'],
        'command': ['reproduce', 'fista-deblurring', '--steps', '10000'],
    },
    'wavelet': {
        'report': 'wavelet.html', 'label': 'PUBLISHED IMAGE PROTOCOL · DECLARED NOISE',
        'question': ['잡음이 있으면 실제 Haar 계수를 왜 줄일까?', 'Why shrink actual Haar coefficients when there is noise?'],
        'scope': ['Figure 4의 256×256·λ=10⁻⁴ 조건, seed 0, 200회. 원 잡음 표본은 아니며 최적값은 미상입니다.',
                  'Figure 4 protocol: 256×256, lambda=10⁻⁴, seed 0, 200 updates. New declared noise; optimum unknown.'],
        'command': ['reproduce', 'fista-wavelet', '--steps', '200', '--seed', '0'],
    },
    'cycle': {
        'report': 'heavy-ball.html', 'label': 'PUBLISHED COUNTEREXAMPLE + ADDED STARTS',
        'question': ['이차함수에서 쓰던 튜닝을 그대로 옮기면?', 'What if the same quadratic tuning is used beyond quadratics?'],
        'scope': ['Lessard–Recht–Packard의 비이차 강볼록 반례와 8개 추가 시작점. 50회, 실제 주기·기울기 비교.',
                  'Lessard–Recht–Packard nonquadratic strongly convex counterexample and eight added starts. 50 updates, cycle and gradient diagnostics.'],
        'command': ['reproduce', 'lessard-2016', '--steps', '50'],
    },
    'simplex': {
        'report': 'simplex.html', 'label': 'CONTROLLED GEOMETRY · 12 CASES',
        'question': ['오라클이 고른 꼭짓점으로 어떻게 이동할까?', 'How does the iterate move toward the oracle vertex?'],
        'scope': ['12개 목표점·시작점 조합, 18회. 삼각형·3D 높이·선형화·dual gap을 같은 계산으로 봅니다.',
                  'Twelve target/start combinations, 18 updates. One computation links triangle, 3D height, affine model and dual gap.'],
        'command': ['geometry', 'frank-wolfe', '--steps', '18'],
    },
    'sparsity': {
        'report': 'fw-sparsity.html', 'label': 'PUBLIC SHARP SUPPORT MINIMUM',
        'question': ['활성 좌표가 적으면 정확도에는 어떤 한계가 있을까?', 'How do few active coordinates limit attainable accuracy?'],
        'scope': ['Jaggi의 지지집합 하한과 실제 FW. n=3,8,32,128에서 40회. 반복별 최악 사례 달성과는 다릅니다.',
                  'Jaggi’s support floor and actual FW: n=3,8,32,128, 40 updates. Distinct from iteration-wise worst-case attainment.'],
        'command': ['case-study', 'fw-sparsity', '--steps', '40'],
    },
    'proximal': {
        'report': 'proximal.html', 'label': 'CONTROLLED COMPOSITE GEOMETRY · 9 CASES',
        'question': ['외삽·기울기·축소는 각각 무엇을 바꿀까?', 'What do extrapolation, gradient and shrinkage each change?'],
        'scope': ['대각 LASSO의 9개 λ·시작점 조합, 18회. 실제 중간점과 비매끄러운 목적함수 높이를 확인합니다.',
                  'Nine lambda/start combinations on diagonal LASSO, 18 updates. Inspect intermediate points and nonsmooth objective heights.'],
        'command': ['geometry', 'ista-fista', '--steps', '18'],
    },
    'landscape': {
        'report': 'landscape.html', 'label': 'ONE CONTROLLED QUADRATIC · UNEQUAL STEP COSTS',
        'question': ['같은 곡면에서 방법별 걸음은 어떻게 다를까?', 'How do method steps differ on the same surface?'],
        'scope': ['κ=20, 회전 32°, 최대 18회, 다섯 방법. PPA는 정확한 이차 resolvent이며 반복 수는 시간 비교가 아닙니다.',
                  'Kappa=20, angle 32°, at most 18 updates, five methods. PPA is an exact quadratic resolvent; iterations are not timing.'],
        'command': ['landscape', '--condition-number', '20', '--angle', '32', '--steps', '18'],
    },
    'tight-gd': {
        'report': 'tight-gd.html', 'label': 'PUBLIC ITERATION-BOUND ATTAINMENT',
        'question': ['상계에 실제로 닿는 함수는 어떤 모습일까?', 'What does a function attaining the bound look like?'],
        'scope': ['Drori–Teboulle의 Huber 구성. N=20, h=L=R=1. 명시한 GD·함수 클래스·예산 안의 결과입니다.',
                  'Drori–Teboulle Huber construction: N=20, h=L=R=1. Scoped to the stated GD rule, function class and horizon.'],
        'command': ['case-study', 'gd-tight', '--horizon', '20', '--h', '1', '--L', '1', '--R', '1'],
    },
}

TOPIC_PATHS = {
    'gd-baseline': ['tight-gd', 'landscape'],
    'nesterov-1983': ['landscape', 'proximal'],
    'polyak-1964': ['cycle', 'landscape'],
    'hestenes-stiefel-1952': ['shewchuk', 'landscape'],
    'jaggi-2013': ['simplex', 'sparsity'],
    'rockafellar-1976': ['landscape'],
    'beck-teboulle-2009': ['proximal', 'deblur', 'wavelet'],
    'ista-vs-fista': ['proximal', 'deblur', 'wavelet'],
}


def topic_paths(slug):
    items = [dict(id=key, **copy.deepcopy(WORKFLOWS[key])) for key in TOPIC_PATHS[slug]]
    items.append({
        'id': 'stress-'+slug, 'report': 'stress-'+slug+'.html', 'label': 'FINITE SEEDED SYNTHETIC COVERAGE',
        'question': ['여러 입력에서도 어떤 관측이 남을까?', 'What is observed across more inputs?'],
        'scope': ['seed 0–31을 모두 보존합니다. 개별 곡선·실제 입력·미해결 비율을 확인하며 대표 데이터나 정리 증명을 주장하지 않습니다.',
                  'All seeds 0–31 retained. Inspect individual curves, actual inputs and unresolved ratios; no representative-data or proof claim.'],
        'command': ['stress', slug, '--trials', '32', '--seed', '0'],
    })
    return items


def known_reports():
    return frozenset(item['report'] for slug in TOPIC_PATHS for item in topic_paths(slug))


def workflow_record(slugs):
    return {'kind': 'curated-reading-paths', 'topics': {slug: topic_paths(slug) for slug in slugs}}


def workflow_html(slug, report_links, lang):
    body = '<div class="workflow-paths"><h3>'+bi('이 질문을 실제 계산으로 이어가기', 'Follow the question into an actual computation')+'</h3>'
    body += '<div class="workflow-cards">'
    for item in topic_paths(slug):
        body += f'<article data-workflow="{item["id"]}"><span class="badge">{escape(item["label"])}</span><h4>'+bi(*item['question'])+'</h4><p>'+bi(*item['scope'])+'</p>'
        if item['report'] in report_links:
            body += f'<a class="workflow-open" data-workflow-link="{item["id"]}" href="{item["report"]}">'+bi('이 묶음의 보고서 열기 →', 'Open this bundle’s report →')+'</a>'
        command = 'python -m chainbench '+' '.join([*item['command'], '--lang', lang, '--output', item['report']])
        body += '<details><summary>'+bi('명령으로 새 보고서 생성하기', 'Generate a new report with a command')+'</summary><pre>'+escape(command)+'</pre></details></article>'
    return body+'</div></div>'
