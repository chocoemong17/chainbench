"""Independent scalar/Decimal audit of the periodic online-loss experiment."""
from __future__ import annotations

import hashlib
import json
import math
from decimal import Decimal, localcontext


def validate_adam_counterexample(data):
    def require(value, message='record differs'):
        if not value:
            raise RuntimeError('Adam counterexample: '+message)

    def close(actual, expected, *, absolute=2e-13, relative=3e-12):
        require(type(actual) in (int,float) and math.isfinite(actual)
                and math.isclose(actual,float(expected),abs_tol=absolute,rel_tol=relative), 'numeric value differs')

    require(data['kind']=='chainbench.adam-counterexample' and data['schema_version']==1)
    require(data['evidence_level']=='published-counterexample-family-with-declared-finite-instantiations')
    require(data['source']=={
        'authors':['Sashank J. Reddi','Satyen Kale','Sanjiv Kumar'],
        'title':'On the Convergence of Adam and Beyond', 'venue_year':2018,
        'version':'arXiv:1904.09237v1 (2019-04-19)', 'url':'https://arxiv.org/pdf/1904.09237v1',
        'adam':'Algorithm 1 / Eq. (1), p.3; no debiasing as in footnote 1',
        'counterexample':'Section 3 / Theorem 1, p.4; Appendix A / Eqs. (4)-(6), pp.10-11',
        'amsgrad':'Algorithm 2, p.5, specialized to beta1=0',
        'inverse_rate':'Eq. (2), p.4; current-minus-previous inverse learning rate for t>=2',
    }, 'source attribution differs')
    steps = data['parameters']['steps']
    require(type(steps) is int and 1<=steps<=12000,'invalid budget')
    require(data['parameters']=={
        'steps':steps,'C_values':[3,10,100],'alpha_fractions':[.1,.5,.9],
        'methods':['adam','amsgrad'],'seed':None,
        'design':'all 3 C values x 3 alpha fractions, both source variants, no outcome filtering',
    }, 'protocol differs')
    require(data['input_hash_encoding']=='SHA-256 of sorted-key compact JSON inputs, encoded UTF-8')
    require(data['series_indexing']=='x[j] is x_(j+1); every other series[j] belongs to round t=j+1')
    require(data['regret_definition']=='R_T=sum_(t=1)^T g_t*x_t - min_(x in [-1,1]) sum_(t=1)^T g_t*x')
    require(data['regret_computation']=='accumulate g_t*(x_t+1); retain difference from cumulative_loss-best_fixed_loss')
    require(data['initial_average_regret'] is None,'invented initial average')
    require([c['id'] for c in data['cases']]==[f'c{C}-a{a:g}' for C in (3,10,100) for a in (.1,.5,.9)],'case coverage differs')
    fields = {'x','first_moment','second_moment','denominator_memory','effective_rate',
              'inverse_rate','inverse_rate_difference','proposal','displacement','projection_correction',
              'loss','regret_increment','cumulative_loss','cumulative_regret','average_regret','loss_regret_difference'}
    with localcontext() as context:
        context.prec = 60
        square_roots = [Decimal(t).sqrt() for t in range(1,steps+1)]
        for case in data['cases']:
            inputs = case['inputs']
            C, fraction = inputs['C'], inputs['alpha_fraction']
            require(type(C) is int and C in (3,10,100) and fraction in (.1,.5,.9))
            require(case['id']==f'c{C}-a{fraction:g}')
            beta = 1/(1+C*C)
            alpha = fraction*math.sqrt(1-beta)
            require(inputs=={
                'C':C,'alpha_fraction':fraction,'alpha':alpha,'beta1':0.,'beta2':beta,
                'bias_correction':False,'epsilon':0.,'initial_x':1.,'initial_m':0.,
                'initial_v':0.,'initial_max_v':0.,'domain':[-1.,1.],'period':3,
                'gradient_pattern':[float(C),-1.,-1.],'steps':steps,
                'step_schedule':'alpha/sqrt(t), t=1..T',
                'loss_timing':'g_t*x_t before the update to x_(t+1)',
            }, 'source variant or input differs')
            require(0<alpha<math.sqrt(1-beta))
            digest = hashlib.sha256(json.dumps(inputs,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            require(case['input_sha256']==digest,'input fingerprint differs')
            require(case['rounds']==list(range(1,steps+1)))
            require(case['native_rounds']==sorted({t for t in (1,2,3,4,5,6,9,30,300,3000,steps) if t<=steps}))
            require(case['source_reference']=={
                'block_regret_lower':2*C-4,'average_regret_lower':2*(C-2)/3,
                'rounds':list(range(3,steps+1,3)),
                'scope':'Adam source variant, complete three-round blocks, x1=1 and stated alpha/beta conditions',
            }, 'source bound scope differs')
            require(case['best_fixed_point']==-1)
            close(case['cycle_mean_loss_slope'],(C-2)/3,absolute=0)
            for key in ('gradients','step_sizes','gradient_sums','best_fixed_cumulative_loss'):
                require(len(case[key])==steps,'schedule coverage differs')
            gradients = [C if t%3==1 else -1 for t in range(1,steps+1)]
            require(case['gradients']==gradients)
            for j in range(steps):
                t = j+1
                # Closed form, independent of the producer's cumulative addition.
                large_count = (t+2)//3
                total_gradient = C*large_count-(t-large_count)
                require(case['gradient_sums'][j]==total_gradient and total_gradient>0)
                require(case['best_fixed_cumulative_loss'][j]==-abs(total_gradient))
                close(case['step_sizes'][j],Decimal.from_float(alpha)/square_roots[j],absolute=0)
            require(set(case['runs'])=={'adam','amsgrad'},'method coverage differs')
            for method, run in case['runs'].items():
                require(run['method']==method and run['updates']==steps and run['termination']=='fixed_budget')
                series = run['series']
                require(set(series)==fields,'series coverage differs')
                require(all(len(values)==steps+int(key=='x') for key,values in series.items()),'round coverage differs')
                require(series['x'][0]==1)
                x, variance, maximum = Decimal(1), Decimal(0), Decimal(0)
                beta_decimal, alpha_decimal = Decimal.from_float(beta), Decimal.from_float(alpha)
                regret_decimal = Decimal(0)
                actual_loss_sum, actual_regret_sum = Decimal(0), Decimal(0)
                for j,g in enumerate(gradients):
                    t = j+1
                    # Independent recurrence: all arithmetic stays at 60 digits,
                    # including sqrt(t) and the normalization; do not reuse a
                    # stored proposal or a production helper to compute x_next.
                    regret_decimal += Decimal(g)*(x+1)
                    variance = beta_decimal*variance+(1-beta_decimal)*g*g
                    maximum = max(maximum,variance)
                    memory = maximum if method=='amsgrad' else variance
                    rate = alpha_decimal/square_roots[j]/memory.sqrt()
                    proposed = x-rate*g
                    following = max(Decimal(-1),min(Decimal(1),proposed))
                    close(series['x'][j],x)
                    close(series['x'][j+1],following)
                    require(-1<=series['x'][j+1]<=1)
                    require(series['first_moment'][j]==g)
                    close(series['second_moment'][j],variance,absolute=0)
                    close(series['denominator_memory'][j],memory,absolute=0)
                    close(series['effective_rate'][j],rate,absolute=0)
                    close(series['inverse_rate'][j],1/rate,absolute=0)
                    close(series['proposal'][j],proposed)
                    if j==0:
                        require(series['inverse_rate_difference'][j] is None,'invented prior learning rate')
                    else:
                        require(series['inverse_rate_difference'][j]==series['inverse_rate'][j]-series['inverse_rate'][j-1])
                    actual_x, next_x = series['x'][j:j+2]
                    require(series['displacement'][j]==next_x-actual_x,'actual displacement differs')
                    require(series['projection_correction'][j]==next_x-series['proposal'][j])
                    require(series['loss'][j]==g*actual_x,'loss used the wrong iterate')
                    require(series['regret_increment'][j]==g*(actual_x+1))
                    actual_loss_sum += Decimal.from_float(series['loss'][j])
                    actual_regret_sum += Decimal.from_float(series['regret_increment'][j])
                    close(series['cumulative_loss'][j],actual_loss_sum,absolute=2e-10)
                    close(series['cumulative_regret'][j],actual_regret_sum,absolute=2e-10)
                    close(series['cumulative_regret'][j],regret_decimal,absolute=2e-10)
                    require(series['average_regret'][j]==series['cumulative_regret'][j]/t)
                    require(series['loss_regret_difference'][j]==series['cumulative_regret'][j]-(series['cumulative_loss'][j]+case['gradient_sums'][j]))
                    x = following
                if method=='adam':
                    require(all(x>0 for x in series['x']),'source positive-state property failed')
                    require(all(x==1 for x in series['x'][::3]),'source return state failed')
                else:
                    require(all(v>=0 for v in series['inverse_rate_difference'][1:]),'max-memory inverse rate decreased')
                require(len(run['complete_cycles'])==steps//3,'cycle coverage differs')
                for j, cycle in enumerate(run['complete_cycles']):
                    start = 3*j
                    actual = math.fsum(series['regret_increment'][start:start+3])
                    lower = 2*C-4 if method=='adam' else None
                    require(cycle=={
                        'first_round':start+1,'last_round':start+3,
                        'start_x':series['x'][start],'end_x':series['x'][start+3],
                        'regret':actual,'source_lower':lower,
                        'lower_margin':actual-lower if lower is not None else None,
                    },'cycle values or source scope differ')
                    if lower is not None:
                        require(actual>=lower,'finite block regret lies below its source lower bound')
                require(run['observations']=={
                    'final_x':series['x'][-1],'min_x':min(series['x']),'max_x':max(series['x']),
                    'final_average_regret':series['average_regret'][-1],
                    'inverse_rate_decreases':[j+1 for j,v in enumerate(series['inverse_rate_difference']) if v is not None and v<0],
                    'projection_rounds':[j+1 for j,v in enumerate(series['projection_correction']) if v!=0],
                    'computed_cycle_start_states_equal_one':all(v==1 for v in series['x'][::3]),
                    'all_computed_states_positive':all(v>0 for v in series['x']),
                },'finite observations differ from the stored path')


def exercise_adam_counterexample(cli, work, env, run, extract_record):
    for steps in (1,4,3000,12000):
        args = [cli,'reproduce','reddi-2018','--steps',str(steps)]
        data = json.loads(run(args+['--format','json'],work,env))
        validate_adam_counterexample(data)
        if steps!=12000:
            html = run(args+['--lang','ko'],work,env)
            if extract_record(html)!=data:
                raise RuntimeError('Adam counterexample HTML differs from independently checked JSON')
