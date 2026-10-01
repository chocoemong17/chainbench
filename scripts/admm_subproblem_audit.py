"""Independent scalar checks of the actual subproblem SVGs and selected DOM state."""
import math
import re

MODEL_STATIC = r"""el=>{
 const shown=e=>e.checkVisibility()&&getComputedStyle(e).visibility==='visible'&&Number(getComputedStyle(e).opacity)>0;
 const x=el.querySelector('[data-admm-x-model]'),z=el.querySelector('[data-admm-shrink]');
 if(!x||!z)return null;
 return {radius:x.dataset.radius,bound:z.dataset.bound,tau:z.dataset.tau,
  titles:[x.querySelector('text').textContent,z.querySelector('text').textContent],
  levels:[...x.querySelectorAll('[data-admm-model-level]')].map(e=>[Number(e.dataset.admmModelLevel),JSON.parse(e.dataset.offsets),e.getAttribute('points'),shown(e)]),
  bands:[...z.querySelectorAll('[data-admm-shrink-band]')].map(e=>[e.dataset.admmShrinkBand,...['x','y','width','height'].map(a=>e.getAttribute(a)),shown(e)]),
  native:[...el.querySelectorAll('[data-admm-model-native]')].map(e=>[Number(e.dataset.admmModelNative),...[...e.querySelectorAll('td')].slice(1).map(c=>c.textContent)])};
}"""

MODEL_FRAME = r"""(el,k)=>{
 const shown=e=>e.checkVisibility()&&getComputedStyle(e).visibility==='visible'&&Number(getComputedStyle(e).opacity)>0;
 const x=el.querySelector('[data-admm-x-model]'),z=el.querySelector('[data-admm-shrink]');
 if(!x||!z)return null;
 return {body:el.querySelector('[data-admm-model-body]').checkVisibility(),
  initial:el.querySelector('[data-admm-model-initial]').checkVisibility(),
  fields:[...el.querySelectorAll('[data-admm-model-read]')].map(e=>[e.dataset.admmModelRead,e.textContent]),
  center:x.querySelector('[data-admm-model-center]').getAttribute('transform'),
  points:[...x.querySelectorAll('[data-admm-model-point]')].map(e=>[e.dataset.admmModelPoint,e.getAttribute('cx'),e.getAttribute('cy'),shown(e)]),
  shrink:[...z.querySelectorAll('[data-admm-shrink-point]')].map(e=>[e.dataset.admmShrinkPoint,e.getAttribute('cx'),e.getAttribute('cy'),shown(e)]),
  arrows:[...z.querySelectorAll('[data-admm-shrink-move]')].map(e=>[e.dataset.admmShrinkMove,e.getAttribute('d'),shown(e)])};
}"""


def require(ok, message):
    if not ok:
        raise RuntimeError('ADMM subproblems: '+message)


def near(actual,expected,absolute=.00051,relative=0):
    value = float(actual)
    require(math.isfinite(value) and math.isclose(value,expected,abs_tol=absolute,rel_tol=relative),
            f'value {value} differs from {expected}')


def readout(actual, expected):
    if expected is None:
        require(actual=='—','invented initial previous state')
    elif isinstance(expected,list):
        require(actual.startswith('(') and actual.endswith(')'),'vector formatting')
        values = actual[1:-1].split(', ')
        require(len(values)==len(expected),'vector dimension')
        for a,b in zip(values,expected):
            readout(a,b)
    else:
        near(actual,expected,0,5.1e-7)


def bound_for(case):
    ip = case['inputs']
    values = [ip['lambda']/ip['rho']]
    for row in case['rows'][1:]:
        values.extend(abs(v) for v in row['shrink_input'])
        values.extend(abs(v) for v in row['z'])
    return 1.15*max(values)


def validate_model_static(case,radius,view):
    require(view is not None,'missing subproblem views')
    near(view['radius'],radius,0)
    bound,tau = bound_for(case),case['inputs']['lambda']/case['inputs']['rho']
    near(view['bound'],bound,0)
    near(view['tau'],tau,0)
    require(view['titles']==['Current x subproblem: Hx(w) − Hx(x_new)',
                            'z_new = soft(v, τ), v = x_new + u_old'],'metric or old-memory label differs')
    require([v[0] for v in view['levels']]==[.1,.5,2.,10.],'model level coverage')
    A,rho = case['inputs']['A'],case['inputs']['rho']
    for level,offsets,pixels,visible in view['levels']:
        require(visible,'missing model contour')
        pairs = [p.split(',') for p in pixels.split()]
        require(len(offsets)==len(pairs)==129,'model contour sample coverage')
        for i,(d,p) in enumerate(zip(offsets,pairs)):
            require(len(d)==len(p)==2,'model contour dimension')
            # Evaluate the centered quadratic directly in data coordinates;
            # no renderer Hessian, eigenvectors or radial routine is imported.
            value = .5*(sum(sum(a*v for a,v in zip(row,d))**2 for row in A)+rho*sum(v*v for v in d))
            near(value,level,3e-11)
            theta = 2*math.pi*i/128
            near(d[0]*math.sin(theta)-d[1]*math.cos(theta),0,1e-12)
            require(d[0]*math.cos(theta)+d[1]*math.sin(theta)>0,'wrong model ray')
            near(p[0],180*d[0]/radius)
            near(p[1],-180*d[1]/radius)
    require([b[0] for b in view['bands']]==['0','1'],'threshold band coverage')
    for i,(_,x,y,width,height,visible) in enumerate(view['bands']):
        require(visible,'missing threshold band')
        for observed,expected in zip((x,y,width,height),(330-250*tau/bound,128+180*i,500*tau/bound,44)):
            near(observed,expected)
    require([r[0] for r in view['native']]==case['native_iterations'],'native model iteration coverage')
    for k,*actual in view['native']:
        expected = [None]*4
        if k:
            old,row = case['rows'][k-1],case['rows'][k]
            expected = [old['z'],old['u'],[z-u for z,u in zip(old['z'],old['u'])],
                        [x+u for x,u in zip(row['x'],old['u'])]]
        require(len(actual)==4,'native model column coverage')
        for a,b in zip(actual,expected):
            readout(a,b)


def validate_model_frame(case,radius,k,view):
    require(view is not None,'missing subproblem frame')
    require(view['body']==(k>0) and view['initial']==(k==0),'initial/defined model visibility')
    if not k:
        return
    ip,row,old = case['inputs'],case['rows'][k],case['rows'][k-1]
    a = [z-u for z,u in zip(old['z'],old['u'])]
    v = [x+u for x,u in zip(row['x'],old['u'])]
    d = [z-x for z,x in zip(old['z'],row['x'])]
    gap = .5*(sum(sum(Ai*di for Ai,di in zip(A,d))**2 for A in ip['A'])+ip['rho']*sum(di*di for di in d))
    wanted = [('old_z',old['z']),('old_u',old['u']),('target',a),('old_z_gap',gap),
              ('v',v),('tau',ip['lambda']/ip['rho']),('new_z',row['z'])]
    require([f[0] for f in view['fields']]==[f[0] for f in wanted],'model readout coverage')
    for (_,actual),(_,expected) in zip(view['fields'],wanted):
        readout(actual,expected)
    translate = re.fullmatch(r'translate\(([^ ]+) ([^ ]+)\)',view['center'])
    require(translate is not None,'malformed model translation')
    center = [330+180*row['x'][0]/radius,245-180*row['x'][1]/radius]
    for actual,expected in zip(translate.groups(),center):
        near(actual,expected)
    require([p[0] for p in view['points']]==['old_z','x'],'model point coverage')
    for (_,x,y,visible),w in zip(view['points'],(old['z'],row['x'])):
        require(visible,'missing model point')
        near(x,330+180*w[0]/radius)
        near(y,245-180*w[1]/radius)
    bound = bound_for(case)
    expected_points = [(f'{name}:{i}',330+250*value/bound,150+180*i+dy)
                       for i in range(2) for name,value,dy in [('v',v[i],-14),('z',row['z'][i],14)]]
    require([p[0] for p in view['shrink']]==[p[0] for p in expected_points],'shrink point coverage')
    for (_,x,y,visible),(_,ex,ey) in zip(view['shrink'],expected_points):
        require(visible,'missing shrink point')
        near(x,ex)
        near(y,ey)
    require([a[0] for a in view['arrows']]==['0','1'],'shrink arrow coverage')
    for i,(_,path,visible) in enumerate(view['arrows']):
        require(visible,'missing shrink arrow')
        coords = re.fullmatch(r'M([^ ]+) ([^ ]+) L([^ ]+) ([^ ]+)',path)
        require(coords is not None,'malformed shrink arrow')
        for actual,expected in zip(coords.groups(),(330+250*v[i]/bound,136+180*i,
                                                    330+250*row['z'][i]/bound,164+180*i)):
            near(actual,expected)
