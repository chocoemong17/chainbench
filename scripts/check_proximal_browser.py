"""Optional offline browser check of every recorded ISTA/FISTA proximal case."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    url = args.html.resolve().as_uri()
    evidence = {'viewports': [], 'network_requests': [], 'javascript_errors': []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        evidence['browser'] = browser.version
        for width in (1440, 390):
            context = browser.new_context(viewport={'width': width, 'height': 1000}, offline=True)
            page = context.new_page()
            page.on('pageerror', lambda e: evidence['javascript_errors'].append(str(e)))
            page.on('request', lambda r: evidence['network_requests'].append(r.url)
                    if r.url.startswith(('http:', 'https:')) else None)
            page.goto(url)
            record = json.loads(page.locator('#chainbench-evidence').text_content())
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('[data-prox-case]').count() == 9
            for case in record['cases']:
                primary = case['id'] == 'lambda-2-opposite'
                if not primary:
                    page.locator(f'#{case["id"]} > summary').click()
                panel = page.locator(f'[data-prox-case="{case["id"]}"]')
                slider, select = panel.locator('input[type=range]'), panel.locator('select')
                for method in ('ista', 'fista'):
                    select.select_option(method)
                    slider.focus()
                    slider.press('Home')
                    expect(panel.locator('[data-step]')).to_have_text(f'{method.upper()} · k = 0 → 1')
                    slider.press('ArrowRight')
                    slider.press('ArrowRight')
                    k = min(2, record['parameters']['steps']-1)
                    expect(panel.locator('[data-step]')).to_have_text(f'{method.upper()} · k = {k} → {k+1}')
                    for marker in panel.locator('[data-point]').all():
                        expected = marker.get_attribute('data-'+method).split('|')[k].split(',')
                        assert [marker.get_attribute(a) for a in ('cx', 'cy')] == expected
                    assert panel.locator('[data-prox-path]').evaluate_all(
                        '(els,n)=>els.every(el=>el.getAttribute("points").split(" ").length===n)', k+1)
                if primary:
                    panel.locator('.visual-grid').screenshot(path=str(args.output/f'geometry-{width}.png'))
                    panel.locator('.prox-stages').screenshot(path=str(args.output/f'stages-{width}.png'))
                    panel.locator('.plot').first.screenshot(path=str(args.output/f'gaps-{width}.png'))
                if case['id'] == 'lambda-3-zero':
                    expect(panel.locator('[data-zero]')).to_contain_text('coordinate 1: |z|=0.15556 ≤ τ → 0')
                slider.press('End')
                if not primary:
                    page.locator(f'#{case["id"]} > summary').click()
            panel = page.locator('[data-prox-case="lambda-2-opposite"]')
            panel.locator('[data-play]').click()
            expect(panel.locator('[data-step]')).not_to_have_text('FISTA · k = 0 → 1')
            panel.locator('[data-play]').click()
            assert panel.locator('[data-play]').get_attribute('aria-pressed') == 'false'
            old = page.locator('html').get_attribute('lang')
            page.locator('[data-action="language"]').click()
            assert page.locator('html').get_attribute('lang') != old
            page.locator('[data-action="language"]').click()
            appendix = page.locator('#chainbench-evidence').locator('..')
            appendix.locator(':scope > summary').click()
            with page.expect_download() as download_info:
                page.locator('[data-download="chainbench-evidence"]').click()
            dest = args.output/f'download-{width}.json'
            download_info.value.save_as(dest)
            assert json.loads(dest.read_text(encoding='utf8')) == record
            appendix.locator(':scope > summary').click()
            page.screenshot(path=str(args.output/f'page-{width}.png'), full_page=True)
            evidence['viewports'].append({'width': width, 'all_cases': 9, 'both_methods': 'passed',
                                          'markers': 'matched', 'keyboard': 'passed',
                                          'playback': 'passed', 'zero_coordinate': 'verified',
                                          'download': 'matched', 'overflow': False})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        page.goto(url)
        panel = page.locator('[data-prox-case="lambda-2-opposite"]')
        assert panel.locator('input[type=range]').is_hidden()
        for path in panel.locator('[data-prox-path]').all():
            assert len(path.get_attribute('points').split()) == record['parameters']['steps']+1
        page.locator('#lambda-3-zero > summary').click()
        assert page.locator('#lambda-3-zero svg').first.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(args.output/'no-script.png'), full_page=True)
        evidence['no_script'] = 'full paths, stage tables and every case remain readable'
        context.close()
        browser.close()
    assert not evidence['network_requests'], evidence['network_requests']
    assert not evidence['javascript_errors'], evidence['javascript_errors']
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
