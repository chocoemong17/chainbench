"""A bounded offline reading path through existing, independently computed reports."""
from __future__ import annotations

import base64
import hashlib
import json
import platform
import re
import tempfile
from html import escape
from itertools import chain
from pathlib import Path

import numpy as np

from . import __version__
from ._learning_paths import known_reports
from ._pages import bi, page
from .adam_counterexample import run_adam_counterexample
from .adam_counterexample_views import adam_counterexample_html
from .admm_geometry import run_admm_geometry
from .admm_views import admm_html
from .case_studies import case_html, gd_tight_case
from .cg_spectrum import run_cg_spectrum
from .cg_spectrum_views import cg_spectrum_html
from .checks import CHECKS
from .deblur_views import deblur_html
from .deblurring import run_deblurring
from .fista_backtracking import run_fista_backtracking
from .fista_backtracking_views import fista_backtracking_html
from .fw_sparsity import run_fw_sparsity
from .fw_sparsity_views import fw_sparsity_html
from .heavy_ball_cycle import run_heavy_ball_cycle
from .heavy_ball_views import heavy_ball_cycle_html
from .kaczmarz import run_kaczmarz
from .kaczmarz_views import kaczmarz_html
from .landscape import landscape_html, run_landscape
from .learning import LESSONS, learning_html
from .mechanisms import CSS as MECHANISM_CSS
from .mechanisms import flow_html
from .nonuniform_sampling import run_nonuniform_sampling
from .nonuniform_views import nonuniform_html
from .proximal_geometry import run_proximal_geometry
from .proximal_views import proximal_html
from .reproduction_views import reproduction_html
from .reproductions import run_reproduction
from .simplex_geometry import run_simplex_geometry, simplex_html
from .stress import run_stress, stress_html
from .wavelet_deblurring import run_wavelet_deblurring
from .wavelet_views import wavelet_html

STRESS_TRIALS = 32
EXTENSIONS = ('fista-wavelet', 'fw-sparsity', 'kaczmarz-expectation', 'kaczmarz-sampling', 'cg-spectrum', 'reddi-2018', 'admm-lasso', 'fista-backtracking')


def _reports(lang, *, extended=False):
    available = known_reports() if extended else known_reports()-{'wavelet.html', 'fw-sparsity.html'}
    yield 'atlas.html', learning_html(lang=lang, report_links=available), {
        'layer': 'canonical illustrations and symbolic explanations',
        'command': ['learn', '--lang', lang], 'topics': list(CHECKS)}
    result = run_reproduction(12)
    yield 'shewchuk.html', reproduction_html(result, lang), {
        'layer': 'published-example reproduction + controlled variations',
        'command': ['reproduce', 'shewchuk-1994', '--steps', '12', '--lang', lang],
        'source': result['source'], 'cases': len(result['cases'])}
    result = run_deblurring()
    yield 'deblur.html', deblur_html(result, lang), {
        'layer': 'published-experiment protocol rerun; declared source differences',
        'command': ['reproduce', 'fista-deblurring', '--steps', '10000', '--lang', lang],
        'source': result['source'], 'steps': 10000, 'dimension': 4096, 'noise_std': 0, 'lambda': 0}
    result = run_heavy_ball_cycle()
    yield 'heavy-ball.html', heavy_ball_cycle_html(result, lang), {
        'layer': 'published counterexample + controlled variations',
        'command': ['reproduce', 'lessard-2016', '--steps', '50', '--lang', lang],
        'source': result['source'], 'steps': 50, 'cases': len(result['cases'])}
    result = run_simplex_geometry(18)
    yield 'simplex.html', simplex_html(result, lang), {
        'layer': 'controlled geometric illustrations',
        'command': ['geometry', 'frank-wolfe', '--steps', '18', '--lang', lang],
        'source': result['source'], 'cases': len(result['cases'])}
    result = run_proximal_geometry(18)
    yield 'proximal.html', proximal_html(result, lang), {
        'layer': 'controlled geometric illustrations',
        'command': ['geometry', 'ista-fista', '--steps', '18', '--lang', lang],
        'source': result['source'], 'cases': len(result['cases'])}
    result = run_landscape()
    yield 'landscape.html', landscape_html(result, lang), {
        'layer': 'one controlled quadratic illustration; unequal work per iteration',
        'command': ['landscape', '--condition-number', '20', '--angle', '32', '--steps', '18', '--lang', lang],
        'sources': result['sources'], 'methods': result['methods'], 'input_sha256': result['input_sha256']}
    for topic in CHECKS:
        result = run_stress(topic, trials=STRESS_TRIALS, seed=0)
        yield f'stress-{topic}.html', stress_html(result, lang), {
            'layer': 'finite seeded synthetic sampling', 'topic': topic,
            'command': ['stress', topic, '--trials', str(STRESS_TRIALS), '--seed', '0', '--lang', lang],
            'seed': 0, 'trials': STRESS_TRIALS, 'sampler': result['sampler'],
            'summary': result['summary'], 'source': result['source']}
    result = gd_tight_case(20)
    yield 'tight-gd.html', case_html(result, lang), {
        'layer': 'public tight construction in its stated scope',
        'command': ['case-study', 'gd-tight', '--horizon', '20', '--h', '1', '--L', '1', '--R', '1', '--lang', lang],
        'source': result['reference']}


def _extended_reports(lang):
    result = run_wavelet_deblurring(200, seed=0)
    yield 'wavelet.html', wavelet_html(result, lang), {
        'layer': 'published noisy-image protocol with a declared noise draw',
        'command': ['reproduce', 'fista-wavelet', '--steps', '200', '--seed', '0', '--lang', lang],
        'source': result['source'], 'steps': 200, 'dimension': 65536,
        'seed': 0, 'noise_std': .001, 'lambda': .0001, 'f_star': None}
    result = run_fw_sparsity(40)
    yield 'fw-sparsity.html', fw_sparsity_html(result, lang), {
        'layer': 'published sharp support-constrained construction; actual FW comparisons',
        'command': ['case-study', 'fw-sparsity', '--steps', '40', '--lang', lang],
        'source': result['source'], 'steps': 40, 'dimensions': [3, 8, 32, 128]}
    result = run_kaczmarz(40, 64)
    yield 'kaczmarz.html', kaczmarz_html(result, lang), {
        'layer': 'published expectation attainment; all finite trials retained',
        'command': ['case-study', 'kaczmarz-expectation', '--steps', '40', '--trials', '64', '--lang', lang],
        'source': result['source'], 'steps': 40, 'trials': 64, 'seeds': list(range(64)),
        'cases': [c['id'] for c in result['cases']], 'metric': 'expected squared Euclidean error'}
    result = run_nonuniform_sampling()
    yield 'sampling.html', nonuniform_html(result, lang), {
        'layer': 'published nonuniform sampling protocol; three declared new inputs',
        'command': ['reproduce', 'kaczmarz-sampling', '--steps', '15000', '--lang', lang],
        'source': result['source'], 'steps': 15000, 'seeds': [0, 1, 2],
        'dimension': 101, 'sample_count': 700, 'bandlimit': 50,
        'cases': [c['id'] for c in result['cases']], 'metric': 'coefficient L2 error',
        'preview': {'case': 'seed-0', 'method': 'weighted', 'iteration': 100,
                    'quantity': 'real part of reconstructed signal'}}
    result = run_cg_spectrum(32)
    yield 'cg-spectrum.html', cg_spectrum_html(result, lang), {
        'layer': 'controlled spectral illustrations; newly declared inputs',
        'command': ['case-study', 'cg-spectrum', '--steps', '32', '--lang', lang],
        'source': result['source'], 'steps': 32, 'dimension': 16, 'rtol': 1e-12, 'atol': 0,
        'cases': [c['id'] for c in result['cases']], 'metric': 'relative A-norm error',
        'preview': {'basis': 'hadamard', 'start_profile': 'equal-energy',
                    'spectra': ['two-values', 'two-clusters', 'spread'],
                    'quantity': 'relative A-norm error over all completed updates'}}
    result = run_adam_counterexample(3000)
    yield 'adam.html', adam_counterexample_html(result, lang), {
        'layer': 'published counterexample family; declared finite instantiations',
        'command': ['reproduce', 'reddi-2018', '--steps', '3000', '--lang', lang],
        'source': result['source'], 'steps': 3000, 'methods': ['adam', 'amsgrad'],
        'C_values': [3,10,100], 'alpha_fractions': [.1,.5,.9],
        'cases': [c['id'] for c in result['cases']], 'metric': 'average online regret R_t/t',
        'variant': {'beta1': 0., 'bias_correction': False, 'epsilon': 0., 'period': 3},
        'preview': {'case': 'c3-a0.1', 'methods': ['adam','amsgrad'],
                    'quantity': 'average online regret over all rounds 1..3000',
                    'reference': 'Adam lower reference at complete three-round blocks only'}}
    result = run_admm_geometry(60)
    yield 'admm.html', admm_html(result, lang), {
        'layer': 'controlled geometric illustrations; newly declared 2D inputs',
        'command': ['geometry', 'admm-lasso', '--steps', '60', '--lang', lang],
        'source': result['source'], 'steps': 60, 'dimension': 2,
        'cases': [c['id'] for c in result['cases']],
        'input_sha256': {c['id']: c['input_sha256'] for c in result['cases']},
        'metric': 'original-primal gap F(w)-F*',
        'variant': {'relaxation': 1., 'penalty': 'fixed rho', 'stopping': 'fixed_budget', 'initial_x': None},
        'preview': {'case': 'coupled-lambda0.1-zero-rho1', 'iteration': 1,
                    'view': 'surface', 'coordinates': ['x', 'z'],
                    'height': 'stable algebraic F(w)-F*'}}
    result = run_fista_backtracking(18)
    yield 'backtracking.html', fista_backtracking_html(result, lang), {
        'layer': 'controlled backtracking illustrations; all declared trials retained',
        'command': ['geometry', 'fista-backtracking', '--steps', '18', '--lang', lang],
        'source': result['source'], 'steps': 18, 'dimension': 2,
        'cases': [c['id'] for c in result['cases']],
        'input_sha256': {c['id']:c['input_sha256'] for c in result['cases']},
        'metric': 'original-objective gap and signed candidate model difference',
        'variant': {'initial_L': [.25,1.,4.], 'eta': 2., 'carry': 'accepted L',
                    'acceptance_tolerance': 0., 'stopping': 'fixed_budget'},
        'gate': result['gate'],
        'preview': {'case': 'lambda0.8-zero-L1', 'iteration': 1, 'attempt': 0, 'trial_L': 1.,
                    'accepted': False, 'view': 'model',
                    'height': 'F(u)-F* and Q_L(u,y)-F* on the first rejected candidate line'}}


def _with_navigation(html, filename=None, *, extended=False):
    nav = '<nav aria-label="Tour"><a href="index.html" data-tour-home>'+bi(
        '← 탐색 안내로 돌아가기', '← Back to the guided tour')+'</a></nav>'
    lesson = {
        'shewchuk.html': 'hestenes-stiefel-1952', 'cg-spectrum.html': 'hestenes-stiefel-1952',
        'heavy-ball.html': 'polyak-1964',
        'simplex.html': 'jaggi-2013', 'fw-sparsity.html': 'jaggi-2013',
        'proximal.html': 'beck-teboulle-2009', 'deblur.html': 'beck-teboulle-2009',
        'backtracking.html': 'beck-teboulle-2009',
        'wavelet.html': 'beck-teboulle-2009', 'tight-gd.html': 'gd-baseline',
        'landscape.html': 'mechanism-comparison',
        **{f'stress-{topic}.html': topic for topic in CHECKS},
    }.get(filename)
    if lesson:
        nav += f'<nav aria-label="Related lesson"><a href="atlas.html#{lesson}" data-tour-lesson>'+bi(
            '관련 방법의 가정·업데이트 설명', 'Assumptions and updates of the related method')+'</a></nav>'
    related = {
        'deblur.html': ('proximal.html', '양의 λ에서 soft threshold는 어떻게 작동할까?', 'How does soft thresholding work at positive lambda?'),
        'proximal.html': ('deblur.html', 'λ=0인 논문의 영상 실험 보기', 'Open the source image experiment at lambda=0'),
        'atlas.html': ('deblur.html', 'FISTA의 공개 영상 실험 열기', 'Open the published FISTA image experiment'),
        'heavy-ball.html': ('atlas.html#polyak-1964', '이차함수에서의 heavy-ball 가정과 비교', 'Compare the heavy-ball assumptions for quadratics'),
        'stress-polyak-1964.html': ('heavy-ball.html', '이차함수 밖의 공개 반례 보기', 'Inspect a published counterexample beyond quadratics'),
        'landscape.html': ('heavy-ball.html', '이차함수의 가정이 빠지면? 공개 반례 보기', 'Without the quadratic assumption: inspect a published counterexample'),
    }
    if extended:
        if filename in ('proximal.html','backtracking.html','atlas.html'):
            target = 'proximal.html' if filename=='backtracking.html' else 'backtracking.html'
            label = (('알려진 L=9로 계산한 FISTA 경로 보기', 'Inspect FISTA with known L=9')
                     if filename=='backtracking.html' else
                     ('이동 크기를 고르는 거부·채택 과정 보기', 'Inspect rejected and accepted step-size trials'))
            nav += '<nav aria-label="FISTA step selection"><a href="'+target+'" data-tour-backtracking>'+bi(*label)+'</a>'
            nav += '<a href="index.html#step-selection" data-tour-backtracking-guide>'+bi(
                '고정 L과 후보 검사 비교하기', 'Compare fixed L with the candidate test')+'</a></nav>'
        if filename in ('proximal.html', 'admm.html', 'atlas.html'):
            target = 'proximal.html' if filename == 'admm.html' else 'admm.html'
            label = (('기울기 이동 뒤 축소하는 ISTA/FISTA와 비교', 'Compare ISTA/FISTA: shrink after a gradient step')
                     if filename == 'admm.html' else
                     ('두 변수를 나누고 불일치를 기억하는 ADMM 보기', 'Inspect ADMM: split variables and remember disagreement'))
            nav += '<nav aria-label="Splitting comparison"><a href="'+target+'" data-tour-splitting>'+bi(*label)+'</a>'
            nav += '<a href="index.html#variable-splitting" data-tour-splitting-guide>'+bi(
                '같은 y·z 표기, 다른 역할 읽기', 'Same y/z notation, different roles')+'</a></nav>'
        related.update({
            'deblur.html': ('wavelet.html', '잡음과 양의 λ가 있는 영상에서는?', 'What changes with noise and positive lambda?'),
            'wavelet.html': ('deblur.html', '잡음과 벌점이 없는 원문 실험과 비교', 'Compare the noiseless, unpenalized source experiment'),
            'proximal.html': ('wavelet.html', '실제 영상의 Haar 계수에서 축소하기', 'Apply shrinkage to actual image Haar coefficients'),
            'simplex.html': ('fw-sparsity.html', '원자를 적게 쓰면 정확도의 한계는?', 'How do few atoms limit attainable accuracy?'),
            'fw-sparsity.html': ('simplex.html', '꼭짓점 선택과 가능한 갱신을 기하로 보기', 'Inspect the oracle and feasible update geometry'),
            'tight-gd.html': ('fw-sparsity.html', '반복 상계 달성과 희소성 하한 달성은 어떻게 다를까?', 'Compare iteration-bound attainment with a sharp support minimum'),
            'kaczmarz.html': ('tight-gd.html', '기대값 보장과 결정론적 반복 상계 달성 비교', 'Compare expectation with deterministic iteration-bound attainment'),
        })
        if filename in ('tight-gd.html', 'fw-sparsity.html'):
            nav += '<nav aria-label="Expectation comparison"><a href="kaczmarz.html" data-tour-probability>'+bi(
                '무작위 실행의 기대값에서 상계를 달성한다는 뜻은?',
                'What does attaining an upper bound in expectation mean?')+'</a></nav>'
        if filename in ('kaczmarz.html', 'sampling.html'):
            target = 'sampling.html' if filename == 'kaczmarz.html' else 'kaczmarz.html'
            text = (('같은 행 투영을 비균일 신호 관측에 적용하면?', 'Apply row projections to irregular signal observations?')
                    if filename == 'kaczmarz.html' else
                    ('기대값 상계를 정확히 달성하는 별도의 구성 보기', 'Inspect the separate construction attaining an expectation bound'))
            nav += '<nav aria-label="Sampling comparison"><a href="'+target+'" data-tour-sampling>'+bi(*text)+'</a></nav>'
        if filename in ('shewchuk.html', 'cg-spectrum.html', 'atlas.html', 'stress-hestenes-stiefel-1952.html'):
            target = 'shewchuk.html' if filename == 'cg-spectrum.html' else 'cg-spectrum.html'
            text = (('원문의 2×2 문제와 실제 이동 경로로 돌아가기', 'Return to the published 2×2 system and its paths')
                    if filename == 'cg-spectrum.html' else
                    ('같은 조건수의 18개 고유값·시작 오차 사례 비교', 'Compare 18 spectra and starts at the same condition number'))
            nav += '<nav aria-label="CG spectral comparison"><a href="'+target+'" data-tour-spectrum>'+bi(*text)+'</a></nav>'
        if filename in ('heavy-ball.html', 'adam.html', 'atlas.html'):
            target = 'heavy-ball.html' if filename == 'adam.html' else 'adam.html'
            text = (('고정 목적함수의 별도 heavy-ball 반례와 비교', 'Compare the separate heavy-ball counterexample on a fixed objective')
                    if filename == 'adam.html' else
                    ('손실이 매번 바뀌면? Adam의 기억과 누적 regret 보기', 'When losses change: inspect Adam memory and cumulative regret'))
            nav += '<nav aria-label="Changing-loss comparison"><a href="'+target+'" data-tour-regret>'+bi(*text)+'</a></nav>'
    if filename in related:
        target,ko,en = related[filename]
        nav += '<nav aria-label="Related report"><a href="'+target+'" data-tour-related>'+bi(ko,en)+'</a></nav>'
    if '<main>' not in html:
        raise ValueError('tour report has no navigation insertion point')
    return html.replace('<main>', '<main>'+nav, 1)


def _thumbnail(html, position=0):
    matches = re.findall(r'<svg\b.*?</svg>', html, flags=re.S)
    if len(matches) <= position:
        raise ValueError('tour preview must come from an actual generated plot')
    return 'data:image/svg+xml;base64,'+base64.b64encode(matches[position].encode('utf8')).decode('ascii')


def _adam_thumbnail(html):
    _, marker, remainder = html.partition('<details data-adam-case="c3-a0.1">')
    case = remainder.split('<details data-adam-case=',1)[0]
    match = re.search(r'(<svg\b[^>]*data-adam-chart="average_regret".*?</svg>)',case,flags=re.S)
    if not marker or match is None:
        raise ValueError('Adam preview must come from the actual c3-a0.1 average-regret chart')
    return 'data:image/svg+xml;base64,'+base64.b64encode(match[1].encode()).decode('ascii')


def _admm_thumbnail(html):
    case = re.search(r'<details\b[^>]*data-admm-case="coupled-lambda0.1-zero-rho1"[^>]*>(.*?)(?=<details\b[^>]*data-admm-case=|\Z)',html,flags=re.S)
    match = re.search(r'(<svg\b[^>]*data-admm-primal="surface".*?</svg>)',case[1],flags=re.S) if case else None
    if match is None:
        raise ValueError('ADMM preview must come from the actual coupled-lambda0.1-zero-rho1 surface')
    return 'data:image/svg+xml;base64,'+base64.b64encode(match[1].encode()).decode('ascii')


def _backtracking_thumbnail(html):
    case = re.search(r'<section\b[^>]*data-bt-case="lambda0.8-zero-L1"[^>]*>(.*?)(?=<section\b[^>]*data-bt-case=|\Z)',html,flags=re.S)
    matches = re.findall(r'<svg\b.*?</svg>',case[1],flags=re.S) if case else []
    models = [svg for svg in matches if 'data-bt-dynamic="model_gap"' in svg]
    if len(models)!=1:
        raise ValueError('Backtracking preview must come from the actual lambda0.8-zero-L1 model')
    return 'data:image/svg+xml;base64,'+base64.b64encode(models[0].encode()).decode('ascii')


def _index(artifacts, previews, lang):
    extended = 'wavelet.html' in previews
    randomized = 'kaczmarz.html' in previews
    sampling = 'sampling.html' in previews
    spectrum = 'cg-spectrum.html' in previews
    adam = 'adam.html' in previews
    admm = 'admm.html' in previews
    backtracking = 'backtracking.html' in previews
    def card(filename, title, explanation, layer):
        body = '<a class="tour-card" href="'+filename+'"><span class="badge">'+escape(layer)+'</span>'
        body += '<h3>'+bi(*title)+'</h3><p>'+bi(*explanation)+'</p>'
        if filename in previews:
            body += '<img alt="'+escape(title[1], quote=True)+'" src="'+previews[filename]+'">'
        if filename == 'atlas.html':
            body += flow_html('beck-teboulle-2009')
        return body+'<span class="tour-open">'+bi('계산과 그림 열기 →', 'Open the calculation and figures →')+'</span></a>'
    css = '''.tour-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.tour-card{display:flex;flex-direction:column;border:1px solid #d7e1ee;border-radius:18px;padding:22px;text-decoration:none;color:#172238;background:linear-gradient(180deg,#fff,#f7faff);min-width:0}
.tour-card h3{font-size:22px;margin:14px 0 8px}.tour-card p{font-size:14px}.tour-card .badge{align-self:start}.tour-card img{width:100%;height:auto;margin:12px 0}.tour-open{margin-top:auto;padding-top:16px;color:#245ec3;font-weight:700;font-size:13px}
.tour-card[href="deblur.html"] img{max-width:300px;align-self:center;image-rendering:pixelated}.tour-card:hover{border-color:#558cdd}.tour-steps{display:flex;gap:10px;flex-wrap:wrap;margin:24px 0}.tour-steps a{padding:10px 14px;border-radius:12px;background:#fff;border:1px solid #d7e1ee;text-decoration:none}
.tour-table td:first-child{min-width:150px}.tour-table th{white-space:normal}.tour-intro{font-size:17px;max-width:950px}@media(max-width:760px){.tour-grid{grid-template-columns:1fr}.tour-card{padding:17px}}
@media print{.tour-grid{grid-template-columns:1fr 1fr}.tour-card{break-inside:avoid}}'''
    body = '<style>'+MECHANISM_CSS+css+'</style><p class="tour-intro">'+bi(
        '논문의 구체적 예제에서 출발해, 점이 움직이는 이유와 여러 입력에서의 관측을 연결하세요. 각 화면에는 원본 수치·설정·출처가 들어 있습니다.',
        'Begin with a concrete published example, follow how its iterates move, then inspect what changes across inputs. Every report retains its samples, settings and source.')+'</p>'
    if extended:
        report_mib = sum(a['bytes'] for a in artifacts)/1024**2
        body += '<div class="evidence-banner">'+bi(
            f'확장 묶음 · HTML {len(artifacts)+1}개 · 보고서 약 {report_mib:.1f} MiB + 안내·manifest. 잡음 영상·희소성 하한·무작위 기대값·신호 복원·CG 고유모드·Adam 반례·ADMM 분할·FISTA 후보 검사를 연결합니다.',
            f'Extended tour · {len(artifacts)+1} HTML files · reports about {report_mib:.1f} MiB plus index/manifest. Connect noisy images, sharp support minima, randomized expectations, signal recovery, CG eigenmodes, the Adam counterexample, ADMM splitting and FISTA candidate tests.')+'</div>'
    body += '<div class="tour-steps">'
    for target, ko, en in [('published', '1 · 논문 예제', '1 · Published setup'), ('geometry', '2 · 갱신의 기하', '2 · Update geometry'),
                            ('breadth', '3 · 여러 표본', '3 · Many instances'), ('understand', '4 · 이론과 연결', '4 · Connect the theory')]:
        body += '<a href="#'+target+'">'+bi(ko,en)+'</a>'
    if randomized:
        body += '<a href="#randomized">'+bi('5 · 무작위 기대값', '5 · Randomized expectation')+'</a>'
    if sampling:
        body += '<a href="#sampling">'+bi('6 · 신호 관측과 선택', '6 · Signal samples and selection')+'</a>'
    if spectrum:
        body += '<a href="#cg-spectrum">'+bi('CG · 고유값과 시작 오차', 'CG · Eigenvalues and initial error')+'</a>'
    if adam:
        body += '<a href="#online-regret">'+bi('Adam · 기억과 바뀌는 손실', 'Adam · Memory and changing losses')+'</a>'
    if admm:
        body += '<a href="#variable-splitting">'+bi('ADMM · 두 변수의 합의', 'ADMM · Bring two variables into agreement')+'</a>'
    if backtracking:
        body += '<a href="#step-selection">'+bi('FISTA · 이동 크기 고르기', 'FISTA · Choose the step size')+'</a>'
    body += '</div><section id="published"><h2>'+bi('먼저, 논문이 실제로 사용한 한 문제', 'Start with a problem the source actually used')+'</h2><div class="tour-grid">'
    body += card('shewchuk.html', ('왜 CG의 경로는 다른가?', 'Why does CG take a different path?'),
        ('Shewchuk의 2×2 문제를 다시 계산합니다. 원 시작점과 추가한 9개 시작점을 구분하고, 등고선·3D 높이·에너지 오차를 함께 봅니다. 같은 걸음을 원형 등고선으로 옮겨 SD의 직각과 CG의 켤레 방향을 비교하세요.',
         'Recompute Shewchuk’s 2×2 example, keeping nine added starts separate. Connect contours, 3D heights and energy error; transform the same steps to circular levels to distinguish SD orthogonality from CG conjugacy.'), 'PUBLISHED SETUP + VARIATIONS')
    body += '<div><p>'+bi('읽을 질문: 두 방법의 첫 이동이 같아도, 왜 그다음 방향은 달라질까요?',
        'Reading question: if both methods take the same first step, why do their next directions differ?')+'</p>'
    body += '<img style="width:100%;height:auto" alt="Same published-example iterates at their actual objective heights" src="'+previews['shewchuk-surface']+'"><p class="callout">'+bi(
        '원 그림의 픽셀을 복사한 것이 아니라 공개된 입력을 독립 계산한 것입니다. 반복 예산·3D 보기·추가 시작점은 ChainBench의 선택입니다.',
        'This independently computes the published inputs rather than copying figure pixels. Budget, 3D views and additional starts are ChainBench choices.')+'</p><p>'+bi(
        '각 페이지 위의 “탐색 안내로 돌아가기”를 누르면 여기로 돌아옵니다. 파일들은 오프라인에서 읽을 수 있습니다.',
        'Use the return link at the top of each page to come back here. These files can be read offline.')+'</p></div></div></section>'
    if spectrum:
        body += '<section id="cg-spectrum"><h2>'+bi('두 고유값에서, 같은 조건수의 여러 분포로', 'From two eigenvalues to different spectra at the same condition number')+'</h2><div class="tour-grid">'
        body += card('cg-spectrum.html', ('조건수가 같으면 CG의 속도도 같을까?', 'Does the same condition number give the same CG convergence?'),
            ('16차원·[2,7]·κ=3.5를 유지하고 고유값 분포 3개, 좌표계 2개, 시작 오차 3개를 빠짐없이 비교합니다. 실제 계수 비율·에너지·참 잔차를 단계별로 확인하세요.',
             'Hold n=16, [2,7] and κ=3.5 fixed across all three spectra, two bases and three initial-error profiles. Inspect actual coefficient ratios, energies and true residuals at every step.'), 'CONTROLLED SPECTRAL ILLUSTRATIONS')
        body += '<div><p class="callout">'+bi('읽을 질문: 고유값이 두 곳에 모여 있거나 시작 오차가 한 모드에만 놓이면 무엇이 달라질까요?',
            'Reading question: what changes when eigenvalues cluster, or the initial error occupies only one mode?')+'</p><p>'+bi(
            '미리보기는 Hadamard 좌표계와 초기 에너지 동일 조건에서 세 분포의 모든 실제 단계입니다. 세로축은 상대 A-노름이며 제곱 오차가 아닙니다. 회색 비교 상계와 별도의 차수 2 다항식은 실제 CG 다항식이나 부동소수점 인증과 구분합니다.',
            'The preview includes every actual step for all three spectra in the Hadamard basis with equal initial energies. Its metric is relative A-norm, not squared error. The grey interval reference and separate degree-2 witness are not actual CG polynomials or floating-point certificates.')+'</p><p>'+bi(
            'Shewchuk §9.1–9.2의 설명을 새로 선언한 입력으로 탐색합니다. 원문 Figure 31(d)의 입력 재현은 아닙니다. 32회 예산 안에서 실제로 멈춘 경로만 남기고, 끝난 뒤의 점이나 0을 추가하지 않습니다.',
            'Explore Shewchuk §9.1–9.2 with newly declared inputs, not a reproduction of Figure 31(d)’s unspecified data. Retain only the computed path within the 32-update budget; no later points or zeros are added.')+'</p></div></div></section>'
    body += '<section id="image-experiment"><h2>'+bi('같은 방법을 실제 영상 역문제에 적용하면?', 'What happens on the source image inverse problem?')+'</h2><div class="tour-grid">'
    body += card('deblur.html', ('흐린 관측에서 영상 복원하기', 'Recover an image from blurred observations'),
        ('Beck–Teboulle Figure 5의 ISTA/FISTA 부분을 64×64 영상과 10,000회 갱신으로 다시 계산합니다. 원문과의 차이와 모든 수치를 함께 봅니다.',
         'Recompute the ISTA/FISTA subset of Beck–Teboulle Figure 5 with a 64×64 image and 10,000 updates. Inspect source differences and every scalar observation.'), 'PUBLISHED PROTOCOL RERUN')
    body += '<div><p class="callout">'+bi('읽을 질문: 목적함수 오차가 매우 작으면 깨끗한 원본 영상도 정확히 복원됐다고 말할 수 있을까요?',
        'Reading question: does a tiny objective error mean that the clean image was recovered exactly?')+'</p><p>'+bi('이 실험은 잡음과 정규화 항이 없는 λ=0 설정입니다. 아래 2D proximal 예제는 양의 λ가 좌표를 0으로 만드는 원리를 설명합니다. 서로 다른 질문을 다룹니다.',
        'This image experiment has no noise and lambda=0. The 2D proximal view below explains how positive lambda can zero a coordinate. The two reports answer different questions.')+'</p><p>'+bi('미리보기는 실제 10,000회 FISTA 복원 영상입니다. 모든 영상이 같은 [0,1] 회색조를 사용하며 전체 수치 배열은 보고서에서 확인합니다.',
        'The preview is the actual FISTA reconstruction at 10,000 steps. Every image uses the same [0,1] grayscale; full numeric arrays are in the report.')+'</p></div></div></section>'
    if extended:
        body += '<style>.tour-card[href="wavelet.html"] img{max-width:300px;align-self:center;image-rendering:pixelated}</style><section id="regularized-image"><h2>'+bi('잡음이 있으면 계수를 줄이는 이유는?', 'Why shrink coefficients when observations contain noise?')+'</h2><div class="tour-grid">'
        body += card('wavelet.html', ('영상의 실제 Haar 계수를 축소하기', 'Shrink actual image Haar coefficients'),
            ('Figure 4의 256×256·λ=10⁻⁴ 조건을 새로 선언한 잡음으로 200회 계산합니다. 복원 영상·계수·잔차와 벌점·RMSE를 연결합니다.',
             'Run 200 updates under the Figure 4 256×256, lambda=10⁻⁴ protocol with a declared new noise draw. Connect reconstructed images, coefficients, residual/penalty and RMSE.'), 'PUBLISHED PROTOCOL · DECLARED NOISE')
        body += '<div><p class="callout">'+bi('읽을 질문: 관측을 더 잘 맞추는 일과 작은 계수를 줄이는 일은 왜 함께 필요할까요?',
            'Reading question: why combine fitting the observation with shrinking small coefficients?')+'</p><p>'+bi('이 보고서는 λ=0 실험과 다른 문제입니다. 깨끗한 원본은 평가에만 쓰며, 알고리즘은 흐리고 잡음이 있는 관측을 받습니다. 최적값을 모르므로 F를 최적성 gap으로 부르지 않습니다.',
            'This differs from the lambda=0 problem. The clean image is only an evaluation reference; optimization uses the blurred noisy observation. Its unknown optimum means F is not an optimality gap.')+'</p><p>'+bi('미리보기는 seed 0, k=200의 실제 FISTA 복원입니다. 원문 잡음 표본은 공개되지 않았고 원문 픽셀·최종값 일치를 주장하지 않습니다. 모든 배열을 포함한 이 페이지는 약 28 MB입니다.',
            'The preview is the computed FISTA reconstruction at seed 0, k=200. Original noise samples are unavailable; no exact pixel or endpoint match is asserted. The full-array page is about 28 MB.')+'</p></div></div></section>'
    body += '<section id="counterexample"><h2>'+bi('수렴 설명은 어디까지 적용될까?', 'Where does a convergence claim stop applying?')+'</h2><div class="tour-grid">'
    body += card('heavy-ball.html', ('강볼록 함수에서 나타나는 주기 궤도', 'A limit cycle on a strongly convex function'),
        ('Lessard–Recht–Packard의 공개 heavy-ball 반례를 재계산합니다. 원 시작점 3.3과 8개 추가 시작점에서 위치·기억 상태·기울기를 비교합니다.',
         'Recompute the Lessard–Recht–Packard heavy-ball counterexample. Compare position, memory state and gradient at the original start 3.3 and eight added starts.'), 'PUBLISHED COUNTEREXAMPLE + VARIATIONS')
    body += '<div><p class="callout">'+bi('읽을 질문: 세 단계마다 거의 같은 점을 방문하면 최적해에 수렴한 것일까요?',
        'Reading question: does returning close to the same point every three steps mean convergence to the optimum?')+'</p><p>'+bi('이 함수는 매끄럽고 강볼록이지만 하나의 이차함수는 아닙니다. 모멘텀의 이전 상태를 위상 평면에서 보고, 반복 주기와 기울기 0을 구분합니다. IQC/SDP 계산 전체를 재현하는 범위는 아닙니다.',
        'The function is smooth and strongly convex, but not one quadratic. Inspect momentum’s memory in the state plane and distinguish repetition from zero gradient. This does not reproduce the full IQC/SDP analysis.')+'</p></div></div></section>'
    if adam:
        body += '<section id="online-regret"><h2>'+bi('목적함수가 매번 바뀌면 무엇을 비교할까?', 'What should we compare when the loss changes each round?')+'</h2><div class="tour-grid">'
        body += card('adam.html', ('큰 기울기를 잊으면 다음 걸음은?', 'What happens after forgetting a large gradient?'),
            ('Reddi·Kale·Kumar 정리 1의 3주기 반례입니다. 9개 설정에서 두 방법의 손실·제곱 기울기 기억·제안·투영·regret을 매 회차 따라가세요.',
             'Reddi–Kale–Kumar Theorem 1 uses period-three losses. Follow both methods’ loss, second-moment memory, proposal, projection and regret at every round across nine settings.'), 'PUBLISHED COUNTEREXAMPLE · DECLARED INPUTS')
        body += '<div><p class="callout">'+bi('읽을 질문: 지금 점의 위치와 지금까지 낸 손실의 합은 왜 다른 정보를 줄까요?',
            'Reading question: why do the current point and the accumulated losses tell different stories?')+'</p><p>'+bi(
            'Regret은 같은 한 점을 처음부터 끝까지 썼을 때의 최선의 누적 손실과 비교합니다. 여기서는 그 고정 비교점이 −1입니다. 한 회의 차이는 음수일 수 있고, T=0의 평균은 미정의입니다. 갱신 전의 점에서 손실을 지불합니다.',
            'Regret compares accumulated losses with the best single point kept fixed throughout the sequence. Here that comparator is −1. One round can contribute negatively, and the T=0 average is undefined. Each loss is incurred before updating.')+'</p><p>'+bi(
            '미리보기는 C=3·보폭 비율 0.1의 실제 1–3,000회 평균 regret입니다. AMSGrad도 이 예산에서는 아직 −1에서 멉니다. 주황 하한은 Adam의 완성된 3회 묶음에만 적용됩니다.',
            'The preview shows actual average regret for rounds 1–3000 at C=3 and alpha fraction 0.1. AMSGrad is still far from −1 at this budget. Orange lower-reference dots apply only to Adam’s complete three-round blocks.')+'</p><p>'+bi(
            '편향 보정 없음·β₁=0·ε=0인 논문의 분석 변형입니다. 주기 101의 Figure 1 실험이나 최신 Adam 기본값의 비교가 아닙니다.',
            'This uses the paper’s analysis variant: no debiasing, β₁=0 and ε=0. It is distinct from the period-101 Figure 1 experiment and modern Adam defaults.')+'</p></div></div>'
        body += '<div class="scroll"><table><tr><th>'+bi('반례','Counterexample')+'</th><th>'+bi('문제와 비교량','Problem and quantity')+'</th><th>'+bi('유지해야 할 범위','Scope to retain')+'</th></tr><tr><td><a href="heavy-ball.html">Heavy-ball · Lessard</a></td><td>'+bi(
            '같은 매끄럽고 강볼록인 함수 · 반복점과 목적함수 gap',
            'One fixed smooth strongly convex function · iterates and objective gap')+'</td><td>'+bi(
            '이차함수용 보폭·모멘텀이 이 비이차함수에서는 주기를 만들 수 있음',
            'Quadratic-tuned step and momentum can cycle on this nonquadratic function')+'</td></tr><tr><td><a href="adam.html">Adam · Reddi</a></td><td>'+bi(
            '회차마다 다른 선형 손실 · 최선의 고정점 대비 Rₜ/t',
            'Changing linear losses · Rₜ/t against the best fixed comparator')+'</td><td>'+bi(
            '명시된 분석 변형과 입력 조건 · 완성된 3회 묶음의 양의 하한',
            'The stated analysis variant and inputs · positive lower reference at complete three-round blocks')+'</td></tr></table></div><p class="small">'+bi(
            '서로 다른 문제와 양을 연결하는 읽기 경로입니다. 곡선을 공통 성능 순위로 합치거나 한쪽 보장을 다른 쪽으로 옮기지 않습니다.',
            'These links connect distinct problems and quantities. The curves do not form a shared performance ranking, and guarantees do not transfer between reports.')+'</p></section>'
    body += '<section id="geometry"><h2>'+bi('다른 문제 구조에서는 어떻게 움직일까?', 'How do updates change with the problem structure?')+'</h2><div class="tour-grid">'
    body += card('simplex.html', ('가능한 삼각형 안에서 이동', 'Move inside a feasible triangle'),
        ('Frank–Wolfe의 꼭짓점 선택과 선분 갱신을 12개 조합에서 봅니다. 목적함수가 증가하는 첫 단계도 그대로 남깁니다.',
         'Inspect Frank–Wolfe’s oracle and segment update over all 12 combinations, including a first step that increases the objective.'), 'CONTROLLED GEOMETRY')
    body += card('proximal.html', ('외삽하고, 이동하고, 수축하기', 'Extrapolate, step, then shrink'),
        ('ISTA/FISTA의 중간점과 soft threshold를 9개 조합에서 확인합니다. λ에 따라 좌표가 0이 되는 이유를 읽어보세요.',
         'Inspect ISTA/FISTA stages and soft thresholding over all nine combinations. Follow why changing lambda can make a coordinate zero.'), 'CONTROLLED GEOMETRY')
    body += '</div></section>'
    if backtracking:
        from ._backtracking_tour import backtracking_comparison
        body += '<section id="step-selection"><h2>'+bi('곡률을 미리 정하지 않으면?', 'What if the curvature is estimated along the way?')+'</h2><div class="tour-grid">'
        body += card('backtracking.html', ('이 후보는 왜 거부됐을까?', 'Why was this candidate rejected?'),
            ('전체 36개 실행에서 모든 후보를 남깁니다. L을 키울 때 이동과 축소 문턱이 어떻게 바뀌는지 실제 경로·모형 곡선·원본 표로 읽으세요.',
             'Keep every candidate in all 36 runs. Read how increasing L changes the step and shrinkage threshold through actual paths, model curves and native tables.'), 'CONTROLLED FISTA MODEL TEST')
        body += '<div><p class="callout">'+bi('읽을 질문: 더 작은 이동이 처음으로 채택되는 순간, 어떤 조건이 달라졌을까요?',
            'Reading question: which condition changes when a smaller step is first accepted?')+'</p><p data-backtracking-preview-context>'+bi(
            '미리보기는 λ=0.8, x₀=(0,0), L₀=1의 k=1, 첫 시도 j=0입니다. q=(0.6,−6.4)에서 F(q)−Q₁(q,y)=163.84>0이어서 거부됩니다. 실제 목적함수와 모형은 같은 F*만큼 이동한 높이입니다.',
            'The preview is k=1, first attempt j=0 for λ=0.8, x₀=(0,0), L₀=1. At q=(0.6,−6.4), F(q)−Q₁(q,y)=163.84>0, so it is rejected. The objective and model heights share the same shift F*.')+'</p><p>'+bi(
            '이는 설명을 위한 한 장면입니다. 보고서에는 λ·시작점·초기 L의 모든 조합과 18회 갱신 전체가 남아 있습니다. s는 이 후보로 향하는 직선의 위치이며 갱신 번호가 아닙니다. 원 영상 실험 대신 새로 선언한 대각 LASSO를 사용합니다.',
            'This is one explanatory scene. The report retains every λ/start/initial-L combination and all 18 updates. s locates a point along the candidate line; it is not an update count. These are declared diagonal LASSO inputs, separate from the source image experiment.')+'</p></div></div>'
        body += backtracking_comparison()+'</section>'
    if admm:
        from ._splitting_comparison import splitting_comparison
        body += '<section id="variable-splitting"><h2>'+bi('축소를 두 하위 문제로 나누면?', 'What changes when shrinkage sits inside a split problem?')+'</h2><div class="tour-grid">'
        body += card('admm.html', ('데이터를 맞추는 x와 좌표를 줄이는 z', 'x fits the data; z shrinks coordinates'),
            ('전체 36개 조합의 선형계 풀이·축소·쌍대 기억을 연결합니다. 실제 2D/3D 경로와 두 잔차 조건을 함께 읽으세요.',
             'Connect the linear solve, shrinkage and dual memory in all 36 cases. Read actual 2D/3D paths alongside both residual tests.'), 'CONTROLLED ADMM GEOMETRY')
        body += '<div><p class="callout">'+bi('읽을 질문: 원래 목적함수 간극이 0이어도, 왜 두 변수의 계산은 아직 합의하지 못했을까요?',
            'Reading question: with a zero original gap, why can the two variables still disagree?')+'</p><p>'+bi(
            '미리보기는 결합 행렬·λ/λ_max=0.1·zero 시작·ρ=1의 실제 k=1입니다. 전체 x/z 경로 위의 큰 점이 선택한 상태이고, 높이는 원래 F(w)−F*입니다. 서로 다른 두 점의 f(x)+g(z)를 표면 높이로 쓰지 않습니다.',
            'The preview is actual k=1 for the coupled matrix, λ/λ_max=0.1, zero start and ρ=1. Large markers select the state on the full x/z paths; height is original F(w)−F*. The mixed f(x)+g(z) value is not used as surface height.')+'</p><p>'+bi(
            'Boyd 등의 2011년 리뷰 §6.4를 새 2차원 입력에서 설명합니다. 원문의 대규모 데이터·최적값·시간·종료 횟수를 재현한 그림은 아닙니다. 초기에는 정의되지 않는 x와 잔차를 그대로 구분합니다.',
            'Explain §6.4 of Boyd et al.’s 2011 review on new 2D inputs. This does not reproduce the source’s large dataset, optimum, timing or stop count. Initial undefined x and residuals remain distinct.')+'</p></div></div>'
        body += splitting_comparison()+'</section>'
    body += '<section id="quadratic"><h2>'+bi('같은 문제여도, 한 걸음의 비용은 다릅니다', 'Same problem; different work per step')+'</h2><div class="tour-grid">'
    body += card('landscape.html', ('다섯 방법을 같은 이차함수에서 보기', 'Five methods on the same quadratic'),
        ('κ=20, 회전 32°, 최대 18회 갱신. 방법별 색상·실제 계산점·종료 표시를 공간과 오차 곡선에서 연결합니다.',
         'Condition number 20, rotation 32°, at most 18 updates. Match method colors, actual iterates and termination across geometry and gap curves.'), 'ONE CONTROLLED ILLUSTRATION')
    body += '<div><p class="callout">'+bi('읽을 질문: CG가 두 걸음에 끝나면, 언제나 가장 빠른 알고리즘일까요?',
        'Reading question: if CG finishes in two updates, is it always the fastest algorithm?')+'</p><p>'+bi(
        '여기는 2차원 SPD 이차함수입니다. PPA는 한 걸음에 선형계를 풀고, CG는 행렬–벡터 곱과 실제 잔차를 검사합니다. 같은 반복 수를 같은 비용으로 해석하지 마세요. 종료된 점은 새 반복으로 늘리지 않습니다.',
        'This is one 2D SPD quadratic. PPA solves a linear system each step; CG uses matrix-vector products and true-residual checks. Equal iteration counts do not mean equal cost, and stopped paths receive no invented iterates.')+'</p></div></div></section>'
    body += '<section id="breadth"><h2>'+bi('한 경로에서 끝내지 않기', 'Look beyond one path')+'</h2><p>'+bi(
        '8개 주제 모두 seed 0–31을 빠짐없이 계산했습니다. 계산 가능한 비율과 unresolved 사례를 구분해 남깁니다. 합성 표본은 대표적인 실제 데이터나 최악 사례 인증이 아닙니다.',
        'Every topic includes every seed 0–31. Resolved ratios and unresolved cases are retained separately. Synthetic sampling is neither representative real data nor a worst-case certificate.')+'</p><div class="scroll"><table class="tour-table"><thead><tr>'
    for ko,en in [('주제', 'Topic'), ('표본', 'Cases'), ('측정 가능', 'Resolved'), ('판정 불가', 'Unresolved')]:
        body += '<th>'+bi(ko,en)+'</th>'
    body += '</tr></thead><tbody>'
    for artifact in artifacts:
        if 'topic' not in artifact:
            continue
        s = artifact['summary']
        body += '<tr><td><a href="'+artifact['path']+'">'+escape(LESSONS[artifact['topic']]['name'])+'</a></td>'
        body += ''.join('<td>'+str(s[k])+'</td>' for k in ('trials','measured','unresolved'))+'</tr>'
    body += '</tbody></table></div><p class="small">'+bi('각 보고서에서 모든 표본의 입력·경로·곡선을 열 수 있습니다. Heavy-ball은 경험적 검사, ISTA/FISTA 비교는 INFO입니다.',
        'Every report exposes all cases, inputs, trajectories and curves. Heavy-ball is empirical; ISTA/FISTA comparison is INFO-only.')+'</p></section>'
    body += '<section id="understand"><h2>'+bi('관측을 가정과 정리에 연결하기', 'Connect observations to assumptions and theory')+'</h2><div class="tour-grid">'
    body += card('atlas.html', ('방법의 계산 흐름과 관계', 'Update flows and method relationships'),
        ('8개 주제의 질문·가정·갱신식·보장을 읽고 두 방법의 연산과 기억 상태를 비교합니다.',
         'Read the questions, assumptions, recurrences and guarantees for eight topics; compare their operations and carried state.'), 'LEARNING ATLAS')
    body += card('tight-gd.html', ('상계에 도달하는 공개 구성', 'A public construction attaining its bound'),
        ('Drori–Teboulle의 제한된 GD 사례입니다. 최악성의 근거는 문헌의 정리이며, 수치 일치는 증명이 아닙니다.',
         'A scoped Drori–Teboulle GD construction. Its extremality comes from the published result; numerical agreement is not a proof.'), 'PUBLIC TIGHT CASE')
    body += '</div></section>'
    if extended:
        body += '<section id="sparse-attainment"><h2>'+bi('활성 좌표 수와 정확도를 연결하기', 'Connect support size to attainable accuracy')+'</h2><div class="tour-grid">'
        body += card('fw-sparsity.html', ('원자를 적게 쓰는 대가', 'The cost of using few atoms'),
            ('Jaggi의 Lemmas 3–4를 실제 FW 가중치와 비교합니다. 네 차원의 모든 반복, 같은 활성 좌표의 균등 가중치, s<n 조건을 확인하세요.',
             'Compare Jaggi’s Lemmas 3–4 with actual FW weights. Inspect every update in four dimensions, equal weights on the same support, and the condition s<n.'), 'PUBLIC SHARP SUPPORT MINIMUM')
        body += '<div><p class="callout">'+bi('읽을 질문: 같은 s개 좌표를 쓴다면 가중치를 어떻게 나눠야 목적함수가 가장 작을까요?',
            'Reading question: with the same s active coordinates, which weights give the smallest objective?')+'</p><p>'+bi('f=Σxᵢ²에서 균등 배분은 1/s를 달성합니다. 실제 FW 반복점이 항상 이 값에 닿는 것은 아닙니다. 이는 GD의 정해진 반복 후 상계 달성과 다른 종류의 정확한 결과입니다.',
            'For f=Σxᵢ², equal weights attain 1/s. Actual FW iterates need not attain it. This is a different sharp statement from GD attaining an iteration-dependent upper bound.')+'</p><p>'+bi('미리보기는 n=3, k=2의 실제 목적함수 높이입니다. 초록 점은 같은 활성 좌표의 비교점이며 별도 알고리즘의 궤도가 아닙니다. dual 하한 2/s는 모든 좌표가 활성화되기 전까지만 적용합니다.',
            'The preview shows actual objective heights at n=3, k=2. Green is a comparison on the same active coordinates, not another algorithm trajectory. The dual floor 2/s ends before full support.')+'</p></div></div></section>'
    if randomized:
        body += '<section id="randomized"><h2>'+bi('같은 “상계 달성”도 무엇의 평균인지 확인하기', 'Ask what an attained expectation actually averages')+'</h2><div class="tour-grid">'
        body += card('kaczmarz.html', ('한 실행이 멈춰 있어도 평균은 줄어들까?', 'Can the mean shrink while one run waits?'),
            ('Strohmer–Vershynin의 상계 달성 구성을 여섯 입력에서 봅니다. 실제 3D 투영을 회전시키고 64개 시드 모두와 정확한 기대값을 비교합니다.',
             'Inspect six members of Strohmer–Vershynin’s sharp construction. Rotate actual 3D projections and compare all 64 seeds with the exact expectation.'), 'PUBLIC EXPECTATION ATTAINMENT')
        body += '<div><p class="callout">'+bi('읽을 질문: 어떤 실행의 오차가 이론 곡선 위에 있으면 정리가 틀린 것일까요?',
            'Reading question: if one run lies above the curve, has the theorem failed?')+'</p><p>'+bi(
            '여기서 보장하는 것은 모든 무작위 행 선택에 대한 오차 제곱의 기대값입니다. 현재의 유한 표본 평균이나 개별 경로를 점별로 제한하지 않습니다. 표본을 모두 보존하고 해에 도달한 뒤에도 추출을 계속합니다.',
            'The theorem bounds squared error averaged over all random row choices. It does not bound each trajectory or the current finite sample mean. Every trial is retained, with sampling continuing after reaching zero.')+'</p><p>'+bi(
            '미리보기의 세 축은 실제 좌표 x₁, x₂, x₃이며 목적함수 높이가 아닙니다. I₃와 시작점 (1,1,1)의 초기 상태입니다. 입력 크기·시드·그림은 추가 설명이며 원문 실험 데이터가 아닙니다.',
            'The preview axes are actual x1, x2, x3 coordinates, not objective height. It shows the initial state for I₃ and start (1,1,1). Sizes, seeds and visuals are added illustrations, not source experimental data.')+'</p></div></div>'
        body += '<div class="scroll"><table><thead><tr><th>'+bi('공개 구성', 'Public construction')+'</th><th>'+bi('정확히 달성하는 대상', 'What is attained')+'</th><th>'+bi('해석 범위', 'Scope')+'</th></tr></thead><tbody>'
        for name,ko,en,scope_ko,scope_en in [
            ('GD · Drori–Teboulle','정해진 N회 후 목적함수 gap 상계','An objective-gap upper bound after N updates','명시된 h≤1 조건의 결정론적 구성','A deterministic construction under the stated h≤1 conditions'),
            ('FW · Jaggi','s개 이하 좌표로 가능한 최소 목적함수','The smallest objective using at most s coordinates','실제 FW 경로가 매번 최소를 달성한다는 뜻은 아님','Actual FW iterates need not attain that support minimum'),
            ('RK · Strohmer–Vershynin','무작위 행 선택에 대한 오차 제곱의 기대값 상계','An expected squared-error upper bound over random row choices','한 경로나 유한 표본 평균의 점별 보장이 아님','Not a pointwise bound on one run or a finite mean'),
        ]:
            body += '<tr><td>'+escape(name)+'</td><td>'+bi(ko,en)+'</td><td>'+bi(scope_ko,scope_en)+'</td></tr>'
        body += '</tbody></table></div></section>'
    if sampling:
        body += '<section id="sampling"><h2>'+bi('기대값 구성에서 실제 신호 복원으로', 'From an expectation construction to signal reconstruction')+'</h2><div class="tour-grid">'
        body += card('sampling.html', ('같은 관측을 어떤 순서로 사용할까?', 'In which order should the same observations be used?'),
            ('Strohmer–Vershynin §4.1의 700개 관측과 101개 Fourier 계수 조건입니다. 세 개의 새 입력에서 정렬 순서·균등 무작위·간격 가중 무작위를 각각 15,000회 실행했습니다.',
             'Strohmer–Vershynin §4.1: 700 observations and 101 Fourier coefficients. Three declared new inputs compare sorted cyclic, uniform and density-weighted row selection over 15,000 projections.'), 'PUBLISHED PROTOCOL · DECLARED NEW INPUTS')
        body += '<div><p class="callout">'+bi('읽을 질문: 샘플이 몰린 곳과 드문 곳의 관측을 같은 확률로 골라도 될까요?',
            'Reading question: should observations in dense and sparse regions have the same selection probability?')+'</p><p>'+bi(
            '이웃 간격으로 선택 확률을 정합니다. 투영식 자체는 같으며 화면에서 실제 파형·선택한 관측·모든 오차를 함께 확인합니다. 미리보기는 seed 0, 가중 무작위의 k=100 파형입니다.',
            'Neighbor gaps determine selection probabilities. The projection formula stays the same; inspect actual waveforms, selected observations and every error. The preview shows seed 0, weighted random selection at k=100.')+'</p><p>'+bi(
            '앞의 유한 상태 구성은 오차 제곱의 기대값을 정확히 계산합니다. 여기의 신호 실험은 세 입력 각각의 계수 L2 오차 경로이며 기대값이나 동일한 문제의 속도 비교가 아닙니다. 첫 입력이 정리 4의 충분조건을 벗어나도 그대로 남깁니다.',
            'The finite-state construction computes expected squared error exactly. This signal experiment records coefficient L2 errors of individual paths on three inputs; it is not an expectation or a timing comparison on the same problem. The first input stays visible when Theorem 4’s sufficient condition is inapplicable.')+'</p></div></div></section>'
    body += '<section><h2>'+bi('묶음의 설정과 파일 확인', 'Inspect the bundle and its settings')+'</h2><p>'+bi(
        '폴더 전체를 복사하면 연결을 유지할 수 있습니다. 수치와 설정은 각 HTML에 포함되어 있고, manifest에는 생성 명령과 파일 SHA-256이 기록됩니다.',
        'Copy the whole folder to preserve its links. Each HTML contains its numeric record; the manifest lists generation commands and file SHA-256 hashes.')+'</p><a href="manifest.json">manifest.json</a><p class="small">'+bi(
        '해시는 파일 변화를 확인하는 수단입니다. 독립적 검토나 사용자 수를 뜻하지 않습니다.',
        'Hashes detect file changes; they are not independent review or evidence of adoption.')+'</p></section>'
    return page('Follow the evidence', bi('논문에서 시작해, 계산과 그림으로 이해하기',
                'From a published idea to computations you can inspect'), body, lang=lang)


def build_tour(output: Path, lang: str = 'en', *, extended: bool = False) -> dict:
    """Stage a complete folder; refuse existing destinations and clean failed writes."""
    if lang not in ('ko', 'en'):
        raise ValueError('lang must be en or ko')
    if type(extended) is not bool:
        raise ValueError('extended must be a boolean')
    destination = Path(output).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('tour destination already exists; choose a new directory')
    if not destination.parent.is_dir():
        raise ValueError('tour destination parent directory must already exist')
    artifacts, previews = [], {}
    with tempfile.TemporaryDirectory(prefix='.chainbench-tour-', dir=destination.parent) as temporary:
        stage = Path(temporary)
        reports = chain(_reports(lang, extended=True), _extended_reports(lang)) if extended else _reports(lang)
        for filename, html, metadata in reports:
            if filename in ('shewchuk.html', 'simplex.html', 'proximal.html', 'tight-gd.html', 'heavy-ball.html', 'landscape.html'):
                previews[filename] = _thumbnail(html, 1 if filename == 'proximal.html' else 0)
            if filename == 'shewchuk.html':
                previews['shewchuk-surface'] = _thumbnail(html, 1)
            if filename == 'deblur.html':
                match = re.search(r'<img data-deblur-image="fista"[^>]*src="(data:image/png;base64,[^"]+)"', html)
                if match is None:
                    raise ValueError('deblurring preview must come from the computed reconstruction')
                previews[filename] = match.group(1)
            if filename == 'wavelet.html':
                match = re.search(r'<img data-wavelet-image="fista"[^>]*src="(data:image/png;base64,[^"]+)"', html)
                if match is None:
                    raise ValueError('wavelet preview must come from the computed reconstruction')
                previews[filename] = match.group(1)
            if filename == 'fw-sparsity.html':
                previews[filename] = _thumbnail(html, 1)
            if filename == 'kaczmarz.html':
                previews[filename] = _thumbnail(html, 1)
            if filename == 'sampling.html':
                match = re.search(r'<details data-sampling-gallery="weighted-100">.*?(<svg\b.*?</svg>)', html, flags=re.S)
                if match is None:
                    raise ValueError('sampling preview must come from the actual seed-0 k=100 waveform')
                previews[filename] = 'data:image/svg+xml;base64,'+base64.b64encode(match.group(1).encode()).decode('ascii')
            if filename == 'cg-spectrum.html':
                match = re.search(r'<details data-cg-overview><summary>hadamard · equal-energy</summary>.*?(<svg\b.*?</svg>)', html, flags=re.S)
                if match is None:
                    raise ValueError('CG spectrum preview must come from the actual Hadamard equal-energy overview')
                previews[filename] = 'data:image/svg+xml;base64,'+base64.b64encode(match.group(1).encode()).decode('ascii')
            if filename == 'adam.html':
                previews[filename] = _adam_thumbnail(html)
            if filename == 'admm.html':
                previews[filename] = _admm_thumbnail(html)
            if filename == 'backtracking.html':
                previews[filename] = _backtracking_thumbnail(html)
            raw = _with_navigation(html, filename, extended=extended).encode('utf8')
            (stage/filename).write_bytes(raw)
            artifacts.append({'path': filename, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), **metadata})
        raw = _index(artifacts, previews, lang).encode('utf8')
        (stage/'index.html').write_bytes(raw)
        artifacts.insert(0, {'path': 'index.html', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                             'layer': 'guided index'})
        manifest = {'kind': 'chainbench.offline-tour', 'schema_version': 1,
                    'extensions': list(EXTENSIONS) if extended else [],
                    'environment': {'chainbench': __version__, 'numpy': np.__version__,
                                    'python': platform.python_version(), 'os': platform.system()},
                    'language': lang, 'start': 'index.html', 'artifacts': artifacts,
                    'hash_scope': 'Exact UTF-8 bytes of listed HTML files; manifest does not hash itself.',
                    'notice': 'Generated finite numerical evidence; not a proof, broad real-data benchmark or external review.'}
        (stage/'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')
        destination.mkdir()  # Exclusive reservation after all calculations succeed.
        created = []
        try:
            # Create files exclusively; publish the manifest last as the completion record.
            for name in [a['path'] for a in artifacts]+['manifest.json']:
                target = destination/name
                with target.open('xb') as stream:
                    created.append(target)
                    stream.write((stage/name).read_bytes())
        except BaseException:
            for target in reversed(created):
                target.unlink()
            if not any(destination.iterdir()):
                destination.rmdir()
            raise
    return manifest
