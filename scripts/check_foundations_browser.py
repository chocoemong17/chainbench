"""Audit computed SVGs, bilingual video decoding and actual input gestures in CI."""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import threading
from pathlib import Path

from check_adam_lesson_browser import QuietHandler
from check_visual_papers_browser import drag, seek
from playwright.sync_api import expect, sync_playwright


def audit(page):
    s=page.evaluate('window.foundationLesson')
    r=s['record']
    def value(id):
        return float(page.locator('#'+id).get_attribute('data-value'))
    if r['slug']=='backprop':
        row=r['trace'][s['parameter']]
        assert abs(value('output')-row['y'])<1e-12
        assert abs(value('loss')-row['loss'])<1e-12
        for point in page.locator('#second-chart circle[data-step]').all():
            step=int(point.get_attribute('data-step'))
            assert abs(float(point.get_attribute('cy'))-(326-(r['trace'][step]['y']-2)*120))<1e-10
    elif r['slug']=='cnn':
        maps=r['one'] if s['stride']==1 else r['stride2']
        output=maps[s['filter']]
        row,col=divmod(s['parameter'],len(output[0]))
        assert value('cell-value')==output[row][col]
        cells=page.locator('#first-chart [data-kind=output]').all()
        for i,cell in enumerate(cells):
            actual=cell.get_attribute('data-value')
            expected=output[i//len(output[0])][i%len(output[0])]
            assert actual=='unknown' if i>s['parameter'] else float(actual)==expected
        assert value('dense')==63*len(output)*len(output[0])*2
        assert value('shared')==18
    else:
        row=r['prediction'] if s['mode']=='prediction' else r['cases'][s['parameter']]
        for i in range(2):
            assert abs(value('score-'+str(i))-row['layers'][3][i])<1e-12
            bar=page.locator(f'[data-series=current][data-score="{i}"]')
            assert abs(float(bar.get_attribute('width'))-abs(row['layers'][3][i])*1070)<1e-9
        assert page.locator('[data-edge]').count()==50
        assert page.locator('circle[data-active=false]').count()==10-sum(row['mask1'])-sum(row['mask2'])


def set_slider(page,id,value):
    page.locator('#'+id).evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input",{bubbles:true}));}',value)
    audit(page)


def check(args):
    args.output.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(args.site.resolve())))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    origin=f'http://127.0.0.1:{server.server_port}'
    proof={'checks':[],'errors':[],'external_requests':[]}
    try:
        with sync_playwright() as pw:
            for engine in ('chromium','webkit'):
                browser=getattr(pw,engine).launch()
                for width in (1440,390):
                    for slug in ('backprop','cnn','dropout'):
                        context=browser.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce')
                        page=context.new_page()
                        page.on('pageerror',lambda e:proof['errors'].append(str(e)))
                        page.on('request',lambda r:proof['external_requests'].append(r.url) if not r.url.startswith(origin) else None)
                        assert page.goto(origin+f'/papers/{slug}/',wait_until='networkidle').status==200
                        page.wait_for_function('()=>Boolean(window.foundationLesson)')
                        expect(page.locator('html')).to_have_attribute('lang','en')
                        movie=page.locator('video')
                        assert movie.evaluate('v=>v.paused')
                        for lang in ('en','ko'):
                            if lang=='ko':
                                page.locator('#language').click()
                            page.wait_for_function('()=>{const v=document.querySelector("video");return v.readyState>=2;}')
                            record=page.evaluate('window.foundationLesson.record')
                            proof['source']=record['source']
                            assert abs(movie.evaluate('v=>v.duration')-record['duration'])<.1
                            if lang=='ko':
                                assert '.ko.' in movie.evaluate('v=>v.currentSrc')
                            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                            audit(page)
                            maximum=int(page.locator('#parameter').get_attribute('max'))
                            for n in range(maximum+1):
                                set_slider(page,'parameter',n)
                            if slug=='backprop':
                                page.locator('[data-mode=backward]').click()
                                assert page.locator('[data-gradient]').count()==10
                                set_slider(page,'parameter',1)
                            elif slug=='cnn':
                                page.locator('[data-filter="1"]').click()
                                for n in range(35):
                                    set_slider(page,'parameter',n)
                                page.locator('#stride').click()
                                assert page.locator('#parameter').get_attribute('max')=='11'
                                for n in range(12):
                                    set_slider(page,'parameter',n)
                                drag(page,'#second-chart',.98)
                                assert page.evaluate('window.foundationLesson.depth')==2
                                page.locator('#stride').click()
                            else:
                                set_slider(page,'parameter',2)
                                assert float(page.locator('#score-0').get_attribute('data-value'))==0
                                page.locator('[data-mode=prediction]').click()
                                audit(page)
                                assert page.locator('circle[data-active=false]').count()==0
                            drag(page,'#first-chart',.72)
                            assert page.evaluate('window.foundationLesson.parameter')>0
                            audit(page)
                            slider=page.locator('#parameter')
                            slider.focus()
                            slider.press('Home')
                            assert page.evaluate('window.foundationLesson.parameter')==0
                            slider.press('ArrowRight')
                            assert page.evaluate('window.foundationLesson.parameter')==1
                            audit(page)
                            # Decode every chapter in both browser engines and both languages.
                            for seconds in record['chapters']:
                                seek(page,seconds+.12)
                                pixels=movie.evaluate('''v=>{const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;const g=c.getContext('2d');g.drawImage(v,0,0);let bright=0;const d=g.getImageData(0,0,c.width,c.height).data;for(let i=0;i<d.length;i+=32)if(d[i]>100)bright++;return [c.width,c.height,bright];}''')
                                assert pixels[:2]==[1200,760] and pixels[2]>50
                            page.locator('[data-time]').first.click()
                            page.wait_for_function('()=>document.querySelector("video").currentTime<.1')
                            page.locator('#iteration').focus()
                            page.locator('#iteration').press('End')
                            page.wait_for_function('(d)=>document.querySelector("video").currentTime>d-1',arg=record['duration'])
                            seek(page,2)
                            movie.evaluate('v=>v.play()')
                            page.wait_for_timeout(200)
                            assert not movie.evaluate('v=>v.paused')
                            movie.evaluate('v=>v.pause()')
                            page.locator('.comparison').screenshot(path=str(args.output/f'{slug}-{engine}-{width}-{lang}.png'))
                            if engine=='chromium':
                                page.screenshot(path=str(args.output/f'{slug}-{width}-{lang}-page.png'),full_page=True)
                            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                        page.goto(origin+f'/papers/{slug}/?lang=en')
                        expect(page.locator('html')).to_have_attribute('lang','en')
                        proof['checks'].append(dict(slug=slug,engine=engine,width=width,languages=['en','ko'],arithmetic=True,gestures=True,chapters_decoded=True))
                        context.close()
                for slug in ('backprop','cnn','dropout'):
                    context=browser.new_context(java_script_enabled=False)
                    page=context.new_page()
                    page.goto(origin+f'/papers/{slug}/')
                    expect(page.locator('.noscript')).to_be_visible()
                    context.close()
                    for body in (None,'{"kind":"chainbench.foundation.v1"}'):
                        context=browser.new_context()
                        page=context.new_page()
                        page.route('**/experiment.json',lambda route,body=body:route.abort() if body is None else route.fulfill(status=200,content_type='application/json',body=body))
                        page.goto(origin+f'/papers/{slug}/')
                        expect(page.locator('#load-status')).to_have_attribute('role','alert')
                        expect(page.locator('#parameter')).to_be_disabled()
                        context.close()
                browser.close()
        assert not proof['errors'],proof['errors']
        assert not proof['external_requests'],proof['external_requests']
        (args.output/'verification.json').write_text(json.dumps(proof,indent=2)+'\n')
        print(json.dumps(proof),flush=True)
    finally:
        server.shutdown()
        server.server_close()


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--site',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    check(p.parse_args())
