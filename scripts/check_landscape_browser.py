"""Offline verification of settings, actual projections and early-stop readouts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from smoke_workflows import validate_landscape


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html', type=Path, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    evidence = {'cases': [], 'network_requests': [], 'javascript_errors': []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        evidence['browser'] = browser.version
        for html in args.html:
            for width in (1440, 390):
                ctx = browser.new_context(viewport={'width': width, 'height': 1000}, offline=True)
                page = ctx.new_page()
                page.on('pageerror', lambda e: evidence['javascript_errors'].append(str(e)))
                page.on('request', lambda r: evidence['network_requests'].append(r.url)
                        if r.url.startswith(('http:', 'https:')) else None)
                page.goto(html.resolve().as_uri())
                record = json.loads(page.locator('#chainbench-evidence').text_content())
                validate_landscape(record)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert page.locator('[data-landscape-readout]').count() == len(record['methods'])
                slider = page.locator('[data-trajectory-slider]')
                slider.focus()
                slider.press('Home')
                slider.press('ArrowRight')
                expect(page.locator('[data-trajectory-label]')).to_have_text('k = 1')
                count = page.evaluate('''r=>{
                  const close=(a,b)=>{if(Math.abs(Number(a)-b)>.0051)throw Error('landscape coordinate mismatch');};
                  const colors={'gd':'#2563eb','smooth-fista':'#7c3aed','heavy-ball':'#dc2626','cg':'#059669','proximal-point':'#d97706'};
                  const slider=document.querySelector('[data-trajectory-slider]');
                  for(let k=0;k<=Number(slider.max);k++){
                    slider.value=String(k);slider.dispatchEvent(new Event('input',{bubbles:true}));
                    for(const svg of document.querySelectorAll('[data-landscape-view]')){
                      const a=JSON.parse(svg.dataset.projection),view=svg.dataset.landscapeView;
                      if(view==='contour')close((a.xmax-a.xmin)/a.width,(a.ymax-a.ymin)/a.height);
                      const project=(xy,z)=>{
                        if(view==='contour')return [a.left+(xy[0]-a.xmin)/a.units_per_pixel,a.top+(a.ymax-xy[1])/a.units_per_pixel];
                        const xn=2*(xy[0]-a.xmin)/(a.xmax-a.xmin)-1,yn=2*(xy[1]-a.ymin)/(a.ymax-a.ymin)-1;
                        return [a.cx+a.scale*(xn-yn),a.cy+a.scale*(.48*(xn+yn)-1.55*z/a.zmax)];};
                      for(const line of svg.querySelectorAll('[data-trajectory-line]')){
                        const m=line.dataset.method,index=Math.min(k,r.runs[m].updates);
                        if(line.getAttribute('stroke')!==colors[m])throw Error('method color changed');
                        const points=line.getAttribute('points').split(' ').map(s=>s.split(',').map(Number));
                        if(points.length!==index+1)throw Error('invented or dropped iterate');
                        points.forEach((xy,j)=>{const expected=project(r.traces[m][j],r.gaps[m][j]);close(xy[0],expected[0]);close(xy[1],expected[1]);});
                        const dot=svg.querySelector('[data-trajectory-marker][data-method="'+m+'"]');
                        const pos=project(r.traces[m][index],r.gaps[m][index]);
                        close(dot.getAttribute('cx'),pos[0]);close(dot.getAttribute('cy'),pos[1]);
                      }
                      for(const label of svg.querySelectorAll('text')){
                        const b=label.getBBox(),v=svg.viewBox.baseVal;
                        if(b.x<0||b.y<0||b.x+b.width>v.width||b.y+b.height>v.height)throw Error('landscape label clipped: '+label.textContent);
                      }
                    }
                    for(const m of r.methods){
                      const run=r.runs[m],j=Math.min(k,run.updates),held=k>run.updates?' (last computed / 마지막 계산점)':'';
                      const expected=m+' · k='+j+held+' · x=('+r.traces[m][j].map(v=>v.toPrecision(6)).join(', ')+')'
                        +' · f−f*='+r.gaps[m][j].toExponential(5)+' · ||r||₂='+run.residual_norms[j].toExponential(5);
                      if(document.querySelector('[data-landscape-readout="'+m+'"]').textContent!==expected)throw Error('landscape readout mismatch');
                    }
                  }
                  const chart=document.querySelectorAll('svg')[document.querySelectorAll('svg').length-1];
                  const meta=JSON.parse(chart.querySelector('metadata').textContent);
                  meta.series.forEach((s,i)=>{if(s.label!==r.methods[i]||JSON.stringify(s.y)!==JSON.stringify(r.gaps[r.methods[i]]))throw Error('curve samples differ');});
                  const lines=Array.from(chart.querySelectorAll('polyline'));
                  meta.series.forEach(s=>{if(!lines.some(l=>l.getAttribute('stroke')===colors[s.label]))throw Error('curve color missing');});
                  return Number(slider.max)+1;
                }''', record)
                slider.press('Home')
                play = page.locator('[data-trajectory-play]')
                play.click()
                expect(page.locator('[data-trajectory-label]')).not_to_have_text('k = 0')
                play.click()
                expect(play).to_have_attribute('aria-pressed', 'false')
                slider.focus()
                slider.press('End')
                lang = page.locator('html').get_attribute('lang')
                page.locator('[data-action="language"]').click()
                assert page.locator('html').get_attribute('lang') != lang
                page.locator('[data-action="language"]').click()
                details = page.locator('#chainbench-evidence').locator('..')
                details.locator('summary').click()
                with page.expect_download() as pending:
                    page.locator('[data-download="chainbench-evidence"]').click()
                destination = args.output/f'{html.stem}-{width}.json'
                pending.value.save_as(destination)
                assert json.loads(destination.read_text(encoding='utf8')) == record
                details.locator('summary').click()
                for selector, name in [('.landscape-context', 'context'), ('.visual-grid', 'geometry'),
                                       ('.landscape-readouts', 'readout')]:
                    page.locator(selector).screenshot(path=str(args.output/f'{html.stem}-{name}-{width}.png'))
                page.screenshot(path=str(args.output/f'{html.stem}-page-{width}.png'), full_page=True)
                evidence['cases'].append({'file': html.name, 'width': width, 'states': count,
                                          'methods': record['methods'], 'offline': 'passed'})
                ctx.close()
        ctx = browser.new_context(java_script_enabled=False, offline=True,
                                  viewport={'width': 390, 'height': 1000})
        page = ctx.new_page()
        page.goto(args.html[0].resolve().as_uri())
        assert not page.locator('.landscape-controls').is_visible()
        page.locator('.landscape-values summary').first.click()
        assert page.locator('.landscape-values table').first.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(args.output/'no-script.png'), full_page=True)
        ctx.close()
        browser.close()
    assert not evidence['network_requests'], evidence['network_requests']
    assert not evidence['javascript_errors'], evidence['javascript_errors']
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
