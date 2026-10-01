"""Inspect every saved step of all nine heavy-ball counterexample cases offline."""

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
    evidence = {'viewports': [], 'network_requests': [], 'javascript_errors': []}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        evidence['browser'] = browser.version
        for width in (1440, 390):
            context = browser.new_context(viewport={'width': width, 'height': 1000}, offline=True)
            page = context.new_page()
            page.on('pageerror', lambda error: evidence['javascript_errors'].append(str(error)))
            page.on('request', lambda r: evidence['network_requests'].append(r.url)
                    if r.url.startswith(('https:', 'http:')) else None)
            page.goto(args.html.resolve().as_uri())
            record = json.loads(page.locator('#chainbench-evidence').text_content())
            assert page.locator('[data-cycle-case]').count() == 9
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            for index, case in enumerate(record['cases']):
                panel = page.locator(f'[data-cycle-case="{case["id"]}"]')
                if index:
                    page.locator(f'#{case["id"]} > summary').click()
                slider = panel.locator('input[type=range]')
                slider.focus()
                slider.press('Home')
                slider.press('ArrowRight')
                expect(panel.locator('[data-cycle-step]')).to_have_text('k = 1')
                panel.evaluate('''(panel,c)=>{
                  const slider=panel.querySelector('input'),steps=c.runs['heavy-ball'].updates;
                  const close=(a,b)=>{if(Math.abs(Number(a)-b)>.00051)throw Error('cycle coordinate mismatch');};
                  const fmt=x=>x===null?'—':Number(x).toExponential(5);
                  for(let k=0;k<=steps;k++){
                    slider.value=String(k);slider.dispatchEvent(new Event('input',{bubbles:true}));
                    for(const svg of panel.querySelectorAll('[data-cycle-view]')){
                      const a=JSON.parse(svg.dataset.axes),view=svg.dataset.cycleView;
                      const project=r=>{const x=view==='history'?r.iteration:view==='phase'?r.previous:r.x;
                        const y=view==='objective'?r.objective:r.x;
                        return [a.left+a.width*(x-a.xmin)/(a.xmax-a.xmin),a.top+a.height-a.height*(y-a.ymin)/(a.ymax-a.ymin)];};
                      for(const name of ['heavy-ball','gd']){
                        const rows=c.runs[name].rows,pos=project(rows[k]);
                        const dot=svg.querySelector('[data-cycle-marker="'+name+'"]');
                        close(dot.getAttribute('cx'),pos[0]);close(dot.getAttribute('cy'),pos[1]);
                        const path=svg.querySelector('[data-cycle-history="'+name+'"]');
                        const points=path.getAttribute('points').split(' ').map(x=>x.split(',').map(Number));
                        const count=view==='history'?rows.length:k+1;
                        if(points.length!==count)throw Error('cycle history count');
                        points.forEach((xy,i)=>{const p=project(rows[i]);close(xy[0],p[0]);close(xy[1],p[1]);});
                      }
                      for(const label of svg.querySelectorAll('text')){
                        const b=label.getBBox(),vb=svg.viewBox.baseVal;
                        if(b.x<0||b.y<0||b.x+b.width>vb.width||b.y+b.height>vb.height)throw Error('cycle text clipped');
                      }
                    }
                    for(const name of ['heavy-ball','gd']){
                      const row=c.runs[name].rows[k],label=panel.querySelector('[data-cycle-readout="'+name+'"]').textContent;
                      for(const [key,prefix]of [['x','x='],['objective','f='],['stationarity','|grad|='],['three_step_difference','|x[k]−x[k−3]|=']])
                        if(!label.includes(prefix+fmt(row[key])))throw Error('cycle readout mismatch');
                    }
                    const label=panel.querySelector('[data-cycle-update]').textContent,row=c.runs['heavy-ball'].rows[k];
                    if(k===steps){if(!label.includes('no next update'))throw Error('invented update');}
                    else if(!label.includes('gradient step '+fmt(row.gradient_step))||!label.includes('momentum '+fmt(row.momentum_step)))throw Error('update terms differ');
                  }
                }''', case)
                for svg, field in zip(panel.locator('.plot svg').all(), ('objective', 'stationarity')):
                    chart = json.loads(svg.locator('metadata').text_content())
                    for actual, run in zip(chart['series'], case['runs'].values()):
                        assert actual['y'] == [r[field] for r in run['rows']]
                        assert actual['x'] == list(range(len(run['rows'])))
                if index == 0:
                    panel.locator('.cycle-geometry').first.screenshot(path=str(args.output/f'geometry-{width}.png'))
                    panel.locator('.cycle-history').screenshot(path=str(args.output/f'history-{width}.png'))
                    panel.locator('.cycle-readout').screenshot(path=str(args.output/f'readout-{width}.png'))
                if index:
                    page.locator(f'#{case["id"]} > summary').click()
            panel = page.locator('[data-cycle-case="published"]')
            panel.locator('[data-cycle-play]').click()
            expect(panel.locator('[data-cycle-step]')).not_to_have_text('k = 0')
            panel.locator('[data-cycle-play]').click()
            assert panel.locator('[data-cycle-play]').get_attribute('aria-pressed') == 'false'
            before = page.locator('html').get_attribute('lang')
            page.locator('[data-action="language"]').click()
            assert page.locator('html').get_attribute('lang') != before
            page.locator('[data-action="language"]').click()
            page.locator('#chainbench-evidence').locator('..').locator('summary').click()
            with page.expect_download() as download:
                page.locator('[data-download="chainbench-evidence"]').click()
            path = args.output/f'download-{width}.json'
            download.value.save_as(path)
            assert json.loads(path.read_text(encoding='utf8')) == record
            page.locator('#chainbench-evidence').locator('..').locator('summary').click()
            page.screenshot(path=str(args.output/f'page-{width}.png'), full_page=True)
            evidence['viewports'].append({'width': width, 'cases': 9,
                'steps_inspected': 9*(record['parameters']['steps']+1),
                'coordinates_and_readouts': 'matched', 'complete_metric_curves': 'matched',
                'keyboard_playback_language_download': 'passed', 'overflow': False})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True, viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        page.goto(args.html.resolve().as_uri())
        assert page.locator('[data-cycle-case="published"] input').is_hidden()
        assert page.locator('[data-cycle-case="published"] svg').count() == 5
        points = page.locator('[data-cycle-case="published"] [data-cycle-history]').first.get_attribute('points')
        assert len(points.split()) == record['parameters']['steps']+1
        page.locator('#grid-1 > summary').click()
        assert page.locator('#grid-1 svg').first.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(args.output/'no-script.png'), full_page=True)
        context.close()
        browser.close()
    assert not evidence['network_requests'] and not evidence['javascript_errors'], evidence
    evidence['no_script'] = 'full paths, curves, tables and all cases remain available'
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
