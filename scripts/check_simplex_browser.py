"""Optional offline browser checks for all twelve Frank–Wolfe geometry cases."""
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
            assert page.locator('[data-fw-case]').count() == 12
            for i, case in enumerate(record['cases']):
                panel = page.locator(f'[data-fw-case="{case["id"]}"]')
                if i:
                    page.locator(f'#{case["id"]} > summary').click()
                slider = panel.locator('input[type=range]')
                slider.focus()
                slider.press('Home')
                expect(panel.locator('[data-step]')).to_have_text('k = 0 → 1')
                assert f'e{case["rows"][0]["vertex_index"]+1}' in panel.locator('[data-oracle]').inner_text()
                if i == 0:
                    panel.locator('.fw-certificate-grid').screenshot(path=str(args.output/f'certificate-{width}.png'))
                slider.press('ArrowRight')
                k = min(1, record['parameters']['steps']-1)
                expect(panel.locator('[data-step]')).to_have_text(f'k = {k} → {k+1}')
                for marker in panel.locator('[data-marker]').all():
                    expected = marker.get_attribute('data-frames').split('|')[k].split(',')
                    assert [marker.get_attribute(a) for a in ('cx', 'cy')] == expected
                assert panel.locator('[data-fw-history]').evaluate_all(
                    '(els, n) => els.every(el => el.getAttribute("points").split(" ").length === n)', k+1)
                if i == 0:
                    panel.locator('.visual-grid').screenshot(path=str(args.output/f'geometry-{width}.png'))
                slider.press('End')
                # Check every displayed certificate directly against the raw scalar values.
                panel.evaluate('''(panel,c) => {
                  const slider=panel.querySelector('input[type=range]');
                  const close=(a,b)=>{if(Math.abs(Number(a)-b)>.00051)throw Error('certificate coordinate mismatch');};
                  const plots=panel.querySelectorAll('[data-fw-certificate]');
                  if(plots.length!==2)throw Error('missing certificate diagrams');
                  for(let k=0;k<c.rows.length-1;k++){
                    slider.value=String(k);slider.dispatchEvent(new Event('input',{bubbles:true}));
                    const row=c.rows[k],cert=row.certificate;
                    for(const svg of plots){
                      const lo=Number(svg.dataset.yMin),hi=Number(svg.dataset.yMax);
                      const y=v=>306-220*(v-lo)/(hi-lo);
                      for(const dot of svg.querySelectorAll('[data-affine-vertex]'))
                        close(dot.getAttribute('cy'),y(cert.affine_vertices[Number(dot.dataset.affineVertex)]));
                      const oracle=svg.querySelector('[data-affine-oracle]');
                      if(oracle){close(oracle.getAttribute('cx'),132+132*row.vertex_index);close(oracle.getAttribute('cy'),y(cert.lower));}
                      for(const dot of svg.querySelectorAll('[data-certificate-end]'))
                        close(dot.getAttribute('cy'),y(cert[dot.dataset.certificateEnd]));
                      const span=svg.querySelector('[data-certificate-span]');
                      if(span){close(span.getAttribute('y1'),y(cert.upper));close(span.getAttribute('y2'),y(cert.lower));}
                    }
                    const label=panel.querySelector('[data-certificate-interval]').textContent;
                    if(!label.includes(cert.lower.toExponential(5)+' ≤ f* ≤ '+cert.upper.toExponential(5))
                       ||!label.includes('width = g_FW = '+row.dual_gap.toExponential(5))||!label.endsWith('k = '+k))
                      throw Error('certificate readout mismatch');
                    const fmt=x=>x.map(v=>Number(v.toPrecision(5))).join(', ');
                    if(!panel.querySelector('[data-certificate-values]').textContent.includes('('+fmt(cert.affine_vertices)+')'))
                      throw Error('affine readout mismatch');
                  }
                  for(const svg of plots)for(const t of svg.querySelectorAll('text')){
                    const b=t.getBBox();if(b.x<0||b.y<0||b.x+b.width>520||b.y+b.height>390)throw Error('certificate text clipped');
                  }
                }''', case)
                if i:
                    page.locator(f'#{case["id"]} > summary').click()
            panel = page.locator('[data-fw-case="interior-e1"]')
            panel.locator('[data-play]').click()
            expect(panel.locator('[data-step]')).not_to_have_text('k = 0 → 1')
            panel.locator('[data-play]').click()
            assert panel.locator('[data-play]').get_attribute('aria-pressed') == 'false'
            previous = page.locator('html').get_attribute('lang')
            page.locator('[data-action="language"]').click()
            assert page.locator('html').get_attribute('lang') != previous
            page.locator('[data-action="language"]').click()
            page.locator('#chainbench-evidence').locator('..').locator('summary').click()
            with page.expect_download() as download_info:
                page.locator('[data-download="chainbench-evidence"]').click()
            dest = args.output/f'download-{width}.json'
            download_info.value.save_as(dest)
            assert json.loads(dest.read_text(encoding='utf8')) == record
            page.locator('#chainbench-evidence').locator('..').locator('summary').click()
            page.screenshot(path=str(args.output/f'page-{width}.png'), full_page=True)
            evidence['viewports'].append({'width': width, 'all_cases': 12, 'overflow': False,
                                          'keyboard': 'passed', 'markers': 'matched',
                                          'certificate_steps': 12*record['parameters']['steps'],
                                          'certificate_coordinates_and_readouts': 'matched',
                                          'playback': 'passed', 'download': 'matched'})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        page.goto(url)
        panel = page.locator('[data-fw-case="interior-e1"]')
        assert panel.locator('svg').count() == 5
        assert panel.locator('[data-certificate-interval]').inner_text().endswith('k = 0')
        assert panel.locator('input[type=range]').is_hidden()
        assert len(panel.locator('[data-fw-history]').first.get_attribute('points').split()) == len(record['cases'][0]['rows'])
        page.locator('#edge-e1 > summary').click()
        assert page.locator('#edge-e1 svg').first.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(args.output/'no-script.png'), full_page=True)
        evidence['no_script'] = 'complete static paths and native details remain readable'
        context.close()
        browser.close()
    assert not evidence['network_requests'], evidence['network_requests']
    assert not evidence['javascript_errors'], evidence['javascript_errors']
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
