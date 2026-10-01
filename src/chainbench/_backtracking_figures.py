"""SVG geometry for actual accepted paths and every recorded line-search trial."""
from __future__ import annotations

import json
from html import escape

import numpy as np

from .proximal_views import _contour, _gaps


def objective_case(case):
    # The same a=(1,3), b=(1.4,-2.4) objective geometry; no fixed-L stages reused.
    return {'lambda':case['inputs']['lambda'], 'x_star':case['optimum']['point']}


def points(values):
    return ' '.join(','.join(f'{v:.3f}' for v in p) for p in values)


def text(x, y, value, size=12):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="#334155">{escape(str(value))}</text>'


def start(title):
    return ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 470" '
        f'role="img" aria-label="{escape(title)}"><rect width="620" height="470" rx="16" fill="#fbfaf7"/>',
        text(20,28,title,16)]


def dynamic(tag, key, attribute, values, extra):
    encoded = escape(json.dumps(values,separators=(',',':')),quote=True)
    initial = escape(str(values[0]),quote=True)
    return (f'<{tag} data-bt-dynamic="{key}" data-bt-attribute="{attribute}" '
        f'data-bt-values="{encoded}" {attribute}="{initial}" {extra}/>')


def project(point, gap=0., surface=False):
    x,y = point
    return (310+38*x+28*y,310-13*x+18*y-1.4*gap) if surface else (310+52*x,250-52*y)


def path_svg(case, *, surface=False):
    fixture = objective_case(case)
    def xy(point):
        return project(point,float(_gaps(point,fixture)),surface)
    title = 'Accepted x only · height F(x)−F*' if surface else 'Accepted x only · equal coordinate scales'
    body = start(title)
    body.append(text(20,49,'Full saved path, k=0…N · ring: selected x_k · purple: anchor y_k',11))
    if surface:
        for axis in (0,1):
            for fixed in np.linspace(-3.5,3.5,13):
                path = [xy([fixed,v] if axis==0 else [v,fixed]) for v in np.linspace(-3.5,3.5,49)]
                body.append('<polyline data-bt-wire="" points="'+points(path)+'" fill="none" stroke="#d6e0e6"/>')
        for end,label in (([3.5,-3.5],'x₁'),([-3.5,3.5],'x₂')):
            a,b = project([-3.5,-3.5],surface=True),project(end,surface=True)
            body.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="#64748b"/>')
            body.append(text(b[0],b[1]+18,label))
        a,b = project([-3.5,-3.5],surface=True),project([-3.5,-3.5],50,True)
        body.append(f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="#64748b"/>')
        body.append(text(b[0]+5,b[1],'height=50',11))
    else:
        clip = 'bt-clip-'+case['id']
        body.append(f'<defs><clipPath id="{clip}"><rect x="128" y="68" width="364" height="364"/></clipPath></defs>')
        body.append('<rect x="128" y="68" width="364" height="364" fill="white" stroke="#d6e0e6"/>')
        for level in (.1,1.,5.,20.):
            world = _contour(fixture,level)
            body.append(f'<polyline data-bt-contour="{level}" clip-path="url(#{clip})" data-bt-world="'
                +escape(json.dumps(world.tolist(),separators=(',',':')),quote=True)+'" points="'
                +points([xy(p) for p in world])+'" fill="none" stroke="#c0d4df"/>')
        for v in (-3,-2,-1,0,1,2,3):
            a,b = project([v,0]),project([0,v])
            body.append(text(a[0]-4,450,v,11)+text(100,b[1]+4,v,11))
        body.append('<path d="M310 68 V432 M128 250 H492" stroke="#b8c8d5" stroke-dasharray="4 4"/>')
        body.append(text(508,255,'x₁')+text(307,62,'x₂'))
    path = [xy(r['x']) for r in case['rows']]
    body.append('<polyline data-bt-path="'+('surface' if surface else 'plane')+'" points="'+points(path)+'" fill="none" stroke="#13856a" stroke-width="2.5"/>')
    star = xy(case['optimum']['point'])
    body.append(f'<circle data-bt-star="" cx="{star[0]:.3f}" cy="{star[1]:.3f}" r="4" fill="#172238"/>')
    body.append(text(round(star[0]+7,3),round(star[1]-7,3),'x*',11))
    for name,color in (('x','#13856a'),('anchor','#8454a6')):
        positions = [xy(case['rows'][s['iteration']]['x'] if name=='x' else s['anchor'])
            for s in case['stages'] for _ in s['trials']]
        body.append(dynamic('circle',name,'transform',[f'translate({a:.3f} {b:.3f})' for a,b in positions],
            f'cx="0" cy="0" r="5" stroke="{color}" fill="white" stroke-width="2.2"'))
    body.append(text(20,465,'XY window: [−3.5,3.5]² · contour gaps .1,1,5,20' if not surface else
        'Fixed projection; wire height and selected markers use the full composite objective.',11))
    return ''.join(body)+'</svg>'


def proposal_scale(stage):
    values = [stage['anchor']]+[v['point'] for v in stage['trials']]
    return max(1.,1.1*max(abs(v) for p in values for v in p))


def proposal_svg(case):
    body = start('All attempted q in this step · no rejected point is clipped')
    body.append(text(20,49,'Anchor y: purple · numbered q: trial order · ring: selected trial',11))
    body.append('<rect x="128" y="68" width="364" height="364" fill="white" stroke="#d6e0e6"/>')
    body.append('<path d="M310 68 V432 M128 250 H492" stroke="#b8c8d5" stroke-dasharray="4 4"/>')
    flat = [(s,v) for s in case['stages'] for v in s['trials']]
    for fraction in (-1,0,1):
        labels = [f'{fraction*proposal_scale(s):.4g}' for s,_ in flat]
        encoded = escape(json.dumps(labels),quote=True)
        body.append(f'<text x="{303+182*fraction}" y="449" font-size="10" data-bt-text="proposal-x-tick" data-bt-values="{encoded}">{labels[0]}</text>')
        body.append(f'<text x="74" y="{254-182*fraction}" font-size="10" data-bt-text="proposal-y-tick" data-bt-values="{encoded}">{labels[0]}</text>')
    body.append(text(509,255,'x₁')+text(307,62,'x₂'))
    # A polyline only establishes proposal order; proposals are not optimizer iterates.
    paths = [points([(310+182*p[0]/proposal_scale(s),250-182*p[1]/proposal_scale(s))
        for p in [s['anchor']]+[q['point'] for q in s['trials']]]) for s,_ in flat]
    body.append(dynamic('polyline','proposals','points',paths,'fill="none" stroke="#d97706" stroke-dasharray="3 4"'))
    for key,color,which in (('proposal-anchor','#8454a6',lambda s,v:s['anchor']),
                            ('proposal-selected','#d97706',lambda s,v:v['point'])):
        positions = [f'translate({310+182*which(s,v)[0]/proposal_scale(s):.3f} {250-182*which(s,v)[1]/proposal_scale(s):.3f})' for s,v in flat]
        body.append(dynamic('circle',key,'transform',positions,f'cx="0" cy="0" r="5" fill="white" stroke="{color}" stroke-width="2"'))
    # Individual numbered proposals may coincide; the full native table retains them.
    for j in range(max(len(s['trials']) for s in case['stages'])):
        positions,labels = [],[]
        for s,_ in flat:
            p = s['trials'][min(j,len(s['trials'])-1)]['point']
            positions.append(f'translate({310+182*p[0]/proposal_scale(s)+6:.3f} {250-182*p[1]/proposal_scale(s)-6:.3f})')
            labels.append(str(j+1) if j<len(s['trials']) else '')
        body.append(dynamic('text',f'proposal-number-{j}','transform',positions,
            'font-size="11" fill="#925a12"').replace('/>', '>'+labels[0]+'</text>'))
        body[-1] = body[-1].replace('font-size=', 'data-bt-labels="'+escape(json.dumps(labels),quote=True)+'" font-size=')
    scales = [f'Each coordinate spans ±{proposal_scale(s):.6g}; equal scales, refitted per step.' for s,_ in flat]
    body.append('<text x="20" y="459" font-size="11" data-bt-text="proposal-scale" data-bt-values="'
        +escape(json.dumps(scales),quote=True)+'">'+scales[0]+'</text>')
    return ''.join(body)+'</svg>'


def model_limits(trial, stage):
    values = trial['slice']['objective_gap']+trial['slice']['model_gap']+[stage['previous_gap'],0.]
    low,high = min(values),max(values)
    padding = .08*(high-low) if high>low else 1.
    return low-padding,high+padding


def model_xy(trial,stage,s,value):
    low,high = model_limits(trial,stage)
    return 86+(s+.25)*460/1.5,390-(value-low)/(high-low)*300


def model_svg(case):
    body = start('Selected trial · F−F* and Q_L−F* on the same line')
    body.append(text(20,49,'F: black · Q_L: purple dashed · grey: previous F(x_{k−1})−F*',11))
    body.append('<rect x="86" y="90" width="460" height="300" fill="white" stroke="#d6e0e6"/>')
    flat = [(s,v) for s in case['stages'] for v in s['trials']]
    for key,color,dash in (('objective_gap','#172238','none'),('model_gap','#8454a6','6 4')):
        paths = [points([model_xy(v,s,t,g) for t,g in zip(v['slice']['parameter'],v['slice'][key])]) for s,v in flat]
        body.append(dynamic('polyline',key,'points',paths,f'fill="none" stroke="{color}" stroke-width="2.5" stroke-dasharray="{dash}"'))
    paths = [points([model_xy(v,s,t,s['previous_gap']) for t in (-.25,1.25)]) for s,v in flat]
    body.append(dynamic('polyline','previous-gap','points',paths,'fill="none" stroke="#84909e" stroke-dasharray="3 4"'))
    for key,field,color in (('candidate-F','stable_gap','#13856a'),('candidate-Q','stable_model_gap','#8454a6')):
        frames = [f'translate({a:.3f} {b:.3f})' for s,v in flat for a,b in [model_xy(v,s,1,v[field])]]
        body.append(dynamic('circle',key,'transform',frames,f'cx="0" cy="0" r="4" fill="white" stroke="{color}" stroke-width="2"'))
    for t in (-.25,0,.5,1,1.25):
        body.append(text(round(86+(t+.25)*460/1.5-5,3),411,t,11))
    for f in (0,.5,1):
        labels = [f'{model_limits(v,s)[0]+f*(model_limits(v,s)[1]-model_limits(v,s)[0]):.4g}' for s,v in flat]
        body.append('<text x="8" y="'+str(394-300*f)+'" font-size="10" data-bt-text="model-tick" data-bt-values="'
            +escape(json.dumps(labels),quote=True)+'">'+labels[0]+'</text>')
    body.append(text(20,437,'s=0: anchor y · s=1: proposed q · s is position, not iteration',11))
    body.append(text(20,459,'Linear height scale refitted per trial, including negative model values.',11))
    return ''.join(body)+'</svg>'
