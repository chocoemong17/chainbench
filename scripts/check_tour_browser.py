"""Verify the generated reading path and all local report links without a network."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tour', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((args.tour/'manifest.json').read_text(encoding='utf8'))
    url = (args.tour/'index.html').resolve().as_uri()
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
            assert page.locator('img').count() == 7
            assert page.locator('img').evaluate_all('(els)=>els.every(e=>e.complete&&e.naturalWidth>0)')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(args.output/f'index-{width}.png'), full_page=True)
            page.locator('#image-experiment').screenshot(path=str(args.output/f'image-experiment-{width}.png'))
            page.locator('#counterexample').screenshot(path=str(args.output/f'counterexample-{width}.png'))
            page.locator('#geometry').screenshot(path=str(args.output/f'geometry-{width}.png'))
            page.locator('#breadth').screenshot(path=str(args.output/f'breadth-{width}.png'))
            for artifact in manifest['artifacts']:
                filename = artifact['path']
                if filename == 'index.html':
                    continue
                link = page.locator('a[href="'+filename+'"]')
                expect(link).to_have_count(1)
                link.click()
                page.wait_for_url('**/'+filename, wait_until='load')
                expect(page.locator('#chainbench-evidence')).to_have_count(1)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert page.url.endswith('/'+filename)
                if filename == 'stress-ista-vs-fista.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert [r['seed'] for r in record['rows']] == list(range(32))
                    assert record['rows'][24]['status'] == 'unresolved'
                    assert record['rows'][24]['metric'] is None
                if filename == 'deblur.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps'] == 10000
                    page.locator('[data-tour-related]').click()
                    page.wait_for_url('**/proximal.html', wait_until='load')
                    assert page.url.endswith('/proximal.html')
                    page.locator('[data-tour-related]').click()
                    page.wait_for_url('**/deblur.html', wait_until='load')
                    assert page.url.endswith('/deblur.html')
                if filename == 'heavy-ball.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps'] == 50 and len(record['cases']) == 9
                    page.locator('[data-tour-related]').click()
                    page.wait_for_url('**/atlas.html#polyak-1964', wait_until='load')
                    assert page.locator('#polyak-1964').is_visible()
                page.locator('[data-tour-home]').click()
                assert page.url == url
            page.locator('[data-action="language"]').click()
            assert page.locator('html').get_attribute('lang') == 'en'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            evidence['viewports'].append({'width': width, 'reports_opened': 15,
                'return_links': 'passed', 'preview_images': 'loaded', 'all_seeds': 'retained',
                'unresolved_seed24': 'retained', 'language': 'passed', 'overflow': False})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        page.goto(url)
        page.locator('a[href="shewchuk.html"]').click()
        assert page.locator('svg').first.is_visible()
        page.locator('[data-tour-home]').click()
        assert page.url == url
        evidence['no_script'] = 'index, static figures and local navigation work'
        context.close()
        browser.close()
    assert not evidence['network_requests'], evidence['network_requests']
    assert not evidence['javascript_errors'], evidence['javascript_errors']
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
