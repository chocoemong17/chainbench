"""Test the hosted reading route, real dragging, mathematics and browser calculations."""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import threading
from pathlib import Path

import numpy as np
from playwright.sync_api import expect, sync_playwright


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--browser', choices=('chromium', 'webkit'), default='chromium')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
        functools.partial(QuietHandler, directory=str(args.site.resolve())))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    record = json.loads((args.site / 'explorer-data.json').read_text(encoding='utf8'))
    proof = {'source': record['source'], 'engine': args.browser, 'views': [], 'errors': [], 'external_requests': []}
    try:
        with sync_playwright() as pw:
            browser = getattr(pw, args.browser).launch()
            for width in (1440, 390):
                context = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
                page = context.new_page()
                page.on('pageerror', lambda error: proof['errors'].append(str(error)))
                page.on('request', lambda request: proof['external_requests'].append(request.url)
                        if request.url.startswith(('http:', 'https:')) and not request.url.startswith(origin + '/') else None)
                page.goto(origin + '/', wait_until='networkidle')
                expect(page.locator('#play')).to_be_enabled()
                expect(page.locator('html')).to_have_attribute('lang', 'en')
                # No auto-play, including reduced-motion readers.
                page.wait_for_timeout(650)
                assert page.evaluate('window.chainbenchExplorer.k') == 0
                if not page.evaluate('document.documentElement.scrollWidth <= innerWidth'):
                    page.screenshot(path=str(args.output / f'overflow-{width}.png'), full_page=True)
                    offending = page.evaluate('''()=>[...document.querySelectorAll('body *')].filter(e=>{
                      const r=e.getBoundingClientRect();return r.width&&r.right>innerWidth+.5;
                    }).map(e=>({tag:e.tagName,id:e.id,class:e.className?.baseVal??e.className,
                               right:e.getBoundingClientRect().right})).slice(0,25)''')
                    raise AssertionError(('horizontal overflow', width, offending))
                assert page.locator('img').evaluate_all('(imgs)=>imgs.every(i=>i.complete&&i.naturalWidth>0)')
                for index, reference in enumerate(record['cases']):
                    page.select_option('#case', str(index))
                    actual = page.evaluate('window.chainbenchExplorer.traces')
                    for method in ('gd', 'smooth-fista'):
                        np.testing.assert_allclose(actual[method]['points'], reference['traces'][method], rtol=2e-10, atol=2e-12)
                        np.testing.assert_allclose(actual[method]['gaps'], reference['gaps'][method], rtol=2e-9, atol=2e-13)
                    # Use the actual pointer path, not just assigning the range's value.
                    slider = page.locator('#iteration')
                    slider.scroll_into_view_if_needed()
                    bounds = slider.bounding_box()
                    y = bounds['y'] + bounds['height'] / 2
                    page.mouse.move(bounds['x'] + 8, y)
                    page.mouse.down()
                    page.mouse.move(bounds['x'] + bounds['width'] * .7, y, steps=15)
                    page.mouse.up()
                    k = page.evaluate('window.chainbenchExplorer.k')
                    assert 30 < k < 55, ('drag', width, k)
                    expect(page.locator('#iteration-label')).to_have_text(f'{k} / 60')
                    assert page.locator('#gd-gap').text_content() == f"{reference['gaps']['gd'][k]:.3e}".replace('e-0', 'e-').replace('e+0', 'e+')
                    slider.focus()
                    slider.press('Home')
                    slider.press('ArrowRight')
                    assert page.evaluate('window.chainbenchExplorer.k') == 1
                page.locator('#play').click()
                page.wait_for_timeout(1150)
                assert page.evaluate('window.chainbenchExplorer.k') >= 3
                page.locator('#play').click()
                paused = page.evaluate('window.chainbenchExplorer.k')
                page.wait_for_timeout(650)
                assert page.evaluate('window.chainbenchExplorer.k') == paused
                expect(page.locator('#play')).to_have_attribute('aria-pressed', 'false')
                page.locator('#reset').click()
                assert page.evaluate('window.chainbenchExplorer.k') == 0
                page.select_option('#case', '1')
                page.locator('#iteration').fill('18')
                # Verify that a fraction is laid out vertically, not rendered as raw TeX.
                assert page.locator('mfrac').evaluate('''el=>{
                    const a=el.children[0].getBoundingClientRect(),b=el.children[1].getBoundingClientRect();
                    return a.width>0&&b.width>0&&a.bottom<=b.top+2;
                }''')
                page.screenshot(path=str(args.output / f'home-en-{width}.png'), full_page=True)
                page.locator('#explore').screenshot(path=str(args.output / f'explorer-{width}.png'))
                page.locator('#language').click()
                expect(page.locator('html')).to_have_attribute('lang', 'ko')
                expect(page.locator('#narration')).to_contain_text('Smooth FISTA')
                page.screenshot(path=str(args.output / f'home-ko-{width}.png'), full_page=True)
                page.locator('a.lesson[href="reports/deblur.html"]').click()
                expect(page.locator('html')).to_have_attribute('lang', 'ko')
                slider = page.locator('[data-deblur-slider]')
                slider.focus()
                slider.press('Home')
                slider.press('ArrowRight')
                expect(page.locator('[data-deblur-label]')).to_have_text('k = 1')
                page.locator('[data-deblur-play]').click()
                page.wait_for_timeout(1050)
                expect(page.locator('[data-deblur-label]')).to_have_text('k = 10')
                page.locator('[data-deblur-play]').click()
                page.locator('[data-action="language"]').click()
                expect(page.locator('html')).to_have_attribute('lang', 'en')
                page.locator('.deblur-outputs').screenshot(path=str(args.output / f'deblur-{width}.png'))
                page.goto(origin + '/reports/atlas.html')
                expect(page.locator('html')).to_have_attribute('lang', 'en')
                assert page.locator('math').count() >= 7
                assert page.locator('.formula sub').count() > 0
                assert page.locator('math').evaluate_all('(els)=>els.every(e=>e.getBoundingClientRect().width>0)')
                page.locator('#gd-baseline .formula').last.screenshot(path=str(args.output / f'math-{width}.png'))
                # All 25 reports default to English with fresh storage; no rewritten evidence.
                context.clear_cookies()
                page.evaluate('localStorage.clear()')
                for path in sorted((args.site / 'reports').glob('*.html')):
                    response = page.goto(origin + '/reports/' + path.name)
                    assert response.status == 200
                    expect(page.locator('html')).to_have_attribute('lang', 'en')
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), path.name
                proof['views'].append({'width': width, 'cases': 3, 'numeric_rows_per_method': 61,
                    'reports': 25, 'drag_keyboard_play_pause': 'passed', 'language_navigation': 'passed',
                    'native_fraction_and_scripts': 'passed', 'overflow': False})
                context.close()
            # The failure path must explain what happened, without a false working UI.
            context = browser.new_context()
            page = context.new_page()
            page.route('**/explorer-data.json', lambda route: route.abort())
            page.goto(origin + '/')
            expect(page.locator('#load-status')).to_have_attribute('role', 'alert')
            expect(page.locator('#play')).to_be_disabled()
            context.close()
            context = browser.new_context(java_script_enabled=False)
            page = context.new_page()
            page.goto(origin + '/')
            expect(page.locator('.no-script')).to_be_visible()
            assert page.locator('mfrac').is_visible()
            context.close()
            browser.close()
        assert not proof['errors'], proof['errors']
        assert not proof['external_requests'], proof['external_requests']
        (args.output / 'verification.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf8')
        print(json.dumps(proof, indent=2))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    main()
