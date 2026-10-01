"""Named faults in a real ADMM DOM must fail the independent geometry audit."""
import argparse
import json
from pathlib import Path

from admm_overview_audit import SNAPSHOT as OVERVIEW
from admm_overview_audit import validate_overview
from check_admm_browser import FRAMES, STATIC, require, validate_frames, validate_static
from playwright.sync_api import sync_playwright

STATIC_FAULTS = {
    'surface-height': "const e=p.querySelector('[data-admm-mesh]'),v=JSON.parse(e.dataset.admmMesh);v[0][2]+=1;e.dataset.admmMesh=JSON.stringify(v);",
    'surface-pixels': "p.querySelector('[data-admm-mesh]').setAttribute('points','0,0');",
    'contour-level': "p.querySelector('[data-admm-level]').dataset.admmLevel='0.2';",
    'missing-primal-path': "p.querySelector('[data-admm-path]').setAttribute('points','');",
    'dual-path': "p.querySelector('[data-admm-dual-path]').setAttribute('points','0,0');",
    'dual-optimum': "p.querySelector('[data-admm-dual-optimum]').setAttribute('cx','1');",
    'mixed-objective': "p.querySelector('[data-admm-objective-path=split_objective]').setAttribute('points',p.querySelector('[data-admm-objective-path=objective_z]').getAttribute('points'));",
    'wrong-objective-reference': "p.querySelector('[data-admm-objective-star]').setAttribute('d','M80 250 H590');",
    'residual-pixel': "p.querySelector('[data-admm-ratio]').setAttribute('cy','999');",
    'nonfinite-residual': "p.querySelector('[data-admm-ratio]').dataset.raw='NaN';",
    'residual-line': "p.querySelector('[data-admm-ratio-line]').setAttribute('points','0,0');",
    'invented-initial-x': "p.querySelector('[data-admm-native=\"0\"] td:nth-child(2)').textContent='(0, 0)';",
    'missing-native-row': "p.querySelector('[data-admm-native]').remove();",
    'false-first-pass': "p.querySelector('[data-admm-first-pass]').dataset.admmFirstPass='0';",
    'model-metric-label': "p.querySelector('[data-admm-x-model] text').textContent='Original gap F(w) − F*';",
    'model-world-contour': "const e=p.querySelector('[data-admm-model-level]'),v=JSON.parse(e.dataset.offsets);v[0][0]+=.3;e.dataset.offsets=JSON.stringify(v);",
    'model-pixels': "p.querySelector('[data-admm-model-level]').setAttribute('points','0,0');",
    'wrong-shrink-threshold': "p.querySelector('[data-admm-shrink]').dataset.tau='999';",
    'clipped-shrink-axis': "p.querySelector('[data-admm-shrink]').dataset.bound='2.5';",
    'threshold-band': "p.querySelector('[data-admm-shrink-band]').setAttribute('width','1');",
    'native-new-memory': "p.querySelector('[data-admm-model-native=\"1\"] td:nth-child(3)').textContent='(0.34, -0.34)';",
}
FRAME_FAULTS = {
    'stale-marker': (1,"p.querySelector('[data-admm-marker=x]').setAttribute('cx','999');"),
    'hidden-defined-z': (1,"p.querySelector('[data-admm-marker=z]').style.display='none';"),
    'invented-initial-marker': (0,"p.querySelector('[data-admm-marker=x]').style.display='';"),
    'wrong-initial-readout': (0,"p.querySelector('[data-admm-field=x]').textContent='(0, 0)';"),
    'wrong-penalty-memory': (1,"p.querySelector('[data-admm-field=y]').textContent='(0, 0)';"),
    'false-stop': (1,"p.querySelector('[data-admm-field=stopping_passed]').textContent='true';"),
    'primal-split-confusion': (1,"p.querySelector('[data-admm-field=objective_z]').textContent=p.querySelector('[data-admm-field=split_objective]').textContent;"),
    'wrong-residual-chord': (1,"p.querySelector('[data-admm-residual-chord]').setAttribute('d','M0 0 L0 0');"),
    'stale-model-center': (1,"p.querySelector('[data-admm-model-center]').setAttribute('transform','translate(330 245)');"),
    'hidden-shrink-result': (1,"p.querySelector('[data-admm-shrink-point=\"z:0\"]').style.display='none';"),
    'new-memory-readout': (1,"p.querySelector('[data-admm-model-read=old_u]').textContent='(0.34, -0.34)';"),
    'unshifted-shrink-input': (2,"const s=p.querySelector('[data-admm-shrink]'),r=JSON.parse(document.getElementById('chainbench-evidence').textContent).cases.find(c=>c.id===p.dataset.admmCase).rows[2];s.querySelector('[data-admm-shrink-point=\"v:0\"]').setAttribute('cx',330+250*r.x[0]/Number(s.dataset.bound));"),
    'wrong-shrink-arrow': (1,"p.querySelector('[data-admm-shrink-move]').setAttribute('d','M0 0 L0 0');"),
    'invented-initial-model': (0,"p.querySelector('[data-admm-model-body]').hidden=false;p.querySelector('[data-admm-model-initial]').hidden=true;"),
}
OVERVIEW_FAULTS = {
    'overview-missing-cell': "document.querySelector('[data-admm-outcome]').remove();",
    'overview-wrong-grid-position': "document.querySelector('[data-admm-outcome]').dataset.admmOutcome='another-case';",
    'overview-ratio': "document.querySelector('[data-admm-outcome-value=primal_ratio]').textContent='999';",
    'overview-gap': "document.querySelector('[data-admm-outcome-value=gap]').textContent='1';",
    'overview-final-decision': "document.querySelector('[data-admm-outcome]').dataset.admmOutcomePass='false';",
    'overview-visible-decision': "document.querySelector('.admm-outcome-status [lang=en]').textContent='Wrong verdict';",
    'overview-invented-pass': "[...document.querySelectorAll('[data-admm-outcome-first]')].find(n=>n.querySelector('[lang=en]')).textContent='61';",
    'overview-first-pass': "[...document.querySelectorAll('[data-admm-outcome-first]')].find(n=>!n.querySelector('[lang=en]')).textContent='0';",
    'overview-wrong-link': "document.querySelector('[data-admm-overview-link]').setAttribute('href','#admm-overview');",
    'overview-missing-native-target': "const a=document.querySelector('[data-admm-overview-link]');document.getElementById(a.getAttribute('href').slice(1)).removeAttribute('id');",
    'overview-duplicate-target': "const a=document.querySelector('[data-admm-overview-link]'),row=document.getElementById(a.getAttribute('href').slice(1));row.after(row.cloneNode(true));",
    'overview-penalty-heading': "document.querySelector('[data-admm-overview-group] thead th:nth-child(2)').textContent='ρ=100';",
    'overview-actual-input-caption': "document.querySelector('[data-admm-overview-group] caption').textContent='Different matrix';",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    rejected = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        p = browser.new_page(viewport=dict(width=1440,height=1000),offline=True)
        p.goto(args.html.resolve().as_uri())
        data = json.loads(p.locator('#chainbench-evidence').text_content())
        case = next(c for c in data['cases'] if c['id']=='coupled-lambda0.1-zero-rho1')
        radius = data['geometry']['primal_bounds'][1]
        selector = '[data-admm-case="'+case['id']+'"]'
        p.locator('#admm-case').select_option(case['id'])
        panel = p.locator(selector)
        original = panel.evaluate('e=>e.outerHTML')
        baseline = panel.evaluate(STATIC)
        validate_static(case,radius,baseline)
        for name,code in STATIC_FAULTS.items():
            panel.evaluate('p=>{'+code+'}')
            try:
                validate_static(case,radius,panel.evaluate(STATIC))
            except RuntimeError:
                rejected.append(name)
            else:
                raise RuntimeError('Undetected real DOM fault: '+name)
            panel.evaluate('(e,html)=>e.outerHTML=html',original)
        for name,(k,code) in FRAME_FAULTS.items():
            # A fresh positive baseline prevents a retained style fault from
            # making a later, unrelated mutation appear to have been detected.
            p.reload()
            p.locator('#admm-case').select_option(case['id'])
            panel = p.locator(selector)
            validate_frames(case,radius,float(baseline['primal'][0]['height']),panel.evaluate(FRAMES,[k]),[k])
            hook='()=>{const p=document.querySelector('+json.dumps(selector)+');'+code+'}'
            p.evaluate('()=>{window.admmFault='+hook+';document.getElementById("admm-step").addEventListener("input",window.admmFault);}')
            try:
                validate_frames(case,radius,float(baseline['primal'][0]['height']),panel.evaluate(FRAMES,[k]),[k])
            except RuntimeError:
                rejected.append(name)
            else:
                raise RuntimeError('Undetected real DOM fault: '+name)
            finally:
                p.evaluate('document.getElementById("admm-step").removeEventListener("input",window.admmFault)')
        for name,code in OVERVIEW_FAULTS.items():
            p.reload()
            validate_overview(data,p.evaluate(OVERVIEW))
            p.evaluate('()=>{'+code+'}')
            try:
                validate_overview(data,p.evaluate(OVERVIEW))
            except RuntimeError:
                rejected.append(name)
            else:
                raise RuntimeError('Undetected real DOM fault: '+name)
        browser.close()
    require(len(rejected)==len(STATIC_FAULTS)+len(FRAME_FAULTS)+len(OVERVIEW_FAULTS),'mutation coverage differs')
    args.output.write_text(json.dumps(dict(rejected=rejected,scope=f'{len(rejected)} named actual-DOM corruptions; not general mutation coverage'),indent=2)+'\n')
    print(json.dumps(dict(rejected=rejected)))


if __name__=='__main__':
    main()
