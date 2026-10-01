"""Independent 60-digit audit; no ChainBench or NumPy imports."""
import hashlib
import itertools
import json
import math
from decimal import Decimal, localcontext


def require(condition, message):
    if not condition:
        raise RuntimeError('FISTA backtracking: '+message)


def near(actual, expected):
    if isinstance(expected, (list, tuple)):
        require(isinstance(actual, list) and len(actual)==len(expected), 'vector length differs')
        for a, e in zip(actual, expected):
            near(a, e)
    else:
        require(type(actual) in (int, float) and math.isfinite(actual), 'missing/nonfinite numeric evidence')
        require(math.isclose(actual, float(expected), rel_tol=3e-11, abs_tol=5e-13), 'numeric evidence differs')


def dec(value):
    return Decimal.from_float(value) if type(value) is float else Decimal(value)


def vector(values):
    return list(map(dec, values))


def shrink(values, threshold):
    return [max(v-threshold, Decimal(0))+min(v+threshold, Decimal(0)) for v in values]


def value(point, lam):
    return ((point[0]-Decimal('1.4'))**2+(3*point[1]+Decimal('2.4'))**2)/2+lam*sum(map(abs, point))


def audit_slice(record, trial, stage, lam, optimum):
    y, q, L = vector(stage['anchor']), vector(trial['point']), dec(trial['L'])
    direction = [a-b for a, b in zip(trial['point'], stage['anchor'])]
    parameters = {-.25+i/32 for i in range(49)}
    for a, d in zip(stage['anchor'], direction):
        if d and -.25 < -a/d < 1.25:
            parameters.add(-a/d)
    require(record['parameter']==sorted(parameters), 'slice samples/corners differ')
    require(type(record['zero_direction']) is bool and record['zero_direction']==(q==y), 'zero-direction state differs')
    require(all(len(record[key])==len(parameters) for key in ('points', 'objective_gap', 'model_gap')), 'slice truncation')
    for s, p, f, model in zip(record['parameter'], record['points'], record['objective_gap'], record['model_gap']):
        point = [a+dec(s)*d for a, d in zip(y, vector(direction))]
        if s==0:
            require(p==stage['anchor'], 'slice anchor not pinned')
            point = y
        if s==1:
            require(p==trial['point'], 'slice candidate not pinned')
            point = q
        near(p, point)
        objective = value(point, lam)-optimum
        difference = sum((a-L)*(v-w)**2 for a, v, w in zip((1,9), point, y))/2
        near(f, objective)
        near(model, objective-difference)


def validate_fista_backtracking(data):
    require(data['kind']=='chainbench.fista-backtracking-geometry' and data['schema_version']==1, 'record identity differs')
    require(data['evidence_level']=='controlled-geometric-illustrations', 'evidence level differs')
    require(data['source']['url']=='https://www.tau.ac.il/~becka/FISTA.pdf'
        and data['source']['algorithm']=='Unnumbered FISTA with backtracking panel, printed p.194 / PDF page 12'
        and data['source']['bound']=='Theorem 4.4 / Eq. (4.4), printed p.195 / PDF page 13; alpha=eta=2', 'source locator differs')
    require(data['problem']==dict(objective='F(x)=0.5||diag(a)x-b||_2^2+lambda||x||_1',
        smooth_L=9., smooth_mu=1., dimension=2, seed=None), 'problem interpretation differs')
    steps = data['parameters']['steps']
    starts = {'opposite':[-1.8,1.2], 'zero':[0.,0.], 'near':[2.,-1.4], 'low-mode':[-3.,-.8]}
    require(type(steps) is int and 1<=steps<=60, 'invalid budget')
    require(data['parameters']==dict(steps=steps,lambdas=[.1,.8,1.8],starts=list(starts),
        initial_L=[.25,1.,4.],eta=2.), 'factorial design differs')
    require(data['gate']==dict(condition='F(q)<=Q_L(q,y)',
        evaluated_difference='0.5*sum((a_i^2-L)*(q_i-y_i)^2)',
        arithmetic='Quadratic identity in float64, no added acceptance tolerance; retain raw F-Q separately.',
        scope='Candidate test at the extrapolated anchor; not a global upper-model certificate or monotone objective test.'), 'gate contract differs')
    require(data['geometry']==dict(slice='u(s)=y+s*(q-y)', interval=[-.25,1.25], base_samples=49,
        corners='Include 0, 1 and every coordinate zero crossing strictly inside the interval.',
        height='Stable F(u)-F* and Q_L(u,y)-F*; rejected models may lie below zero.',
        paths='Only accepted x iterates form trajectories; rejected q are trial proposals.'), 'geometry contract differs')
    design = list(itertools.product((.1,.8,1.8), starts, (.25,1.,4.)))
    require(len(data['cases'])==36, 'missing/extra runs')
    with localcontext() as context:
        context.prec = 60
        for case, (lam_float, name, initial) in zip(data['cases'], design):
            require(case['id']==f'lambda{lam_float:g}-{name}-L{initial:g}' and case['start_name']==name, 'case order differs')
            inputs = dict(a=[1.,3.],b=[1.4,-2.4],**{'lambda':lam_float},x0=starts[name],
                initial_L=initial,eta=2.,steps=steps,initial_t=1.,
                policy='carry accepted L forward; double after a rejected trial',
                stopping='fixed budget; no early stopping')
            require(case['inputs']==inputs, 'inputs differ')
            fingerprint = hashlib.sha256(json.dumps(inputs,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            require(case['input_sha256']==fingerprint, 'input hash differs')
            lam = Decimal(str(lam_float))
            star = [max(Decimal('1.4')-lam,Decimal(0)), -max(Decimal('7.2')-lam,Decimal(0))/9]
            optimum = value(star, lam)
            near(case['optimum']['point'], star)
            near(case['optimum']['value'], optimum)
            x = [Decimal(str(v)) for v in starts[name]]
            y, t, L = x[:], Decimal(1), initial
            radius2 = sum((v-w)**2 for v, w in zip(x, star))
            near(case['radius_squared'], radius2)
            rows, stages = case['rows'], case['stages']
            require(case['updates']==steps and case['termination']=='fixed_budget'
                and len(rows)==steps+1 and len(stages)==steps, 'budget or termination differs')
            require(rows[0]['x']==starts[name] and rows[0]['bound'] is None
                and rows[0]['stable_gap_change'] is None, 'initial state differs')
            for k, row in enumerate(rows):
                require(row['iteration']==k, 'row order differs')
                if k:
                    stage = stages[k-1]
                    require(stage['iteration']==k and stage['previous_x']==rows[k-1]['x']
                        and stage['carried_L']==L, 'stage/carried curvature differs')
                    if k==1:
                        require(stage['anchor']==starts[name] and stage['t']==1., 'initial anchor differs')
                    else:
                        require(stage['anchor']==stages[k-2]['next_anchor'] and stage['t']==stages[k-2]['next_t'], 'momentum carry differs')
                    near(stage['anchor'], y)
                    gradient = [y[0]-Decimal('1.4'),9*y[1]+Decimal('7.2')]
                    near(stage['gradient'], gradient)
                    near(stage['t'], t)
                    near(stage['previous_gap'], rows[k-1]['stable_gap'])
                    near(stage['anchor_gap'], value(y,lam)-optimum)
                    trials = stage['trials']
                    require(1<=len(trials)<=7, 'trial count differs')
                    for j, trial in enumerate(trials):
                        require(trial['attempt']==j and trial['L']==L*2**j, 'trial order/curvature differs')
                        trial_L = dec(trial['L'])
                        near(trial['step_size'],1/trial_L)
                        near(trial['threshold'],lam/trial_L)
                        z = [v-g/trial_L for v,g in zip(y,gradient)]
                        q = shrink(z,lam/trial_L)
                        near(trial['gradient_step'],z)
                        near(trial['point'],q)
                        require(trial['zeroed']==[abs(v)<=trial['threshold'] for v in trial['gradient_step']]
                            and all(type(v) is bool for v in trial['zeroed']), 'shrinkage status differs')
                        require(trial['displacement']==[v-w for v,w in zip(trial['point'],stage['anchor'])], 'rounded displacement differs')
                        # Audit the small signed gate against its actual rounded operands,
                        # with relative term-scale error, never a fixed absolute floor.
                        terms = [(a-trial_L)*d*d/2 for a,d in zip((1,9),vector(trial['displacement']))]
                        expected = sum(terms)
                        actual = trial['stable_model_difference']
                        require(type(actual) in (int,float) and math.isfinite(actual), 'nonfinite gate')
                        require(abs(dec(actual)-expected)<=Decimal('2e-12')*sum(map(abs,terms)), 'stable gate identity differs')
                        require(type(trial['accepted']) is bool and trial['accepted']==(actual<=0)
                            and trial['accepted']==(j==len(trials)-1), 'first passing trial not used')
                        require(trial['raw_model_difference']==trial['objective']-trial['raw_model'], 'raw gate subtraction differs')
                        require(type(trial['raw_would_accept']) is bool
                            and trial['raw_would_accept']==(trial['raw_model_difference']<=0), 'raw gate decision differs')
                        fy = value(y,lam)-lam*sum(map(abs,y))
                        delta = [v-w for v,w in zip(q,y)]
                        model = fy+sum(g*d for g,d in zip(gradient,delta))+trial_L*sum(d*d for d in delta)/2+lam*sum(map(abs,q))
                        near(trial['objective'],value(q,lam))
                        near(trial['raw_model'],model)
                        near(trial['stable_gap'],value(q,lam)-optimum)
                        near(trial['stable_model_gap'],model-optimum)
                        require(trial['stable_model_gap']==trial['stable_gap']-actual, 'model gap shift differs')
                        audit_slice(trial['slice'],trial,stage,lam,optimum)
                    L = trials[-1]['L']
                    require(stage['accepted_L']==L and L<=16 and row['x']==trials[-1]['point'], 'accepted update differs')
                    tn = (1+(1+4*t*t).sqrt())/2
                    beta = (t-1)/tn
                    near(stage['next_t'],tn)
                    near(stage['next_momentum'],beta)
                    y = [v+beta*(v-w) for v,w in zip(q,x)]
                    x, t = q, tn
                    near(stage['next_anchor'],y)
                    near(row['bound'],36*radius2/(k+1)**2)
                    require(row['stable_gap_change']==row['stable_gap']-rows[k-1]['stable_gap'], 'gap change differs')
                    require(row['stable_gap']<=row['bound']*(1+1e-10), 'finite envelope violation')
                near(row['x'],x)
                near(row['objective'],value(x,lam))
                near(row['stable_gap'],value(x,lam)-optimum)
                require(row['stable_gap']>=0 and row['raw_gap']==row['objective']-case['optimum']['value'], 'gap meaning differs')
            expected_observations = dict(total_trials=sum(len(s['trials']) for s in stages),
                rejected_trials=sum(len(s['trials'])-1 for s in stages),
                accepted_L_changes=[dict(iteration=s['iteration'],L=s['accepted_L']) for i,s in enumerate(stages)
                    if i==0 or s['accepted_L']!=stages[i-1]['accepted_L']],
                objective_increase_rounds=[r['iteration'] for r in rows[1:] if r['stable_gap_change']>1e-12],
                raw_gate_disagreements=[dict(iteration=s['iteration'],attempt=v['attempt'])
                    for s in stages for v in s['trials'] if v['accepted']!=v['raw_would_accept']])
            require(case['observations']==expected_observations, 'finite observation summary differs')


def exercise_fista_backtracking(cli, work, env, run, extract_record):
    for steps in (1,18,60):
        args = [cli,'geometry','fista-backtracking','--steps',str(steps)]
        record = json.loads(run(args+['--format','json'],work,env))
        validate_fista_backtracking(record)
        html = run(args+['--lang','ko'],work,env)
        require(extract_record(html)==record and html.count('data-bt-case=')==36, 'HTML omits or changes audited evidence')
