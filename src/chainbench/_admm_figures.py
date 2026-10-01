"""Code-native geometry of original-primal points and ADMM dual-feature states."""
import json
import math
from functools import lru_cache
from html import escape

import numpy as np


def text(x,y,value,size=12,anchor='start'):
    return f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" text-anchor="{anchor}" fill="#334155">{escape(str(value))}</text>'


def points(values):
    return ' '.join(f'{x:.3f},{y:.3f}' for x,y in values)


def _gap(w,A,star,subgradient,lam):
    w = np.asarray(w)
    error = (w-star)@A.T
    return .5*np.sum(error*error,axis=-1)+lam*np.sum(np.abs(w)-subgradient*w,axis=-1)


@lru_cache(maxsize=24)
def _geometry(matrix,star,subgradient,lam,radius):
    A = np.array(matrix).reshape(2,2)
    star,sg = np.array(star),np.array(subgradient)
    grid = np.linspace(-radius,radius,21)
    mesh = []
    for flip in (False,True):
        for fixed in grid:
            w = np.array([[fixed,free] if not flip else [free,fixed] for free in grid])
            mesh.append(np.column_stack((w,_gap(w,A,star,sg,lam))).tolist())
    maximum = max(v[2] for line in mesh for v in line)
    height = max(10.,math.ceil(maximum/10)*10.)
    directions = np.column_stack((np.cos(np.linspace(0,2*np.pi,129)),np.sin(np.linspace(0,2*np.pi,129))))
    contours = []
    for level in (.1,.5,2.,10.,40.):
        lo,hi = np.zeros(129),np.full(129,32.)
        for _ in range(44):
            mid = (lo+hi)/2
            inside = _gap(star+mid[:,None]*directions,A,star,sg,lam)<level
            lo,hi = np.where(inside,mid,lo),np.where(inside,hi,mid)
        contours.append((level,(star+((lo+hi)/2)[:,None]*directions).tolist()))
    return mesh,height,contours


def projection(w,gap,radius,height,surface):
    if surface:
        return (330+125*w[0]/radius+85*w[1]/radius,
                345-45*w[0]/radius+65*w[1]/radius-190*gap/height)
    return 330+180*w[0]/radius,245-180*w[1]/radius


def primal_svg(case,radius,*,surface=False):
    ip,opt = case['inputs'],case['optimum']
    mesh,height,contours = _geometry(tuple(v for row in ip['A'] for v in row),tuple(opt['point']),tuple(opt['subgradient']),ip['lambda'],radius)
    mode = 'surface' if surface else 'contour'
    project = lambda w,gap=0.: projection(w,gap,radius,height,surface)  # noqa: E731
    body = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 510" role="img" '
            f'aria-label="Original LASSO {mode}: actual x and z states" data-admm-primal="{mode}" data-radius="{radius}" data-height="{height}">'
            '<rect width="660" height="510" rx="12" fill="#f7fafb"/>')
    body += text(24,28,'Original-primal gap height F(w) − F*' if surface else 'Original-primal contours F(w) − F*',16)
    body += text(24,49,'Blue x · green z · black optimum · amber joins x and z (r=x−z)',11)
    if surface:
        for line in mesh:
            body += f'<polyline data-admm-mesh="{escape(json.dumps(line,separators=(",",":")))}" points="{points([project(v[:2],v[2]) for v in line])}" fill="none" stroke="#cbd9df"/>'
        origin = project([-radius,-radius])
        for end,label in (([radius,-radius],'w₁'),([-radius,radius],'w₂')):
            x,y = project(end)
            body += f'<path d="M{origin[0]} {origin[1]} L{x} {y}" stroke="#64748b"/>'+text(x+8,y,label)
        front = project([-radius,radius])
        body += f'<path d="M{front[0]} {front[1]} V{front[1]-190}" stroke="#64748b"/>'
        for fraction in (0,.5,1):
            body += text(front[0]-9,front[1]-190*fraction+4,f'{height*fraction:g}',11,'end')
        body += text(front[0],front[1]-207,'gap',11,'middle')
        body += text(24,486,f'w₁,w₂ ∈ [−{radius:g},{radius:g}] · height scale [0,{height:g}] shared across ρ/starts for this F',11)
    else:
        clip = 'admm-contour-'+case['id']
        body += f'<defs><clipPath id="{clip}"><rect x="150" y="65" width="360" height="360"/></clipPath></defs><rect x="150" y="65" width="360" height="360" fill="white" stroke="#cbd5e1"/><g clip-path="url(#{clip})">'
        for level,world in contours:
            body += f'<polyline data-admm-level="{level}" data-world="{escape(json.dumps(world,separators=(",",":")))}" points="{points([project(w) for w in world])}" fill="none" stroke="#b7cad5"/>'
        body += '</g>'
        for v in (-radius,-radius/2,0.,radius/2,radius):
            x,y = project([v,v])
            body += f'<path d="M{x} 65 V425 M150 {y} H510" stroke="#e2e8f0"/>'
            body += text(x,446,f'{v:g}',11,'middle')+text(141,y+4,f'{v:g}',11,'end')
        body += text(534,249,'w₁')+text(330,62,'w₂',12,'middle')
        body += text(24,486,'Equal coordinate scales · contour gaps: 0.1, 0.5, 2, 10, 40',11)
    star = project(opt['point'])
    body += f'<circle data-admm-optimum="" cx="{star[0]:.3f}" cy="{star[1]:.3f}" r="5" fill="#172238"/>'
    frames = {}
    for name,color in (('x','#2563eb'),('z','#0f766e')):
        frames[name] = [None if row[name] is None else project(row[name],row['stable_gap_'+name]) for row in case['rows']]
        known = [p for p in frames[name] if p is not None]
        body += f'<polyline data-admm-path="{name}" points="{points(known)}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="{"6 4" if name=="x" else "none"}"/>'
    p,q = frames['x'][1],frames['z'][1]
    body += f'<path data-admm-residual-chord="" d="M{p[0]:.3f} {p[1]:.3f} L{q[0]:.3f} {q[1]:.3f}" stroke="#b45309" stroke-width="3" stroke-dasharray="4 3"/>'
    for name,color in (('x','#2563eb'),('z','#0f766e')):
        p = frames[name][1]
        body += f'<circle data-admm-marker="{name}" data-frames="{escape(json.dumps(frames[name],separators=(",",":")))}" cx="{p[0]:.3f}" cy="{p[1]:.3f}" r="6" fill="{color}" stroke="white" stroke-width="1.5"/>'
    return body+'</svg>'


def dual_svg(case):
    lam = case['inputs']['lambda']
    # y is in feature coordinates. Padding retains small raw floating excess.
    scale = 150/lam
    project = lambda y:(330+scale*y[0],220-scale*y[1])  # noqa: E731
    frames = [project(row['y']) for row in case['rows']]
    body = (f'<svg viewBox="0 0 660 455" role="img" aria-label="Scaled-dual memory in the L1 subgradient box" '
            f'data-admm-dual="" data-lambda="{lam}"><rect width="660" height="455" rx="12" fill="#f7fafb"/>')
    body += text(24,28,'Dual-feature memory y = ρu',16)+text(24,49,'The box describes ∂(λ||z||₁); raw y is retained without clipping',11)
    body += '<rect x="180" y="70" width="300" height="300" fill="#e8f3ef" stroke="#0f766e"/><path d="M150 220 H510 M330 55 V390" stroke="#cbd5e1"/>'
    for v in (-lam,0.,lam):
        x,y = project([v,v])
        body += text(x,390,f'{v:.4g}',11,'middle')+text(171,y+4,f'{v:.4g}',11,'end')
    body += text(521,224,'y₁')+text(330,62,'y₂',12,'middle')
    body += f'<polyline data-admm-dual-path="" points="{points(frames)}" fill="none" stroke="#7c3aed" stroke-width="2"/>'
    optimum = project([lam*v for v in case['optimum']['subgradient']])
    body += f'<circle data-admm-dual-optimum="" cx="{optimum[0]:.3f}" cy="{optimum[1]:.3f}" r="5" fill="#172238"/>'
    p = frames[1]
    body += f'<circle data-admm-marker="y" data-frames="{escape(json.dumps(frames,separators=(",",":")))}" cx="{p[0]:.3f}" cy="{p[1]:.3f}" r="6" fill="#7c3aed" stroke="white" stroke-width="1.5"/>'
    return body+text(24,427,f'Box [−λ,λ]² · λ={lam:.6g} · not the measurement-space residual dual',11)+'</svg>'


def objective_svg(case):
    rows = case['rows']
    star = case['optimum']['value']
    high = max(star,*[r['objective_z'] for r in rows],*[r['split_objective'] for r in rows[1:]])*1.08
    px = lambda k:80+510*k/case['inputs']['steps']  # noqa: E731
    py = lambda v:250-175*v/high  # noqa: E731
    body = f'<svg viewBox="0 0 660 310" role="img" aria-label="Original and split objective values" data-admm-objectives="" data-high="{high}"><rect width="660" height="310" rx="12" fill="#f7fafb"/>'
    body += text(24,27,'One point F(z) vs two points f(x)+g(z)',16)
    for f in (0,.25,.5,.75,1):
        v = high*f
        body += f'<path d="M80 {py(v)} H590" stroke="#dbe4ee"/>'+text(73,py(v)+4,f'{v:.4g}',11,'end')
    body += f'<path data-admm-objective-star="" d="M80 {py(star):.3f} H590" stroke="#172238" stroke-dasharray="4 3"/>'
    for name,color,start in (('objective_z','#0f766e',0),('split_objective','#b45309',1)):
        body += f'<polyline data-admm-objective-path="{name}" points="{points([(px(r["iteration"]),py(r[name])) for r in rows[start:]])}" fill="none" stroke="{color}" stroke-width="2"/>'
        if len(rows[start:])==1:
            body += f'<circle cx="{px(1):.3f}" cy="{py(rows[1][name]):.3f}" r="3" fill="{color}"/>'
    for k in sorted({0,case['inputs']['steps']//2,case['inputs']['steps']}):
        body += text(px(k),271,k,11,'middle')
    return body+text(24,297,'Green F(z) · amber split value (may be below F*) · dashed original optimum F*',11)+'</svg>'


def residual_svg(case):
    ratios = {name:[row[name+'_norm']/row['eps_'+name] for row in case['rows'][1:]] for name in ('primal','dual')}
    positive = [1.,*[v for values in ratios.values() for v in values if v>0]]
    low,high = math.floor(math.log10(min(positive)))-1,math.ceil(math.log10(max(positive)))+1
    px = lambda k:80+510*k/case['inputs']['steps']  # noqa: E731
    py = lambda v:235-165*(math.log10(v)-low)/(high-low) if v else 274.  # noqa: E731
    body = f'<svg viewBox="0 0 660 340" role="img" aria-label="Each residual divided by its own stopping tolerance" data-admm-residuals="" data-low="{low}" data-high="{high}"><rect width="660" height="340" rx="12" fill="#f7fafb"/>'
    body += text(24,27,'Residual / its own tolerance · both ratios must be ≤1',15)
    for power in sorted({low,0,high,*range(low,high+1,max(1,math.ceil((high-low)/5)))}):
        y = py(10.**power)
        body += f'<path d="M80 {y:.3f} H590" stroke="{"#475569" if power==0 else "#dbe4ee"}"/>'+text(73,y+4,f'10^{power}',11,'end')
    body += '<path d="M80 274 H590" stroke="#dbe4ee"/>'+text(73,278,'0',11,'end')
    for name,color in (('primal','#2563eb'),('dual','#7c3aed')):
        segment = []
        for k,v in enumerate(ratios[name],1):
            if v:
                segment.append((px(k),py(v)))
            elif segment:
                body += f'<polyline data-admm-ratio-line="{name}" points="{points(segment)}" stroke="{color}" fill="none"/>'
                segment = []
            body += f'<circle data-admm-ratio="{name}:{k}" data-raw="{v!r}" cx="{px(k):.3f}" cy="{py(v):.3f}" r="1.8" fill="{color}"/>'
        if segment:
            body += f'<polyline data-admm-ratio-line="{name}" points="{points(segment)}" stroke="{color}" fill="none"/>'
    for k in sorted({1,case['inputs']['steps']//2 or 1,case['inputs']['steps']}):
        body += text(px(k),298,k,11,'middle')
    return body+text(24,325,'Blue primal · purple dual · positive: log · zero: separate row · k=0 undefined',11)+'</svg>'
