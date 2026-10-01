"""The two selected ADMM subproblems, derived from the existing recorded states."""
import json
import math
from html import escape

from ._admm_figures import points, text
from ._pages import bi

LEVELS = (.1, .5, 2., 10.)


def hessian(case):
    A, rho = case['inputs']['A'], case['inputs']['rho']
    return [[sum(row[i]*row[j] for row in A)+(rho if i==j else 0.)
             for j in range(2)] for i in range(2)]


def model_values(case, k):
    if k==0:
        return dict.fromkeys(('old_z','old_u','target','old_z_gap','v','tau','new_z'))
    row, old = case['rows'][k], case['rows'][k-1]
    H = hessian(case)
    d = [old['z'][i]-row['x'][i] for i in range(2)]
    return dict(old_z=old['z'],old_u=old['u'],target=row['x_target'],
                old_z_gap=.5*sum(d[i]*H[i][j]*d[j] for i in range(2) for j in range(2)),
                v=row['shrink_input'],tau=case['inputs']['lambda']/case['inputs']['rho'],
                new_z=row['z'])


def shrink_bound(case):
    tau = case['inputs']['lambda']/case['inputs']['rho']
    return 1.15*max(tau,*[abs(v) for row in case['rows'][1:]
                         for name in ('shrink_input','z') for v in row[name]])


def quadratic_svg(case, radius):
    H = hessian(case)
    scale = 180/radius
    row, old = case['rows'][1], case['rows'][0]
    if any(abs(v)>radius for r in case['rows'][1:] for v in r['x']) or any(
            abs(v)>radius for r in case['rows'] for v in r['z']):
        raise ValueError('ADMM x-model window omits a recorded x/z point')
    project = lambda w:(330+scale*w[0],245-scale*w[1])  # noqa: E731
    center, previous = project(row['x']), project(old['z'])
    clip = 'admm-x-model-'+case['id']
    body = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 510" role="img" '
            f'aria-label="Selected quadratic x subproblem gap" data-admm-x-model="" data-radius="{radius}">'
            '<rect width="660" height="510" rx="12" fill="#f7fafb"/>')
    body += text(24,28,'Current x subproblem: Hx(w) − Hx(x_new)',16)
    body += text(24,49,'Blue: actual minimizer x_new · grey: previous z_old',11)
    body += f'<defs><clipPath id="{clip}"><rect x="150" y="65" width="360" height="360"/></clipPath></defs>'
    body += '<rect x="150" y="65" width="360" height="360" fill="white" stroke="#cbd5e1"/>'
    for v in (-radius,-radius/2,0.,radius/2,radius):
        x,y = project([v,v])
        body += f'<path d="M{x} 65 V425 M150 {y} H510" stroke="#e2e8f0"/>'
        body += text(x,446,f'{v:g}',11,'middle')+text(141,y+4,f'{v:g}',11,'end')
    body += text(534,249,'w₁')+text(330,62,'w₂',12,'middle')
    body += f'<g clip-path="url(#{clip})"><g data-admm-model-center="" transform="translate({center[0]:.3f} {center[1]:.3f})">'
    for level in LEVELS:
        offsets = []
        for i in range(129):
            u = [math.cos(2*math.pi*i/128), math.sin(2*math.pi*i/128)]
            curvature = sum(u[a]*H[a][b]*u[b] for a in range(2) for b in range(2))
            distance = math.sqrt(2*level/curvature)
            offsets.append([distance*v for v in u])
        body += f'<polyline data-admm-model-level="{level}" data-offsets="{escape(json.dumps(offsets,separators=(",",":")))}" points="{points([(scale*w[0],-scale*w[1]) for w in offsets])}" stroke="#8faec3" fill="none"/>'
    body += '</g></g>'
    body += f'<circle data-admm-model-point="old_z" cx="{previous[0]:.3f}" cy="{previous[1]:.3f}" r="5" fill="#64748b" stroke="white"/>'
    body += f'<circle data-admm-model-point="x" cx="{center[0]:.3f}" cy="{center[1]:.3f}" r="6" fill="#2563eb" stroke="white"/>'
    body += text(24,480,'Hx gap levels: 0.1, 0.5, 2, 10 · not the original F gap',11)
    body += text(24,499,f'Window [−{radius:g},{radius:g}]² · penalty target a is given numerically below',11)
    return body+'</svg>'


def shrink_svg(case):
    bound = shrink_bound(case)
    tau = case['inputs']['lambda']/case['inputs']['rho']
    row = case['rows'][1]
    px = lambda v:330+250*v/bound  # noqa: E731
    arrow = 'admm-shrink-arrow-'+case['id']
    body = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 510" role="img" '
            f'aria-label="Coordinate shrinkage of x_new plus old memory" data-admm-shrink="" data-bound="{bound}" data-tau="{tau}">'
            '<rect width="660" height="510" rx="12" fill="#f7fafb"/>')
    body += text(24,28,'z_new = soft(v, τ), v = x_new + u_old',16)
    body += text(24,49,'Purple input v · green result z · shaded interval [−τ,τ] maps to zero',11)
    body += f'<defs><marker id="{arrow}" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7 Z" fill="#0f766e"/></marker></defs>'
    for i in range(2):
        y = 150+180*i
        body += text(24,y-51,f'Coordinate {i+1}',13)
        body += f'<rect data-admm-shrink-band="{i}" x="{px(-tau):.3f}" y="{y-22}" width="{px(tau)-px(-tau):.3f}" height="44" fill="#dbece5"/>'
        body += f'<path d="M80 {y} H580" stroke="#64748b"/>'
        for v in (-bound,0.,bound):
            body += f'<path d="M{px(v):.3f} {y-5} V{y+5}" stroke="#64748b"/>'
            body += text(px(v),y+42,f'{v:.4g}',11,'middle')
        left, right = px(row['shrink_input'][i]),px(row['z'][i])
        body += f'<path data-admm-shrink-move="{i}" d="M{left:.3f} {y-14} L{right:.3f} {y+14}" stroke="#0f766e" stroke-width="2" marker-end="url(#{arrow})"/>'
        for name,value,dy,color in (('v',row['shrink_input'][i],-14,'#7c3aed'),('z',row['z'][i],14,'#0f766e')):
            body += f'<circle data-admm-shrink-point="{name}:{i}" cx="{px(value):.3f}" cy="{y+dy}" r="5" fill="{color}" stroke="white"/>'
    body += text(24,430,f'τ = λ/ρ = {tau:.6g} · |vᵢ| ≤ τ ⇒ zᵢ = 0',13)
    body += text(24,456,'Both coordinate axes: one fixed linear scale for every step in this case',11)
    body += text(24,482,'Vertical offsets separate input/output glyphs; they are not extra coordinates',11)
    return body+'</svg>'


def subproblem_section(case,radius,formatted):
    values = model_values(case,1)
    body = '<details class="admm-models" open><summary>'+bi('이 한 걸음에서 푸는 두 문제', 'The two problems solved within this step')+'</summary>'
    body += '<p>'+bi('왼쪽은 선택한 반복의 이차 하위 문제입니다. 오른쪽은 이전 기억 u_old를 더한 뒤 좌표를 축소하는 과정입니다. 파란 점은 실제 선형계 해이고, 회색 점은 이전 z입니다.',
        'The left panel is the quadratic subproblem at the selected iteration. The right panel shrinks coordinates after adding the previous memory u_old. The blue point is the actual linear-system solution; grey is the previous z.')+'</p>'
    body += '<p data-admm-model-initial="" hidden>'+bi('k=0: 아직 한 번의 하위 문제도 풀지 않았습니다.', 'k=0: no subproblem update has been completed.')+'</p><div data-admm-model-body=""><div class="visual-grid">'
    for title,formula,svg,fields in [
        (('x: 벌점을 더한 이차 문제','x: the penalized quadratic'),
         'a=z_old−u_old<br>Hx(w)=½||Aw−b||²+ρ/2||w−a||²<br>Hx(w)−Hx(x_new)=½(w−x_new)ᵀ(AᵀA+ρI)(w−x_new)',
         quadratic_svg(case,radius),[('old_z','z_old'),('old_u','u_old'),('target','a = z_old − u_old'),('old_z_gap','Hx(z_old) − Hx(x_new)')]),
        (('z: 이동한 점의 좌표별 축소','z: coordinate shrinkage at the shifted point'),
         'v=x_new+u_old · τ=λ/ρ<br>Hz(w)=λ||w||₁+ρ/2||w−v||²<br>z_new=argmin Hz(w)=soft(v,τ)',
         shrink_svg(case),[('v','v = x_new + u_old'),('tau','τ = λ/ρ'),('new_z','z_new')]),
    ]:
        body += '<div><h3>'+bi(*title)+'</h3><p class="formula">'+formula+'</p><div class="admm-figure" tabindex="0" aria-label="Subproblem figure / 하위 문제 그림">'+svg+'</div><div class="scroll" tabindex="0"><table><tbody>'
        for key,label in fields:
            body += '<tr><th scope="row">'+escape(label)+'</th><td data-admm-model-read="'+key+'">'+formatted(values[key])+'</td></tr>'
        body += '</tbody></table></div></div>'
    body += '</div></div><p class="small">'+bi(
        'Hx와 Hz는 선택한 k에 따라 바뀝니다. 이 하위 문제의 간극을 원래 F(w)−F*나 서로 다른 반복을 잇는 수렴 곡선으로 읽지 않습니다. a는 그림 창 밖에 있을 수 있어 수치로 표시합니다. 축소 그림은 이 사례의 모든 v·z와 ±τ를 담는 고정 선형축을 사용하며, 왼쪽 좌표축과 범위가 다릅니다.',
        'Hx and Hz change with the selected k. Their gaps are not original F(w)−F* or a convergence curve joining different iterations. The target a is shown numerically because it may lie outside the window. Shrinkage uses a fixed linear axis covering every v/z and ±τ in this case, with a different range from the left panel.')+'</p>'
    body += '<details><summary>'+bi('스크립트 없이 읽는 이전 기억과 축소 입력','Read previous memory and shrinkage inputs without scripts')+'</summary><div class="scroll" tabindex="0"><table><thead><tr><th>k</th><th>z_old</th><th>u_old</th><th>a=z_old−u_old</th><th>v=x_new+u_old</th></tr></thead><tbody>'
    for k in case['native_iterations']:
        values = model_values(case,k)
        body += f'<tr data-admm-model-native="{k}"><td>{k}</td>'+''.join('<td>'+formatted(values[key])+'</td>' for key in ('old_z','old_u','target','v'))+'</tr>'
    return body+'</tbody></table></div></details></details>'


MODEL_UPDATE = r"""
   {
    const body=el.querySelector('[data-admm-model-body]'),empty=el.querySelector('[data-admm-model-initial]');
    body.hidden=k===0;empty.hidden=k!==0;
    if(k>0){
     const old=c.rows[k-1],rho=c.inputs.rho,A=c.inputs.A,d=old.z.map((v,i)=>v-row.x[i]);
     const oldGap=.5*(A.reduce((s,a)=>s+a.reduce((t,v,i)=>t+v*d[i],0)**2,0)+rho*d.reduce((s,v)=>s+v*v,0));
     const values={old_z:old.z,old_u:old.u,target:row.x_target,old_z_gap:oldGap,v:row.shrink_input,tau:c.inputs.lambda/rho,new_z:row.z};
     el.querySelectorAll('[data-admm-model-read]').forEach(e=>e.textContent=format(values[e.dataset.admmModelRead]));
     const model=el.querySelector('[data-admm-x-model]'),scale=180/Number(model.dataset.radius),point=w=>[330+scale*w[0],245-scale*w[1]];
     const center=point(row.x);model.querySelector('[data-admm-model-center]').setAttribute('transform',`translate(${center[0]} ${center[1]})`);
     model.querySelectorAll('[data-admm-model-point]').forEach(e=>{const p=point(e.dataset.admmModelPoint==='x'?row.x:old.z);e.setAttribute('cx',p[0]);e.setAttribute('cy',p[1]);});
     const shrink=el.querySelector('[data-admm-shrink]'),px=v=>330+250*v/Number(shrink.dataset.bound);
     shrink.querySelectorAll('[data-admm-shrink-point]').forEach(e=>{const [name,i]=e.dataset.admmShrinkPoint.split(':');e.setAttribute('cx',px((name==='v'?row.shrink_input:row.z)[Number(i)]));});
     shrink.querySelectorAll('[data-admm-shrink-move]').forEach(e=>{const i=Number(e.dataset.admmShrinkMove),y=150+180*i;e.setAttribute('d',`M${px(row.shrink_input[i])} ${y-14} L${px(row.z[i])} ${y+14}`);});
    }
   }
"""
