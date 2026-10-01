"""Audit rendered DOM geometry and every actual case/update/trial control state."""
import argparse
import json
import math
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from smoke_fista_backtracking import validate_fista_backtracking

STATIC = r'''el=>({id:el.dataset.btCase,
 paths:[...el.querySelectorAll('[data-bt-path]')].map(n=>[n.dataset.btPath,n.getAttribute('points')]),
 contours:[...el.querySelectorAll('[data-bt-contour]')].map(n=>[Number(n.dataset.btContour),JSON.parse(n.dataset.btWorld),n.getAttribute('points')]),
 wires:[...el.querySelectorAll('[data-bt-wire]')].map(n=>n.getAttribute('points')),
 stars:[...el.querySelectorAll('[data-bt-star]')].map(n=>[n.getAttribute('cx'),n.getAttribute('cy')]),
 native:[...el.querySelectorAll('[data-bt-native-row]')].map(n=>[n.id,...[...n.querySelectorAll('td')].map(t=>t.textContent)]),
 headers:[...el.querySelectorAll('th')].every(n=>getComputedStyle(n).textTransform==='none'),
 svgCount:el.querySelectorAll('svg').length})'''

FRAME = r'''el=>({
 step:Number(el.dataset.btCurrentStep),trial:Number(el.dataset.btCurrentTrial),
 values:['summary','vectors','gate','gaps'].map(s=>el.querySelector('[data-bt-'+s+']').textContent),
 decision:el.querySelector('[data-bt-gate]').dataset.btAccepted,
 link:el.querySelector('[data-bt-native-link]').getAttribute('href'),
 figures:[...el.querySelectorAll('svg')].map(s=>({
  dynamic:[...s.querySelectorAll('[data-bt-dynamic]')].map(n=>[n.dataset.btDynamic,n.getAttribute(n.dataset.btAttribute),n.tagName==='text'?n.textContent:null]),
  texts:[...s.querySelectorAll('[data-bt-text]')].map(n=>[n.dataset.btText,n.textContent]),
  labelsFit:[...s.querySelectorAll('text')].every(t=>{if(!t.textContent)return true;
   const r=t.getBoundingClientRect(),v=s.getBoundingClientRect();
   return r.left>=v.left-.5&&r.top>=v.top-.5&&r.right<=v.right+.5&&r.bottom<=v.bottom+.5;})
 }))})'''

FRAMES = r'''el=>{
 const out=[],step=document.getElementById('bt-step'),trial=document.getElementById('bt-trial');
 for(let k=1;k<=Number(step.max);k++){
  step.value=k;step.dispatchEvent(new Event('input',{bubbles:true}));
  for(let j=0;j<trial.options.length;j++){
   trial.value=j;trial.dispatchEvent(new Event('change',{bubbles:true}));
   out.push(('''+FRAME+r''')(el));
  }
 }return out;
}'''


def require(value, message):
    if not value:
        raise RuntimeError('FISTA DOM: '+message)


def near(actual, expected, atol=.00051, rtol=0):
    require(math.isfinite(float(actual)) and math.isclose(float(actual),expected,abs_tol=atol,rel_tol=rtol),
        f'value {actual} != {expected}')


def coords(actual, expected):
    values = [p.split(',') for p in actual.split()]
    require(len(values)==len(expected),'path sample count differs')
    for p,q in zip(values,expected):
        require(len(p)==len(q)==2,'coordinate dimension differs')
        for a,b in zip(p,q):
            near(a,b)


def translated(actual, expected):
    match = re.fullmatch(r'translate\(([-+\d.e]+) ([-+\d.e]+)\)',actual)
    require(match is not None,'marker transform differs')
    for a,b in zip(match.groups(),expected):
        near(a,b)


def shown(actual, expected, rtol=5.1e-6):
    if isinstance(expected,list):
        require(actual.startswith('(') and actual.endswith(')'),'vector delimiters differ')
        values = actual[1:-1].split(', ')
        require(len(values)==len(expected),'vector dimension differs')
        for a,b in zip(values,expected):
            shown(a,b,rtol)
    else:
        near(actual,expected,atol=0,rtol=rtol)


def gap(point,case):
    lam = case['inputs']['lambda']
    star = case['optimum']['point']
    signs = [min(1,1.4/lam),max(-1,-7.2/lam)]
    return .5*sum(a*(x-s)**2 for a,x,s in zip((1,9),point,star))+lam*sum(abs(x)-s*x for x,s in zip(point,signs))


def project(point,height=0.,surface=False):
    x,y = point
    return [310+38*x+28*y,310-13*x+18*y-1.4*height] if surface else [310+52*x,250-52*y]


def validate_static(case, view):
    require(view['id']==case['id'] and view['svgCount']==4 and view['headers'],'case/figure/math header differs')
    require([p[0] for p in view['paths']]==['plane','surface'],'accepted path coverage differs')
    for mode,path in view['paths']:
        coords(path,[project(r['x'],r['stable_gap'],mode=='surface') for r in case['rows']])
    for surface,point in zip((False,True),view['stars']):
        for a,b in zip(point,project(case['optimum']['point'],surface=surface)):
            near(a,b)
    require(len(view['stars'])==2 and len(view['wires'])==26,'reference/surface coverage differs')
    for path,(axis,i) in zip(view['wires'],[(axis,i) for axis in (0,1) for i in range(13)]):
        fixed = -3.5+7*i/12
        world = [[fixed,-3.5+7*j/48] if axis==0 else [-3.5+7*j/48,fixed] for j in range(49)]
        coords(path,[project(p,gap(p,case),True) for p in world])
    require([c[0] for c in view['contours']]==[.1,1,5,20],'contour levels differ')
    for level,world,path in view['contours']:
        require(len(world)==257,'contour ray coverage differs')
        for i,p in enumerate(world):
            near(gap(p,case),level,atol=5e-11)
            theta = 2*math.pi*i/256
            d = [v-s for v,s in zip(p,case['optimum']['point'])]
            near(d[0]*math.sin(theta)-d[1]*math.cos(theta),0,atol=1e-12)
            require(d[0]*math.cos(theta)+d[1]*math.sin(theta)>0,'contour wrong ray')
        coords(path,[project(p) for p in world])
    flat = [(s,v) for s in case['stages'] for v in s['trials']]
    require(len(view['native'])==len(flat),'native trial coverage differs')
    for row,(s,v) in zip(view['native'],flat):
        require(len(row)==12 and row[0]==f'bt-{case["id"]}-k{s["iteration"]}-j{v["attempt"]}', 'native identity differs')
        require(row[1]==f'{s["iteration"]} / {v["attempt"]+1}', 'native trial index differs')
        for a,b in zip(row[2].split(' / '),(v['L'],v['step_size'])):
            shown(a,b,5.1e-8)
        shown(row[3],v['threshold'],5.1e-8)
        for a,b in zip(row[4:7],(s['anchor'],v['gradient_step'],v['point'])):
            shown(a,b)
        for a,b in zip((row[7],row[8],row[10],row[11]),(v['stable_model_difference'],v['raw_model_difference'],v['stable_gap'],v['stable_model_gap'])):
            shown(a,b,5.1e-8)
        require(row[9]==('accepted' if v['accepted'] else 'rejected'),'native decision differs')


def validate_frame(case, frame, k, j):
    s,v = case['stages'][k-1],case['stages'][k-1]['trials'][j]
    require(frame['step']==k and frame['trial']==j,'selected state differs')
    require(frame['decision']==str(v['accepted']).lower(),'displayed gate state differs')
    require(frame['link']==f'#bt-{case["id"]}-k{k}-j{j}','native target differs')
    summary,vectors,gate,gaps = frame['values']
    parts = summary.split(' · ')
    require(len(parts)==6 and parts[:2]==[f'k={k}',f'trial={j+1}/{len(s["trials"])}'],'summary index differs')
    for actual,expected in zip(parts[2:],(s['carried_L'],v['L'],v['step_size'],v['threshold'])):
        shown(actual.split('=')[1],expected)
    for actual,expected in zip(vectors.split(' → '),(s['anchor'],v['gradient_step'],v['point'])):
        shown(actual.split('=')[1],expected)
    parts = gate.split(' · ')
    require(len(parts)==3 and parts[-1]==('채택 / accepted' if v['accepted'] else '거부 / rejected'),'gate label differs')
    for actual,expected in zip(parts[:2],(v['stable_model_difference'],v['raw_model_difference'])):
        shown(actual.split('=')[1],expected)
    for actual,expected in zip(gaps.split(' · '),(v['stable_gap'],v['stable_model_gap'],s['anchor_gap'],s['previous_gap'])):
        shown(actual.split('=')[1],expected)
    require(len(frame['figures'])==4 and all(f['labelsFit'] for f in frame['figures']),'clipped SVG labels')
    for surface,f in zip((False,True),frame['figures'][:2]):
        require([x[0] for x in f['dynamic']]==['x','anchor'],'path marker coverage differs')
        for (_,actual,_),point in zip(f['dynamic'],(case['rows'][k]['x'],s['anchor'])):
            translated(actual,project(point,gap(point,case),surface))
    proposals = frame['figures'][2]
    radius = max(1.,1.1*max(abs(x) for p in [s['anchor']]+[q['point'] for q in s['trials']] for x in p))
    def xy(point):
        return [310+182*point[0]/radius,250-182*point[1]/radius]
    elements = proposals['dynamic']
    require([e[0] for e in elements[:3]]==['proposals','proposal-anchor','proposal-selected'],'proposal coverage differs')
    coords(elements[0][1],[xy(p) for p in [s['anchor']]+[q['point'] for q in s['trials']]])
    translated(elements[1][1],xy(s['anchor']))
    translated(elements[2][1],xy(v['point']))
    require(len(elements)==3+max(len(t['trials']) for t in case['stages']),'proposal numbers omitted')
    for index,(name,position,label) in enumerate(elements[3:]):
        require(name==f'proposal-number-{index}' and label==(str(index+1) if index<len(s['trials']) else ''),'trial number differs')
        a,b = xy(s['trials'][min(index,len(s['trials'])-1)]['point'])
        translated(position,[a+6,b-6])
    texts = proposals['texts']
    require([name for name,_ in texts]==['proposal-x-tick','proposal-y-tick']*3+['proposal-scale'],'proposal scale labels omitted')
    for (_,label),expected in zip(texts[:6],[-radius,-radius,0,0,radius,radius]):
        shown(label,expected,5.1e-4)
    require(texts[-1][1]==f'Each coordinate spans ±{radius:.6g}; equal scales, refitted per step.','proposal axis meaning differs')
    model = frame['figures'][3]
    samples = v['slice']
    values = samples['objective_gap']+samples['model_gap']+[s['previous_gap'],0.]
    lo,hi = min(values),max(values)
    pad = .08*(hi-lo) if hi>lo else 1.
    low,high = lo-pad,hi+pad
    def model_xy(t,g):
        return [86+(t+.25)*460/1.5,390-(g-low)/(high-low)*300]
    require([e[0] for e in model['dynamic']]==['objective_gap','model_gap','previous-gap','candidate-F','candidate-Q'],'model elements differ')
    for (_,actual,_),field in zip(model['dynamic'][:2],('objective_gap','model_gap')):
        coords(actual,[model_xy(t,g) for t,g in zip(samples['parameter'],samples[field])])
    coords(model['dynamic'][2][1],[model_xy(t,s['previous_gap']) for t in (-.25,1.25)])
    for (_,actual,_),field in zip(model['dynamic'][3:],('stable_gap','stable_model_gap')):
        translated(actual,model_xy(1,v[field]))
    require([name for name,_ in model['texts']]==['model-tick']*3,'model ticks omitted')
    for (_,label),fraction in zip(model['texts'],(0,.5,1)):
        shown(label,low+fraction*(high-low),5.1e-4)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        audited = False
        for width in (1440,390):
            context = browser.new_context(viewport=dict(width=width,height=1000),accept_downloads=True)
            page = context.new_page()
            errors,requests = [],[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:requests.append(r.url) if r.url.startswith(('https:','http:')) else None)
            page.goto(args.html.resolve().as_uri(),wait_until='load')
            record = json.loads(page.locator('#chainbench-evidence').text_content())
            if not audited:
                validate_fista_backtracking(record)
                audited = True
            expect(page.locator('#bt-case option')).to_have_count(36)
            states = 0
            for i,case in enumerate(record['cases']):
                page.select_option('#bt-case',str(i))
                el = page.locator('[data-bt-case]').nth(i)
                expect(el).to_be_visible()
                expect(page.locator('[data-bt-case]:visible')).to_have_count(1)
                validate_static(case,el.evaluate(STATIC))
                frames = el.evaluate(FRAMES)
                expected = [(s['iteration'],v['attempt']) for s in case['stages'] for v in s['trials']]
                require(len(frames)==len(expected),'frame coverage differs')
                for frame,(k,j) in zip(frames,expected):
                    validate_frame(case,frame,k,j)
                states += len(frames)
                for button in el.locator('[data-bt-jump]').all():
                    k = int(button.get_attribute('data-bt-jump'))
                    button.click()
                    validate_frame(case,el.evaluate(FRAME),k,0)
                # The native link is a real click, not a forced scroll or fabricated DOM.
                el.locator('[data-bt-native-link]').click()
                target = page.locator('[id="'+page.url.split('#')[1]+'"]')
                expect(target).to_be_visible()
                require(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'page overflow')
            page.select_option('#bt-case','0')
            page.locator('#bt-step').focus()
            page.locator('#bt-step').press('Home')
            page.locator('#bt-step').press('ArrowRight')
            require(page.locator('#bt-step').input_value()==str(min(2,record['parameters']['steps'])),'keyboard step failed')
            page.locator('[data-action="language"]').click()
            expect(page.locator('html')).to_have_attribute('lang','en')
            page.locator('[data-action="language"]').click()
            expect(page.locator('html')).to_have_attribute('lang','ko')
            page.locator('#chainbench-evidence').evaluate('e=>e.parentElement.open=true')
            with page.expect_download() as download:
                page.locator('[data-download]').click()
            saved = args.output/f'download-{width}.json'
            download.value.save_as(saved)
            require(json.loads(saved.read_text())==record,'download changed record')
            page.locator('#chainbench-evidence').evaluate('e=>e.parentElement.open=false')
            page.locator('#bt-case').scroll_into_view_if_needed()
            page.screenshot(path=str(args.output/f'controls-{width}.png'))
            require(not errors and not requests,'script error or external request')
            context.close()
            native = browser.new_context(viewport=dict(width=width,height=1000),java_script_enabled=False)
            page = native.new_page()
            page.goto(args.html.resolve().as_uri(),wait_until='load')
            for i,case in enumerate(record['cases']):
                el = page.locator('[data-bt-case]').nth(i)
                expect(el).to_be_visible()
                validate_static(case,el.evaluate(STATIC))
                el.locator('[data-bt-native-link]').click()
                expect(page.locator('[id="bt-'+case['id']+'-k1-j0"]')).to_be_visible()
            require(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'native page overflow')
            native.close()
            results.append(dict(width=width,cases=36,trial_states=states,native_cases=36,errors=errors,external_requests=requests))
        browser.close()
    (args.output/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results))


if __name__=='__main__':
    main()
