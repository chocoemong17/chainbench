"""Generate and inspect installed-CLI saved comparisons entirely on the runner."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
from html import escape
from pathlib import Path

import fitz
from playwright.sync_api import expect, sync_playwright
from smoke_comparison import validate_comparison


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = os.environ.get('GITHUB_SHA', 'unrecorded local source')
    def cli(*arguments):
        result = subprocess.run([sys.executable, '-m', 'chainbench', *map(str, arguments)],
                                check=True, capture_output=True, text=True, encoding='utf8')
        return result.stdout
    inputs, originals = [], []
    for name, family, steps, extra in [
        ('a', 'quadratic', 8, ['--methods', 'gd', 'cg']),
        ('b', 'quadratic', 12, ['--methods', 'gd', 'cg']),
        ('c', 'quadratic', 8, ['--condition-number', '100', '--methods', 'gd', 'cg']),
        ('d', 'diagonal-lasso', 8, []),
    ]:
        path = args.output/f'input-{name}.json'
        cli('experiment', '--preset', family, '--dimension', 4, '--steps', steps,
            *extra, '--output', path)
        inputs.append(path)
        originals.append(json.loads(path.read_text(encoding='utf8')))
    records, audits = {}, {}
    for name, count in [('matched', 2), ('mixed', 4)]:
        html = args.output/f'{name}.html'
        cli('compare', *inputs[:count], '--lang', 'ko', '--output', html)
        record = json.loads(cli('compare', *inputs[:count], '--format', 'json'))
        audits[name] = validate_comparison(record, originals[:count], html.read_text(encoding='utf8'))
        records[name] = record
    assert audits['matched']['shared_recorded_problem'] and not audits['mixed']['shared_recorded_problem']
    evidence = {'source_commit': source, 'audits': audits, 'viewports': [],
                'network_requests': [], 'javascript_errors': []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        evidence['browser'] = browser.version
        for width in (1440, 390):
            context = browser.new_context(viewport={'width': width, 'height': 1000}, offline=True)
            page = context.new_page()
            page.on('pageerror', lambda e: evidence['javascript_errors'].append(str(e)))
            page.on('request', lambda r: evidence['network_requests'].append(r.url)
                    if r.url.startswith(('http:', 'https:')) else None)
            for name, count in [('matched', 2), ('mixed', 4)]:
                page.goto((args.output/f'{name}.html').resolve().as_uri())
                page.evaluate("document.documentElement.style.scrollBehavior='auto'")
                assert page.locator('[data-record]').count() == count
                assert page.locator('[data-pair]').count() == count*(count-1)//2
                assert page.locator('[data-comparison-chart^="shared-"]').count() == (2 if name == 'matched' else 0)
                assert json.loads(page.locator('#chainbench-evidence').text_content()) == records[name]
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.locator('#comparison-context').screenshot(path=str(args.output/f'{name}-context-{width}.png'))
                if width == 390:
                    region = page.locator('[aria-label="Record diagnostics"]')
                    assert region.evaluate('(el)=>el.scrollWidth>el.clientWidth')
                    region.focus()
                    region.press('ArrowRight')
                    page.wait_for_function("document.querySelector('[aria-label=\"Record diagnostics\"]').scrollLeft>0")
                    region.evaluate('(el)=>el.scrollLeft=el.scrollWidth')
                    page.locator('#comparison-context').screenshot(path=str(args.output/f'{name}-context-right-{width}.png'))
                    region.evaluate('(el)=>el.scrollLeft=0')
                # Native anchors/details/language/downloads must remain keyboard operable.
                link = page.locator('nav a[href="#record-A"]')
                link.focus()
                link.press('Enter')
                expect(page.locator('#record-A')).to_be_in_viewport()
                detail = page.locator('#record-A details')
                detail.locator('summary').focus()
                detail.locator('summary').press('Enter')
                expect(detail.locator('pre')).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                detail.locator('summary').press('Enter')
                page.locator('[data-action="language"]').focus()
                page.locator('[data-action="language"]').press('Enter')
                assert page.locator('html').get_attribute('lang') == 'en'
                page.locator('[data-action="language"]').press('Enter')
                appendix = page.locator('#chainbench-evidence').locator('..')
                appendix.locator(':scope > summary').click()
                with page.expect_download() as download:
                    page.locator('[data-download="chainbench-evidence"]').click()
                destination = args.output/f'{name}-download-{width}.json'
                download.value.save_as(destination)
                assert json.loads(destination.read_text(encoding='utf8')) == records[name]
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                if name == 'matched':
                    if width == 390:
                        chart = page.locator('[data-comparison-chart="shared-gd"]')
                        chart.focus()
                        chart.press('ArrowRight')
                        page.wait_for_function("document.querySelector('[data-comparison-chart=\"shared-gd\"]').scrollLeft>0")
                        chart.evaluate('(el)=>el.scrollLeft=el.scrollWidth')
                        chart.screenshot(path=str(args.output/'shared-gd-right-390.png'))
                        chart.evaluate('(el)=>el.scrollLeft=0')
                    page.locator('[data-comparison-chart="shared-gd"]').screenshot(path=str(args.output/f'shared-gd-{width}.png'))
                evidence['viewports'].append({'width': width, 'case': name, 'records': count,
                    'keyboard': 'passed', 'horizontal_regions': 'keyboard checked' if width == 390 else 'full width',
                    'download': 'exact', 'horizontal_page_overflow': False})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        for name, count in [('matched', 2), ('mixed', 4)]:
            page.goto((args.output/f'{name}.html').resolve().as_uri())
            assert page.locator('[data-record]:visible').count() == count
            page.locator('#record-A summary').click()
            expect(page.locator('#record-A pre')).to_be_visible()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        evidence['no_script'] = 'both reports, diagnostic tables, static curves and native details passed'
        context.close()
        assert not evidence['network_requests'] and not evidence['javascript_errors']

        # Larger text in the print packet than scaling a wide desktop screenshot.
        context = browser.new_context(viewport={'width': 900, 'height': 1100}, offline=True)
        page = context.new_page()
        for name in ('matched', 'mixed'):
            page.goto((args.output/f'{name}.html').resolve().as_uri())
            page.locator('#comparison-context').screenshot(path=str(args.output/f'{name}-context-print.png'))
            if name == 'matched':
                page.locator('[data-comparison-chart="shared-gd"]').screenshot(path=str(args.output/'shared-gd-print.png'))
        context.close()

        # A static, two-page judgment packet uses the actual inspected screenshots.
        def picture(name):
            raw = (args.output/name).read_bytes()
            return '<img src="data:image/png;base64,' + base64.b64encode(raw).decode('ascii') + '">'
        packet = ('<!doctype html><html><head><meta charset="utf-8"><style>'
                  '@page{size:A4;margin:14mm}body{font:12px/1.45 sans-serif;color:#172238;margin:0}'
                  'section{break-after:page}section:last-child{break-after:auto}'
                  'h1{font-size:25px}h2{font-size:20px}img{display:block;max-width:100%;max-height:112mm;object-fit:contain;margin:12px 0}'
                  'code{overflow-wrap:anywhere;font-size:9px}.note{background:#eef2f7;padding:12px}</style></head><body>'
                  '<section><h1>ChainBench · saved experiments</h1>'
                  '<p>Two actual records, one declared quadratic: dimension 4, condition number 10, '
                  'L=1, Householder rotation, zero start. Record A requests 8 updates; B requests 12. '
                  'GD and CG retain their own actual endpoints and stopping states.</p>'
                  + picture('matched-context-print.png') + picture('shared-gd-print.png')
                  + '<p class="note">The plot contains saved objective-gap samples. Comparison runs no solver. '
                  'Matching input fingerprints do not authenticate the arrays or the author.</p>'
                  '<p>Source: <code>' + escape(source) + '</code></p></section><section>'
                  '<h2>Different problems stay visibly different</h2>'
                  '<p>Add record C with condition number 100 and record D with diagonal LASSO, '
                  'dimension 4, lambda=0.12 and 8 updates. All six record pairs remain inspectable.</p>'
                  + picture('mixed-context-print.png')
                  + '<p>No common overlay is offered for these four records. Individual panels retain '
                  'their own axes, parameters and environments. A smaller final value on a different '
                  'objective is not a method ranking.</p>'
                  '<h2>Read the complete evidence</h2><p>Open matched.html or mixed.html from this packet. '
                  'Both are self-contained offline reports with Korean/English text, native expandable '
                  'settings, exact SVG samples and a complete JSON download. The input-*.json files '
                  'are the four actual CLI-generated inputs; browser-verification.json records this audit.</p>'
                  '<p class="note">These are selected deterministic examples, not representative sampling, '
                  'paper-figure reproduction or outside review. Validation covers 1440px / 390px, '
                  'keyboard use, no-script reading, downloads and no network requests.</p>'
                  '<p>Source: <code>' + escape(source) + '</code></p></section></body></html>')
        (args.output/'review.html').write_text(packet, encoding='utf8')
        context = browser.new_context(offline=True)
        page = context.new_page()
        page.goto((args.output/'review.html').resolve().as_uri())
        page.pdf(path=str(args.output/'ChainBench_saved_comparison_review.pdf'), print_background=True,
                 prefer_css_page_size=True)
        context.close()
        browser.close()
    with fitz.open(args.output/'ChainBench_saved_comparison_review.pdf') as document:
        assert len(document) == 2, 'Review packet must retain exactly two complete pages'
        assert 'Read the complete evidence' in document[1].get_text()
        for index, pdf_page in enumerate(document):
            pdf_page.get_pixmap(matrix=fitz.Matrix(1.25, 1.25)).save(args.output/f'review-page-{index+1}.png')
        evidence['pdf'] = {'pages': len(document), 'final_section_present': True}
    outputs = {}
    for path in sorted(args.output.iterdir()):
        if path.is_file():
            raw = path.read_bytes()
            outputs[path.name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    evidence['outputs'] = outputs
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
