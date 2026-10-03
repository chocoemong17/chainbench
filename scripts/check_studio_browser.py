"""Actual live computations, accessible controls and offline downloads on CI only."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import tempfile
from html import escape
from pathlib import Path

import pymupdf
from playwright.sync_api import sync_playwright
from smoke_instances import audit_instance_result
from smoke_studio import audit_response, studio_session
from studio_evidence import FAMILIES, case_request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    work = args.output.resolve()
    work.mkdir(parents=True, exist_ok=True)
    proof = {'source_commit': os.environ['GITHUB_SHA'], 'viewports': [], 'outside_requests': [],
             'javascript_errors': [], 'offline_downloads': []}
    with tempfile.TemporaryDirectory(prefix='chainbench-studio-browser-') as directory, sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (1440, 390):
            with studio_session(['chainbench'], Path(directory), os.environ.copy()) as session:
                context = browser.new_context(viewport={'width': width, 'height': 1000}, accept_downloads=True)
                def route(request):
                    if request.request.url.startswith(session['origin']+'/'):
                        request.continue_()
                    else:
                        proof['outside_requests'].append(request.request.url)
                        request.abort()
                context.route('**/*', route)
                page = context.new_page()
                page.on('pageerror', lambda error: proof['javascript_errors'].append(str(error)))
                page.goto(session['url'])
                page.wait_for_function("!document.getElementById('run').disabled")
                assert page.url == session['origin']+'/'
                assert session['token'] not in page.content()
                page.locator('[data-action="language"]').click()
                assert page.locator('html').get_attribute('lang') == 'en'
                page.locator('[data-action="language"]').click()
                assert page.locator('html').get_attribute('lang') == 'ko'
                page.locator('#dimension').fill('4')
                page.locator('#steps').fill('2')
                summary = {'width': width, 'cases': [], 'keyboard': True, 'language': True}
                fingerprints = {}
                for family in FAMILIES:
                    page.locator('#family').select_option(family)
                    if family == 'quadratic':
                        page.locator('#L').fill('2')
                        page.locator('#condition-number').fill('10')
                    elif family == 'diagonal-lasso':
                        page.locator('#lam').fill('.3')
                    for seed in (0, 7):
                        page.locator('#seed').fill(str(seed))
                        assert page.locator('#studio-result').is_hidden()
                        if family == 'quadratic' and seed == 0:
                            page.locator('#studio-form').screenshot(path=str(work/f'controls-{width}.png'))
                        page.locator('#run').focus()
                        with page.expect_response(lambda r: r.url == session['origin']+'/api/run') as pending:
                            page.keyboard.press('Enter')
                        response = pending.value
                        assert response.status == 200
                        value = response.json()
                        request = case_request(family, seed)
                        row = audit_response(value, request)
                        page.wait_for_function("!document.getElementById('studio-result').hidden")
                        record = value['result']
                        assert page.locator('#studio-hash').inner_text() == record['instance']['input_sha256']
                        if page.locator('#studio-result details').get_attribute('open') is None:
                            page.locator('#studio-result summary').focus()
                            page.keyboard.press('Enter')
                        assert json.loads(page.locator('#studio-settings').inner_text()) == request
                        assert session['token'] not in json.dumps(value)
                        fingerprints[family, seed] = row['input_sha256']
                        frame = page.frame_locator('#studio-frame')
                        for run in record['runs']:
                            frame.locator('#instance-method').select_option(run['method'])
                            frame.locator('#instance-step').focus()
                            page.keyboard.press('End')
                            assert json.loads(frame.locator('#instance-sample').inner_text()) == run['rows'][-1]
                            page.keyboard.press('Home')
                            assert json.loads(frame.locator('#instance-sample').inner_text()) == run['rows'][0]
                        name = f'{family}-{seed}-{width}'
                        for id, suffix in [('download-input', 'input.json'), ('download-result', 'result.json'), ('download-html', 'html')]:
                            with page.expect_download() as pending_download:
                                page.locator('#'+id).click()
                            path = work/f'{name}.{suffix}'
                            pending_download.value.save_as(path)
                            if suffix == 'html':
                                assert path.read_text(encoding='utf8') == value['html']
                            else:
                                assert json.loads(path.read_bytes()) == (record['instance'] if suffix == 'input.json' else record)
                                assert path.read_text(encoding='utf8') == value['input_json' if suffix == 'input.json' else 'result_json']
                            assert session['token'] not in path.read_text(encoding='utf8')
                        if family == 'quadratic' and seed == 0:
                            # Capture the live frame as a single viewport. Cropping a
                            # descendant across two scrolling documents was unstable in Chromium.
                            page.locator('#studio-frame').screenshot(path=str(work/f'live-result-{width}.png'))
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
                        summary['cases'].append(row)
                assert all(fingerprints[family, 0] != fingerprints[family, 7] for family in FAMILIES)
                # Controls really select methods, and a changed form cannot export a stale result.
                page.locator('#family').select_option('quadratic')
                for method in FAMILIES['quadratic'][1:]:
                    page.locator(f'input[value="{method}"]').uncheck()
                assert page.locator('#studio-result').is_hidden()
                with page.expect_response(lambda r: r.url == session['origin']+'/api/run') as pending:
                    page.locator('#run').click()
                selected = pending.value.json()
                assert [r['method'] for r in selected['result']['runs']] == ['gd']
                audit_instance_result(selected['result'], selected['result']['instance'], selected['html'])
                page.wait_for_function("!document.getElementById('stop').disabled")
                page.locator('#stop').focus()
                page.keyboard.press('Enter')
                assert session['process'].wait(timeout=10) == 0
                page.wait_for_function("document.getElementById('run').disabled")
                with page.expect_download() as pending_download:
                    page.locator('#download-html').click()
                after = work/f'after-shutdown-{width}.html'
                pending_download.value.save_as(after)
                assert after.read_text(encoding='utf8') == selected['html']
                summary.update(shutdown=True, downloads_after_shutdown=True, method_selection=True, distinct_seeds=True)
                proof['viewports'].append(summary)
                context.close()
        assert not list(Path(directory).iterdir()), 'Studio created files in its working directory'
        for js in (True, False):
            context = browser.new_context(offline=True, java_script_enabled=js, viewport={'width': 390, 'height': 900})
            context.on('request', lambda request: proof['outside_requests'].append(request.url)
                       if request.url.startswith(('https://', 'http://')) else None)
            page = context.new_page()
            page.on('pageerror', lambda error: proof['javascript_errors'].append(str(error)))
            for path in sorted(work.glob('*.html')):
                page.goto(path.as_uri())
                assert page.locator('[data-instance-chart]').count() == 3
                assert page.locator('#instance-context').inner_text()
                record = json.loads(path.with_suffix('.result.json').read_bytes()) if 'after-shutdown' not in path.name else None
                if record:
                    audit_instance_result(record, record['instance'], path.read_text(encoding='utf8'))
                if js and path.name in ('quadratic-0-1440.html', 'quadratic-0-390.html'):
                    width = int(path.stem.rsplit('-', 1)[1])
                    page.set_viewport_size({'width': width, 'height': 1000})
                    page.locator('#instance-context').screenshot(path=str(work/f'result-context-{width}.png'))
                    page.locator('[data-instance-chart="gap"]').screenshot(path=str(work/f'gap-{width}.png'))
                    page.set_viewport_size({'width': 390, 'height': 900})
                proof['offline_downloads'].append({'file': path.name, 'javascript': js, 'readable': True})
            context.close()
        with studio_session(['chainbench'], Path(directory), os.environ.copy()) as session:
            context = browser.new_context(java_script_enabled=False)
            page = context.new_page()
            page.goto(session['url'])
            assert page.locator('#run').is_disabled() and page.locator('#stop').is_disabled()
            assert 'JavaScript' in page.locator('#studio-status').inner_text()
            context.close()
        assert not proof['outside_requests'] and not proof['javascript_errors']
        def image(name):
            return '<img src="data:image/png;base64,'+base64.b64encode((work/name).read_bytes()).decode()+'">'
        source = escape(proof['source_commit'])
        packet = ('<!doctype html><html lang="ko"><meta charset="utf-8"><style>'
            '@page{size:A4;margin:15mm}body{font-family:"Noto Sans CJK KR",sans-serif;color:#172238;font-size:11pt}'
            'section{break-after:page;height:265mm;overflow:hidden}section:last-child{break-after:auto}'
            'h1{font-size:25pt}h2{font-size:18pt}img{display:block;max-width:100%;max-height:155mm;margin:10px auto}'
            'code{font-size:8pt;overflow-wrap:anywhere}.note{font-size:9pt;color:#56657b}</style>'
            '<section><h1>조건을 바꾸고 직접 계산하기</h1><p>ChainBench · Experiment studio</p>'
            '<p>브라우저에서 문제군, 차원, 시드, 업데이트 수와 방법을 선택합니다. 계산하기를 누르면 '
            '저장된 그림을 교체하는 것이 아니라 이 조건의 실제 수치 실험을 실행합니다.</p>'
            +image('controls-1440.png')+
            '<h2>시드와 조건수를 나누어 살펴보세요</h2><p>같은 시드에서 조건수를 바꾸어 이차함수의 기울기 방향 차이를 읽고, '
            '시드를 바꾸어 다른 행렬과 시작점도 관찰하세요. LASSO의 λ는 희소성 가중치입니다.</p>'
            '<p class="note">공개 합성 예제입니다. 논문 전체 재현이나 모든 입력에 대한 순위를 뜻하지 않습니다.</p>'
            '<p>Source: <code>'+source+'</code></p></section><section><h1>실제 궤적을 읽고 가져가기</h1>'
            +image('gap-1440.png')+
            '<p>각 점은 실제 계산된 업데이트입니다. 입력 JSON에는 행렬·벡터·시작점이, 결과 JSON에는 '
            '설정·환경·계산된 행이 보존됩니다. HTML은 서버를 종료한 뒤에도 읽을 수 있습니다.</p>'
            '<h2>검증 · Evidence</h2><p>세 문제군 × 두 시드 × 데스크톱·모바일 화면에서 실제 요청과 결과를 확인합니다. '
            '모든 행의 네 척도와 입력 해시는 별도의 스칼라 계산으로 대조하며, 키보드 선택·정확한 다운로드·종료 후 읽기도 검사합니다.</p>'
            '<p class="note">루프백 서버는 사용자가 명시적으로 시작합니다. 서버에는 보고서를 저장하지 않습니다. '
            '입력·시간·출력 제한이 있고, 정리의 증명이나 외부 사용자 검증을 주장하지 않습니다.</p>'
            '<p>Source: <code>'+source+'</code></p></section></html>')
        (work/'review.html').write_text(packet, encoding='utf8')
        context = browser.new_context(offline=True)
        page = context.new_page()
        page.goto((work/'review.html').as_uri())
        page.pdf(path=str(work/'ChainBench_studio_review.pdf'), print_background=True, prefer_css_page_size=True)
        context.close()
        browser.close()
    with pymupdf.open(work/'ChainBench_studio_review.pdf') as pdf:
        assert len(pdf) == 2 and 'Evidence' in pdf[1].get_text()
        for i, page in enumerate(pdf):
            page.get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25)).save(work/f'review-page-{i+1}.png')
    proof.update(pdf_pages=2, no_server_files=True)
    proof['files'] = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in sorted(work.iterdir()) if p.is_file()}
    (work/'browser-verification.json').write_text(json.dumps(proof, indent=2)+'\n', encoding='utf8')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
