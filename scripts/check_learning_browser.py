"""Exercise symbolic maps, pair comparison and filtered navigation offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', type=Path, required=True)
    parser.add_argument('--focused', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
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
            page.goto(args.html.resolve().as_uri())
            record = json.loads(page.locator('#chainbench-evidence').text_content())
            topics = list(record['mechanism_maps']['topics'])
            assert len(topics) == 8
            assert page.locator('.method-flow').count() == 8
            left, right = (page.locator(f'[data-compare="{s}"]') for s in ('left', 'right'))
            for slug in topics:
                # Choosing the same method automatically picks a different partner.
                left.select_option(slug)
                right.select_option(slug)
                assert left.input_value() != right.input_value()
                visible = page.locator('[data-mechanism]:visible')
                assert visible.count() == 2
                assert set(visible.evaluate_all('(els)=>els.map(e=>e.dataset.mechanism)')) == {
                    left.input_value(), right.input_value()}
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            # Native selects remain keyboard operable.
            left.focus()
            left.press('Home')
            left.press('ArrowDown')
            expect(left).to_have_value(topics[1])
            left.select_option('hestenes-stiefel-1952')
            right.select_option('rockafellar-1976')
            page.locator('#mechanism-comparison').screenshot(path=str(args.output/f'comparison-{width}.png'))
            page.locator('#beck-teboulle-2009 .method-flow').screenshot(path=str(args.output/f'flow-{width}.png'))
            # A comparison link must unhide its lesson after a filter hides it.
            page.locator('#lesson-filter').fill('no-such-method')
            assert page.locator('[data-search]:visible').count() == 0
            page.locator('[data-mechanism="hestenes-stiefel-1952"] a').click()
            expect(page.locator('#lesson-filter')).to_have_value('')
            expect(page.locator('#hestenes-stiefel-1952')).to_be_visible()
            # Related-method links must also clear filters before their anchor jump.
            page.locator('#lesson-filter').fill('conjugate')
            expect(page.locator('#gd-baseline')).to_be_hidden()
            page.locator('#hestenes-stiefel-1952 [data-lesson-link="gd-baseline"]').click()
            expect(page.locator('#gd-baseline')).to_be_visible()
            expect(page.locator('#lesson-filter')).to_have_value('')
            page.locator('[data-action="language"]').click()
            assert page.locator('html').get_attribute('lang') == 'en'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.locator('[data-action="language"]').click()
            appendix = page.locator('#chainbench-evidence').locator('..')
            appendix.locator(':scope > summary').click()
            with page.expect_download() as download_info:
                page.locator('[data-download="chainbench-evidence"]').click()
            dest = args.output/f'download-{width}.json'
            download_info.value.save_as(dest)
            assert json.loads(dest.read_text(encoding='utf8')) == record
            page.goto(args.focused.resolve().as_uri())
            assert page.locator('[data-compare]').count() == 0
            assert page.locator('.method-flow').count() == 1
            assert page.locator('.related-methods code').count() == 2
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            evidence['viewports'].append({'width': width, 'all_topics': 8,
                'comparison_selection': 'passed', 'keyboard': 'passed', 'filtered_navigation': 'passed',
                'language': 'passed', 'download': 'matched', 'focused': 'passed', 'overflow': False})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        page.goto(args.html.resolve().as_uri())
        assert page.locator('[data-mechanism]:visible').count() == 8
        assert page.locator('.comparison-controls').is_hidden()
        assert page.locator('.method-flow:visible').count() == 8
        assert page.locator('[data-search]:visible').count() == 16
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        evidence['no_script'] = 'all eight comparison cards, flows and lessons readable'
        context.close()
        browser.close()
    assert not evidence['network_requests'], evidence['network_requests']
    assert not evidence['javascript_errors'], evidence['javascript_errors']
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
