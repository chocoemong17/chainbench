"""Optional Playwright check of a generated report; saves real browser screenshots.

Usage: python scripts/check_reproduction_browser.py --html paper.html --output browser-check
Playwright is a development tool, not a ChainBench runtime dependency.
"""
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
            page.on('pageerror', lambda error: evidence['javascript_errors'].append(str(error)))
            page.on('request', lambda request: evidence['network_requests'].append(request.url)
                    if request.url.startswith(('https:', 'http:')) else None)
            page.goto(url)
            page.wait_for_selector('[data-repro-case="paper"]')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'page overflows'
            panel = page.locator('[data-repro-case="paper"]')
            slider = panel.locator('input[type=range]')
            slider.focus()
            slider.press('Home')
            assert panel.locator('[data-step]').inner_text() == 'k = 0'
            slider.press('ArrowRight')
            assert panel.locator('[data-step]').inner_text() == 'k = 1'
            assert '0.080000' in panel.locator('[data-readout="cg"]').inner_text()
            # Both projections must show exactly the first two computed points.
            assert panel.locator('polyline[data-points]').evaluate_all(
                "els => els.every(el => el.getAttribute('points').split(' ').length === 2)")
            slider.press('End')
            assert 'k=2' in panel.locator('[data-readout="cg"]').inner_text()
            assert 'last computed' in panel.locator('[data-readout="cg"]').inner_text()
            panel.locator('[data-play]').click()
            expect(panel.locator('[data-step]')).not_to_have_text('k = 0')
            panel.locator('[data-play]').click()
            slider.focus()
            slider.press('End')
            old_lang = page.locator('html').get_attribute('lang')
            page.locator('[data-action="language"]').click()
            assert page.locator('html').get_attribute('lang') != old_lang
            page.locator('[data-action="language"]').click()
            # Open every declared variation; controls must remain independently scoped.
            for i in range(1, 10):
                details = page.locator(f'#start-{i}')
                details.locator('summary').first.click()
                control = details.locator('input[type=range]')
                control.focus()
                control.press('Home')
                assert details.locator('[data-step]').inner_text() == 'k = 0'
                control.press('End')
                details.locator('summary').first.click()
            record = page.locator('#chainbench-evidence').text_content()
            page.locator('#chainbench-evidence').locator('..').locator('summary').click()
            with page.expect_download() as download_info:
                page.locator('[data-download="chainbench-evidence"]').click()
            download = download_info.value
            dest = args.output / f'download-{width}.json'
            download.save_as(dest)
            assert json.loads(dest.read_text(encoding='utf8')) == json.loads(record)
            page.locator('#chainbench-evidence').locator('..').locator('summary').click()
            page.screenshot(path=str(args.output / f'desktop-{width}.png'), full_page=True)
            page.locator('#paths').screenshot(path=str(args.output / f'paths-{width}.png'))
            evidence['viewports'].append({'width': width, 'overflow': False, 'keyboard': 'passed',
                                          'playback': 'passed', 'download': 'matched',
                                          'all_variations': 9})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        page.goto(url)
        assert page.locator('[data-repro-case="paper"] svg').count() == 3
        page.locator('#start-1 > summary').click()
        assert page.locator('#start-1 svg').first.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(args.output / 'no-script.png'), full_page=True)
        evidence['no_script'] = 'readable with native details and complete static paths'
        context.close()
        browser.close()
    assert not evidence['network_requests'], evidence['network_requests']
    assert not evidence['javascript_errors'], evidence['javascript_errors']
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
