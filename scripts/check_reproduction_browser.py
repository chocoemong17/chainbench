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
            numeric = json.loads(page.locator('#chainbench-evidence').text_content())
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
            inspected = 0
            for i, case in enumerate(numeric['cases']):
                if i:
                    page.locator(f'#{case["id"]} > summary').click()
                details = page.locator(f'[data-repro-case="{case["id"]}"]')
                control = details.locator('input[type=range]')
                control.focus()
                control.press('Home')
                assert details.locator('[data-step]').inner_text() == 'k = 0'
                control.press('End')
                inspected += details.evaluate('''(panel,c)=>{
                  const slider=panel.querySelector('input[type=range]');
                  const close=(a,b)=>{if(Math.abs(Number(a)-b)>.00051)throw Error('metric coordinate mismatch');};
                  const s=Math.sqrt(14),den=Math.sqrt(9+2*s);
                  const transform=v=>[((3+s)*v[0]+2*v[1])/den,(2*v[0]+(6+s)*v[1])/den];
                  for(let k=0;k<=Number(slider.max);k++){
                    slider.value=String(k);slider.dispatchEvent(new Event('input',{bubbles:true}));
                    for(const method of ['sd','cg']){
                      const run=c.runs[method],index=Math.min(k,run.updates),row=run.rows[index];
                      const points=run.rows.slice(0,index+1).map(r=>{
                        const z=transform([r.x[0]-2,r.x[1]+2]);return [280+15*z[0],256-15*z[1]];});
                      const svg=panel.querySelector('[data-metric-view="path"]');
                      const line=svg.querySelector('polyline[data-method="'+method+'"]');
                      const actual=line.getAttribute('points').split(' ').map(p=>p.split(',').map(Number));
                      if(actual.length!==points.length)throw Error('invented metric iterate');
                      actual.forEach((xy,j)=>{close(xy[0],points[j][0]);close(xy[1],points[j][1]);});
                      const marker=svg.querySelector('circle[data-method="'+method+'"]');
                      close(marker.getAttribute('cx'),points[index][0]);close(marker.getAttribute('cy'),points[index][1]);
                      const pair=row.step_pair;
                      for(const metric of ['euclidean','a']){
                        const value=pair?pair['cos_'+metric]:null;
                        const label=panel.querySelector('[data-cosine="'+method+'-'+metric+'"]');
                        if(label.textContent!==(value===null?'pair unavailable':'cos = '+value.toExponential(3)))throw Error('cosine readout mismatch');
                        for(const name of ['previous','current']){
                          let vector=[0,0];
                          if(index>=2){const end=index-(name==='previous'?1:0);
                            vector=run.rows[end].x.map((v,j)=>v-run.rows[end-1].x[j]);
                            if(metric==='a')vector=transform(vector);}
                          const norm=Math.hypot(...vector);
                          panel.querySelectorAll('[data-direction="'+method+'-'+metric+'-'+name+'"]').forEach(el=>{
                            const [cx,cy]=el.dataset.origin.split(',').map(Number);
                            const x=norm?cx+68*vector[0]/norm:cx,y=norm?cy-68*vector[1]/norm:cy;
                            const line=el.tagName.toLowerCase()==='line';
                            close(el.getAttribute(line?'x2':'cx'),x);close(el.getAttribute(line?'y2':'cy'),y);
                            if(!line && el.getAttribute('visibility')!==(norm?'visible':'hidden'))throw Error('undefined vector visible');
                          });
                        }
                      }
                      const held=panel.querySelector('[data-readout="'+method+'"]').textContent;
                      if(held.includes('last computed')!==(k>run.updates))throw Error('termination label mismatch');
                    }
                  }
                  for(const svg of panel.querySelectorAll('[data-metric-view]')){
                    for(const label of svg.querySelectorAll('text')){
                      const b=label.getBBox(),v=svg.viewBox.baseVal;
                      if(b.x<0||b.y<0||b.x+b.width>v.width||b.y+b.height>v.height)throw Error('metric text clipped');
                    }
                  }
                  return Number(slider.max)+1;
                }''', case)
                if i:
                    page.locator(f'#{case["id"]} > summary').click()
            slider.fill('2')
            slider.dispatch_event('input')
            panel.locator('.metric-details').screenshot(path=str(args.output / f'metric-{width}.png'))
            slider.press('End')
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
                                          'all_variations': 9, 'metric_states': inspected})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        page.goto(url)
        assert page.locator('[data-repro-case="paper"] svg').count() == 5
        assert page.locator('[data-repro-case="paper"] [data-metric-view]').count() == 2
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
