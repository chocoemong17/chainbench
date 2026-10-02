"""Generate, independently audit and read stored-input reports on the CI runner."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
from html import escape
from pathlib import Path

import pymupdf
from instance_evidence import CASES
from playwright.sync_api import expect, sync_playwright
from smoke_instances import exercise_instances


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    def run(argv, cwd, env):
        return subprocess.run(argv, cwd=cwd, env=env, check=True, capture_output=True,
                              text=True, encoding='utf8').stdout
    cli = shutil.which('chainbench')
    assert cli, 'installed CLI is required'
    work = args.output.resolve()
    audits = exercise_instances(cli, work, os.environ.copy(), run)
    replay_path = work/'replay.html'
    run([cli, 'instance', 'replay', str(work/'imported-quadratic-result.json'), '--format', 'html',
         '--lang', 'ko', '--output', str(replay_path)], work, os.environ.copy())
    source = os.environ['GITHUB_SHA']
    proof = {'source_commit': source, 'audits': audits, 'viewports': [],
             'network_requests': [], 'javascript_errors': []}
    names = [case[0] for case in CASES] + ['replay']
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        proof['browser'] = browser.version
        for width in (1440, 390):
            context = browser.new_context(viewport={'width': width, 'height': 1000}, offline=True)
            page = context.new_page()
            page.on('pageerror', lambda e: proof['javascript_errors'].append(str(e)))
            page.on('request', lambda r: proof['network_requests'].append(r.url)
                    if r.url.startswith(('http:', 'https:')) else None)
            for name in names:
                page.goto((work/f'{name}.html').as_uri())
                page.evaluate("document.documentElement.style.scrollBehavior='auto'")
                payload = json.loads(page.locator('#chainbench-evidence').text_content())
                record = payload['replayed'] if name == 'replay' else payload
                assert page.locator('[data-instance-chart]').count() == 3
                assert page.locator('[data-instance-method]').count() == len(record['runs'])
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.locator('nav a[href="#instance-context"]').focus()
                page.locator('nav a[href="#instance-context"]').press('Enter')
                expect(page.locator('#instance-context')).to_be_in_viewport()
                details = page.locator('#instance-context details')
                details.locator('summary').focus()
                details.locator('summary').press('Enter')
                expect(details.locator('pre')).to_be_visible()
                inputs = json.loads(details.locator('pre').text_content())
                assert inputs['instance'] == record['instance']
                assert inputs['reference'] == record['fixture']['x_star']
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                details.locator('summary').press('Enter')
                for method in record['runs']:
                    page.locator('#instance-method').select_option(method['method'])
                    slider = page.locator('#instance-step')
                    slider.focus()
                    slider.press('Home')
                    assert json.loads(page.locator('#instance-sample').text_content()) == method['rows'][0]
                    slider.press('End')
                    assert slider.get_attribute('max') == str(method['updates'])
                    assert json.loads(page.locator('#instance-sample').text_content()) == method['rows'][-1]
                page.locator('[data-action="language"]').focus()
                page.locator('[data-action="language"]').press('Enter')
                assert page.locator('html').get_attribute('lang') == 'en'
                page.locator('[data-action="language"]').press('Enter')
                appendix = page.locator('#chainbench-evidence').locator('..')
                appendix.locator(':scope > summary').click()
                with page.expect_download() as download:
                    page.locator('[data-download="chainbench-evidence"]').click()
                target = work/f'{name}-download-{width}.json'
                download.value.save_as(target)
                assert json.loads(target.read_text(encoding='utf8')) == payload
                appendix.locator(':scope > summary').click()
                if width == 390:
                    region = page.locator('[data-instance-chart="gap"]')
                    assert region.evaluate('(el)=>el.scrollWidth>el.clientWidth')
                    region.focus()
                    region.press('ArrowRight')
                    page.wait_for_function('el=>el.scrollLeft>0', arg=region.element_handle())
                    region.evaluate('(el)=>el.scrollLeft=0')
                if name in ('imported-quadratic', 'imported-psd'):
                    page.locator('#instance-context').screenshot(path=str(work/f'{name}-context-{width}.png'))
                    page.locator('[data-instance-chart="gap"]').screenshot(path=str(work/f'{name}-gap-{width}.png'))
                    if width == 1440 and name == 'imported-psd':
                        page.locator('[data-instance-chart="distance_to_reference"]').screenshot(path=str(work/'psd-distance.png'))
                proof['viewports'].append({'case': name, 'width': width, 'plots': 3,
                    'methods': len(record['runs']), 'exact_keyboard_samples': True,
                    'exact_download': True, 'page_overflow': False})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        for name in names:
            page.goto((work/f'{name}.html').as_uri())
            assert page.locator('[data-instance-chart] svg:visible').count() == 3
            assert page.locator('#instance-inspector-controls').is_hidden()
            page.locator('#instance-context summary').click()
            expect(page.locator('#instance-context pre')).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        context.close()
        proof['no_script'] = {'reports': len(names), 'static_plots_and_input_details': True}
        assert not proof['network_requests'] and not proof['javascript_errors']
        def picture(name):
            return '<img src="data:image/png;base64,' + base64.b64encode((work/name).read_bytes()).decode() + '">'
        packet = ('<!doctype html><html lang="ko"><meta charset="utf-8"><style>'
            '@page{size:A4;margin:14mm}body{font:12px/1.5 sans-serif;color:#172238;margin:0}'
            'section{break-after:page}section:last-child{break-after:auto}h1{font-size:24px}'
            'h2{font-size:20px}img{display:block;max-width:100%;max-height:94mm;object-fit:contain}'
            'pre{font:11px/1.5 monospace;white-space:pre-wrap}code{font-size:9px;overflow-wrap:anywhere}'
            '.note{padding:12px;background:#eef2f7}</style><body><section>'
            '<h1>저장한 숫자로 다시 실행하기</h1><p>Stored inputs · exact replay</p>'
            '<p>예제 설정을 재생성하는 대신 행렬·벡터·시작점의 실제 float64 값을 저장합니다. '
            '행렬을 가져올 때 대칭성을 몰래 수정하지 않고, 기준해의 조건을 확인합니다.</p>'
            '<pre>Q = [[2, 1], [1, 2]]    b = [1, -1]\nx* = [1, -1]    x0 = [2, -1]    L = 3, μ = 1\n'
            'GD 첫 업데이트: [4/3, -4/3]\nPPA(c=1) 첫 업데이트: [11/8, -9/8]</pre>'
            + picture('imported-quadratic-gap-1440.png')
            + '<p class="note">그래프는 실제 저장된 행입니다. x축 k는 완료한 업데이트이며, '
            '같은 k가 같은 계산 비용을 뜻하지 않습니다. CG의 잔차 종료와 방법별 설정은 HTML에 남습니다.</p>'
            '<p>입력 해시: <code>' + audits[6]['input_sha256'] + '</code></p>'
            '<p>Source: <code>' + escape(source) + '</code></p></section><section>'
            '<h2>gap이 0이어도 기준점과 다를 수 있습니다</h2>'
            '<pre>Q = diag(0, 2)    b = [0, -2]\nx* = [4, -1]    x0 = [0, 1]</pre>'
            '<p>GD는 한 번 갱신해 [0, -1]에 도달합니다. 목적함수 gap은 0이고 기울기도 0이지만 '
            '지정한 기준점까지의 거리는 4입니다. 여러 최적해가 있는 문제의 차이를 그대로 보여줍니다.</p>'
            + picture('psd-distance.png')
            + '<h2>검증과 한계 · Evidence and limits</h2><p>세 문제군의 두 시드씩 6개 생성 입력, '
            '4개 직접 입력을 독립적인 스칼라 계산·바이트 해시로 대조합니다. 11개 HTML을 데스크톱·모바일에서 '
            '오프라인, 키보드, JSON 다운로드, JavaScript 없이 확인합니다.</p>'
            '<p class="note">MATCH는 명시한 오차 범위 안에서 재실행과 일치함을 뜻합니다. '
            '작성자·난수 생성 이력·정리를 인증하지 않습니다. 이 입력들은 공개 합성 예제이며 논문 전체 재현이나 보편적 순위가 아닙니다.</p>'
            '<p>Open imported-quadratic.html, imported-psd.html or replay.html. '
            'browser-verification.json binds the source and inspected outputs.</p>'
            '<p>Source: <code>' + escape(source) + '</code></p></section></body></html>')
        (work/'review.html').write_text(packet, encoding='utf8')
        context = browser.new_context(offline=True)
        page = context.new_page()
        page.goto((work/'review.html').as_uri())
        page.pdf(path=str(work/'ChainBench_stored_inputs_review.pdf'), print_background=True,
                 prefer_css_page_size=True)
        context.close()
        browser.close()
    with pymupdf.open(work/'ChainBench_stored_inputs_review.pdf') as pdf:
        assert len(pdf) == 2
        assert 'Evidence and limits' in pdf[1].get_text()
        for i, p in enumerate(pdf):
            p.get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25)).save(work/f'review-page-{i+1}.png')
        proof['pdf'] = {'pages': 2, 'final_section_present': True}
    proof['files'] = {p.name: {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                      for p in sorted(work.iterdir()) if p.is_file()}
    (work/'browser-verification.json').write_text(json.dumps(proof, indent=2)+'\n', encoding='utf8')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
