"""Validate displayed CG mode coordinates against the exported numerical record."""

import argparse
import json
import math
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

# Trigger the real event listener, then return raw DOM values. Numerical checks
# live in Python; this snapshot does not import or call rendering functions.
SNAPSHOT = """panel=>{
 const slider=panel.querySelector('[data-cg-step]'),frames=[];
 for(let k=0;k<=Number(slider.max);k++){
  slider.value=String(k);slider.dispatchEvent(new Event('input',{bubbles:true}));
  const visible=[...panel.querySelectorAll('[data-cg-frame]')].filter(e=>getComputedStyle(e).display!=='none');
  if(visible.length!==1)throw Error('expected one visible frame');
  const f=visible[0],ref=f.querySelector('[data-cg-reference]');
  frames.push({k:Number(f.dataset.cgFrame),open:f.open,label:panel.querySelector('[data-cg-step-label]').textContent,
   text:f.querySelector('[data-cg-readout]').textContent,reference:ref.getAttribute('points'),
   labelsFit:[...f.querySelectorAll('svg')].every(svg=>{const b=svg.getBoundingClientRect();return [...svg.querySelectorAll('text')].every(t=>{const r=t.getBoundingClientRect();return r.left>=b.left-.5&&r.right<=b.right+.5&&r.top>=b.top-.5&&r.bottom<=b.bottom+.5;});}),
   ratios:[...f.querySelectorAll('[data-cg-ratio]')].map(e=>[Number(e.dataset.cgRatio),e.getAttribute('cx'),e.getAttribute('cy')]),
   bars:[...f.querySelectorAll('[data-cg-mode]')].map(e=>[Number(e.dataset.cgMode),e.getAttribute('x'),e.getAttribute('y'),e.getAttribute('height')])});
 }
 const w=panel.querySelector('[data-cg-witness]');
 return {frames,witness:w.getAttribute('points'),nodes:[...panel.querySelectorAll('[data-cg-witness-node]')].map(e=>[Number(e.dataset.cgWitnessNode),e.getAttribute('cx'),e.getAttribute('cy')])};
}"""


def near(actual, expected):
    value = float(actual)
    if not math.isfinite(value) or not math.isclose(value, expected, rel_tol=0, abs_tol=.00051):
        raise RuntimeError(f'CG spectrum coordinate differs: {actual} != {expected}')


def points(actual, xs, ys, low, high):
    pairs = [pair.split(',') for pair in actual.split()]
    if len(pairs) != len(xs):
        raise RuntimeError('CG spectrum point coverage differs')
    for pair, x, y in zip(pairs,xs,ys):
        if len(pair) != 2:
            raise RuntimeError('invalid coordinate pair')
        near(pair[0],70+85*x)
        near(pair[1],270-200*(y-low)/(high-low))


def validate_snapshot(case, comparisons, snapshot):
    ratios = [v for r in case['rows'] for v in r['component_ratios'] if v is not None]
    low, high = min(-1.,min(ratios))*1.1, max(1.,max(ratios))*1.1
    energy_high = 1.08*max(v for r in case['rows'] for v in r['normalized_mode_energy'])
    if len(snapshot['frames']) != len(case['rows']):
        raise RuntimeError('CG spectrum frame coverage differs')
    for row, frame in zip(case['rows'],snapshot['frames']):
        k = row['iteration']
        if (frame['k'] != k or frame['open'] is not True or frame['labelsFit'] is not True
                or frame['label'] != f'k={k} / {case["completed_updates"]}'):
            raise RuntimeError('CG spectrum selected stage differs')
        text = (f'k={k} · direct ratio={row["energy_ratio"]:.8e} · spectral ratio={row["spectral_energy_ratio"]:.8e}'
                f'direct energy − spectral energy={row["energy_identity_difference"]:.8e} · true residual={row["true_residual_norm"]:.8e}')
        if frame['text'] != text:
            raise RuntimeError('CG spectrum readout differs')
        reference = comparisons[k]
        points(frame['reference'],reference['abscissae'],reference['values'],low,high)
        active = [i for i,v in enumerate(row['component_ratios']) if v is not None]
        if [r[0] for r in frame['ratios']] != active or [b[0] for b in frame['bars']] != list(range(16)):
            raise RuntimeError('CG spectrum missing or duplicate mode')
        for i,x,y in frame['ratios']:
            near(x,70+85*case['declared_eigenvalues'][i])
            near(y,270-200*(row['component_ratios'][i]-low)/(high-low))
        for i,x,y,height in frame['bars']:
            expected = 200*row['normalized_mode_energy'][i]/energy_high
            near(x,76+42*i)
            near(y,270-expected)
            near(height,expected)
    w = case['quadratic_witness']
    low, high = min(-.1,min(w['values'])*1.1), max(w['values'])*1.1
    points(snapshot['witness'],w['abscissae'],w['values'],low,high)
    if [v[0] for v in snapshot['nodes']] != list(range(16)):
        raise RuntimeError('CG witness missing or duplicate mode')
    for i,x,y in snapshot['nodes']:
        near(x,70+85*case['declared_eigenvalues'][i])
        near(y,270-200*(w['at_eigenvalues'][i]-low)/(high-low))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    evidence = dict(viewports=[],javascript_errors=[],network_requests=[])
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        evidence['browser'] = browser.version
        for width in (1440,390):
            context = browser.new_context(viewport=dict(width=width,height=1000),offline=True)
            p = context.new_page()
            p.on('pageerror',lambda e:evidence['javascript_errors'].append(str(e)))
            p.on('request',lambda r:evidence['network_requests'].append(r.url) if r.url.startswith(('http:','https:')) else None)
            p.goto(args.html.resolve().as_uri())
            data = json.loads(p.locator('#chainbench-evidence').text_content())
            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert p.locator('[data-cg-case]').count()==18
            assert p.locator('[data-cg-overview]').count()==6
            stages = 0
            for case in data['cases']:
                p.locator('[data-cg-case-select]').select_option(case['id'])
                panel = p.locator(f'[data-cg-case="{case["id"]}"]')
                expect(panel).to_be_visible()
                assert p.locator('[data-cg-case]:visible').count()==1
                validate_snapshot(case,data['comparisons'],panel.evaluate(SNAPSHOT))
                stages += len(case['rows'])
                panel.locator('[data-cg-first]').click()
                slider = panel.locator('[data-cg-step]')
                slider.focus()
                slider.press('ArrowRight')
                expect(panel.locator('[data-cg-frame="1"]')).to_be_visible()
                slider.press('End')
                expect(panel.locator(f'[data-cg-frame="{case["completed_updates"]}"]')).to_be_visible()
                panel.locator('[data-cg-last]').click()
                assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            first = p.locator('[data-cg-overview]').first
            first.locator('summary').click()
            chart = json.loads(first.locator('metadata').text_content())
            assert len(chart['series'])==4 and chart['y_label']=='relative A-norm error'
            for overview in p.locator('[data-cg-overview]').all():
                metadata = json.loads(overview.locator('metadata').text_content())
                basis,profile = metadata['title'].split(' · ')
                for series in metadata['series'][:3]:
                    case = next(c for c in data['cases'] if c['spectrum']==series['label'] and c['basis_name']==basis and c['start_profile']==profile)
                    assert series['x']==[r['iteration'] for r in case['rows']]
                    assert series['y']==[r['energy_ratio'] for r in case['rows']]
            p.locator('[data-cg-case-select]').select_option('two-clusters-hadamard-equal-energy')
            panel = p.locator('[data-cg-case="two-clusters-hadamard-equal-energy"]')
            slider = panel.locator('[data-cg-step]')
            slider.fill('1')
            panel.scroll_into_view_if_needed()
            p.screenshot(path=str(args.output/f'modes-{width}.png'),full_page=False)
            if width==390:
                scroll = panel.locator('[data-cg-frame="1"] .cg-figure').first
                scroll.focus()
                scroll.press('ArrowRight')
                p.wait_for_timeout(200)
                assert scroll.evaluate('e=>e.scrollLeft>0')
            p.locator('[data-action="language"]').click()
            assert p.locator('html').get_attribute('lang')=='en'
            download = p.locator('[data-download="chainbench-evidence"]')
            download.evaluate('e=>e.closest("details").open=true')
            with p.expect_download() as event:
                download.click()
            target = args.output/f'download-{width}.json'
            event.value.save_as(target)
            assert json.loads(target.read_text())==data
            evidence['viewports'].append(dict(width=width,cases=18,stages=stages))
            context.close()
        context = browser.new_context(viewport=dict(width=390,height=900),java_script_enabled=False,offline=True)
        p = context.new_page()
        p.goto(args.html.resolve().as_uri())
        assert p.locator('[data-cg-case]:visible').count()==18
        assert p.locator('[data-cg-frame]').count()==sum(len(c['rows']) for c in data['cases'])
        assert p.locator('.cg-controls:visible').count()==0
        frame = p.locator('[data-cg-case]').last.locator('[data-cg-frame]').last
        frame.locator('summary').first.click()
        expect(frame.locator('svg').first).to_be_visible()
        assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
        context.close()
        browser.close()
    assert not evidence['javascript_errors'] and not evidence['network_requests'],evidence
    (args.output/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))


if __name__=='__main__':
    main()
