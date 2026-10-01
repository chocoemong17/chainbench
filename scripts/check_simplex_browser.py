"""Optional offline browser checks for all twelve Frank–Wolfe geometry cases."""
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
    url = args.html.resolve().as_uri()
    evidence = {'viewports': [], 'network_requests': [], 'javascript_errors': []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        evidence['browser'] = browser.version
        for width in (1440, 390):
            context = browser.new_context(viewport={'width': width, 'height': 1000}, offline=True)
            page = context.new_page()
            page.on('pageerror', lambda error: evidence['javascript_errors'].append(str(error)))
            page.on('request', lambda request: evidence['network_requests'].append(request.url)
                    if request.url.startswith(('https:', 'http:')) else None)
            page.goto(url)
            record = json.loads(page.locator('#chainbench-evidence').text_content())
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('[data-fw-case]').count() == 12
            segment_frames = segment_points = 0
            for i, case in enumerate(record['cases']):
                panel = page.locator(f'[data-fw-case="{case["id"]}"]')
                if i:
                    page.locator(f'#{case["id"]} > summary').click()
                slider = panel.locator('input[type=range]')
                slider.focus()
                slider.press('Home')
                expect(panel.locator('[data-step]')).to_have_text('k = 0 → 1')
                assert f'e{case["rows"][0]["vertex_index"]+1}' in panel.locator('[data-oracle]').inner_text()
                if i == 0:
                    panel.locator('.fw-certificate-grid').screenshot(path=str(args.output/f'certificate-{width}.png'))
                slider.press('ArrowRight')
                k = min(1, record['parameters']['steps']-1)
                expect(panel.locator('[data-step]')).to_have_text(f'k = {k} → {k+1}')
                for marker in panel.locator('[data-marker]').all():
                    expected = marker.get_attribute('data-frames').split('|')[k].split(',')
                    assert [marker.get_attribute(a) for a in ('cx', 'cy')] == expected
                assert panel.locator('[data-fw-history]').evaluate_all(
                    '(els, n) => els.every(el => el.getAttribute("points").split(" ").length === n)', k+1)
                if i == 0:
                    panel.locator('.visual-grid').screenshot(path=str(args.output/f'geometry-{width}.png'))
                slider.press('End')
                # Check every displayed certificate directly against the raw scalar values.
                stats = panel.evaluate('''(panel,c) => {
                  const slider=panel.querySelector('input[type=range]');
                  const close=(a,b,tol=.00051)=>{a=Number(a);if(!Number.isFinite(a)||!Number.isFinite(b)||Math.abs(a-b)>tol)throw Error('geometry coordinate mismatch');};
                  const plots=panel.querySelectorAll('[data-fw-certificate]');
                  if(plots.length!==2)throw Error('missing certificate diagrams');
                  let frames=0,points=0;
                  const matchPoints=(el,expected)=>{
                    if(!el)throw Error('missing segment path');
                    const actual=el.getAttribute('points').trim().split(/\\s+/).map(p=>p.split(',').map(Number));
                    if(actual.length!==expected.length)throw Error('segment path length');
                    actual.forEach((xy,i)=>{if(xy.length!==2)throw Error('segment point dimension');xy.forEach((v,j)=>close(v,expected[i][j],.0000051));});
                    points+=actual.length;
                  };
                  let lo,hi;
                  if(c.rows[0].segment){
                    const profiles=c.rows.slice(0,-1).map(r=>r.segment);
                    lo=Math.min(...profiles.flatMap(p=>p.affine));hi=Math.max(...profiles.flatMap(p=>p.objective));
                    const span=hi-lo||1;lo-=.06*span;hi+=.06*span;
                  }
                  for(let k=0;k<c.rows.length-1;k++){
                    slider.value=String(k);slider.dispatchEvent(new Event('input',{bubbles:true}));
                    const row=c.rows[k],cert=row.certificate;
                    for(const svg of plots){
                      const lo=Number(svg.dataset.yMin),hi=Number(svg.dataset.yMax);
                      const y=v=>306-220*(v-lo)/(hi-lo);
                      for(const dot of svg.querySelectorAll('[data-affine-vertex]'))
                        close(dot.getAttribute('cy'),y(cert.affine_vertices[Number(dot.dataset.affineVertex)]));
                      const oracle=svg.querySelector('[data-affine-oracle]');
                      if(oracle){close(oracle.getAttribute('cx'),132+132*row.vertex_index);close(oracle.getAttribute('cy'),y(cert.lower));}
                      for(const dot of svg.querySelectorAll('[data-certificate-end]'))
                        close(dot.getAttribute('cy'),y(cert[dot.dataset.certificateEnd]));
                      const span=svg.querySelector('[data-certificate-span]');
                      if(span){close(span.getAttribute('y1'),y(cert.upper));close(span.getAttribute('y2'),y(cert.lower));}
                    }
                    const label=panel.querySelector('[data-certificate-interval]').textContent;
                    if(!label.includes(cert.lower.toExponential(5)+' ≤ f* ≤ '+cert.upper.toExponential(5))
                       ||!label.includes('width = g_FW = '+row.dual_gap.toExponential(5))||!label.endsWith('k = '+k))
                      throw Error('certificate readout mismatch');
                    const fmt=x=>x.map(v=>Number(v.toPrecision(5))).join(', ');
                    if(!panel.querySelector('[data-certificate-values]').textContent.includes('('+fmt(cert.affine_vertices)+')'))
                      throw Error('affine readout mismatch');
                    if(row.segment){
                      const p=row.segment,svg=panel.querySelector('.fw-segment-figure svg');
                      if(!svg)throw Error('missing scalar segment figure');
                      const project=(g,v)=>[86+460*g,302-210*(v-lo)/(hi-lo)];
                      const curves=[...svg.querySelectorAll('[data-segment-curve]')];
                      if(curves.length!==2||new Set(curves.map(e=>e.dataset.segmentCurve)).size!==2)throw Error('segment curve coverage');
                      for(const el of curves)matchPoints(el,p.parameter.map((g,i)=>project(g,p[el.dataset.segmentCurve][i])));
                      const markers=[...svg.querySelectorAll('[data-segment-marker]')];
                      if(markers.length!==3||new Set(markers.map(e=>e.dataset.segmentMarker)).size!==3)throw Error('segment marker coverage');
                      for(const el of markers){
                        const j={current:0,scheduled:p.scheduled_index,minimum:p.minimum_index}[el.dataset.segmentMarker],xy=project(p.parameter[j],p.objective[j]);
                        close(el.getAttribute('cx'),xy[0],.0000051);close(el.getAttribute('cy'),xy[1],.0000051);points++;
                      }
                      const spaces=[...panel.querySelectorAll('[data-fw-space]')];
                      if(spaces.length!==2||new Set(spaces.map(e=>e.dataset.fwSpace)).size!==2)throw Error('segment space coverage');
                      for(const space of spaces){
                        const surface=space.dataset.fwSpace==='surface';
                        const project=(x,f)=>{const u=x[1]+.5*x[2],v=Math.sqrt(3)/2*x[2];return surface?[90+380*u-80*v,435-170*v-240*f]:[70+420*u,440-420*v];};
                        const markers=space.querySelectorAll('[data-segment-marker="minimum"]');
                        if(markers.length!==1)throw Error('missing segment minimum marker');
                        const xy=project(p.minimum_point,p.minimum_value);
                        close(markers[0].getAttribute('cx'),xy[0],.0000051);close(markers[0].getAttribute('cy'),xy[1],.0000051);points++;
                        if(surface){
                          const rays=space.querySelectorAll('[data-segment-ray]');
                          if(rays.length!==1)throw Error('missing surface ray');
                          matchPoints(rays[0],p.points.map((x,i)=>project(x,p.objective[i])));
                        }
                      }
                      const fmt6=v=>Number(v.toPrecision(6)).toString();
                      const expected=`k=${k} · γ=${fmt6(row.gamma)} · γ_min=${fmt6(p.minimum_gamma)} · f(current)=${fmt6(row.gap)} · f(actual next)=${fmt6(c.rows[k+1].gap)} · f(segment min)=${fmt6(p.minimum_value)}`;
                      if(panel.querySelector('[data-segment-values]').textContent!==expected)throw Error('segment readout mismatch');
                      frames++;
                    }
                  }
                  for(const svg of plots)for(const t of svg.querySelectorAll('text')){
                    const b=t.getBBox();if(b.x<0||b.y<0||b.x+b.width>520||b.y+b.height>390)throw Error('certificate text clipped');
                  }
                  for(const svg of panel.querySelectorAll('.fw-segment-figure svg'))for(const t of svg.querySelectorAll('text')){
                    const b=t.getBBox(),v=svg.viewBox.baseVal;if(b.x<0||b.y<0||b.x+b.width>v.width||b.y+b.height>v.height)throw Error('segment text clipped');
                  }
                  return {frames,points};
                }''', case)
                segment_frames += stats['frames']
                segment_points += stats['points']
                if 'segment_geometry' in record:
                    increases = [k for k,(row,nxt) in enumerate(zip(case['rows'],case['rows'][1:])) if nxt['gap']>row['gap']+1e-12]
                    button = panel.locator('[data-segment-increase]')
                    if increases:
                        button.click()
                        assert int(slider.input_value()) == increases[0]
                    else:
                        assert button.count() == 0
                    if i == 0:
                        if width == 390:
                            figure = panel.locator('.fw-segment-figure')
                            assert figure.evaluate('el=>el.scrollWidth>el.clientWidth')
                            figure.focus()
                            figure.press('ArrowRight')
                            page.wait_for_function('el=>el.scrollLeft>0', arg=figure.element_handle())
                            figure.evaluate('el=>el.scrollLeft=0')
                            expect(panel.locator('.fw-segment-scroll-cue')).to_be_visible()
                        panel.locator('.fw-segment').screenshot(path=str(args.output/f'segment-{width}.png'))
                        panel.locator('.visual-grid').screenshot(path=str(args.output/f'segment-geometry-{width}.png'))
                if i:
                    page.locator(f'#{case["id"]} > summary').click()
            panel = page.locator('[data-fw-case="interior-e1"]')
            panel.locator('input[type=range]').press('End')
            panel.locator('[data-play]').click()
            expect(panel.locator('[data-play]')).to_have_attribute('aria-pressed', 'true')
            if record['parameters']['steps'] == 1:
                expect(panel.locator('[data-step]')).to_have_text('k = 0 → 1')
                expect(panel.locator('[data-play]')).to_have_attribute('aria-pressed', 'false')
            else:
                expect(panel.locator('[data-step]')).not_to_have_text('k = 0 → 1')
                if panel.locator('[data-play]').get_attribute('aria-pressed') == 'true':
                    panel.locator('[data-play]').click()
            assert panel.locator('[data-play]').get_attribute('aria-pressed') == 'false'
            previous = page.locator('html').get_attribute('lang')
            page.locator('[data-action="language"]').click()
            assert page.locator('html').get_attribute('lang') != previous
            page.locator('[data-action="language"]').click()
            page.locator('#chainbench-evidence').locator('..').locator('summary').click()
            with page.expect_download() as download_info:
                page.locator('[data-download="chainbench-evidence"]').click()
            dest = args.output/f'download-{width}.json'
            download_info.value.save_as(dest)
            assert json.loads(dest.read_text(encoding='utf8')) == record
            page.locator('#chainbench-evidence').locator('..').locator('summary').click()
            page.screenshot(path=str(args.output/f'page-{width}.png'), full_page=True)
            evidence['viewports'].append({'width': width, 'all_cases': 12, 'overflow': False,
                                          'keyboard': 'passed', 'markers': 'matched',
                                          'certificate_steps': 12*record['parameters']['steps'],
                                          'certificate_coordinates_and_readouts': 'matched',
                                          'segment_frames': segment_frames, 'segment_points': segment_points,
                                          'playback': 'passed', 'download': 'matched'})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        page.goto(url)
        panel = page.locator('[data-fw-case="interior-e1"]')
        assert panel.locator('svg').count() == (6 if 'segment_geometry' in record else 5)
        if 'segment_geometry' in record:
            assert panel.locator('.fw-segment-figure svg').is_visible()
            if panel.locator('[data-segment-increase]').count():
                assert panel.locator('[data-segment-increase]').is_hidden()
            panel.locator('.fw-segment details > summary').click()
            assert panel.locator('[data-segment-row]').count() == record['parameters']['steps']
            assert all(row.is_visible() for row in panel.locator('[data-segment-row]').all())
        assert panel.locator('[data-certificate-interval]').inner_text().endswith('k = 0')
        assert panel.locator('input[type=range]').is_hidden()
        assert len(panel.locator('[data-fw-history]').first.get_attribute('points').split()) == len(record['cases'][0]['rows'])
        page.locator('#edge-e1 > summary').click()
        assert page.locator('#edge-e1 svg').first.is_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(args.output/'no-script.png'), full_page=True)
        evidence['no_script'] = 'complete static paths and native details remain readable'
        context.close()
        browser.close()
    assert not evidence['network_requests'], evidence['network_requests']
    assert not evidence['javascript_errors'], evidence['javascript_errors']
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
