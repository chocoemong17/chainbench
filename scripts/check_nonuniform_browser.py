"""Offline controls and every plotted sampling state checked against embedded data."""

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
    evidence = dict(viewports=[], network_requests=[], javascript_errors=[])
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        evidence["browser"] = browser.version
        for width in (1440, 390):
            context = browser.new_context(viewport=dict(width=width, height=1000), offline=True)
            page = context.new_page()
            page.on("pageerror", lambda e: evidence["javascript_errors"].append(str(e)))
            page.on(
                "request",
                lambda r: (
                    evidence["network_requests"].append(r.url)
                    if r.url.startswith(("http:", "https:"))
                    else None
                ),
            )
            page.goto(args.html.resolve().as_uri())
            record = json.loads(page.locator("#chainbench-evidence").text_content())
            result = page.evaluate("""()=>{
              const d=JSON.parse(document.getElementById('chainbench-evidence').textContent);
              let states=0, points=0;
              const check=(value,message)=>{if(!value)throw Error(message);};
              const close=(a,b)=>Math.abs(Number(a)-b)<.000501;
              const panels=[...document.querySelectorAll('[data-sampling-case]')];
              check(panels.length===3,'case count');
              for(const [index,panel] of panels.entries()){
                const c=d.cases[index],svg=panel.querySelector('[data-signal-low]');
                check(panel.dataset.samplingCase===c.id,'case id');
                const all=[...c.truth_signal.real,...c.observed_samples.real,
                  ...Object.values(c.runs).flatMap(run=>run.snapshots.flatMap(s=>[
                    ...s.signal.real,...(s.last_projection?.signal_update?.previous_signal.real||[]),
                    ...(s.last_projection?.signal_update?.next_signal.real||[])]))];
                const minimum=Math.min(...all),maximum=Math.max(...all),pad=.06*(maximum-minimum);
                const lo=minimum-pad,hi=maximum+pad;
                check(Number(svg.dataset.signalLow)===lo&&Number(svg.dataset.signalHigh)===hi,'shared limits');
                const compare=(line,values)=>{
                  const xy=line.getAttribute('points').split(' ').map(p=>p.split(',').map(Number));
                  check(xy.length===513,'waveform length');
                  for(let j=0;j<513;j++){
                    check(close(xy[j][0],80+800*d.display_grid[j])&&close(xy[j][1],300-220*(values[j]-lo)/(hi-lo)),'waveform coordinates');points++;
                  }
                };
                compare(svg.querySelector('polyline'),c.truth_signal.real);
                const ms=panel.querySelector('[data-sampling-method]'),ks=panel.querySelector('[data-sampling-step]');
                for(const m of ['cyclic','uniform','weighted'])for(const s of c.runs[m].snapshots){
                  const k=s.iteration;ms.value=m;ms.dispatchEvent(new Event('change'));
                  ks.value=String(k);ks.dispatchEvent(new Event('change'));
                  compare(panel.querySelector('[data-sampling-prediction]'),s.signal.real);
                  const native=panel.querySelector('[data-sampling-gallery="'+m+'-'+k+'"]');
                  compare(native.querySelectorAll('polyline')[1],s.signal.real);
                  const marker=panel.querySelector('[data-picked-sample]');
                  check(marker.getAttribute('visibility')===(k?'visible':'hidden'),'initial marker');
                  if(k){const row=c.runs[m].rows[k-1];
                    check(row===s.last_projection.row,'actual selected row');
                    check(close(marker.getAttribute('cx'),80+800*c.nodes[row]),'marker x');
                    check(close(marker.getAttribute('cy'),300-220*(c.observed_samples.real[row]-lo)/(hi-lo)),'marker y');
                    check(panel.querySelector('[data-sampling-row]').textContent.includes('Last row '+row+' ·'),'row caption');
                  }
                  const caption=panel.querySelector('[data-sampling-values]').textContent;
                  check(caption.includes('completed k='+k+' ·'),'iteration caption');
                  check(caption.includes('error='+c.runs[m].error_l2[k].toExponential(6)),'error caption');
                  check(caption.includes('residual='+s.weighted_residual_l2.toExponential(6)),'residual caption');
                  if(d.projection_geometry){
                    const frames=panel.querySelectorAll('.projection-frame.is-current');
                    check(frames.length===1&&frames[0].dataset.projectionFrame===m+'-'+k,'projection state');
                    const frame=frames[0];check(frame.open,'projection frame closed');
                    if(!k)check(frame.querySelector('svg')===null,'initial projection fabricated');
                    else{
                      const u=s.last_projection.signal_update;
                      const mapping={before:u.previous_signal.real,after:u.next_signal.real,
                        kernel:u.normalized_kernel,actual:u.correction_signal.real,ideal:u.ideal_signal_correction.real};
                      const amp=Math.max(...u.correction_signal.real.map(Math.abs),...u.ideal_signal_correction.real.map(Math.abs));
                      const radius=amp?1.08*amp:1;
                      for(const curve of frame.querySelectorAll('[data-response-curve]')){
                        const axis=curve.closest('[data-response-axis]'),key=curve.dataset.responseCurve;
                        const low=Number(axis.dataset.low),high=Number(axis.dataset.high),top=Number(axis.dataset.top),height=Number(axis.dataset.height);
                        const expectedLimits=axis.dataset.responseAxis==='waveforms'?[lo,hi]:axis.dataset.responseAxis==='kernel'?[-.3,1.1]:[-radius,radius];
                        check(low===expectedLimits[0]&&high===expectedLimits[1],'projection scale');
                        const xy=curve.getAttribute('points').split(' ').map(p=>p.split(',').map(Number));
                        check(xy.length===u.grid.length,'projection curve length');
                        for(let j=0;j<xy.length;j++){
                          check(close(xy[j][0],80+800*u.grid[j])&&close(xy[j][1],top+height-height*(mapping[key][j]-low)/(high-low)),'projection curve coordinate');
                        }
                      }
                      check(u.grid[u.node_index]===s.last_projection.node&&u.normalized_kernel[u.node_index]===1,'sampled kernel center');
                      check(frame.querySelector('[data-response-readout]').textContent.includes('row '+s.last_projection.row+' ·'),'projection readout');
                    }
                  }
                  states++;
                }
                const probability=[...panel.querySelectorAll('[data-sampling-probability]')],top=Math.max(...c.probabilities)*1.08;
                check(probability.length===700,'probability count');
                for(let j=0;j<700;j++){
                  check(close(probability[j].getAttribute('x1'),80+800*c.nodes[j]),'probability node');
                  check(close(probability[j].getAttribute('y2'),280-190*c.probabilities[j]/top),'probability height');
                }
                const chart=JSON.parse(panel.querySelector('.plot metadata').textContent);
                for(const [i,m] of ['cyclic','uniform','weighted'].entries()){
                  check(JSON.stringify(chart.series[i].y)===JSON.stringify(c.runs[m].error_l2),'full error curve');
                  check(chart.series[i].x.every((v,k)=>v===k)&&chart.series[i].x.length===d.parameters.steps+1,'every update');
                }
              }
              check(document.documentElement.scrollWidth<=innerWidth,'page overflow');
              return {states,waveform_points:points,probabilities:2100};
            }""")
            panel = page.locator("[data-sampling-case]").first
            select = panel.locator("[data-sampling-step]")
            select.focus()
            select.press("Home")
            select.press("ArrowDown")
            expect(select).to_have_value("1")
            k = min(100, record["parameters"]["steps"])
            if k not in record["parameters"]["snapshot_iterations"]:
                k = record["parameters"]["snapshot_iterations"][-1]
            select.select_option(str(k))
            panel.locator("[data-sampling-method]").select_option("weighted")
            if "projection_geometry" in record:
                panel.locator("[data-projection-first]").click()
                expect(select).to_have_value("1")
                expect(panel.locator(".projection-frame.is-current")).to_have_attribute(
                    "data-projection-frame", "weighted-1"
                )
                select.select_option(str(k))
                panel.locator(".projection-frame.is-current svg").screenshot(
                    path=str(args.output / f"response-{width}.png")
                )
                assert panel.locator(".projection-frame.is-current svg").evaluate("""svg=>{
                    const v=svg.getBoundingClientRect();return [...svg.querySelectorAll('text')].every(t=>{
                        const b=t.getBoundingClientRect();return b.left>=v.left-.5&&b.top>=v.top-.5&&b.right<=v.right+.5&&b.bottom<=v.bottom+.5;
                    });}""")
            panel.locator(".sampling-figure").first.screenshot(
                path=str(args.output / f"waveform-{width}.png")
            )
            panel.locator(".plot").screenshot(path=str(args.output / f"curves-{width}.png"))
            panel.locator(".sampling-figure").nth(1).screenshot(
                path=str(args.output / f"probability-{width}.png")
            )
            assert page.locator(
                "[data-sampling-case] > .sampling-figure svg, .plot svg"
            ).evaluate_all("""svgs=>svgs.every(svg=>{
              const v=svg.getBoundingClientRect();return [...svg.querySelectorAll('text')].every(t=>{
                const b=t.getBoundingClientRect();return b.left>=v.left-.5&&b.top>=v.top-.5&&b.right<=v.right+.5&&b.bottom<=v.bottom+.5;
              });})""")
            old = page.locator("html").get_attribute("lang")
            page.locator('[data-action="language"]').click()
            assert page.locator("html").get_attribute("lang") != old
            page.locator('[data-action="language"]').click()
            appendix = page.locator("#chainbench-evidence").locator("..")
            appendix.locator(":scope > summary").click()
            with page.expect_download() as download:
                page.locator('[data-download="chainbench-evidence"]').click()
            destination = args.output / f"download-{width}.json"
            download.value.save_as(destination)
            assert json.loads(destination.read_text()) == record
            appendix.locator(":scope > summary").click()
            page.screenshot(path=str(args.output / f"page-{width}.png"), full_page=True)
            evidence["viewports"].append(
                dict(
                    width=width,
                    **result,
                    keyboard="passed",
                    labels="within SVG",
                    download="matched",
                    all_curves="matched",
                    overflow=False,
                )
            )
            context.close()
        context = browser.new_context(
            java_script_enabled=False, offline=True, viewport=dict(width=390, height=1000)
        )
        page = context.new_page()
        page.goto(args.html.resolve().as_uri())
        assert all(p.is_hidden() for p in page.locator(".sampling-controls").all())
        for panel in page.locator("[data-sampling-case]").all():
            gallery = panel.locator("[data-sampling-gallery-list]")
            if gallery.count() == 0:
                gallery = panel.locator(":scope > details").first
            gallery.locator(":scope > summary").click()
            assert gallery.locator("[data-sampling-gallery]").count() == 3 * len(
                record["parameters"]["snapshot_iterations"]
            )
            first = gallery.locator("[data-sampling-gallery]").first
            first.locator("summary").click()
            assert first.locator("svg").is_visible()
            if "projection_geometry" in record:
                assert panel.locator(".projection-frame").count() == 3 * len(
                    record["parameters"]["snapshot_iterations"]
                )
                initial = panel.locator('[data-projection-frame="weighted-0"]')
                initial.locator(":scope > summary").click()
                assert initial.locator("svg").count() == 0
                initial.locator(":scope > summary").click()
                response = panel.locator('[data-projection-frame="weighted-1"]')
                if response.get_attribute("open") is None:
                    response.locator(":scope > summary").click()
                assert response.locator("svg").is_visible()
            assert "Last row" in panel.locator("[data-sampling-row]").text_content()
            rows = panel.locator(":scope > details").last
            rows.locator(":scope > summary").click()
            assert rows.locator("tr").count() == 701
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
        page.screenshot(path=str(args.output / "no-script.png"), full_page=True)
        context.close()
        browser.close()
    assert not evidence["network_requests"] and not evidence["javascript_errors"], evidence
    evidence["no_script"] = (
        "native waveform gallery, all curves, all nodes/counts and current row visible"
    )
    (args.output / "browser-verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
