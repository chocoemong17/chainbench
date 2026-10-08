"""Build approved foundation films, captions, posters and numerical records in CI."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from foundation_board import SIZE, Scene, pulses
from foundation_scenes import (
    BP_CAPTIONS,
    CNN_CAPTIONS,
    DO_CAPTIONS,
    backprop,
    backprop_repeat,
    cnn,
    dropout,
)
from PIL import Image

from chainbench.foundations import FPS, TOPICS, experiment, verify

CAPTIONS = {
    'backprop': BP_CAPTIONS + [
        ('Calculate, send gradients back, update. Repeat.', '다시 계산하고, 기울기를 돌려보내고, 갱신합니다.'),
        ('Each shown update approaches target 4.', '표시된 갱신마다 목표 4에 가까워집니다.')],
    'cnn': CNN_CAPTIONS,
    'dropout': DO_CAPTIONS,
}


def timestamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//60000:02d}:{ms//1000%60:02d}.{ms%1000:03d}'


def still(slug,lang,state):
    chapter=state['chapter']
    if slug=='backprop':
        if chapter==10:
            return backprop_repeat(lang,chapter,state['iteration'],state['phase'])
        return backprop(lang,chapter)
    if slug=='cnn':
        return cnn(lang,chapter,state.get('step'))
    return dropout(lang,chapter,state.get('variant'))


def render(output,record,lang,review):
    slug=record['slug']
    suffix='' if lang=='en' else '.ko'
    color=['-vf','scale=out_color_matrix=bt709:out_range=tv','-colorspace','bt709',
           '-color_primaries','bt709','-color_trc','bt709','-color_range','tv','-an']
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24',
         '-video_size','1200x760','-framerate',str(FPS),'-i','pipe:0']
    cmd+=color+['-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p',
                '-movflags','+faststart',str(output/f'film{suffix}.mp4')]
    cmd+=color+['-c:v','libvpx-vp9','-b:v','0','-crf','31','-cpu-used','5','-row-mt','1',
                '-pix_fmt','yuv420p',str(output/f'film{suffix}.webm')]
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    representative={}
    try:
        for state in record['timeline']:
            base=still(slug,lang,state)
            paths=Scene.last.paths
            representative[state['chapter']]=base
            if state['start']==0:
                base.save(output/f'poster{suffix}.jpg',quality=94)
            for frame in range(state['start'],state['end']):
                phase=(frame-state['start'])/FPS
                if slug=='dropout' and state['chapter']==3:
                    image=dropout(lang,3,pulse=min(2.999,phase*3/4))
                else:
                    image=pulses(base.copy(),paths,phase*.85)
                process.stdin.write(image.tobytes())
        process.stdin.close()
        if process.wait():
            raise RuntimeError('Film encoding failed')
    except BaseException:
        process.kill()
        process.wait()
        raise
    media={}
    for ext in ('mp4','webm'):
        path=output/f'film{suffix}.{ext}'
        probe=json.loads(subprocess.check_output([
            'ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries',
            'stream=width,height,nb_read_frames,color_space,color_range:format=duration',
            '-of','json',str(path)]))
        stream=probe['streams'][0]
        assert (stream['width'],stream['height'])==SIZE
        assert int(stream['nb_read_frames'])==record['timeline'][-1]['end']
        assert abs(float(probe['format']['duration'])-record['duration'])<.08
        assert stream['color_space']=='bt709' and stream['color_range']=='tv'
        media[path.name]=probe
    starts=record['chapters']+[record['duration']]
    vtt='WEBVTT\n\n'+'\n'.join(
        f'{timestamp(starts[i])} --> {timestamp(starts[i+1])}\n{caption[lang=="ko"]}\n'
        for i,caption in enumerate(CAPTIONS[slug]))
    (output/f'{lang}.vtt').write_text(vtt,encoding='utf8')
    if review:
        review.mkdir(parents=True,exist_ok=True)
        for chapter,image in representative.items():
            image.save(review/f'{slug}-{lang}-{chapter+1:02d}.jpg',quality=91)
        for start in range(0,len(representative),4):
            contact=Image.new('RGB',(1200,760),'#172127')
            for j in range(min(4,len(representative)-start)):
                contact.paste(representative[start+j].resize((600,380)),((j%2)*600,(j//2)*380))
            contact.save(review/f'{slug}-{lang}-contact{start//4+1}.jpg',quality=92)
    return media


def build(output,slug,source,review=None):
    verify()
    record=experiment(slug,source)
    output.mkdir(parents=True,exist_ok=True)
    record['decoded_media']={}
    for lang in ('en','ko'):
        record['decoded_media'].update(render(output,record,lang,review))
    record['media']={}
    for name in ('film.mp4','film.webm','film.ko.mp4','film.ko.webm','poster.jpg','poster.ko.jpg',
                 'en.vtt','ko.vtt'):
        raw=(output/name).read_bytes()
        record['media'][name]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    assert sum(v['bytes'] for v in record['media'].values())<25_000_000
    (output/'experiment.json').write_text(json.dumps(record,allow_nan=False,separators=(',',':'))+'\n')
    print(json.dumps(dict(slug=slug,source=source,duration=record['duration'],media=record['media'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source',required=True)
    p.add_argument('--review',type=Path)
    args=p.parse_args()
    for slug in TOPICS:
        build(args.output/slug,slug,args.source,args.review)
