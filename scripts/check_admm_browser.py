"""Read actual DOM coordinates; independently audit original-primal and split views."""
import argparse
import json
import math
import re
from pathlib import Path

from admm_overview_audit import SNAPSHOT as OVERVIEW
from admm_overview_audit import validate_overview
from admm_subproblem_audit import (
    MODEL_FRAME,
    MODEL_STATIC,
    validate_model_frame,
    validate_model_static,
)
from playwright.sync_api import expect, sync_playwright
from smoke_admm_geometry import validate_admm_geometry

FIELDS = ('x_target','x_rhs','x','x_equation_residual','shrink_input','z','u','y',
          'primal_residual','dual_residual','primal_norm','eps_primal','dual_norm','eps_dual',
          'stopping_passed','objective_z','split_objective','stable_gap_z','split_minus_optimum',
          'dual_identity_residual','dual_box_excess')

STATIC = r"""el=>{
 const attr=(e,n)=>e.getAttribute(n), xy=e=>[attr(e,'cx'),attr(e,'cy')];
 const paths=(e,s,key)=>[...e.querySelectorAll(s)].map(n=>[n.dataset[key],attr(n,'points')]);
 return {id:el.dataset.admmCase,first:el.querySelector('[data-admm-first-pass]').dataset.admmFirstPass,
  labelsFit:[...el.querySelectorAll('svg')].every(svg=>{const b=svg.getBoundingClientRect();return [...svg.querySelectorAll('text')].every(t=>{const r=t.getBoundingClientRect();return r.left>=b.left-.5&&r.right<=b.right+.5&&r.top>=b.top-.5&&r.bottom<=b.bottom+.5;});}),
  primal:[...el.querySelectorAll('[data-admm-primal]')].map(s=>({mode:s.dataset.admmPrimal,radius:s.dataset.radius,height:s.dataset.height,
   paths:paths(s,'[data-admm-path]','admmPath'),optimum:xy(s.querySelector('[data-admm-optimum]')),
   mesh:[...s.querySelectorAll('[data-admm-mesh]')].map(n=>[JSON.parse(n.dataset.admmMesh),attr(n,'points')]),
   contours:[...s.querySelectorAll('[data-admm-level]')].map(n=>[Number(n.dataset.admmLevel),JSON.parse(n.dataset.world),attr(n,'points')])})),
  dual:(()=>{const s=el.querySelector('[data-admm-dual]');return {lambda:s.dataset.lambda,path:attr(s.querySelector('[data-admm-dual-path]'),'points'),optimum:xy(s.querySelector('[data-admm-dual-optimum]'))};})(),
  objective:(()=>{const s=el.querySelector('[data-admm-objectives]');return {high:s.dataset.high,star:attr(s.querySelector('[data-admm-objective-star]'),'d'),paths:paths(s,'[data-admm-objective-path]','admmObjectivePath')};})(),
  residual:(()=>{const s=el.querySelector('[data-admm-residuals]');return {low:s.dataset.low,high:s.dataset.high,
   points:[...s.querySelectorAll('[data-admm-ratio]')].map(n=>[n.dataset.admmRatio,n.dataset.raw,...xy(n)]),lines:paths(s,'[data-admm-ratio-line]','admmRatioLine')};})(),
  native:[...el.querySelectorAll('[data-admm-native]')].map(r=>[Number(r.dataset.admmNative),...[...r.querySelectorAll('td')].slice(1).map(n=>n.textContent)]),
  models:("""+MODEL_STATIC+r""")(el)};
}"""

FRAMES = r"""(el,selected)=>{
 const slider=document.getElementById('admm-step'),out=[];
 for(const k of selected){
  slider.value=String(k);slider.dispatchEvent(new Event('input',{bubbles:true}));
  out.push({k,label:el.querySelector('[data-admm-k]').textContent,global:document.getElementById('admm-step-label').textContent,
   fields:[...el.querySelectorAll('[data-admm-field]')].map(n=>[n.dataset.admmField,n.textContent]),
   markers:[...el.querySelectorAll('[data-admm-marker]')].map(n=>[n.closest('svg').dataset.admmPrimal||'dual',n.dataset.admmMarker,getComputedStyle(n).display,n.getAttribute('cx'),n.getAttribute('cy')]),
   chords:[...el.querySelectorAll('[data-admm-residual-chord]')].map(n=>[getComputedStyle(n).display,n.getAttribute('d')]),
   model:("""+MODEL_FRAME+r""")(el,k)});
 }return out;
}"""


def require(condition, message):
    if not condition:
        raise RuntimeError('ADMM DOM: '+message)


def near(actual, expected, atol=.00051, rtol=0):
    value = float(actual)
    require(math.isfinite(value) and math.isclose(value,expected,abs_tol=atol,rel_tol=rtol),
            f'coordinate/value {value} != {expected}')


def displayed(text, value):
    if value is None:
        require(text=='—','undefined initial value was invented')
    elif isinstance(value,bool):
        require(text==str(value).lower(),'residual decision differs')
    elif isinstance(value,list):
        require(text.startswith('(') and text.endswith(')'),'vector format differs')
        parts = text[1:-1].split(', ')
        require(len(parts)==len(value),'vector coverage differs')
        for part,v in zip(parts,value):
            displayed(part,v)
    else:
        near(text,value,atol=0,rtol=5.1e-7)


def gap(w, case):
    error = [a-b for a,b in zip(w,case['optimum']['point'])]
    A = case['inputs']['A']
    return .5*sum(sum(a*b for a,b in zip(row,error))**2 for row in A)+case['inputs']['lambda']*sum(
        abs(v)-s*v for v,s in zip(w,case['optimum']['subgradient']))


def projected(w, g, radius, height, mode):
    if mode=='surface':
        return [330+125*w[0]/radius+85*w[1]/radius,345-45*w[0]/radius+65*w[1]/radius-190*g/height]
    return [330+180*w[0]/radius,245-180*w[1]/radius]


def coordinates(actual, expected):
    pairs = [p.split(',') for p in actual.split()]
    require(len(pairs)==len(expected),'path sample count differs')
    for pair,point in zip(pairs,expected):
        require(len(pair)==2,'malformed coordinate pair')
        for a,b in zip(pair,point):
            near(a,b)


def validate_static(case, radius, view):
    validate_model_static(case,radius,view['models'])
    require(view['id']==case['id'] and view['first']==str(case['first_residual_pass']), 'case or first-pass identity differs')
    require(view['labelsFit'],'SVG text leaves its viewBox')
    require([s['mode'] for s in view['primal']]==['contour','surface'],'primal coverage differs')
    grid = [-radius+radius*i/10 for i in range(21)]
    mesh = [[[fixed,free] if not flip else [free,fixed] for free in grid] for flip in (False,True) for fixed in grid]
    height = max(10.,math.ceil(max(gap(w,case) for line in mesh for w in line)/10)*10.)
    for s in view['primal']:
        near(s['radius'],radius,0)
        near(s['height'],height,0)
        mode = s['mode']
        project = lambda w,g:projected(w,g,radius,height,mode)  # noqa: E731
        expected_mesh = mesh if mode=='surface' else []
        require(len(s['mesh'])==len(expected_mesh),'surface grid coverage differs')
        for (world,pixels),line in zip(s['mesh'],expected_mesh):
            require(len(world)==len(line),'surface sample count differs')
            for v,w in zip(world,line):
                require(len(v)==3,'surface vertex has wrong dimension')
                for a,b in zip(v,(*w,gap(w,case))):
                    near(a,b,1e-10)
            coordinates(pixels,[project(w,gap(w,case)) for w in line])
        require([c[0] for c in s['contours']]==([.1,.5,2.,10.,40.] if mode=='contour' else []),'contour levels differ')
        for level,world,pixels in s['contours']:
            require(len(world)==129 and all(len(w)==2 for w in world),'contour coverage differs')
            for i,w in enumerate(world):
                near(gap(w,case),level,3e-10)
                d = [a-b for a,b in zip(w,case['optimum']['point'])]
                theta = 2*math.pi*i/128
                near(d[0]*math.sin(theta)-d[1]*math.cos(theta),0,1e-12)
                require(d[0]*math.cos(theta)+d[1]*math.sin(theta)>0,'contour is on wrong ray')
            coordinates(pixels,[project(w,level) for w in world])
        require([p[0] for p in s['paths']]==['x','z'],'original-primal path coverage differs')
        for name,pixels in s['paths']:
            coordinates(pixels,[project(r[name],r['stable_gap_'+name]) for r in case['rows'] if r[name] is not None])
        for a,b in zip(s['optimum'],project(case['optimum']['point'],0)):
            near(a,b)
    lam = case['inputs']['lambda']
    dual_project = lambda w:[330+150*w[0]/lam,220-150*w[1]/lam]  # noqa: E731
    near(view['dual']['lambda'],lam,0)
    coordinates(view['dual']['path'],[dual_project(r['y']) for r in case['rows']])
    for a,b in zip(view['dual']['optimum'],dual_project([lam*v for v in case['optimum']['subgradient']])):
        near(a,b)
    n,rows = case['inputs']['steps'],case['rows']
    high = max(case['optimum']['value'],*[r['objective_z'] for r in rows],*[r['split_objective'] for r in rows[1:]])*1.08
    near(view['objective']['high'],high,0)
    require([p[0] for p in view['objective']['paths']]==['objective_z','split_objective'],'objective labels differ')
    for name,pixels in view['objective']['paths']:
        coordinates(pixels,[[80+510*r['iteration']/n,250-175*r[name]/high] for r in rows if r[name] is not None])
    star = re.fullmatch(r'M80 ([\d.]+) H590',view['objective']['star'])
    require(star is not None,'objective optimum line differs')
    near(star[1],250-175*case['optimum']['value']/high)
    ratios = {name:[r[name+'_norm']/r['eps_'+name] for r in rows[1:]] for name in ('primal','dual')}
    positive = [1.,*[v for a in ratios.values() for v in a if v>0]]
    lo,hi = math.floor(math.log10(min(positive)))-1,math.ceil(math.log10(max(positive)))+1
    near(view['residual']['low'],lo,0)
    near(view['residual']['high'],hi,0)
    project_ratio = lambda k,v:[80+510*k/n,235-165*(math.log10(v)-lo)/(hi-lo) if v else 274.]  # noqa: E731
    expected_lines,expected_points = [],[]
    for name,values in ratios.items():
        segment = []
        for k,v in enumerate(values,1):
            xy = project_ratio(k,v)
            expected_points.append((f'{name}:{k}',v,*xy))
            if v:
                segment.append(xy)
            elif segment:
                expected_lines.append((name,segment))
                segment = []
        if segment:
            expected_lines.append((name,segment))
    require(len(view['residual']['points'])==len(expected_points),'residual sample count differs')
    for actual,expected in zip(view['residual']['points'],expected_points):
        require(actual[0]==expected[0],'residual sample identity differs')
        near(actual[1],expected[1],0)
        for a,b in zip(actual[2:],expected[2:]):
            near(a,b)
    require(len(view['residual']['lines'])==len(expected_lines),'zero ratios incorrectly bridged')
    for (name,pixels),(expected_name,xy) in zip(view['residual']['lines'],expected_lines):
        require(name==expected_name,'residual curve identity differs')
        coordinates(pixels,xy)
    require([r[0] for r in view['native']]==case['native_iterations'],'native stage coverage differs')
    for k,*actual in view['native']:
        row = rows[k]
        expected = [row[key] for key in ('x','z','y','stable_gap_z')]
        expected += [None if k==0 else ratios[name][k-1] for name in ('primal','dual')]+[row['stopping_passed']]
        require(len(actual)==len(expected),'native columns differ')
        for a,b in zip(actual,expected):
            displayed(a,b)


def validate_frames(case, radius, height, frames, selected):
    require([f['k'] for f in frames]==selected,'frame coverage differs')
    lam = case['inputs']['lambda']
    for f in frames:
        k = f['k']
        validate_model_frame(case,radius,k,f['model'])
        row = case['rows'][k]
        require(f['label']==f['global']==f'k = {k}','selected frame label differs')
        require(tuple(v[0] for v in f['fields'])==FIELDS,'readout coverage differs')
        for key,value in f['fields']:
            displayed(value,row[key])
        expected_ids = [('contour','x'),('contour','z'),('surface','x'),('surface','z'),('dual','y')]
        require([(m[0],m[1]) for m in f['markers']]==expected_ids,'marker coverage differs')
        for mode,name,visibility,x,y in f['markers']:
            w = row[name]
            if w is None:
                require(visibility=='none','invented initial x marker')
                continue
            require(visibility!='none','missing defined marker')
            xy = ([330+150*w[0]/lam,220-150*w[1]/lam] if name=='y'
                  else projected(w,row['stable_gap_'+name],radius,height,mode))
            near(x,xy[0])
            near(y,xy[1])
        require(len(f['chords'])==2,'residual chord coverage differs')
        for mode,(visibility,path) in zip(('contour','surface'),f['chords']):
            if k==0:
                require(visibility=='none','invented initial residual chord')
            else:
                require(visibility!='none','missing residual chord')
                actual = re.fullmatch(r'M([^ ]+) ([^ ]+) L([^ ]+) ([^ ]+)',path)
                require(actual is not None,'malformed residual chord')
                expected = [*projected(row['x'],row['stable_gap_x'],radius,height,mode),
                            *projected(row['z'],row['stable_gap_z'],radius,height,mode)]
                for a,b in zip(actual.groups(),expected):
                    near(a,b)


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
            if width==1440:
                validate_admm_geometry(data)
            radius = data['geometry']['primal_bounds'][1]
            require(p.locator('[data-admm-case]').count()==36,'case coverage differs')
            validate_overview(data,p.evaluate(OVERVIEW))
            p.locator('#admm-overview').screenshot(path=str(args.output/f'overview-{width}.png'))
            stages = 0
            for case in data['cases']:
                link = p.locator(f'[data-admm-overview-link="{case["id"]}"]')
                link.click()
                expect(p.locator('#admm-case')).to_have_value(case['id'])
                expect(p.locator('#admm-step')).to_have_value(str(data['parameters']['steps']))
                expect(link).to_have_attribute('aria-current','true')
                panel = p.locator(f'[data-admm-case="{case["id"]}"]')
                expect(panel).to_be_visible()
                expect(panel.locator(':scope > summary')).to_be_focused()
                require(p.locator('[data-admm-case]:visible').count()==1,'case selection differs')
                static = panel.evaluate(STATIC)
                validate_static(case,radius,static)
                selected = list(range(len(case['rows'])))
                validate_frames(case,radius,float(static['primal'][0]['height']),panel.evaluate(FRAMES,selected),selected)
                stages += len(selected)
                require(p.evaluate('document.documentElement.scrollWidth<=innerWidth'),'page overflows')
            p.locator('#admm-case').select_option('coupled-lambda0.1-zero-rho1')
            p.locator('[data-admm-move="first"]').click()
            expect(p.locator('#admm-step-label')).to_have_text('k = 0')
            require(p.locator('[data-admm-overview-link][aria-current]').count()==0,'final link claims a different current iteration')
            p.locator('[data-admm-move="next"]').click()
            expect(p.locator('#admm-step-label')).to_have_text('k = 1')
            p.locator('#admm-step').focus()
            p.locator('#admm-step').press('End')
            expect(p.locator('#admm-step-label')).to_have_text(f'k = {data["parameters"]["steps"]}')
            p.locator('[data-admm-move="first"]').click()
            p.locator('#admm-step').focus()
            p.locator('#admm-step').press('ArrowRight')
            expect(p.locator('#admm-step-label')).to_have_text('k = 1')
            p.locator('[data-admm-move="last"]').click()
            expect(p.locator('#admm-step-label')).to_have_text(f'k = {data["parameters"]["steps"]}')
            p.locator('#admm-step').fill('1')
            panel = p.locator('[data-admm-case]:visible')
            panel.scroll_into_view_if_needed()
            p.screenshot(path=str(args.output/f'admm-{width}.png'),full_page=False)
            model_figure = panel.locator('.admm-models .admm-figure').first
            model_figure.scroll_into_view_if_needed()
            bar = p.locator('.admm-step-controls')
            require(bar.evaluate('e=>{const b=e.getBoundingClientRect();return getComputedStyle(e).position==="sticky"&&b.top>=0&&b.bottom<=innerHeight;}'),
                    'iteration controls leave the subproblem viewport')
            p.locator('[data-admm-move="next"]').click()
            expect(p.locator('#admm-step-label')).to_have_text(f'k = {min(2,data["parameters"]["steps"])}')
            p.locator('#admm-step').fill('1')
            panel.locator('.admm-models').screenshot(path=str(args.output/f'subproblems-{width}.png'))
            if width==390:
                for scroll in [panel.locator('.admm-figure').first,
                               *panel.locator('.admm-models .admm-figure').all()]:
                    scroll.focus()
                    scroll.press('ArrowRight')
                    p.wait_for_timeout(200)
                    require(scroll.evaluate('e=>e.scrollLeft>0'),'keyboard figure scroll failed')
                scroll = p.locator('.admm-overview-group .scroll').first
                scroll.focus()
                scroll.press('ArrowRight')
                p.wait_for_timeout(200)
                require(scroll.evaluate('e=>e.scrollLeft>0'),'keyboard outcome-table scroll failed')
            first_link = p.locator('[data-admm-overview-link]').first
            first_link.focus()
            first_link.press('Enter')
            expect(p.locator('#admm-step')).to_have_value(str(data['parameters']['steps']))
            expect(p.locator('#admm-case')).to_have_value(data['cases'][0]['id'])
            back = p.locator('[data-admm-case]:visible [data-admm-overview-return]')
            back.focus()
            back.press('Enter')
            expect(p.locator('#admm-overview')).to_be_in_viewport()
            initial_lang = p.locator('html').get_attribute('lang')
            p.locator('[data-action="language"]').click()
            require(p.locator('html').get_attribute('lang')!=initial_lang,'language toggle failed')
            validate_overview(data,p.evaluate(OVERVIEW))
            download = p.locator('[data-download="chainbench-evidence"]')
            download.evaluate('e=>e.closest("details").open=true')
            with p.expect_download() as event:
                download.click()
            target = args.output/f'download-{width}.json'
            event.value.save_as(target)
            require(json.loads(target.read_text())==data,'downloaded record differs')
            evidence['viewports'].append(dict(width=width,cases=36,stages=stages,
                geometry='all original meshes/paths, subproblem contours/shrinkage, residuals and readouts',
                sticky_iteration_controls='visible at model panels',
                overview='36 final states, all links, keyboard navigation and native targets'))
            context.close()
        context = browser.new_context(viewport=dict(width=390,height=1000),java_script_enabled=False,offline=True)
        p = context.new_page()
        p.goto(args.html.resolve().as_uri())
        require(p.locator('[data-admm-case]:visible').count()==36,'native cases missing')
        require(p.locator('.admm-controls:visible').count()==0,'native controls falsely promise interactivity')
        validate_overview(data,p.evaluate(OVERVIEW))
        for case in data['cases']:
            p.locator(f'[data-admm-overview-link="{case["id"]}"]').click()
            panel = p.locator(f'[data-admm-case="{case["id"]}"]')
            expect(panel.locator('[data-admm-native]').last).to_be_visible()
            static = panel.evaluate(STATIC)
            validate_static(case,radius,static)
            validate_frames(case,radius,float(static['primal'][0]['height']),panel.evaluate(FRAMES,[1]),[1])
            expect(panel.locator('[data-admm-native]').last).to_be_visible()
            panel.locator('[data-admm-model-native]').first.evaluate('e=>e.closest("details").open=true')
            expect(panel.locator('[data-admm-model-native]').last).to_be_visible()
            require(p.evaluate('document.documentElement.scrollWidth<=innerWidth'),'native page overflows')
        native_rows = sum(len(c['native_iterations']) for c in data['cases'])
        evidence['no_javascript'] = dict(cases=36,native_rows=native_rows,subproblem_native_rows=native_rows,
                                        overview_links='all 36 native final-row fragments open their details')
        context.close()
        browser.close()
    require(not evidence['javascript_errors'] and not evidence['network_requests'],'offline runtime errors or requests')
    (args.output/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence))


if __name__=='__main__':
    main()
