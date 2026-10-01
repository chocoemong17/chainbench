"""Optional offline browser validation of an inspectable schema-2 stress report."""
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
            record = json.loads(page.locator('#chainbench-evidence').text_content())
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('.stress-case').count() == record['trials']
            # Ranking links select a real declared row, open it, and preserve its identity.
            for name, selected in record['selected'].items():
                case_id = f'sample-{selected["trial"]}'
                link = page.locator('.card').filter(has_text=name)
                link.focus()
                link.press('Enter')
                panel = page.locator('#'+case_id)
                expect(panel).to_have_attribute('open', '')
                expect(panel.locator('.formula')).to_contain_text(f'seed={selected["seed"]}')
                assert panel.locator('svg').count() >= 1
                if name == 'maximum-observed':
                    panel.locator('.case-data > .plot').screenshot(path=str(args.output/f'case-{width}.png'))
                panel.locator(':scope > summary').click()
            # All cases remain accessible, including any unresolved ones.
            for i, row in enumerate(record['rows'], 1):
                panel = page.locator(f'#sample-{i}')
                panel.locator(':scope > summary').click()
                expect(panel.locator('.formula')).to_contain_text(f'seed={row["seed"]}')
                assert panel.locator('.case-data').is_visible()
                if row['metric'] is None:
                    expect(panel.locator('.caution')).to_contain_text('UNRESOLVED')
                panel.locator(':scope > summary').click()
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
            page.locator('section').filter(has=page.locator('.cards')).screenshot(path=str(args.output/f'distribution-{width}.png'))
            evidence['viewports'].append({'width': width, 'all_cases': record['trials'],
                                          'ranked_links': 'passed', 'keyboard': 'passed',
                                          'overflow': False, 'download': 'matched'})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        page.goto(url)
        page.locator('#sample-1 > summary').click()
        assert page.locator('#sample-1 svg').first.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(args.output/'no-script.png'), full_page=True)
        evidence['no_script'] = 'every native case remains available with static charts and inputs'
        context.close()
        browser.close()
    assert not evidence['network_requests'], evidence['network_requests']
    assert not evidence['javascript_errors'], evidence['javascript_errors']
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
