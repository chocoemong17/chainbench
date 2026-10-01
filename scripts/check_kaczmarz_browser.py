"""Inspect every recorded trial and iteration, including stationary/zero updates."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

VERIFY = """id=>{
 const data=JSON.parse(document.getElementById('chainbench-evidence').textContent),c=data.cases.find(c=>c.id===id),panel=document.querySelector('[data-rk-case="'+id+'"]'),slider=document.querySelector('[data-rk-slider]'),seed=document.querySelector('[data-rk-seed]'),camera=document.querySelector('[data-rk-camera]');
 const near=(a,b)=>{if(Math.abs(Number(a)-b)>1e-5)throw Error('pixel mismatch '+a+' '+b);};
 const fire=(el,v,type)=>{el.value=String(v);el.dispatchEvent(new Event(type,{bubbles:true}));};
 const proj=x=>{const a=Number(camera.value)*Math.PI/180,e=25*Math.PI/180;return [230+130*Math.cos(a)*x[0]-130*Math.sin(a)*x[1],260-130*Math.sin(e)*Math.sin(a)*x[0]-130*Math.sin(e)*Math.cos(a)*x[1]-130*Math.cos(e)*x[2]];};
 const checkPoints=(el,expected)=>{const actual=el.getAttribute('points').trim().split(' ').map(p=>p.split(','));if(actual.length!==expected.length)throw Error('point count');actual.forEach((p,i)=>{near(p[0],expected[i][0]);near(p[1],expected[i][1]);});};
 const chart=panel.querySelector('[data-rk-chart]'),cp=(v,k)=>[65+630*k/data.parameters.steps,335-260*v/c.exact_expectation[0]];
 for(const field of ['exact_expectation','empirical_mean'])checkPoints(chart.querySelector('[data-rk-series="'+field+'"]'),c[field].map(cp));
 for(const run of c.runs){
  fire(seed,run.seed,'change');checkPoints(chart.querySelector('[data-rk-trial="'+run.seed+'"]'),run.squared_errors.map(cp));
  for(let k=0;k<=data.parameters.steps;k++){
   fire(slider,k,'input');
   const row=k?run.row_indices[k-1]:null,axis=row===null?null:c.inputs.A[row].indexOf(1),readout=panel.querySelector('[data-rk-readout]').textContent;
   if(!readout.includes('seed='+run.seed+' · k='+k+' ·')||!readout.includes('x=['+run.iterates[k].join(', ')+']')||!readout.includes('||x−x*||²='+run.squared_errors[k]+' ·'))throw Error('readout differs');
   if(!readout.includes('selected row (0-based)='+(row===null?'none / 초기':row)))throw Error('wrong selected row');
   const marker=chart.querySelector('[data-rk-current]'),p=cp(run.squared_errors[k],k);near(marker.getAttribute('cx'),p[0]);near(marker.getAttribute('cy'),p[1]);near(chart.querySelector('[data-rk-cursor]').getAttribute('x1'),p[0]);
   checkPoints(chart.querySelector('[data-rk-selected]'),run.squared_errors.map(cp));
   if(id==='cube'){
    const cube=panel.querySelector('[data-rk-cube]');
    checkPoints(cube.querySelector('[data-rk-path]'),run.iterates.slice(0,k+1).map(proj));
    for(const [name,x] of [['previous',run.iterates[Math.max(0,k-1)]],['current',run.iterates[k]]]){const el=cube.querySelector('[data-rk-point="'+name+'"]'),p=proj(x);near(el.getAttribute('cx'),p[0]);near(el.getAttribute('cy'),p[1]);}
    cube.querySelectorAll('[data-rk-plane]').forEach(el=>{if((getComputedStyle(el).display!=='none')!==(Number(el.dataset.rkPlane)===axis))throw Error('wrong plane');});
   }else{const el=panel.querySelector('[data-rk-state]');near(el.getAttribute('cx'),run.iterates[k][0]===1?110:365);}
   const proof=panel.querySelector('[data-rk-proof]'),before=run.iterates[Math.max(0,k-1)],chart2=proof.querySelector('[data-rk-candidates]'),total=c.inputs.equations,max=c.exact_expectation[0];
   if(proof.dataset.currentStep!==String(k)||proof.dataset.currentSeed!==String(run.seed)||proof.dataset.stateKey!==before.join(','))throw Error('conditional context differs');
   let expected=0;
   c.inputs.direction_counts.forEach((count,j)=>{
    const err=before.reduce((sum,v,i)=>sum+(i===j?0:v*v),0),height=200*err/max,bar=chart2.querySelector('[data-rk-candidate="'+j+'"]');
    near(bar.getAttribute('height'),height);near(bar.getAttribute('y'),270-height);expected+=count/total*err;
    if(bar.getAttribute('fill')!==(j===axis?'#d97706':'#2563eb'))throw Error('wrong candidate highlight');
    const marker=chart2.querySelector('[data-rk-candidate-marker="'+j+'"]');if((getComputedStyle(marker).display!=='none')!==(j===axis))throw Error('wrong zero candidate marker');
   });
   near(chart2.querySelector('[data-rk-conditional-line]').getAttribute('y1'),270-200*expected/max);
   const triangle=proof.querySelector('[data-rk-triangle]'),active=triangle.querySelector('[data-rk-triangle-active]'),initial=triangle.querySelector('[data-rk-triangle-initial]');
   if((getComputedStyle(active).display!=='none')!==(k>0)||(getComputedStyle(initial).display!=='none')!==(k===0))throw Error('invented initial projection');
   if(k){
    const next=run.iterates[k],removed=Math.hypot(...before.map((v,i)=>v-next[i])),remaining=Math.hypot(...next),scale=215/Math.sqrt(max),o=[90,290],n=[90,290-scale*remaining],prev=[90+scale*removed,290-scale*remaining];
    for(const [name,ps] of [['old',[o,prev]],['remaining',[o,n]],['removed',[n,prev]]])checkPoints(triangle.querySelector('[data-rk-error-leg="'+name+'"]'),ps);
    for(const [name,point] of [['solution',o],['next',n],['previous',prev]]){const el=triangle.querySelector('[data-rk-error-point="'+name+'"]');near(el.getAttribute('cx'),point[0]);near(el.getAttribute('cy'),point[1]);}
    if((getComputedStyle(triangle.querySelector('[data-rk-right-angle]')).display!=='none')!==(removed>0&&remaining>0))throw Error('false right-angle mark');
   }
   const proofText=proof.querySelector('[data-rk-proof-status]').textContent;
   if((before.every(x=>x===0))!==proofText.includes('undefined at zero error'))throw Error('false contraction ratio');
  }
 }
 if(id==='cube'){
  for(const angle of [-180,-135,-90,0,35,90,135,180]){
   fire(camera,angle,'input');const cube=panel.querySelector('[data-rk-cube]');
   cube.querySelectorAll('[data-rk-coordinates]').forEach(el=>{const expected=JSON.parse(el.dataset.rkCoordinates).map(proj);checkPoints(el,expected);for(const p of expected){if(p[0]<0||p[0]>480||p[1]<0||p[1]>365)throw Error('clipped cube geometry');}});
  }fire(camera,35,'input');
 }
 return c.runs.length*(data.parameters.steps+1);
}"""


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
            record = json.loads(p.locator('#chainbench-evidence').text_content())
            assert not evidence['javascript_errors'],evidence
            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            for c in record['cases']:
                name = c['id']
                p.locator('[data-rk-select]').select_option(name)
                panel = p.locator(f'[data-rk-case="{name}"]')
                expect(panel).to_be_visible()
                assert p.locator('[data-rk-case]:visible').count()==1
                states = p.evaluate(VERIFY,name)
                assert panel.locator('svg').evaluate_all('''svgs=>svgs.every(svg=>{const v=svg.getBoundingClientRect();return [...svg.querySelectorAll('text')].filter(t=>t.getClientRects().length).every(t=>{const b=t.getBoundingClientRect();return b.left>=v.left-.5&&b.right<=v.right+.5&&b.top>=v.top-.5&&b.bottom<=v.bottom+.5;});})''')
                p.locator('[data-rk-seed]').select_option('0')
                p.locator('[data-rk-slider]').evaluate('(el,k)=>{el.value=String(k);el.dispatchEvent(new Event("input",{bubbles:true}));}',min(2,record['parameters']['steps']))
                panel.locator('.rk-grid').screenshot(path=str(args.output/f'{name}-{width}.png'))
                panel.locator('.rk-proof-grid').screenshot(path=str(args.output/f'proof-{name}-{width}.png'))
                evidence['viewports'].append(dict(width=width,case=name,verified_states=states))
            slider = p.locator('[data-rk-slider]')
            slider.focus()
            slider.press('Home')
            slider.press('ArrowRight')
            expect(slider).to_have_value('1')
            slider.press('Home')
            p.locator('[data-rk-play]').click()
            expect(p.locator('[data-rk-play]')).to_have_attribute('aria-pressed','true')
            p.wait_for_timeout(550)
            assert int(slider.input_value()) >= 1
            p.locator('[data-rk-select]').select_option('cube')
            expect(p.locator('[data-rk-play]')).to_have_attribute('aria-pressed','false')
            old = p.locator('html').get_attribute('lang')
            p.locator('[data-action="language"]').click()
            assert p.locator('html').get_attribute('lang') != old
            p.locator('[data-action="language"]').click()
            p.locator('#chainbench-evidence').locator('..').locator('summary').click()
            with p.expect_download() as event:
                p.locator('[data-download="chainbench-evidence"]').click()
            dest = args.output/f'download-{width}.json'
            event.value.save_as(dest)
            assert json.loads(dest.read_text())==record
            context.close()
        context = browser.new_context(viewport=dict(width=390,height=1000),offline=True,java_script_enabled=False)
        p = context.new_page()
        p.goto(args.html.resolve().as_uri())
        assert p.locator('.rk-controls').is_hidden()
        assert p.locator('[data-rk-case]:visible').count()==6
        assert p.locator('[data-rk-run]').count()==6*record['parameters']['trials']
        assert p.locator('[data-rk-run] tbody tr').count()==6*record['parameters']['trials']*(record['parameters']['steps']+1)
        assert p.locator('[data-rk-proof-state]').count()==sum(len(c['conditional_projection']['states']) for c in record['cases'])
        p.locator('[data-rk-case="cube"] > details').last.locator(':scope > summary').click()
        run = p.locator('[data-rk-case="cube"] [data-rk-run="0"]')
        run.locator('summary').click()
        expect(run.locator('tbody tr').last).to_be_visible()
        assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
        p.locator('[data-rk-case="cube"] .rk-grid').screenshot(path=str(args.output/'no-script.png'))
        context.close()
        browser.close()
    assert not evidence['javascript_errors'] and not evidence['network_requests'],evidence
    evidence['no_script'] = 'all six cases and every seed table available'
    (args.output/'browser-verification.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))


if __name__=='__main__':
    main()
