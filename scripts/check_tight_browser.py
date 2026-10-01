"""Optional offline checks of real tight-GD points and the resolved centre."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    evidence = {'cases': [], 'network_requests': [], 'javascript_errors': []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        evidence['browser'] = browser.version
        for source in args.html:
            url = source.resolve().as_uri()
            for width in (1440, 390):
                context = browser.new_context(viewport={'width': width, 'height': 1000}, offline=True)
                page = context.new_page()
                page.on('pageerror', lambda e: evidence['javascript_errors'].append(str(e)))
                page.on('request', lambda r: evidence['network_requests'].append(r.url)
                        if r.url.startswith(('http:', 'https:')) else None)
                page.goto(url)
                record = json.loads(page.locator('#chainbench-evidence').text_content())
                N = record['config']['horizon']
                slider, marker = page.locator('[data-tight-slider]'), page.locator('[data-tight-point]')
                assert marker.evaluate("""marker=>{
                    const record=JSON.parse(document.getElementById('chainbench-evidence').textContent);
                    const points=marker.dataset.points.split(' '), slider=document.querySelector('[data-tight-slider]');
                    for(let k=0;k<record.rows.length;k++){
                        slider.value=k;slider.dispatchEvent(new Event('input'));
                        if(document.querySelector('[data-tight-step]').textContent!=='k = '+k)return false;
                        if([marker.getAttribute('cx'),marker.getAttribute('cy')].join(',')!==points[k])return false;
                        if(document.querySelector('[data-tight-path]').getAttribute('points')!==points.slice(0,k+1).join(' '))return false;
                        for(const field of ['x','gap','gradient']){
                            const actual=Number(document.querySelector('[data-tight-'+field+']').textContent);
                            const target=record.rows[k][field];
                            if(Math.abs(actual-target)>Math.abs(target)*1e-6)return false;
                        }
                    }return true;
                }""")
                slider.focus()
                slider.press('Home')
                slider.press('ArrowRight')
                expect(page.locator('[data-tight-step]')).to_have_text('k = 1')
                slider.press('End')
                play = page.locator('[data-tight-play]')
                play.click()
                expect(page.locator('[data-tight-step]')).not_to_have_text('k = 0')
                if play.get_attribute('aria-pressed') == 'true':
                    play.click()
                expect(play).to_have_attribute('aria-pressed','false')
                slider.press('End')
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert page.locator('.tight-views svg').evaluate_all("""els=>els.every(svg=>
                    [...svg.querySelectorAll('text')].every(t=>{const b=t.getBBox(),v=svg.viewBox.baseVal;
                    return b.x>=0 && b.y>=0 && b.x+b.width<=v.width && b.y+b.height<=v.height;}))""")
                page.locator('.tight-views').screenshot(path=str(args.output/f'geometry-{N}-{width}.png'))
                page.locator('.tight-proof').screenshot(path=str(args.output/f'proof-{N}-{width}.png'))
                page.screenshot(path=str(args.output/f'page-{N}-{width}.png'),full_page=True)
                old = page.locator('html').get_attribute('lang')
                page.locator('[data-action="language"]').click()
                assert page.locator('html').get_attribute('lang') != old
                appendix = page.locator('#chainbench-evidence').locator('..')
                appendix.locator(':scope > summary').click()
                with page.expect_download() as download_info:
                    page.locator('[data-download="chainbench-evidence"]').click()
                dest = args.output/f'download-{N}-{width}.json'
                download_info.value.save_as(dest)
                assert json.loads(dest.read_text(encoding='utf8')) == record
                evidence['cases'].append({'horizon': N, 'width': width, 'all_points': N+1,
                    'coordinates_readouts_paths': 'matched', 'keyboard_playback': 'passed',
                    'svg_labels': 'inside view boxes', 'overflow': False, 'download': 'matched'})
                context.close()
            context = browser.new_context(java_script_enabled=False, offline=True,
                                          viewport={'width':390, 'height':1000})
            page = context.new_page()
            page.goto(url)
            assert page.locator('[data-tight-slider]').is_hidden()
            assert len(page.locator('[data-tight-path]').get_attribute('points').split()) == N+1
            assert page.locator('.tight-views svg').count() == 2
            table = page.locator('.tight-proof + details')
            table.locator('summary').click()
            assert table.locator('tbody tr').count() == N+1
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(args.output/f'no-script-{N}.png'),full_page=True)
            context.close()
        browser.close()
    evidence['no_script'] = 'full path, centre, proof and every stored row available'
    assert not evidence['network_requests'], evidence['network_requests']
    assert not evidence['javascript_errors'], evidence['javascript_errors']
    (args.output/'browser-verification.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf8')
    print(json.dumps(evidence,indent=2))


if __name__ == '__main__':
    main()
