"""Actual GD points and a resolved centre for the public horizon-specific example."""
from __future__ import annotations

from html import escape

from ._pages import bi


def _point(result, x, value):
    R, L = result['config']['R'], result['config']['L']
    ymax = max(result['charts']['function']['series'][0]['y'])/(L*R*R)
    return 70+620*(x/R+1.1)/2.2, 330-250*(value/(L*R*R))/ymax


def _text(x, y, value, size=12, anchor='start'):
    return f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" text-anchor="{anchor}" fill="#334155">'+escape(str(value))+'</text>'


def _poly(points):
    return ' '.join(f'{x:.3f},{y:.3f}' for x,y in points)


def function_svg(result):
    rows, a, R = result['rows'], result['transition'], result['config']['R']
    data = result['charts']['function']['series'][0]
    curve = [_point(result, x, y) for x,y in zip(data['x'], data['y'])]
    path = [_point(result, r['x'], r['gap']) for r in rows]
    left, right = _point(result, -a, 0)[0], _point(result, a, 0)[0]
    body = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 420" role="img" aria-label="Actual GD points on the fixed Huber function" font-family="system-ui,sans-serif">'
    body += '<rect width="760" height="420" rx="14" fill="#fbfaf7"/>'
    body += _text(28,30,'One fixed function · actual GD points',16)
    body += f'<rect x="{left:.3f}" y="72" width="{right-left:.3f}" height="258" fill="#d1fae5"/>'
    body += '<path d="M70,72 V330 H690" fill="none" stroke="#8495a9"/>'
    ymax = max(data['y'])
    for fraction in (0., .5, 1.):
        y = 330-250*fraction
        body += f'<path d="M70,{y:.3f} H690" stroke="#e2e8f0"/>'
        body += _text(61,y+4,f'{ymax*fraction:.3g}',11,'end')
    for value in (-R,0.,R):
        x = _point(result,value,0)[0]
        body += _text(x,351,f'{value:.3g}',11,'middle')
    body += _text(380,377,'x (original units)',12,'middle')+_text(28,61,'f(x)',12)
    body += f'<polyline points="{_poly(curve)}" fill="none" stroke="#536d88" stroke-width="2.1"/>'
    body += f'<polyline data-tight-path="" points="{_poly(path)}" data-points="{_poly(path)}" fill="none" stroke="#2563eb" stroke-width="3"/>'
    for p, label, color in ((path[0], 'x0=R', '#2563eb'), (path[-1], 'xN', '#c26b17')):
        body += f'<circle cx="{p[0]:.3f}" cy="{p[1]:.3f}" r="6" fill="white" stroke="{color}" stroke-width="2"/>'
        body += _text(p[0],p[1]+(19 if label == 'xN' else -13),label,12,'middle')
    body += f'<circle data-tight-point="" data-points="{_poly(path)}" cx="{path[0][0]:.3f}" cy="{path[0][1]:.3f}" r="5" fill="#0f766e"/>'
    body += '<circle cx="380" cy="330" r="4" fill="#0f766e"/>'+_text(380,316,'x*=0',11,'middle')
    body += _text(28,401,'Green strip: |x| ≤ a (quadratic centre). Blue: recorded iterates, all in the affine tail.',11)
    return body+'</svg>'


def center_svg(result):
    geometry = result['geometry']
    def point(u,v):
        return 70+520*(u+2)/4, 330-240*v/1.5
    curve = [point(u,v) for u,v in zip(geometry['normalized_x'],geometry['normalized_value'])]
    body = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 420" role="img" aria-label="Normalized quadratic centre with smooth joins at plus and minus one" font-family="system-ui,sans-serif">'
    body += '<rect width="660" height="420" rx="14" fill="#fbfaf7"/>'+_text(26,30,'Zoom: the smooth centre',16)
    body += '<rect x="200" y="80" width="260" height="250" fill="#d1fae5"/>'
    body += '<path d="M70,80 V330 H590" fill="none" stroke="#8495a9"/>'
    for u in (-2,-1,0,1,2):
        x = point(u,0)[0]
        body += _text(x,351,u,11,'middle')
    for value in (0.,.5,1.,1.5):
        y = point(0,value)[1]
        body += f'<path d="M70,{y:.3f} H590" stroke="#e2e8f0"/>'+_text(60,y+4,value,11,'end')
    body += f'<polyline data-tight-center="" points="{_poly(curve)}" fill="none" stroke="#0f766e" stroke-width="2.5"/>'
    for u in (-1,1):
        x,y = point(u,.5)
        body += f'<circle cx="{x:.3f}" cy="{y:.3f}" r="5" fill="#0f766e"/>'
    body += _text(330,377,'u = x/a',12,'middle')+_text(28,61,'φ(u) = f(a·u)/(L·a²)',12)
    body += _text(28,400,'Continuous slope at u=±1; the flat-curvature tails are affine, not flat in value.',11)
    return body+'</svg>'


CSS = '''.tight-views{display:grid;grid-template-columns:1fr 1fr;gap:18px}.tight-views svg{display:block;width:100%;height:auto;min-width:580px}.tight-views>div{overflow:auto;min-width:0}
.tight-controls{display:none;align-items:center;gap:14px;flex-wrap:wrap;background:#142841;color:#fff;border-radius:14px;padding:16px;margin:18px 0}.tight-js .tight-controls{display:flex}.tight-controls input{flex:1;min-width:160px;padding:0}.tight-controls label{font-weight:700}
.tight-readout{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0}.tight-readout div{padding:12px;background:#edf4f8;border-radius:12px;min-width:0}.tight-readout span{font-size:12px}.tight-readout strong{display:block;font-family:monospace;overflow-wrap:anywhere;font-size:15px}.tight-proof{border-left:4px solid #0f766e;background:#effaf5;padding:16px;margin:18px 0}
@media(max-width:760px){.tight-views{grid-template-columns:1fr}.tight-readout{grid-template-columns:1fr}}
@media print{.tight-controls{display:none!important}}'''

SCRIPT = '''(()=>{
 const slider=document.querySelector('[data-tight-slider]');if(!slider)return;
 const record=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 const marker=document.querySelector('[data-tight-point]'),path=document.querySelector('[data-tight-path]');
 const points=marker.dataset.points.split(' ').map(p=>p.split(','));
 const label=document.querySelector('[data-tight-step]'),play=document.querySelector('[data-tight-play]');
 document.documentElement.classList.add('tight-js');let timer=null;
 const stop=()=>{if(timer)clearInterval(timer);timer=null;play.setAttribute('aria-pressed','false');};
 const update=()=>{
  const k=Number(slider.value),r=record.rows[k];marker.setAttribute('cx',points[k][0]);marker.setAttribute('cy',points[k][1]);
  path.setAttribute('points',points.slice(0,k+1).map(p=>p.join(',')).join(' '));label.textContent='k = '+k;
  document.querySelector('[data-tight-x]').textContent=r.x.toPrecision(7);
  document.querySelector('[data-tight-gap]').textContent=r.gap.toPrecision(7);
  document.querySelector('[data-tight-gradient]').textContent=r.gradient.toPrecision(7);
 };
 slider.addEventListener('input',()=>{stop();update();});
 play.addEventListener('click',()=>{
  if(timer){stop();return;}if(Number(slider.value)>=Number(slider.max))slider.value='0';
  play.setAttribute('aria-pressed','true');update();timer=setInterval(()=>{
   if(Number(slider.value)>=Number(slider.max)){stop();return;}slider.value=String(Number(slider.value)+1);update();
  },450);
 });update();
})();'''


def tight_geometry_html(result):
    rows, c = result['rows'], result['config']
    body = '<style>'+CSS+'</style><div class="tight-views"><div>'+function_svg(result)+'</div><div>'+center_svg(result)+'</div></div>'
    body += '<p class="small">'+bi('첫 그림은 원래 좌표, 둘째는 u=x/a와 f/(La²)로 확대한 같은 함수의 중심입니다. N이 커져도 중심을 읽을 수 있습니다. 좁은 화면에서는 각 그림을 가로로 스크롤하세요.',
        'First: original units. Second: the same centre in u=x/a and f/(La²), resolved even at large N. On narrow screens, scroll each diagram horizontally.')+'</p>'
    body += '<div class="tight-controls"><button type="button" data-tight-play aria-pressed="false">'+bi('재생 / 일시정지','Play / pause')+'</button>'
    body += '<label for="tight-iteration">'+bi('실제 반복점','Recorded iterate')+'</label><input id="tight-iteration" data-tight-slider type="range" min="0" max="'+str(c['horizon'])+'" value="0"><strong data-tight-step>k = 0</strong></div>'
    body += '<div class="tight-readout" aria-live="polite">'
    for field, ko, en in [('x','위치 x','Position x'),('gap','목적함수 gap','Objective gap'),('gradient','기울기','Gradient')]:
        body += '<div>'+bi(ko,en)+'<strong data-tight-'+field+'>'+format(rows[0][field],'.7g')+'</strong></div>'
    body += '</div><div class="tight-proof"><h3>'+bi('마지막 값이 상계와 일치하는 이유','Why the final value attains the envelope')+'</h3>'
    body += '<div class="formula">a = R/(2Nh+1)\nx_N = R − Nha = (Nh+1)a > a\nf(x_N) = La²(Nh+½) = LR²/(4Nh+2)</div><p>'+bi(
        '모든 저장된 점이 양의 affine 구간에 있어 기울기는 La로 일정합니다. 한 갱신의 이동 거리는 ha입니다. 이 대입 계산은 구성의 달성값을 설명하며, 전체 함수 계열에 대한 상계의 증명은 정리 3.1에 있습니다.',
        'Every stored point lies in the positive affine region, so its gradient is La and each update moves ha. This substitution explains attainment by the construction; the class-wide upper-bound proof is Theorem 3.1.')+'</p></div>'
    body += '<details><summary>'+bi('모든 실제 반복점 보기','Inspect every recorded iterate')+'</summary><div class="scroll"><table><thead><tr><th>k</th><th>x</th><th>f(x)</th><th>gradient</th></tr></thead><tbody>'
    for r in rows:
        body += '<tr><td>'+str(r['iteration'])+'</td>'+''.join('<td>'+format(r[key],'.10g')+'</td>' for key in ('x','gap','gradient'))+'</tr>'
    # Script runs after the evidence block at the end of the shared page.
    return body+'</tbody></table></div></details>'
