"""Verify the generated reading path and all local report links without a network."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def assert_table_notation(page):
    """Keep authored mathematical case, including hidden iteration tables."""
    result = page.locator('th, th *').evaluate_all('''nodes => ({
      count: nodes.length,
      changed: nodes.filter(n => getComputedStyle(n).textTransform !== 'none')
        .map(n => ({text: n.textContent.slice(0, 80),
                    transform: getComputedStyle(n).textTransform}))
    })''')
    assert not result['changed'], ('table notation changes case', page.url, result['changed'][:8])
    return result['count']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tour', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((args.tour/'manifest.json').read_text(encoding='utf8'))
    extensions = manifest.get('extensions', [])
    extended = 'fista-wavelet' in extensions
    randomized = 'kaczmarz-expectation' in extensions
    sampling = 'kaczmarz-sampling' in extensions
    spectrum = 'cg-spectrum' in extensions
    adam = 'reddi-2018' in extensions
    admm = 'admm-lasso' in extensions
    backtracking = 'fista-backtracking' in extensions
    url = (args.tour/'index.html').resolve().as_uri()
    evidence = {'viewports': [], 'network_requests': [], 'javascript_errors': []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        evidence['browser'] = browser.version
        for width in (1440, 390):
            context = browser.new_context(viewport={'width': width, 'height': 1000}, offline=True)
            page = context.new_page()
            page.on('pageerror', lambda e: evidence['javascript_errors'].append(str(e)))
            page.on('request', lambda r: evidence['network_requests'].append(r.url)
                    if r.url.startswith(('http:', 'https:')) else None)
            page.goto(url)
            table_labels = {'index.html': assert_table_notation(page)}
            assert page.locator('img').count() == (10 if extended else 8)+int(randomized)+int(sampling)+int(spectrum)+int(adam)+int(admm)+int(backtracking)
            assert page.locator('img').evaluate_all('(els)=>els.every(e=>e.complete&&e.naturalWidth>0)')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.screenshot(path=str(args.output/f'index-{width}.png'), full_page=True)
            page.locator('#image-experiment').screenshot(path=str(args.output/f'image-experiment-{width}.png'))
            page.locator('#counterexample').screenshot(path=str(args.output/f'counterexample-{width}.png'))
            page.locator('#geometry').screenshot(path=str(args.output/f'geometry-{width}.png'))
            page.locator('#quadratic').screenshot(path=str(args.output/f'quadratic-{width}.png'))
            page.locator('#breadth').screenshot(path=str(args.output/f'breadth-{width}.png'))
            if extended:
                page.locator('#regularized-image').screenshot(path=str(args.output/f'wavelet-{width}.png'))
                page.locator('#sparse-attainment').screenshot(path=str(args.output/f'sparsity-{width}.png'))
            if randomized:
                page.locator('#randomized').screenshot(path=str(args.output/f'randomized-{width}.png'))
            if sampling:
                page.locator('#sampling').screenshot(path=str(args.output/f'sampling-{width}.png'))
            if spectrum:
                page.locator('#cg-spectrum').screenshot(path=str(args.output/f'cg-spectrum-{width}.png'))
            if adam:
                page.locator('#online-regret').screenshot(path=str(args.output/f'online-regret-{width}.png'))
            if admm:
                from smoke_admm_tour import validate_admm_tour_presentation
                validate_admm_tour_presentation(args.tour)
                guide = page.locator('#variable-splitting')
                expect(guide.locator('[data-split-method]')).to_have_count(2)
                expect(guide.locator('[data-split-meaning]')).to_have_count(5)
                guide.screenshot(path=str(args.output/f'variable-splitting-{width}.png'))
                if width==390:
                    scroll = guide.locator('.split-bridge .scroll')
                    scroll.focus()
                    scroll.press('ArrowRight')
                    page.wait_for_timeout(200)
                    assert scroll.evaluate('e=>e.scrollLeft>0')
            if backtracking:
                from smoke_backtracking_tour import validate_backtracking_tour_presentation
                validate_backtracking_tour_presentation(args.tour)
                guide = page.locator('#step-selection')
                expect(guide.locator('[data-backtracking-flow]')).to_have_count(2)
                expect(guide.locator('[data-backtracking-meaning]')).to_have_count(7)
                for language in ('ko','en'):
                    expect(page.locator('html')).to_have_attribute('lang',language)
                    guide.screenshot(path=str(args.output/f'step-selection-{language}-{width}.png'))
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    page.locator('[data-action="language"]').click()
                if width==390:
                    scroll = guide.locator('.bt-bridge .scroll')
                    scroll.focus()
                    scroll.press('ArrowRight')
                    page.wait_for_timeout(200)
                    assert scroll.evaluate('e=>e.scrollLeft>0')
            for artifact in manifest['artifacts']:
                filename = artifact['path']
                if filename == 'index.html':
                    continue
                # The comparison table can offer additional links to the same
                # report; follow each primary card (or stress table row) here.
                selector = 'a' if filename.startswith('stress-') else 'a.tour-card'
                link = page.locator(selector+'[href="'+filename+'"]')
                expect(link).to_have_count(1)
                link.click()
                page.wait_for_url('**/'+filename, wait_until='load')
                expect(page.locator('#chainbench-evidence')).to_have_count(1)
                table_labels[filename] = assert_table_notation(page)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert page.url.endswith('/'+filename)
                if filename == 'stress-ista-vs-fista.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert [r['seed'] for r in record['rows']] == list(range(32))
                    assert record['rows'][24]['status'] == 'unresolved'
                    assert record['rows'][24]['metric'] is None
                if backtracking and filename in ('proximal.html','atlas.html','backtracking.html'):
                    target = 'proximal.html' if filename=='backtracking.html' else 'backtracking.html'
                    page.locator('[data-tour-backtracking]').click()
                    page.wait_for_url('**/'+target,wait_until='load')
                    page.locator('[data-tour-backtracking-guide]').click()
                    page.wait_for_url('**/index.html#step-selection',wait_until='load')
                    expect(page.locator('[data-backtracking-comparison]')).to_be_visible()
                    page.locator(f'a.tour-card[href="{filename}"]').click()
                    page.wait_for_url('**/'+filename,wait_until='load')
                if filename=='backtracking.html':
                    from check_fista_backtracking_browser import FRAMES as BT_FRAMES
                    from check_fista_backtracking_browser import STATIC as BT_STATIC
                    from check_fista_backtracking_browser import validate_frame as validate_bt_frame
                    from check_fista_backtracking_browser import (
                        validate_static as validate_bt_static,
                    )
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps']==18 and len(record['cases'])==36
                    states = 0
                    for i,case in enumerate(record['cases']):
                        page.select_option('#bt-case',str(i))
                        panel = page.locator('[data-bt-case]').nth(i)
                        expect(panel).to_be_visible()
                        validate_bt_static(case,panel.evaluate(BT_STATIC))
                        frames = panel.evaluate(BT_FRAMES)
                        expected = [(step['iteration'],trial['attempt']) for step in case['stages'] for trial in step['trials']]
                        assert len(frames)==len(expected)
                        for frame,(k,j) in zip(frames,expected):
                            validate_bt_frame(case,frame,k,j)
                        states += len(frames)
                    evidence.setdefault('backtracking_trials',[]).append({'width':width,'cases':36,'states':states})
                    page.locator('#bt-step').focus()
                    page.locator('#bt-step').press('Home')
                    page.locator('#bt-step').press('ArrowRight')
                    expect(page.locator('#bt-step')).to_have_value('2')
                    page.locator('[data-tour-lesson]').click()
                    page.wait_for_url('**/atlas.html#beck-teboulle-2009',wait_until='load')
                if admm and filename in ('proximal.html','atlas.html'):
                    page.locator('[data-tour-splitting]').click()
                    page.wait_for_url('**/admm.html',wait_until='load')
                    page.locator('[data-tour-splitting]').click()
                    page.wait_for_url('**/proximal.html',wait_until='load')
                    if filename=='atlas.html':
                        page.locator('[data-tour-home]').click()
                        page.locator('a.tour-card[href="atlas.html"]').click()
                        page.wait_for_url('**/atlas.html',wait_until='load')
                if filename=='admm.html':
                    from admm_overview_audit import SNAPSHOT as OVERVIEW
                    from admm_overview_audit import validate_overview
                    from check_admm_browser import FRAMES, STATIC, validate_frames, validate_static
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps']==60 and len(record['cases'])==36
                    validate_overview(record,page.evaluate(OVERVIEW))
                    for selected in ('coupled-lambda0.1-zero-rho1','coupled-lambda1.1-zero-rho1'):
                        page.locator(f'[data-admm-overview-link="{selected}"]').click()
                        expect(page.locator('#admm-case')).to_have_value(selected)
                        expect(page.locator('#admm-step')).to_have_value('60')
                        case = next(c for c in record['cases'] if c['id']==selected)
                        panel = page.locator('[data-admm-case]:visible')
                        radius = record['geometry']['primal_bounds'][1]
                        static = panel.evaluate(STATIC)
                        validate_static(case,radius,static)
                        iterations = [0,1,2,30,60]
                        validate_frames(case,radius,float(static['primal'][0]['height']),panel.evaluate(FRAMES,iterations),iterations)
                    assert case['rows'][1]['stable_gap_z']==0 and not case['rows'][1]['stopping_passed']
                    slider = page.locator('#admm-step')
                    slider.focus()
                    slider.press('Home')
                    expect(page.locator('#admm-step-label')).to_have_text('k = 0')
                    slider.press('ArrowRight')
                    expect(page.locator('#admm-step-label')).to_have_text('k = 1')
                    slider.press('End')
                    expect(page.locator('#admm-step-label')).to_have_text('k = 60')
                    page.locator('[data-tour-splitting-guide]').click()
                    page.wait_for_url('**/index.html#variable-splitting',wait_until='load')
                    expect(page.locator('[data-splitting-comparison]')).to_be_visible()
                    page.locator('a.tour-card[href="admm.html"]').click()
                    page.wait_for_url('**/admm.html',wait_until='load')
                if adam and filename in ('heavy-ball.html','atlas.html'):
                    page.locator('[data-tour-regret]').click()
                    page.wait_for_url('**/adam.html',wait_until='load')
                    page.locator('[data-tour-regret]').click()
                    page.wait_for_url('**/heavy-ball.html',wait_until='load')
                    if filename=='atlas.html':
                        page.locator('[data-tour-home]').click()
                        page.locator('a.tour-card[href="atlas.html"]').click()
                        page.wait_for_url('**/atlas.html',wait_until='load')
                if filename=='adam.html':
                    from check_adam_counterexample_browser import SNAPSHOT, validate_snapshot
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps']==3000 and len(record['cases'])==9
                    page.locator('[data-adam-select]').select_option('c3-a0.1')
                    rounds = [1,2,3,4,30,3000]
                    validate_snapshot(record['cases'][0],page.evaluate(SNAPSHOT,rounds),rounds,
                                      require_cycles=page.locator('#cycle-inspector').count()>0)
                    assert -.25<record['cases'][0]['runs']['amsgrad']['observations']['final_x']<-.24
                    slider = page.locator('[data-adam-round]')
                    slider.focus()
                    slider.press('Home')
                    slider.press('ArrowRight')
                    expect(page.locator('[data-adam-label]')).to_have_text('t=2 / 3000')
                    slider.press('End')
                    expect(page.locator('[data-adam-label]')).to_have_text('t=3000 / 3000')
                    page.locator('[data-tour-regret]').click()
                    page.wait_for_url('**/heavy-ball.html',wait_until='load')
                    page.locator('[data-tour-regret]').click()
                    page.wait_for_url('**/adam.html',wait_until='load')
                if spectrum and filename in ('shewchuk.html', 'atlas.html', 'stress-hestenes-stiefel-1952.html'):
                    page.locator('[data-tour-spectrum]').click()
                    page.wait_for_url('**/cg-spectrum.html', wait_until='load')
                    page.locator('[data-tour-spectrum]').click()
                    page.wait_for_url('**/shewchuk.html', wait_until='load')
                if filename == 'cg-spectrum.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps']==32 and len(record['cases'])==18
                    page.locator('[data-cg-case-select]').select_option('spread-hadamard-single-mode')
                    panel = page.locator('[data-cg-case="spread-hadamard-single-mode"]')
                    assert panel.locator('[data-cg-frame]').count()==2
                    slider = panel.locator('[data-cg-step]')
                    slider.focus()
                    slider.press('End')
                    expect(panel.locator('[data-cg-frame="1"]')).to_be_visible()
                    page.locator('[data-tour-spectrum]').click()
                    page.wait_for_url('**/shewchuk.html', wait_until='load')
                    page.locator('[data-tour-spectrum]').click()
                    page.wait_for_url('**/cg-spectrum.html', wait_until='load')
                    page.locator('[data-tour-lesson]').click()
                    page.wait_for_url('**/atlas.html#hestenes-stiefel-1952', wait_until='load')
                if filename == 'deblur.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps'] == 10000
                    page.locator('[data-tour-related]').click()
                    target = 'wavelet.html' if extended else 'proximal.html'
                    page.wait_for_url('**/'+target, wait_until='load')
                    assert page.url.endswith('/'+target)
                    page.locator('[data-tour-related]').click()
                    page.wait_for_url('**/deblur.html', wait_until='load')
                    assert page.url.endswith('/deblur.html')
                if filename == 'wavelet.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps'] == 200 and record['parameters']['seed'] == 0
                    assert record['problem']['f_star'] is None
                    page.locator('[data-wavelet-select]').select_option('100')
                    expect(page.locator('[data-wavelet-metrics="fista"]')).to_contain_text('k=100')
                    page.locator('[data-tour-related]').click()
                    page.wait_for_url('**/deblur.html', wait_until='load')
                if filename == 'fw-sparsity.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps'] == 40
                    page.locator('[data-sparse-select]').select_option('3')
                    page.locator('[data-sparse-slider]').evaluate('(el)=>{el.value="3";el.dispatchEvent(new Event("input",{bubbles:true}));}')
                    expect(page.locator('[data-sparse-case="3"] [data-sparse-readout]')).to_contain_text('not applicable (s=n)')
                    page.locator('[data-tour-related]').click()
                    page.wait_for_url('**/simplex.html', wait_until='load')
                    page.locator('[data-tour-related]').click()
                    page.wait_for_url('**/fw-sparsity.html', wait_until='load')
                    if randomized:
                        page.locator('[data-tour-probability]').click()
                        page.wait_for_url('**/kaczmarz.html', wait_until='load')
                if filename == 'kaczmarz.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps']==40 and record['parameters']['trials']==64
                    assert [r['seed'] for r in record['cases'][0]['runs']]==list(range(64))
                    page.locator('[data-rk-select]').select_option('one-in-eight')
                    page.locator('[data-rk-slider]').evaluate('(el)=>{el.value="40";el.dispatchEvent(new Event("input",{bubbles:true}));}')
                    expect(page.locator('[data-rk-case="one-in-eight"] [data-rk-readout]')).to_contain_text('k=40')
                    page.locator('[data-tour-related]').click()
                    page.wait_for_url('**/tight-gd.html', wait_until='load')
                    page.locator('[data-tour-probability]').click()
                    page.wait_for_url('**/kaczmarz.html', wait_until='load')
                    if sampling:
                        page.locator('[data-tour-sampling]').click()
                        page.wait_for_url('**/sampling.html', wait_until='load')
                        page.locator('[data-tour-sampling]').click()
                        page.wait_for_url('**/kaczmarz.html', wait_until='load')
                if filename == 'sampling.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps']==15000
                    assert [c['seed'] for c in record['cases']]==[0,1,2]
                    assert record['cases'][0]['conditioning']['theorem4_condition_upper'] is None
                    panel = page.locator('[data-sampling-case="seed-0"]')
                    panel.locator('[data-sampling-method]').select_option('cyclic')
                    panel.locator('[data-sampling-step]').select_option('100')
                    expect(panel.locator('[data-sampling-values]')).to_contain_text('cyclic · completed k=100')
                    page.locator('[data-tour-sampling]').click()
                    page.wait_for_url('**/kaczmarz.html', wait_until='load')
                if extended and filename in ('proximal.html', 'tight-gd.html'):
                    target = 'wavelet.html' if filename == 'proximal.html' else 'fw-sparsity.html'
                    page.locator('[data-tour-related]').click()
                    page.wait_for_url('**/'+target, wait_until='load')
                if filename == 'heavy-ball.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['parameters']['steps'] == 50 and len(record['cases']) == 9
                    page.locator('[data-tour-related]').click()
                    page.wait_for_url('**/atlas.html#polyak-1964', wait_until='load')
                    assert page.locator('#polyak-1964').is_visible()
                if filename == 'landscape.html':
                    record = json.loads(page.locator('#chainbench-evidence').text_content())
                    assert record['steps'] == 18 and len(record['methods']) == 5
                    assert 'last computed' in page.locator('[data-landscape-readout="cg"]').inner_text()
                    page.locator('[data-tour-related]').click()
                    page.wait_for_url('**/heavy-ball.html', wait_until='load')
                page.locator('[data-tour-home]').click()
                assert page.url == url
            # Every topic-specific card must open an artifact that is in this exact bundle.
            atlas_url = (args.tour/'atlas.html').resolve().as_uri()
            page.goto(atlas_url)
            atlas = json.loads(page.locator('#chainbench-evidence').text_content())
            available = {a['path'] for a in manifest['artifacts']}
            opened = 0
            for topic, cards in atlas['workflow_guides']['topics'].items():
                for card in cards:
                    locator = page.locator(f'#{topic} [data-workflow="{card["id"]}"]')
                    if card['report'] not in available:
                        assert locator.locator('[data-workflow-link]').count() == 0
                        continue
                    locator.locator('[data-workflow-link]').click()
                    page.wait_for_url('**/'+card['report'], wait_until='load')
                    expect(page.locator('#chainbench-evidence')).to_have_count(1)
                    page.locator('[data-tour-lesson]').click()
                    page.wait_for_url('**/atlas.html#*', wait_until='load')
                    target = page.url.rsplit('#',1)[1]
                    expect(page.locator('#'+target)).to_be_visible()
                    opened += 1
            assert opened == (25 if extended else 22)
            page.locator('#beck-teboulle-2009 .workflow-paths').screenshot(path=str(args.output/f'atlas-paths-{width}.png'))
            page.goto(url)
            page.locator('[data-action="language"]').click()
            assert page.locator('html').get_attribute('lang') == 'en'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            evidence['viewports'].append({'width': width, 'reports_opened': len(manifest['artifacts'])-1,
                'return_links': 'passed', 'preview_images': 'loaded', 'all_seeds': 'retained',
                'unresolved_seed24': 'retained', 'language': 'passed', 'overflow': False})
            evidence['viewports'][-1]['atlas_workflow_links'] = opened
            evidence['viewports'][-1]['case_preserved_table_nodes'] = table_labels
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        page.goto(url)
        page.locator('a[href="shewchuk.html"]').click()
        assert page.locator('svg').first.is_visible()
        page.locator('[data-tour-home]').click()
        assert page.url == url
        page.locator('a[href="atlas.html"]').click()
        page.locator('#jaggi-2013 [data-workflow-link="simplex"]').click()
        assert page.locator('[data-tour-lesson]').is_visible()
        page.locator('[data-tour-lesson]').click()
        assert page.url.endswith('/atlas.html#jaggi-2013')
        page.locator('[data-tour-home]').click()
        if extended:
            cases = [('wavelet.html', '.deblur-outputs'), ('fw-sparsity.html', '.sparse-space')]
            if randomized:
                cases.append(('kaczmarz.html','[data-rk-cube]'))
            if sampling:
                cases.append(('sampling.html','[data-signal-low]'))
            if spectrum:
                cases.append(('cg-spectrum.html','[data-cg-overview] svg'))
            if adam:
                cases.append(('adam.html','[data-adam-case="c3-a0.1"] table:has([data-adam-native])'))
            if admm:
                cases.append(('admm.html','[data-admm-case="coupled-lambda0.1-zero-rho1"] [data-admm-primal="surface"]'))
            if backtracking:
                cases.append(('backtracking.html','[data-bt-case="lambda0.8-zero-L1"] svg'))
            for name, figure in cases:
                page.locator(f'a.tour-card[href="{name}"]').click()
                page.wait_for_url('**/'+name,wait_until='load')
                if name=='cg-spectrum.html':
                    page.locator('[data-cg-overview] summary').first.click()
                if name=='adam.html':
                    page.locator('[data-adam-case="c3-a0.1"] summary').first.click()
                    assert page.locator('[data-adam-case]').count()==9
                if name=='admm.html':
                    assert page.locator('[data-admm-case]').count()==36
                    panel = page.locator('[data-admm-case="coupled-lambda0.1-zero-rho1"]')
                    panel.locator('.admm-native > summary').click()
                    expect(panel.locator('[data-admm-native="0"]')).to_be_visible()
                if name=='backtracking.html':
                    expect(page.locator('[data-bt-case]')).to_have_count(36)
                    panel = page.locator('[data-bt-case="lambda0.8-zero-L1"]')
                    panel.locator('[data-bt-native-link]').click()
                    expect(page.locator('[id="bt-lambda0.8-zero-L1-k1-j0"]')).to_be_visible()
                    page.locator('[data-tour-backtracking-guide]').click()
                    page.wait_for_url('**/index.html#step-selection',wait_until='load')
                    expect(page.locator('[data-backtracking-comparison]')).to_be_visible()
                    page.locator('a.tour-card[href="backtracking.html"]').click()
                    page.wait_for_url('**/backtracking.html',wait_until='load')
                assert page.locator(figure).first.is_visible()
                page.locator('[data-tour-home]').click()
                assert page.url == url
        evidence['no_script'] = 'index, static figures and local navigation work'
        context.close()
        browser.close()
    assert not evidence['network_requests'], evidence['network_requests']
    assert not evidence['javascript_errors'], evidence['javascript_errors']
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
