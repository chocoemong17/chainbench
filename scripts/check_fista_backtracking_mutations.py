"""Inject actual DOM faults, retain each failure, and require all to be detected."""
import argparse
import json
from pathlib import Path

from check_fista_backtracking_browser import FRAME, STATIC, validate_frame, validate_static
from playwright.sync_api import sync_playwright

MUTATIONS = r'''el=>{
 const out=[];
 const snapshot=scope=>(scope==='static'?('''+STATIC+r'''):('''+FRAME+r'''))(el);
 function attribute(name,scope,selector,attribute,value){
  const node=el.querySelector(selector),before=node.getAttribute(attribute);
  node.setAttribute(attribute,value);out.push({name,scope,view:snapshot(scope)});
  if(before===null)node.removeAttribute(attribute);else node.setAttribute(attribute,before);
 }
 function text(name,scope,selector,value){
  const node=el.querySelector(selector),before=node.textContent;
  node.textContent=value;out.push({name,scope,view:snapshot(scope)});node.textContent=before;
 }
 function remove(name,scope,selector){
  const node=el.querySelector(selector),parent=node.parentNode,next=node.nextSibling;
  node.remove();out.push({name,scope,view:snapshot(scope)});parent.insertBefore(node,next);
 }
 attribute('accepted-path-coordinate','static','[data-bt-path]','points','1,2 3,4');
 attribute('surface-wire-missing-samples','static','[data-bt-wire]','points','1,2');
 attribute('wrong-optimum','static','[data-bt-star]','cx','999');
 attribute('wrong-contour-world','static','[data-bt-contour]','data-bt-world','[[0,0]]');
 attribute('native-row-target','static','[data-bt-native-row]','id','invented-row');
 text('native-decision','static','[data-bt-native-row] td:nth-child(9)','accepted');
 remove('missing-native-trial','static','[data-bt-native-row]');
 attribute('math-header-uppercase','static','th','style','text-transform:uppercase');
 attribute('selected-path-marker','frame','[data-bt-dynamic="x"]','transform','translate(0 0)');
 attribute('nonfinite-proposal-marker','frame','[data-bt-dynamic="proposal-selected"]','transform','translate(NaN 0)');
 attribute('model-curve-sample','frame','[data-bt-dynamic="objective_gap"]','points','1,2');
 attribute('wrong-model-candidate','frame','[data-bt-dynamic="candidate-Q"]','transform','translate(1 2)');
 text('wrong-proposal-number','frame','[data-bt-dynamic="proposal-number-0"]','8');
 text('hidden-negative-model-scale','frame','[data-bt-text="model-tick"]','0');
 text('wrong-displayed-gate','frame','[data-bt-gate]','F(q)−Q_L(q,y)=0 · raw F−Q=0 · 채택 / accepted');
 attribute('wrong-gate-status','frame','[data-bt-gate]','data-bt-accepted','true');
 attribute('wrong-native-link','frame','[data-bt-native-link]','href','#wrong');
 remove('missing-selected-anchor','frame','[data-bt-dynamic="anchor"]');
 return out;
}'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=dict(width=1440,height=1000))
        page.goto(args.html.resolve().as_uri(),wait_until='load')
        case = json.loads(page.locator('#chainbench-evidence').text_content())['cases'][0]
        el = page.locator('[data-bt-case]').first
        validate_static(case,el.evaluate(STATIC))
        validate_frame(case,el.evaluate(FRAME),1,0)
        mutations = el.evaluate(MUTATIONS)
        results = []
        for mutation in mutations:
            try:
                if mutation['scope']=='static':
                    validate_static(case,mutation['view'])
                else:
                    validate_frame(case,mutation['view'],1,0)
            except RuntimeError as error:
                results.append(dict(name=mutation['name'],detected=True,reason=str(error)))
            else:
                results.append(dict(name=mutation['name'],detected=False))
        validate_static(case,el.evaluate(STATIC))
        validate_frame(case,el.evaluate(FRAME),1,0)
        browser.close()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(results,indent=2)+'\n')
    if len(results)!=18 or not all(r['detected'] for r in results):
        raise RuntimeError('one or more actual DOM faults escaped detection')
    print(f'All {len(results)} actual DOM faults rejected; restored original passes.')


if __name__=='__main__':
    main()
