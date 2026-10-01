"""Independent scalar/Decimal audit; imports neither ChainBench nor NumPy."""
import hashlib
import itertools
import json
import math
from decimal import Decimal, localcontext


def require(condition, message):
    if not condition:
        raise RuntimeError('ADMM geometry: '+message)


def near(actual, expected):
    if isinstance(expected,(list,tuple)):
        require(isinstance(actual,list) and len(actual)==len(expected),'vector size differs')
        for a,e in zip(actual,expected):
            near(a,e)
    elif expected is None:
        require(actual is None,'invented initial value')
    else:
        require(type(actual) in (int,float) and math.isfinite(actual),'missing or non-finite number')
        require(math.isclose(actual,float(expected),rel_tol=3e-11,abs_tol=5e-13),'numeric value differs')


def mv(A,x):
    return [sum(a*b for a,b in zip(row,x)) for row in A]


def norm(x):
    return sum(v*v for v in x).sqrt()


def solve2(H,q):
    determinant = H[0][0]*H[1][1]-H[0][1]*H[1][0]
    return [(H[1][1]*q[0]-H[0][1]*q[1])/determinant,
            (H[0][0]*q[1]-H[1][0]*q[0])/determinant]


def shrink(x,level):
    return [max(v-level,Decimal(0))+min(v+level,Decimal(0)) for v in x]


def value(w,A,b,lam):
    return sum((a-c)**2 for a,c in zip(mv(A,w),b))/2+lam*sum(map(abs,w))


def closed_optimum(family,fraction,lam):
    # Independently derived active regimes for these declared fixtures. This
    # does not repeat the runtime's numerical enumeration of sign patterns.
    if family=='diagonal':
        return [max(Decimal('1.4')-lam,Decimal(0)), -max(Decimal('7.2')-lam,Decimal(0))/9]
    if fraction==.1:
        return [Decimal(26)/15-lam,-Decimal(31)/15+lam]
    if fraction==.6:
        return [Decimal(0),(lam-Decimal('3.4'))/5]
    return [Decimal(0),Decimal(0)]


def validate_admm_geometry(data):
    require(data['kind']=='chainbench.admm-lasso-geometry' and data['schema_version']==1,'record type differs')
    require(data['evidence_level']=='controlled-geometric-illustrations','evidence level differs')
    require(data['source']['url']=='https://web.stanford.edu/~boyd/papers/pdf/admm_distr_stats.pdf'
            and data['source']['year']==2011
            and data['source']['role']=='review of an algorithm originating in the 1970s','source attribution differs')
    require(data['source']['recurrence']=='Section 6.4 / Eq. (6.2) and displayed updates, printed p.43 / PDF page 46'
            and data['source']['residuals']=='Section 3.3, printed pp.18-19 / PDF pages 21-22; Eq. (3.12)','source locator differs')
    require(data['problem']['constraint_matrices']=='I and -I, distinct from the feature matrix A'
            and data['problem']['seed'] is None,'problem interpretation differs')
    require(data['geometry']['surface_height']=='stable algebraic F(w)-F*, not the infeasible split value f(x)+g(z)-F*','surface meaning differs')
    require(data['geometry']['dual_coordinates']=='y=rho*u in feature coordinates; not measurement-space residual dual variables','dual coordinate meaning differs')
    steps = data['parameters']['steps']
    require(type(steps) is int and 1<=steps<=160,'budget differs')
    require(data['parameters']==dict(steps=steps,families=['diagonal','coupled'],lambda_fractions=[.1,.6,1.1],
        starts=['zero','opposite'],rhos=[.1,1.,10.],abs_tol=1e-4,rel_tol=1e-2,relaxation=1.),'factorial design differs')
    design = list(itertools.product(('diagonal','coupled'),(.1,.6,1.1),('zero','opposite'),(.1,1.,10.)))
    require(len(data['cases'])==len(design),'missing or extra case')
    all_points = []
    with localcontext() as context:
        context.prec = 60
        for case,(family,fraction,start_name,rho_float) in zip(data['cases'],design):
            require(case['id']==f'{family}-lambda{fraction:g}-{start_name}-rho{rho_float:g}'
                    and case['family']==family and case['start_name']==start_name,'case identity/order differs')
            inputs = case['inputs']
            matrix = [[1.,0.],[0.,3.]] if family=='diagonal' else [[2.,1.],[1.,2.]]
            start = [0.,0.] if start_name=='zero' else [-1.8,1.2]
            maximum = max(abs(sum(matrix[j][i]*[1.4,-2.4][j] for j in range(2))) for i in range(2))
            expected_inputs = dict(A=matrix,b=[1.4,-2.4],dimension=2,lambda_fraction=fraction,
                lambda_max=maximum,**{'lambda':fraction*maximum},rho=rho_float,z0=start,u0=[0.,0.],
                initial_x=None,relaxation=1.,abs_tol=1e-4,rel_tol=1e-2,steps=steps,
                penalty_policy='fixed rho',stopping_policy='fixed budget; record <= residual test without early exit')
            require(inputs==expected_inputs,'declared inputs differ')
            encoded = json.dumps(inputs,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            require(case['input_sha256']==hashlib.sha256(encoded).hexdigest(),'input fingerprint differs')
            require(case['smooth_spectrum']==[1.,9.] and case['smooth_condition']==9.,'smooth spectrum differs')
            A = [[Decimal(str(v)) for v in row] for row in matrix]
            AT = list(map(list,zip(*A)))
            b = [Decimal('1.4'),Decimal('-2.4')]
            Q = [[sum(AT[i][k]*A[k][j] for k in range(2)) for j in range(2)] for i in range(2)]
            c = mv(AT,b)
            lam,rho = Decimal(str(inputs['lambda'])),Decimal(str(rho_float))
            star = closed_optimum(family,fraction,lam)
            optimum = value(star,A,b,lam)
            gradient = [a-b for a,b in zip(mv(Q,star),c)]
            subgradient = [-v/lam for v in gradient]
            near(case['optimum']['point'],star)
            near(case['optimum']['value'],optimum)
            near(case['optimum']['subgradient'],subgradient)
            near(case['optimum']['stationarity_residual'],[0,0])
            require(case['optimum']['active_coordinates']==[i for i,v in enumerate(star) if v!=0],'active regime differs')
            require(all(abs(v)<=1+Decimal('1e-55') for v in subgradient),'independent optimum fails KKT box')
            for x,g in zip(star,subgradient):
                if x:
                    require(abs(g-(1 if x>0 else -1))<Decimal('1e-55'),'independent optimum fails active KKT')
            require(case['updates']==steps and case['termination']=='fixed_budget','invented stop or missing update')
            require(case['native_iterations']==sorted({k for k in (0,1,2,5,10,30,60,160,steps) if k<=steps}),'native coverage differs')
            rows = case['rows']
            require(len(rows)==steps+1,'row count differs')
            z = list(map(lambda v:Decimal(str(v)),start))
            u = [Decimal(0),Decimal(0)]
            H = [[Q[i][j]+(rho if i==j else 0) for j in range(2)] for i in range(2)]
            first_pass = None
            for k,row in enumerate(rows):
                require(row['iteration']==k,'iteration order differs')
                if k==0:
                    for name in ('x','x_target','x_rhs','x_equation_residual','shrink_input','primal_residual',
                                 'dual_residual','primal_norm','dual_norm','eps_primal','eps_dual',
                                 'stopping_passed','dual_stationarity','dual_identity_residual','dual_box_excess',
                                 'objective_x','split_objective','stable_gap_x','split_minus_optimum'):
                        near(row[name],None)
                else:
                    prior = z[:]
                    target = [a-b for a,b in zip(z,u)]
                    rhs = [c[i]+rho*target[i] for i in range(2)]
                    x = solve2(H,rhs)
                    shrink_input = [a+b for a,b in zip(x,u)]
                    z = shrink(shrink_input,lam/rho)
                    primal = [a-b for a,b in zip(x,z)]
                    u = [a+b for a,b in zip(u,primal)]
                    dual = [-rho*(a-b) for a,b in zip(z,prior)]
                    y = [rho*v for v in u]
                    ep = Decimal(2).sqrt()*Decimal('1e-4')+Decimal('.01')*max(norm(x),norm(z))
                    ed = Decimal(2).sqrt()*Decimal('1e-4')+Decimal('.01')*norm(y)
                    split = sum((a-b)**2 for a,b in zip(mv(A,x),b))/2+lam*sum(map(abs,z))
                    expected = dict(x=x,x_target=target,x_rhs=rhs,x_equation_residual=[0,0],shrink_input=shrink_input,
                        primal_residual=primal,dual_residual=dual,primal_norm=norm(primal),dual_norm=norm(dual),
                        eps_primal=ep,eps_dual=ed,dual_stationarity=dual,dual_identity_residual=[0,0],
                        dual_box_excess=[abs(v)-lam for v in y],objective_x=value(x,A,b,lam),
                        split_objective=split,stable_gap_x=value(x,A,b,lam)-optimum,split_minus_optimum=split-optimum)
                    for key,v in expected.items():
                        near(row[key],v)
                    # Bind rounded subtraction fields to the retained floats;
                    # mathematical zero is not substituted for raw differences.
                    require(row['primal_residual']==[a-b for a,b in zip(row['x'],row['z'])],'raw primal difference differs')
                    require(row['dual_identity_residual']==[a-b for a,b in zip(row['dual_stationarity'],row['dual_residual'])],'raw stationarity difference differs')
                    require(row['dual_box_excess']==[abs(v)-inputs['lambda'] for v in row['y']],'raw box excess differs')
                    require(row['split_minus_optimum']==row['split_objective']-case['optimum']['value'],'raw split difference differs')
                    passed = row['primal_norm']<=row['eps_primal'] and row['dual_norm']<=row['eps_dual']
                    require(type(row['stopping_passed']) is bool and row['stopping_passed']==passed,'residual decision differs')
                    if passed and first_pass is None:
                        first_pass = k
                    all_points.append(row['x'])
                near(row['z'],z)
                near(row['u'],u)
                near(row['y'],[rho*v for v in u])
                fz = value(z,A,b,lam)
                near(row['objective_z'],fz)
                near(row['stable_gap_z'],fz-optimum)
                near(row['raw_gap_z'],fz-optimum)
                require(row['stable_gap_z']>=0,'negative algebraic original-primal gap')
                require(row['raw_gap_z']==row['objective_z']-case['optimum']['value'],'raw objective subtraction differs')
                require(row['gap_roundoff_difference']==row['raw_gap_z']-row['stable_gap_z'],'gap roundoff field differs')
                all_points.append(row['z'])
            require(case['first_residual_pass']==first_pass,'first diagnostic pass differs')
            observed = dict(final_primal_norm=rows[-1]['primal_norm'],final_dual_norm=rows[-1]['dual_norm'],
                final_stable_gap=rows[-1]['stable_gap_z'],final_residual_pass=rows[-1]['stopping_passed'],
                split_below_optimum_rounds=[r['iteration'] for r in rows[1:] if r['split_minus_optimum']<0],
                primal_objective_increase_rounds=[k for k in range(1,len(rows)) if rows[k]['objective_z']-rows[k-1]['objective_z']>1e-12])
            require(case['observations']==observed,'finite observations differ')
            all_points.append(case['optimum']['point'])
    radius = max(1.,math.ceil(max(abs(v) for p in all_points for v in p)*1.1*2)/2)
    require(data['geometry']['primal_bounds']==[-radius,radius,-radius,radius],'shared geometry bounds differ')


def exercise_admm_geometry(cli, work, env, run, extract_record):
    for steps in (1,60,160):
        args = [cli,'geometry','admm-lasso','--steps',str(steps)]
        data = json.loads(run(args+['--format','json'],work,env))
        validate_admm_geometry(data)
        html = run(args+['--lang','ko'],work,env)
        if extract_record(html)!=data or html.count('data-admm-case=')!=36:
            raise RuntimeError('ADMM HTML differs from independently audited full JSON or omits cases')
