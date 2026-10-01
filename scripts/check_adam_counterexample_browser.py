"""Audit actual offline controls and DOM geometry, independently of view code."""
import argparse
import json
import math
import re
from pathlib import Path

from adam_cycle_browser import CYCLE_SNAPSHOT, validate_cycle
from smoke_adam_counterexample import validate_adam_counterexample

SNAPSHOT = """rounds=>{
 const slider=document.querySelector('[data-adam-round]');
 const cycleSnapshot=CYCLE_SNAPSHOT_PLACEHOLDER,hasCycles=!!document.querySelector('#cycle-inspector');let previousBlock=-1;
 return rounds.map(t=>{
  slider.value=String(t);slider.dispatchEvent(new Event('input',{bubbles:true}));
  const block=Math.floor((t-1)/3),cycle=hasCycles&&block!==previousBlock?cycleSnapshot():null;previousBlock=block;
  return {t,label:document.querySelector('[data-adam-label]').textContent,
   cycle,cycleLabel:document.querySelector('[data-cycle-label]')?.textContent??null,
   highlights:[...document.querySelectorAll('#cycle-inspector [data-cycle-highlight]')].map(n=>n.getAttribute('opacity')),
   methods:[...document.querySelectorAll('[data-adam-method]')].map(p=>({method:p.dataset.adamMethod,
    values:[...p.querySelectorAll('[data-adam-value]')].map(n=>[n.dataset.adamValue,n.textContent,n.dataset.raw]),
    markers:[...p.querySelectorAll('[data-adam-marker]')].map(n=>[n.dataset.adamMarker,n.getAttribute('cx'),n.getAttribute('cy')]),
    bars:[...p.querySelectorAll('[data-adam-memory]')].map(n=>[n.dataset.adamMemory,n.getAttribute('width')]),
    projection:p.querySelector('[data-adam-projection]').getAttribute('d')}))};
 });
}""".replace('CYCLE_SNAPSHOT_PLACEHOLDER',CYCLE_SNAPSHOT)


def near(actual, expected, tolerance):
    value = float(actual)
    if not math.isfinite(value) or not math.isclose(value,expected,rel_tol=0,abs_tol=tolerance):
        raise RuntimeError(f'Adam displayed coordinate differs: {actual} != {expected}')


def validate_snapshot(case, frames, rounds, *, require_cycles=True):
    if [f['t'] for f in frames]!=rounds:
        raise RuntimeError('Adam selected-round coverage differs')
    previous_block = -1
    for f in frames:
        t, j = f['t'], f['t']-1
        start = 3*(j//3)
        stop = min(start+3,case['inputs']['steps'])
        if require_cycles:
            if f['cycleLabel']!=f'{case["id"]} · t={start+1}…{stop} · {stop-start}/3':
                raise RuntimeError('Adam cycle label differs')
            if list(map(float,f['highlights']))!=[.55 if i==j%3 else 0 for i in range(3)]*2:
                raise RuntimeError('Adam cycle selected-round highlight differs')
            if (f['cycle'] is not None)!=(j//3!=previous_block):
                raise RuntimeError('Adam cycle snapshot coverage differs')
        previous_block = j//3
        if f['cycle'] is not None:
            validate_cycle(case,t,f['cycle'])
        if f['label']!=f't={t} / {case["inputs"]["steps"]}' or [m['method'] for m in f['methods']]!=['adam','amsgrad']:
            raise RuntimeError('Adam displayed round or method differs')
        for m in f['methods']:
            s = case['runs'][m['method']]['series']
            expected = {
                'round':t,'gradient':case['gradients'][j],'before':s['x'][j],'loss':s['loss'][j],
                'v_before':s['second_moment'][j-1] if j else 0.,'v':s['second_moment'][j],
                'memory':s['denominator_memory'][j],'alpha_t':case['step_sizes'][j],
                'effective_rate':s['effective_rate'][j],'inverse_change':s['inverse_rate_difference'][j],
                'proposal':s['proposal'][j],'after':s['x'][j+1],'projection':s['projection_correction'][j],
                'regret_increment':s['regret_increment'][j],'average_regret':s['average_regret'][j],
            }
            if [v[0] for v in m['values']]!=list(expected):
                raise RuntimeError('Adam missing, duplicate or reordered readout')
            for key,text,raw in m['values']:
                value = expected[key]
                if value is None:
                    if raw!='null' or text!='undefined / 미정의':
                        raise RuntimeError('Adam invented initial inverse-rate change')
                else:
                    if float(raw)!=value or not math.isfinite(float(text)) or not math.isclose(float(text),value,rel_tol=5.1e-9,abs_tol=0):
                        raise RuntimeError('Adam raw or formatted readout differs')
            if [v[0] for v in m['markers']]!=['before','proposal','after'] or [v[0] for v in m['bars']]!=['v','memory']:
                raise RuntimeError('Adam missing geometric marker')
            for (key,x,y),target_y in zip(m['markers'],(65,75,85)):
                near(x,70+165*(expected[key]+2),.00000051)
                near(y,target_y,0)
            for key,width in m['bars']:
                near(width,540*expected[key]/case['inputs']['C']**2,.00000051)
            match = re.fullmatch(r'M([-\d.]+) 95 H([-\d.]+)',m['projection'])
            if match is None:
                raise RuntimeError('Adam invalid projection segment')
            near(match[1],70+165*(expected['proposal']+2),.00000051)
            near(match[2],70+165*(expected['after']+2),.00000051)


def validate_chart(case, metric, snapshot):
    values = [v for r in case['runs'].values() for v in r['series'][metric]]
    lo,hi = (-1.1,1.1) if metric=='x' else (min(0.,min(values)),1.05*max(max(values),case['source_reference']['average_regret_lower']))
    if snapshot['low']!=lo or snapshot['high']!=hi or [p[0] for p in snapshot['paths']]!=['adam','amsgrad']:
        raise RuntimeError('Adam chart scale or method coverage differs')
    steps = case['inputs']['steps']
    for method,text in snapshot['paths']:
        pairs = [p.split(',') for p in text.split()]
        ys = case['runs'][method]['series'][metric]
        if len(pairs)!=len(ys):
            raise RuntimeError('Adam chart omitted a computed round')
        for j,(pair,y) in enumerate(zip(pairs,ys)):
            if len(pair)!=2:
                raise RuntimeError('Adam malformed chart coordinate')
            near(pair[0],85+655*(j+int(metric!='x'))/steps,.00051)
            near(pair[1],245-180*(y-lo)/(hi-lo),.00051)
    expected_rounds = [] if metric=='x' else list(range(3,steps+1,3))
    if [b[0] for b in snapshot['bounds']]!=expected_rounds:
        raise RuntimeError('Adam lower-reference scope differs')
    for t,x,y in snapshot['bounds']:
        near(x,85+655*t/steps,.00051)
        near(y,245-180*(case['source_reference']['average_regret_lower']-lo)/(hi-lo),.00051)


def main():
    from playwright.sync_api import expect, sync_playwright
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
            if width==1440:
                validate_adam_counterexample(data)
            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert p.locator('[data-adam-case]').count()==9
            total = 0
            for case in data['cases']:
                p.locator('[data-adam-select]').select_option(case['id'])
                rounds = list(range(1,case['inputs']['steps']+1)) if width==1440 else case['native_rounds']
                for start in range(0,len(rounds),250):
                    selected = rounds[start:start+250]
                    validate_snapshot(case,p.evaluate(SNAPSHOT,selected),selected)
                total += len(rounds)*2
                panel = p.locator(f'[data-adam-case="{case["id"]}"]')
                for metric in ('x','average_regret'):
                    snapshot = panel.locator(f'[data-adam-chart="{metric}"]').evaluate('''svg=>({
                      low:Number(svg.dataset.low),high:Number(svg.dataset.high),
                      paths:[...svg.querySelectorAll('[data-adam-path]')].map(n=>[n.dataset.adamPath,n.getAttribute('points')]),
                      bounds:[...svg.querySelectorAll('[data-adam-bound]')].map(n=>[Number(n.dataset.adamBound),n.getAttribute('cx'),n.getAttribute('cy')])})''')
                    validate_chart(case,metric,snapshot)
                assert panel.locator('[data-adam-native]').count()==2*len(case['native_rounds'])
            p.locator('[data-adam-select]').select_option('c3-a0.5')
            slider = p.locator('[data-adam-round]')
            slider.focus()
            slider.press('Home')
            expect(p.locator('[data-adam-label]')).to_have_text(f't=1 / {data["parameters"]["steps"]}')
            slider.press('ArrowRight')
            expected = min(2,data['parameters']['steps'])
            expect(p.locator('[data-adam-label]')).to_have_text(f't={expected} / {data["parameters"]["steps"]}')
            slider.press('End')
            expect(p.locator('[data-adam-label]')).to_have_text(f't={data["parameters"]["steps"]} / {data["parameters"]["steps"]}')
            p.locator('[data-adam-first]').click()
            p.locator('[data-adam-next]').click()
            p.locator('[data-cycle-select]').select_option('c3-a0.5')
            expect(p.locator('[data-adam-select]')).to_have_value('c3-a0.5')
            p.locator('[data-adam-first]').click()
            blocks = p.locator('[data-cycle-block]')
            blocks.focus()
            blocks.press('End')
            block_first = 3*((data['parameters']['steps']-1)//3)+1
            expect(slider).to_have_value(str(block_first))
            validate_snapshot(data['cases'][1],p.evaluate(SNAPSHOT,[block_first]),[block_first])
            blocks.press('Home')
            expect(slider).to_have_value('1')
            slider.press('ArrowRight')
            expect(p.locator('[data-adam-label]')).to_have_text(f't={expected} / {data["parameters"]["steps"]}')
            p.locator('[data-adam-last]').click()
            p.locator('[data-action="language"]').click()
            p.locator('[data-action="language"]').click()
            p.locator('[data-adam-first]').click()
            p.locator('[data-adam-next]').click()
            p.locator('#round-inspector').screenshot(path=str(args.output/f'round-{width}.png'))
            p.locator('#cycle-inspector').screenshot(path=str(args.output/f'cycle-{width}.png'))
            if width==390:
                for selector in ('#cycle-inspector .adam-figure','#cycle-inspector .scroll'):
                    region = p.locator(selector).first
                    assert region.evaluate('e=>e.scrollWidth>e.clientWidth')
                    region.focus()
                    region.press('ArrowRight')
                    p.wait_for_function('selector=>document.querySelector(selector).scrollLeft>0',arg=selector)
                    region.evaluate('e=>e.scrollLeft=e.scrollWidth')
                assert p.locator('#cycle-inspector td').evaluate_all('nodes=>nodes.every(n=>getComputedStyle(n).whiteSpace==="nowrap")')
                p.locator('#cycle-inspector').screenshot(path=str(args.output/'cycle-mobile-scrolled.png'))
            assert p.locator('#round-inspector svg, #cycle-inspector svg').evaluate_all('''svgs=>svgs.every(svg=>{const b=svg.getBoundingClientRect();
             return [...svg.querySelectorAll('text')].filter(t=>t.getClientRects().length).every(t=>{const r=t.getBoundingClientRect();return r.left>=b.left-.5&&r.right<=b.right+.5&&r.top>=b.top-.5&&r.bottom<=b.bottom+.5;});})''')
            p.locator('#chainbench-evidence').evaluate('e=>e.parentElement.open=true')
            with p.expect_download() as download:
                p.locator('[data-download]').click()
            downloaded = args.output/f'download-{width}.json'
            download.value.save_as(downloaded)
            assert json.loads(downloaded.read_text())==data
            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            evidence['viewports'].append(dict(width=width,checked_method_rounds=total,cases=9,charts=18,
                                             complete_and_partial_blocks_checked=True))
            context.close()
        context = browser.new_context(java_script_enabled=False,offline=True,viewport=dict(width=390,height=1000))
        p = context.new_page()
        p.goto(args.html.resolve().as_uri())
        assert p.locator('[data-adam-case]').count()==9
        assert p.locator('[data-adam-native]').count()==sum(2*len(c['native_rounds']) for c in data['cases'])
        p.locator('[data-adam-case]').last.locator('summary').first.click()
        expect(p.locator('[data-adam-case]').last.locator('table').last).to_be_visible()
        assert p.locator('.adam-controls:visible').count()==0
        assert p.locator('[data-adam-native-cycle]').count()==9
        # Inspect all native first blocks with JavaScript disabled, including
        # partial budgets. Reuse the independent audit on each native subtree.
        for case in data['cases']:
            panel = p.locator(f'[data-adam-case="{case["id"]}"] [data-adam-native-cycle]')
            panel.evaluate('e=>{e.parentElement.open=true;e.open=true;}')
            native = panel.evaluate('(root)=>{const document={querySelectorAll:q=>root.querySelectorAll(q.replace("#cycle-inspector ",""))};return ('+CYCLE_SNAPSHOT+')();}')
            validate_cycle(case,1,native)
            expect(panel.locator('table').first).to_be_visible()
        assert json.loads(p.locator('#chainbench-evidence').text_content())==data
        assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
        evidence['no_javascript_native_tables'] = True
        browser.close()
    if evidence['javascript_errors'] or evidence['network_requests']:
        raise RuntimeError('Adam page made external requests or raised JavaScript errors')
    (args.output/'browser.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))


if __name__=='__main__':
    main()
