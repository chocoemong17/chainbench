"""Render a two-page Korean reading guide from the independently audited tour.

Development-only tools: Playwright/Chromium, PyMuPDF and Noto CJK fonts.
Keep the tour unchanged; store provenance beside the separate review packet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import tempfile
from html import escape
from importlib.metadata import version
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright
from smoke_workflows import validate_tour

CSS = """
@page{size:A4 landscape;margin:0}*{box-sizing:border-box}
body{margin:0;color:#18304a;font:12px/1.5 'Noto Sans CJK KR',sans-serif}
article{width:297mm;height:210mm;padding:10mm 12mm;position:relative;break-after:page}
article:last-child{break-after:auto}[lang=en]{display:none}
h1{font-size:25px;line-height:1.25;margin:7px 0 12px}
h2{font-size:17px;margin:10px 0}h4{margin:2px 0 8px;font-size:14px}p{margin:7px 0}
.eyebrow{font:10px sans-serif;letter-spacing:.13em;color:#536d89}
.columns{display:grid;grid-template-columns:1.1fr 1fr;gap:23px;margin-top:12px}
.figure img{display:block;width:100%;height:auto}.figure{min-width:0}
.bt-flow{background:#f5f8fc;border:1px solid #d5e1ee;border-radius:12px;padding:13px 18px;margin-bottom:15px}
ol{padding-left:22px;margin:5px 0}li{padding:3px 0}code{font:10px monospace;white-space:normal}
table{border-collapse:collapse;width:100%;font-size:12px;margin:12px 0}
th,td{border-bottom:1px solid #d5e0eb;padding:10px;text-align:left;vertical-align:top}
th{background:#edf3fa}td:first-child{width:21%}td{width:39.5%}
.note{background:#fff4e2;border-left:3px solid #d99531;padding:9px 12px;margin-top:12px}
.cards{display:grid;grid-template-columns:1fr 1fr 1fr;gap:15px;margin-top:14px}
.card{padding:10px;border:1px solid #d5e0eb;border-radius:10px;background:#f5f8fc}
.card strong{display:block;font-size:16px}.small{font-size:10px}
.foot{position:absolute;bottom:8mm;left:12mm;right:12mm;border-top:1px solid #ccd7e4;padding-top:5px;font-size:9px;display:flex;justify-content:space-between}
a{color:#235bbd}
"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_html(src, flows, table, counts, commit, run_url):
    pages, runs, trials, updates = counts
    return f'''<!doctype html><html lang="ko"><meta charset="utf-8">
<title>ChainBench · FISTA 이동 크기 선택</title><style>{CSS}</style><body>
<article><div class="content">
<div class="eyebrow">CHAINBENCH / FOLLOW THE STEP-SELECTION QUESTION</div>
<h1>같은 축소 계산에서, 이동 크기 선택으로</h1>
<p>고정 L=9의 FISTA → 후보 검사 → 채택된 경로와 전체 원본 표</p>
<div class="columns"><div class="figure"><h2>실제 첫 후보가 거부되는 장면</h2>
<img alt="첫 거부 후보에서 목적함수와 이차 모형을 비교한 실제 계산 그림" src="{escape(src, quote=True)}">
<p>λ=0.8, x₀=(0,0), L₀=1 · k=1, j=0<br>
q=(0.6,−6.4)에서 F(q)−Q₁(q,y)=163.84&gt;0입니다.</p>
<p class="small">그림은 보고서의 실제 SVG입니다. 높이는 같은 F*를 뺀 값이며 음수 모형 값도 남깁니다.
s는 후보로 향하는 직선의 위치이고 반복 번호가 아닙니다.</p></div>
<div>{flows}</div></div>
<p class="note">두 흐름은 FISTA의 외삽점 y_k에서 시작합니다. 고정 L 보고서의 ISTA 부분에는 외삽이 없습니다.
흐름도는 기호 설명이며, 실제 좌표와 모든 후보는 연결된 보고서에 있습니다.</p>
<p class="small">함께 읽기: 전체 묶음의 index.html → 이동 크기 선택 → backtracking.html 또는 proximal.html</p>
</div><div class="foot"><span>½‖diag(1,3)x−(1.4,−2.4)‖²+λ‖x‖₁ · 새 설명용 입력</span><span>1 / 2</span></div></article>
<article><div class="content">
<div class="eyebrow">CHAINBENCH / COMPARE THE MECHANISM AND READ THE EVIDENCE</div>
<h1>무엇이 같고, 무엇을 다르게 읽어야 할까?</h1>{table}
<p class="note">한 후보의 통과는 함수 전체의 상한 인증이나 이전 x보다 작은 목적값을 뜻하지 않습니다.
각 상한의 R은 해당 시작점에서 최적해까지의 거리입니다. 후보 수·갱신 수·이론 상한을 실행 시간 순위로 읽지 마세요.</p>
<div class="cards"><div class="card"><strong>{pages}개 HTML 페이지</strong>
전체 묶음의 index.html에서 시작합니다. 논문 설명·3D 그림·다양한 사례를 함께 탐색합니다.</div>
<div class="card"><strong>{runs}개 실행 · {trials}개 후보</strong>
실행마다 {updates}회 채택 갱신의 모든 시도를 보존합니다. 후보 수는 검증한 기록에서 집계합니다.</div>
<div class="card"><strong>그림에서 원본 기록으로</strong>
전체 보고서에서 실제 좌표·후보·조건을 확인하세요. 한국어·영어와 스크립트 없는 읽기를 지원합니다.</div></div>
<p class="small">생성 커밋 <code>{commit}</code> · <a href="{escape(run_url, quote=True)}">GitHub 생성 기록</a><br>
이 PDF의 기록 검증·조판 검사는 전체 CI 통과나 외부 검토를 뜻하지 않습니다. 파일 지문은 evidence.json에 있습니다.</p>
</div><div class="foot"><span><a href="https://www.tau.ac.il/~becka/FISTA.pdf">Beck–Teboulle (2009): fixed L p.193/PDF11; backtracking p.194/PDF12; Thm4.4 p.195/PDF13</a></span><span>2 / 2</span></div></article>
</body></html>'''


def render(tour, output, run_url):
    if output.exists():
        raise FileExistsError(output)
    if not re.fullmatch(r'https://github\.com/chocoemong17/chainbench/actions/runs/[0-9]+', run_url):
        raise ValueError('Use the actual ChainBench Actions run URL')
    commit = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[1], text=True,
    ).strip()
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise RuntimeError('Missing full source commit')
    records = validate_tour(tour)
    manifest = json.loads((tour/'manifest.json').read_text(encoding='utf8'))
    if len(records) != 24 or 'backtracking.html' not in records:
        raise ValueError('The complete extended tour is required')
    record = records['backtracking.html']
    trials = sum(len(s['trials']) for c in record['cases'] for s in c['stages'])
    counts = len(manifest['artifacts']), len(record['cases']), trials, record['parameters']['steps']
    evidence = dict(source_commit=commit, run_url=run_url, manifest_sha256=digest(tour/'manifest.json'),
                    numerical_records=len(records), html_pages=counts[0], backtracking_runs=counts[1],
                    candidate_trials=trials, accepted_updates_per_run=counts[3],
                    renderer_sha256=digest(Path(__file__)),
                    environment=dict(python=platform.python_version(),
                                     playwright=version('playwright'), pymupdf=pymupdf.VersionBind),
                    scope='Tour record audit and PDF layout only; not full CI or independent review')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.review-', dir=output.parent) as tmp:
        stage = Path(tmp)/'packet'
        stage.mkdir()
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(offline=True, java_script_enabled=False,
                                          viewport={'width': 1440, 'height': 1000})
            page = context.new_page()
            page.goto((tour/'index.html').resolve().as_uri())
            src = page.locator('a.tour-card[href="backtracking.html"] img').get_attribute('src')
            flows = page.locator('[data-backtracking-comparison] .bt-flows').evaluate('e=>e.outerHTML')
            table = page.locator('[data-backtracking-comparison] table').evaluate('e=>e.outerHTML')
            source = stage/'review.html'
            source.write_text(render_html(src, flows, table, counts, commit, run_url), encoding='utf8')
            page.goto(source.resolve().as_uri())
            page.emulate_media(media='print')
            page.evaluate('document.fonts.ready')
            if not page.locator('img').evaluate_all('(es)=>es.length===1&&es.every(e=>e.complete&&e.naturalWidth>0)'):
                raise RuntimeError('PDF figure did not load')
            if page.locator('[data-backtracking-flow]').count() != 2 or page.locator('[data-backtracking-meaning]').count() != 7:
                raise RuntimeError('Missing comparison content')
            geometry = page.locator('article').evaluate_all('''articles=>articles.map(a=>{
              const nodes=[...a.querySelectorAll('.content, .content *')]
                .filter(e=>e.getClientRects().length);
              const boxes=nodes.map(e=>e.getBoundingClientRect());
              return {bottom:Math.max(...boxes.map(b=>b.bottom)),
                footer:a.querySelector('.foot').getBoundingClientRect().top,
                left:Math.min(...boxes.map(b=>b.left)),right:Math.max(...boxes.map(b=>b.right)),
                width:a.clientWidth};})''')
            if len(geometry) != 2 or any(g['bottom']+7 >= g['footer'] or g['left'] < 0 or g['right'] > g['width']+1 for g in geometry):
                raise RuntimeError(f'PDF content overflow: {geometry}')
            pdf = stage/'ChainBench_FISTA_review.pdf'
            page.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
            evidence.update(browser=browser.version, geometry=geometry)
            browser.close()
        with pymupdf.open(pdf) as document:
            if len(document) != 2:
                raise RuntimeError('Expected exactly two PDF pages')
            titles = ('같은축소계산에서,이동크기선택으로', '무엇이같고,무엇을다르게읽어야할까?')
            evidence['pdf_fonts'] = []
            for index, sheet in enumerate(document):
                text = sheet.get_text()
                if len(text) < 400 or '\ufffd' in text or titles[index] not in re.sub(r'\s+', '', text):
                    raise RuntimeError('Missing or broken PDF text')
                fonts = sheet.get_fonts()
                # Chromium may rename CJK subsets; check the delivered text and
                # font bytes rather than depending on a particular basefont name.
                if not fonts or any(not document.extract_font(f[0])[3] for f in fonts):
                    raise RuntimeError('PDF font is not embedded')
                evidence['pdf_fonts'].append([dict(name=f[3], type=f[2],
                    embedded_bytes=len(document.extract_font(f[0])[3])) for f in fonts])
                sheet.get_pixmap(matrix=pymupdf.Matrix(1.2, 1.2)).save(stage/f'page-{index+1}.png')
        evidence['pdf_pages'] = 2
        evidence['files'] = {p.name: dict(bytes=p.stat().st_size, sha256=digest(p)) for p in sorted(stage.iterdir())}
        (stage/'evidence.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
        stage.rename(output)
    print(json.dumps(evidence, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tour', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-url', required=True)
    args = parser.parse_args()
    render(args.tour, args.output, args.run_url)


if __name__ == '__main__':
    main()
