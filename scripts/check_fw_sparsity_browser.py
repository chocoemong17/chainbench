"""Verify every atom, repeated-support observation and 3D point, offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    evidence = dict(viewports=[], javascript_errors=[], network_requests=[])
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        evidence["browser"] = browser.version
        for width in (1440, 390):
            context = browser.new_context(viewport=dict(width=width, height=1000), offline=True)
            p = context.new_page()
            p.on("pageerror", lambda e: evidence["javascript_errors"].append(str(e)))
            p.on(
                "request",
                lambda r: (
                    evidence["network_requests"].append(r.url)
                    if r.url.startswith(("http:", "https:"))
                    else None
                ),
            )
            p.goto(args.html.resolve().as_uri())
            # Capture static evidence without smooth-scroll transitions.
            p.add_style_tag(content='html{scroll-behavior:auto!important}')
            record = json.loads(p.locator("#chainbench-evidence").text_content())
            assert p.evaluate("document.documentElement.scrollWidth<=innerWidth")
            for case in record["cases"]:
                n = case["dimension"]
                p.locator("[data-sparse-select]").select_option(str(n))
                panel = p.locator(f'[data-sparse-case="{n}"]')
                expect(panel).to_be_visible()
                assert p.locator("[data-sparse-case]:visible").count() == 1
                count = p.evaluate(
                    """n=>{
                 const data=JSON.parse(document.getElementById('chainbench-evidence').textContent),c=data.cases.find(x=>x.dimension===n),panel=document.querySelector('[data-sparse-case="'+n+'"]'),slider=document.querySelector('[data-sparse-slider]');
                 const near=(a,b)=>{if(Math.abs(Number(a)-b)>1e-5)throw new Error('coordinate mismatch '+a+' '+b);};
                 for(const r of c.rows){
                  slider.value=String(r.iteration);slider.dispatchEvent(new Event('input',{bubbles:true}));const upper=1.15*Math.max(...r.x);
                  for(const kind of ['actual','balanced']){
                   const values=kind==='actual'?r.x:r.balanced,base=kind==='actual'?175:355,bars=panel.querySelectorAll('[data-sparse-bar="'+kind+'"]');
                   if(bars.length!==n)throw new Error('missing bars');
                   bars.forEach((bar,i)=>{near(bar.getAttribute('height'),130*values[i]/upper);near(bar.getAttribute('y'),base-130*values[i]/upper);near(bar.getAttribute('x'),65+(i+.08)*660/n);});
                  }
                  const readout=panel.querySelector('[data-sparse-readout]').textContent;
                  if(!readout.includes('k='+r.iteration+' · support s='+r.support+'/'+n)||!readout.includes('f='+r.objective.toExponential(6)))throw new Error('wrong readout');
                  if((r.support===n)!==readout.includes('not applicable'))throw new Error('false dual bound');
                  const marker=panel.querySelector('[data-sparse-support-current]');near(marker.getAttribute('cx'),75+610*(r.support-1)/(n-1));near(marker.getAttribute('cy'),60+270*Math.log(1/r.objective)/Math.log(n));
                  if(n===3){
                   const project=x=>[120+360*(x[1]+.5*x[2])-70*Math.sqrt(3)/2*x[2],360-120*Math.sqrt(3)/2*x[2]-190*x.reduce((s,v)=>s+v*v,0)];
                   for(const [kind,x] of [['actual',r.x],['balanced',r.balanced]]){const marker=panel.querySelector('[data-sparse-point="'+kind+'"]'),pt=project(x);near(marker.getAttribute('cx'),pt[0]);near(marker.getAttribute('cy'),pt[1]);}
                   const pts=panel.querySelector('[data-sparse-path]').getAttribute('points').trim().split(' ');if(pts.length!==r.iteration+1)throw new Error('invented history');
                   pts.forEach((s,i)=>{const xy=s.split(','),expected=project(c.rows[i].x);near(xy[0],expected[0]);near(xy[1],expected[1]);});
                  }
                 }return c.rows.length;
                }""",
                    n,
                )
                charts = panel.locator(".plot svg")
                scatter = json.loads(charts.nth(0).locator("metadata").text_content())
                assert scatter["rows"] == [
                    {k: r[k] for k in ("iteration", "support", "objective")} for r in case["rows"]
                ]
                assert panel.locator("[data-sparse-observation]").count() == len(case["rows"])
                primal = json.loads(charts.nth(1).locator("metadata").text_content())
                assert primal["series"][0]["y"] == [r["primal_gap"] for r in case["rows"]]
                assert primal["series"][1]["y"] == [r["support_floor"] for r in case["rows"]]
                assert primal["series"][2]["x"] == list(range(1, case["updates"] + 1))
                assert primal["series"][2]["y"] == [
                    8 / (k + 2) for k in range(1, case["updates"] + 1)
                ]
                dual = json.loads(charts.nth(2).locator("metadata").text_content())
                assert dual["series"][0]["y"] == [r["dual_gap"] for r in case["rows"]]
                assert dual["series"][1]["x"] == [
                    r["iteration"] for r in case["rows"] if r["support"] < n
                ]
                assert dual["series"][1]["y"] == [
                    2 / r["support"] for r in case["rows"] if r["support"] < n
                ]
                assert panel.locator("svg").evaluate_all(
                    """svgs=>svgs.every(svg=>{const v=svg.getBoundingClientRect();return [...svg.querySelectorAll('text')].every(t=>{const b=t.getBoundingClientRect();return b.left>=v.left-.5&&b.right<=v.right+.5&&b.top>=v.top-.5&&b.bottom<=v.bottom+.5;});})"""
                )
                p.locator("[data-sparse-slider]").evaluate(
                    '(el,k)=>{el.value=String(k);el.dispatchEvent(new Event("input",{bubbles:true}));}',
                    min(2, case["updates"]),
                )
                panel.locator(".sparse-bars").screenshot(
                    path=str(args.output / f"bars-n{n}-{width}.png")
                )
                charts.nth(0).screenshot(path=str(args.output / f"support-n{n}-{width}.png"))
                if n == 3:
                    panel.locator(".sparse-space").screenshot(
                        path=str(args.output / f"space-{width}.png")
                    )
                evidence["viewports"].append(
                    dict(
                        width=width,
                        dimension=n,
                        verified_states=count,
                        bars="all coordinates",
                        curves="all observations including duplicate supports",
                        dual_full_support="no invented bound",
                    )
                )
            slider = p.locator("[data-sparse-slider]")
            slider.focus()
            slider.press("Home")
            slider.press("ArrowRight")
            expect(slider).to_have_value("1")
            p.locator("[data-sparse-play]").click()
            expect(p.locator("[data-sparse-play]")).to_have_attribute("aria-pressed", "true")
            p.wait_for_timeout(550)
            p.locator("[data-sparse-play]").click()
            assert int(slider.input_value()) >= min(2, record["parameters"]["steps"])
            old = p.locator("html").get_attribute("lang")
            p.locator('[data-action="language"]').click()
            assert p.locator("html").get_attribute("lang") != old
            p.locator('[data-action="language"]').click()
            p.locator("#chainbench-evidence").locator("..").locator("summary").click()
            with p.expect_download() as event:
                p.locator('[data-download="chainbench-evidence"]').click()
            path = args.output / f"download-{width}.json"
            event.value.save_as(path)
            assert json.loads(path.read_text()) == record
            context.close()
        context = browser.new_context(
            viewport=dict(width=390, height=1000), offline=True, java_script_enabled=False
        )
        p = context.new_page()
        p.goto(args.html.resolve().as_uri())
        assert p.locator(".sparse-controls").is_hidden()
        assert p.locator("[data-sparse-case]:visible").count() == 4
        assert p.locator("[data-sparse-case] tbody tr").count() == 4 * (
            record["parameters"]["steps"] + 1
        )
        assert p.evaluate("document.documentElement.scrollWidth<=innerWidth")
        p.locator('[data-sparse-case="3"] details > summary').click()
        expect(p.locator('[data-sparse-case="3"] tbody tr').last).to_be_visible()
        p.locator('[data-sparse-case="3"]').screenshot(path=str(args.output / "no-script.png"))
        context.close()
        browser.close()
    assert not evidence["javascript_errors"] and not evidence["network_requests"], evidence
    evidence["no_script"] = "all four cases, curves and complete tables available"
    (args.output / "browser-verification.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
