"""Independent finite-state and rational checks; no ChainBench package imports."""

import hashlib
import json
import math
from fractions import Fraction


def validate_kaczmarz(data):
    def require(condition):
        if not condition:
            raise RuntimeError('Kaczmarz evidence differs from the declared construction')

    def close(actual, expected):
        require(math.isfinite(actual) and math.isclose(actual, float(expected), rel_tol=3e-14, abs_tol=1e-30))

    params = data['parameters']
    steps, trials = params['steps'], params['trials']
    require(type(steps) is int and 1 <= steps <= 160)
    require(type(trials) is int and 1 <= trials <= 128)
    require(data['kind'] == 'chainbench.kaczmarz-expectation' and data['schema_version'] == 1)
    require(params['seeds'] == list(range(trials)))
    fixtures = [('cube',[1,1,1]), ('half',[1,1]), ('one-in-eight',[1,7]),
                ('one-in-thirty-two',[1,31]), ('three-directions',[2,5,5]),
                ('eight-directions',[2,9,9,9,9,9,9,8])]
    require(len(data['cases']) == len(fixtures))
    for case, (name,counts) in zip(data['cases'],fixtures):
        require(case['id'] == name)
        inputs = case['inputs']
        n, m, r = len(counts), sum(counts), min(counts)
        axes = [axis for axis,count in enumerate(counts) for _ in range(count)]
        matrix = [[int(j == axis) for j in range(n)] for axis in axes]
        start = [1]*3 if name=='cube' else [1]+[0]*(n-1)
        require(inputs['A'] == matrix and inputs['b'] == [0]*m)
        require(inputs['start'] == start and inputs['solution'] == [0]*n)
        require(inputs['row_norm_squared'] == [1]*m and inputs['row_probabilities'] == [1/m]*m)
        require(inputs['dimension'] == n and inputs['equations'] == m and inputs['direction_counts'] == counts)
        digest = hashlib.sha256(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        require(case['input_sha256'] == digest)
        require(case['scaled_condition_squared'] == m/r and case['spectral_condition_squared'] == max(counts)/r)
        require(case['contraction_numerator'] == m-r and case['contraction_denominator'] == m)
        require(case['updates'] == steps and case['termination'] == 'fixed_budget_including_after_zero')
        require(len(case['runs']) == trials)
        totals, zero_counts, histogram = [0]*(steps+1), [0]*(steps+1), [0]*(steps+1)
        unresolved = 0
        for seed,run in enumerate(case['runs']):
            require(run['seed'] == seed and len(run['row_indices']) == steps)
            require(len(run['iterates']) == steps+1 and len(run['squared_errors']) == steps+1)
            x = start.copy()
            first = None
            for k in range(steps+1):
                if k:
                    index = run['row_indices'][k-1]
                    require(type(index) is int and 0 <= index < m)
                    # A coordinate remains exactly its starting value until its first hit.
                    x[axes[index]] = 0
                error = sum(v*v for v in x)
                require(run['iterates'][k] == x and run['squared_errors'][k] == error)
                totals[k] += error
                zero_counts[k] += int(error == 0)
                if first is None and error == 0:
                    first = k
            require(run['first_zero'] == first)
            if first is None:
                unresolved += 1
            else:
                histogram[first] += 1
        for field in ('exact_expectation','theorem_upper','empirical_mean','zero_counts','first_zero_counts'):
            require(len(case[field]) == steps+1)
        for k in range(steps+1):
            # Exact rational survival probability, independent of floating exponentiation.
            expected = Fraction(sum(start)) * Fraction(m-r,m)**k
            close(case['exact_expectation'][k],expected)
            close(case['theorem_upper'][k],expected)
            close(case['empirical_mean'][k],Fraction(totals[k],trials))
        require(case['zero_counts'] == zero_counts and case['first_zero_counts'] == histogram)
        require(case['unresolved_trials'] == unresolved)
        if 'conditional_projection' in case:
            validate_conditional_projections(case)


def validate_conditional_projections(case):
    def require(condition):
        if not condition:
            raise RuntimeError('Kaczmarz conditional projection evidence differs')

    def close(actual, expected, atol=1e-30):
        require(math.isfinite(actual) and math.isclose(actual,float(expected),rel_tol=3e-14,abs_tol=atol))

    record = case['conditional_projection']
    inputs = case['inputs']
    counts = inputs['direction_counts']
    n,m = len(counts),sum(counts)
    axes = [axis for axis,count in enumerate(counts) for _ in range(count)]
    require(record['kind']=='chainbench.kaczmarz-conditional-projections')
    require(record['frobenius_squared']==m and record['minimum_singular_squared']==min(counts))
    points = sorted({tuple(x) for run in case['runs'] for x in run['iterates']})
    require(len(record['states'])==len(points))
    for state,point in zip(record['states'],points):
        error = sum(x*x for x in point)
        require(state['x']==list(point) and state['key']==','.join(str(int(x)) for x in point))
        require(state['squared_error']==error and len(state['outcomes'])==m)
        total_next,total_removed = 0,0
        for i,(row,axis) in enumerate(zip(state['outcomes'],axes)):
            nxt = [0 if j==axis else x for j,x in enumerate(point)]
            removed = [x-y for x,y in zip(point,nxt)]
            next2,removed2 = sum(x*x for x in nxt),sum(x*x for x in removed)
            require(row['row_index']==i and row['probability']==1/m)
            require(row['next']==nxt and row['remaining_error']==nxt and row['removed_error']==removed)
            require(row['squared_error']==next2 and row['squared_step']==removed2)
            require(row['inner_product']==0 and row['pythagorean_residual']==0)
            total_next += int(next2)
            total_removed += int(removed2)
        close(state['conditional_squared_error'],Fraction(total_next,m))
        close(state['conditional_squared_step'],Fraction(total_removed,m))
        close(state['residual_energy_over_frobenius'],Fraction(sum(int(v*v)*c for v,c in zip(point,counts)),m))
        close(state['theorem_conditional_upper'],Fraction(int(error)*(m-min(counts)),m))
        close(state['conditional_identity_residual'],state['squared_error']-state['conditional_squared_error']-state['conditional_squared_step'])
        if error:
            close(state['conditional_ratio'],Fraction(total_next,m*int(error)))
        else:
            require(state['conditional_ratio'] is None)
        require(len(state['directions'])==n)
        offset = 0
        for j,(group,count) in enumerate(zip(state['directions'],counts)):
            require(group['direction']==j and group['row_indices']==list(range(offset,offset+count)))
            close(group['probability'],Fraction(count,m))
            representative = state['outcomes'][offset]
            require(all(group[field]==representative[field] for field in ('next','squared_error','squared_step')))
            offset += count


def exercise_kaczmarz(cli, work, env, run, extract_record):
    for steps,trials in ((1,1),(40,64),(160,128)):
        args = [cli,'case-study','kaczmarz-expectation','--steps',str(steps),'--trials',str(trials)]
        data = json.loads(run(args+['--format','json'],work,env))
        validate_kaczmarz(data)
        if any('conditional_projection' not in case for case in data['cases']):
            raise RuntimeError('installed Kaczmarz explanation omitted conditional evidence')
        if steps != 160:
            html = run(args+['--lang','ko'],work,env)
            if extract_record(html) != data or html.count('<section data-rk-case=') != 6:
                raise RuntimeError('Kaczmarz HTML differs from installed JSON')
