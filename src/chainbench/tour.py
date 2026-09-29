"""A bounded offline reading path through existing, independently computed reports."""
from __future__ import annotations

import base64
import hashlib
import json
import platform
import re
import tempfile
from html import escape
from pathlib import Path

import numpy as np

from . import __version__
from ._pages import bi, page
from .case_studies import case_html, gd_tight_case
from .checks import CHECKS
from .deblur_views import deblur_html
from .deblurring import run_deblurring
from .learning import LESSONS, learning_html
from .mechanisms import CSS as MECHANISM_CSS
from .mechanisms import flow_html
from .proximal_geometry import run_proximal_geometry
from .proximal_views import proximal_html
from .reproduction_views import reproduction_html
from .reproductions import run_reproduction
from .simplex_geometry import run_simplex_geometry, simplex_html
from .stress import run_stress, stress_html

STRESS_TRIALS = 32


def _reports(lang):
    yield 'atlas.html', learning_html(lang=lang), {
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


def _with_navigation(html, filename=None):
    nav = '<nav aria-label="Tour"><a href="index.html" data-tour-home>'+bi(
        '← 탐색 안내로 돌아가기', '← Back to the guided tour')+'</a></nav>'
    related = {
        'deblur.html': ('proximal.html', '양의 λ에서 soft threshold는 어떻게 작동할까?', 'How does soft thresholding work at positive lambda?'),
        'proximal.html': ('deblur.html', 'λ=0인 논문의 영상 실험 보기', 'Open the source image experiment at lambda=0'),
        'atlas.html': ('deblur.html', 'FISTA의 공개 영상 실험 열기', 'Open the published FISTA image experiment'),
    }
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


def _index(artifacts, previews, lang):
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
    body += '<div class="tour-steps">'
    for target, ko, en in [('published', '1 · 논문 예제', '1 · Published setup'), ('geometry', '2 · 갱신의 기하', '2 · Update geometry'),
                            ('breadth', '3 · 여러 표본', '3 · Many instances'), ('understand', '4 · 이론과 연결', '4 · Connect the theory')]:
        body += '<a href="#'+target+'">'+bi(ko,en)+'</a>'
    body += '</div><section id="published"><h2>'+bi('먼저, 논문이 실제로 사용한 한 문제', 'Start with a problem the source actually used')+'</h2><div class="tour-grid">'
    body += card('shewchuk.html', ('왜 CG의 경로는 다른가?', 'Why does CG take a different path?'),
        ('Shewchuk의 2×2 문제를 다시 계산합니다. 원 시작점과 추가한 9개 시작점을 구분하고, 등고선·3D 높이·에너지 오차를 함께 봅니다.',
         'Recompute Shewchuk’s 2×2 example. Separate the published start from nine added starts; connect contours, 3D heights and energy error.'), 'PUBLISHED SETUP + VARIATIONS')
    body += '<div><p>'+bi('읽을 질문: 두 방법의 첫 이동이 같아도, 왜 그다음 방향은 달라질까요?',
        'Reading question: if both methods take the same first step, why do their next directions differ?')+'</p>'
    body += '<img style="width:100%;height:auto" alt="Same published-example iterates at their actual objective heights" src="'+previews['shewchuk-surface']+'"><p class="callout">'+bi(
        '원 그림의 픽셀을 복사한 것이 아니라 공개된 입력을 독립 계산한 것입니다. 반복 예산·3D 보기·추가 시작점은 ChainBench의 선택입니다.',
        'This independently computes the published inputs rather than copying figure pixels. Budget, 3D views and additional starts are ChainBench choices.')+'</p><p>'+bi(
        '각 페이지 위의 “탐색 안내로 돌아가기”를 누르면 여기로 돌아옵니다. 파일들은 오프라인에서 읽을 수 있습니다.',
        'Use the return link at the top of each page to come back here. These files can be read offline.')+'</p></div></div></section>'
    body += '<section id="image-experiment"><h2>'+bi('같은 방법을 실제 영상 역문제에 적용하면?', 'What happens on the source image inverse problem?')+'</h2><div class="tour-grid">'
    body += card('deblur.html', ('흐린 관측에서 영상 복원하기', 'Recover an image from blurred observations'),
        ('Beck–Teboulle Figure 5의 ISTA/FISTA 부분을 64×64 영상과 10,000회 갱신으로 다시 계산합니다. 원문과의 차이와 모든 수치를 함께 봅니다.',
         'Recompute the ISTA/FISTA subset of Beck–Teboulle Figure 5 with a 64×64 image and 10,000 updates. Inspect source differences and every scalar observation.'), 'PUBLISHED PROTOCOL RERUN')
    body += '<div><p class="callout">'+bi('읽을 질문: 목적함수 오차가 매우 작으면 깨끗한 원본 영상도 정확히 복원됐다고 말할 수 있을까요?',
        'Reading question: does a tiny objective error mean that the clean image was recovered exactly?')+'</p><p>'+bi('이 실험은 잡음과 정규화 항이 없는 λ=0 설정입니다. 아래 2D proximal 예제는 양의 λ가 좌표를 0으로 만드는 원리를 설명합니다. 서로 다른 질문을 다룹니다.',
        'This image experiment has no noise and lambda=0. The 2D proximal view below explains how positive lambda can zero a coordinate. The two reports answer different questions.')+'</p><p>'+bi('미리보기는 실제 10,000회 FISTA 복원 영상입니다. 모든 영상이 같은 [0,1] 회색조를 사용하며 전체 수치 배열은 보고서에서 확인합니다.',
        'The preview is the actual FISTA reconstruction at 10,000 steps. Every image uses the same [0,1] grayscale; full numeric arrays are in the report.')+'</p></div></div></section>'
    body += '<section id="geometry"><h2>'+bi('다른 문제 구조에서는 어떻게 움직일까?', 'How do updates change with the problem structure?')+'</h2><div class="tour-grid">'
    body += card('simplex.html', ('가능한 삼각형 안에서 이동', 'Move inside a feasible triangle'),
        ('Frank–Wolfe의 꼭짓점 선택과 선분 갱신을 12개 조합에서 봅니다. 목적함수가 증가하는 첫 단계도 그대로 남깁니다.',
         'Inspect Frank–Wolfe’s oracle and segment update over all 12 combinations, including a first step that increases the objective.'), 'CONTROLLED GEOMETRY')
    body += card('proximal.html', ('외삽하고, 이동하고, 수축하기', 'Extrapolate, step, then shrink'),
        ('ISTA/FISTA의 중간점과 soft threshold를 9개 조합에서 확인합니다. λ에 따라 좌표가 0이 되는 이유를 읽어보세요.',
         'Inspect ISTA/FISTA stages and soft thresholding over all nine combinations. Follow why changing lambda can make a coordinate zero.'), 'CONTROLLED GEOMETRY')
    body += '</div></section><section id="breadth"><h2>'+bi('한 경로에서 끝내지 않기', 'Look beyond one path')+'</h2><p>'+bi(
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
    body += '</div></section><section><h2>'+bi('묶음의 설정과 파일 확인', 'Inspect the bundle and its settings')+'</h2><p>'+bi(
        '폴더 전체를 복사하면 연결을 유지할 수 있습니다. 수치와 설정은 각 HTML에 포함되어 있고, manifest에는 생성 명령과 파일 SHA-256이 기록됩니다.',
        'Copy the whole folder to preserve its links. Each HTML contains its numeric record; the manifest lists generation commands and file SHA-256 hashes.')+'</p><a href="manifest.json">manifest.json</a><p class="small">'+bi(
        '해시는 파일 변화를 확인하는 수단입니다. 독립적 검토나 사용자 수를 뜻하지 않습니다.',
        'Hashes detect file changes; they are not independent review or evidence of adoption.')+'</p></section>'
    return page('Follow the evidence', bi('논문에서 시작해, 계산과 그림으로 이해하기',
                'From a published idea to computations you can inspect'), body, lang=lang)


def build_tour(output: Path, lang: str = 'en') -> dict:
    """Stage a complete folder; refuse existing destinations and clean failed writes."""
    if lang not in ('ko', 'en'):
        raise ValueError('lang must be en or ko')
    destination = Path(output).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('tour destination already exists; choose a new directory')
    if not destination.parent.is_dir():
        raise ValueError('tour destination parent directory must already exist')
    artifacts, previews = [], {}
    with tempfile.TemporaryDirectory(prefix='.chainbench-tour-', dir=destination.parent) as temporary:
        stage = Path(temporary)
        for filename, html, metadata in _reports(lang):
            if filename in ('shewchuk.html', 'simplex.html', 'proximal.html', 'tight-gd.html'):
                previews[filename] = _thumbnail(html, 1 if filename == 'proximal.html' else 0)
            if filename == 'shewchuk.html':
                previews['shewchuk-surface'] = _thumbnail(html, 1)
            if filename == 'deblur.html':
                match = re.search(r'<img data-deblur-image="fista"[^>]*src="(data:image/png;base64,[^"]+)"', html)
                if match is None:
                    raise ValueError('deblurring preview must come from the computed reconstruction')
                previews[filename] = match.group(1)
            raw = _with_navigation(html, filename).encode('utf8')
            (stage/filename).write_bytes(raw)
            artifacts.append({'path': filename, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), **metadata})
        raw = _index(artifacts, previews, lang).encode('utf8')
        (stage/'index.html').write_bytes(raw)
        artifacts.insert(0, {'path': 'index.html', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                             'layer': 'guided index'})
        manifest = {'kind': 'chainbench.offline-tour', 'schema_version': 1,
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
