"""Installed CLI evidence for learning, one-factor sweeps, replay and a public case.

Called for both wheel and sdist by smoke_install, using its external venv.
No package imports from the checkout are used here.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from html.parser import HTMLParser


def extract_record(text: str) -> dict:
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.active = False
            self.chunks = []
        def handle_starttag(self, tag, attrs):
            if tag == 'pre' and dict(attrs).get('id') == 'chainbench-evidence':
                self.active = True
        def handle_endtag(self, tag):
            if tag == 'pre':
                self.active = False
        def handle_data(self, data):
            if self.active:
                self.chunks.append(data)
    parser = Parser()
    parser.feed(text)
    return json.loads(''.join(parser.chunks))


def exercise_workflows(cli, work, env, version, run):
    path = work/'learning.html'
    run([cli, 'learn', '--lang', 'ko', '--output', str(path)], work, env)
    text = path.read_text(encoding='utf8')
    learning = extract_record(text)
    actual = json.loads(run([cli, 'check', 'all', '--json'], work, env))
    converted = []
    for r in learning['results']:
        row = dict(r)
        state = row.pop('consistent')
        row['status'] = 'INFO' if state is None else 'CONSISTENT' if state else 'NOT CONSISTENT'
        converted.append(row)
    if (learning['kind'] != 'chainbench.learning' or converted != actual
            or learning['environment']['chainbench'] != version or text.count('data-search=') != 16):
        raise RuntimeError('learning report disagrees with installed checks')
    # Selected default-normalized curves independently reproduce bound ratios.
    for slug in ('gd-baseline', 'nesterov-1983', 'beck-teboulle-2009', 'jaggi-2013'):
        figure = learning['charts'][slug]
        expected = [a/b for a,b in zip(figure['series'][0]['y'], figure['series'][1]['y'])]
        if expected != learning['normalized_charts'][slug]['series'][0]['y']:
            raise RuntimeError('learning normalized plot differs from samples')

    args = [cli, 'sweep', '--preset', 'quadratic', '--parameter', 'condition_number',
            '--values', '10', '100', '--dimension', '6', '--steps', '8', '--methods', 'gd', 'cg']
    sweep = json.loads(run(args+['--format', 'json'], work, env))
    html = run(args+['--format', 'html'], work, env)
    if extract_record(html) != sweep:
        raise RuntimeError('sweep HTML differs from computed JSON')
    for exp, condition in zip(sweep['experiments'], (10., 100.)):
        config = work/f'sweep-{condition}-config.json'
        config.write_text(json.dumps(exp['config']), encoding='utf8')
        rerun = json.loads(run([cli, 'experiment', '--config', str(config)], work, env))
        if exp != rerun or exp['config']['problem']['condition_number'] != condition:
            raise RuntimeError('sweep did not execute the saved one-field configuration')
    original = sweep['experiments'][0]
    saved = work/'saved-experiment.json'
    saved.write_text(json.dumps(original),encoding='utf8')
    replay = json.loads(run([cli,'replay',str(saved),'--format','json'],work,env))
    if (replay['status'] != 'MATCH' or replay['mismatch_count'] != 0
            or replay['replayed'] != original or replay['numeric_samples_compared'] <= 0):
        raise RuntimeError('saved experiment replay is missing or inconsistent')
    replay_html = run([cli,'replay',str(saved)],work,env)
    if extract_record(replay_html) != replay:
        raise RuntimeError('replay HTML evidence differs')

    case = json.loads(run([cli,'case-study','gd-tight','--horizon','1','--format','json'],work,env))
    if (not math.isclose(case['rows'][-1]['gap'], 1/6, abs_tol=1e-14)
            or not math.isclose(case['rows'][-1]['x'], 2/3, abs_tol=1e-14)
            or not math.isclose(case['observed_ratio'],1,abs_tol=1e-12)):
        raise RuntimeError('public Huber case failed independent N=1 calculation')
    html = run([cli,'case-study','gd-tight','--horizon','1'],work,env)
    if extract_record(html) != case:
        raise RuntimeError('case-study HTML differs from computed JSON')
    stress_args = [cli, 'stress', 'nesterov-1983', '--trials', '3', '--seed', '9']
    stress = json.loads(run(stress_args + ['--format', 'json'], work, env))
    stress_page = run(stress_args, work, env)
    if (extract_record(stress_page) != stress or stress['summary'].get('within_threshold') != 3
            or len(stress['rows']) != 3):
        raise RuntimeError('seeded stress evidence differs from computed JSON')
    if stress.get('schema_version') != 2 or stress.get('sampler') != 'stratified-pcg64-v2':
        raise RuntimeError('stress sampler version is missing')
    for row in stress['rows']:
        validate_stress_sample('nesterov-1983', row)
    for topic, seed in (('nesterov-1983', 10), ('ista-vs-fista', 24)):
        args = [cli, 'stress-case', topic, '--seed', str(seed)]
        sampled = json.loads(run(args+['--format', 'json'], work, env))
        if extract_record(run(args, work, env)) != sampled:
            raise RuntimeError('single stress case HTML differs from computed JSON')
        validate_stress_sample(topic, sampled['case'])
        if topic == 'nesterov-1983' and sampled['case'] != stress['rows'][1]:
            raise RuntimeError('single stress rerun differs from the distribution case')

    landscape_args = [cli, 'landscape', '--condition-number', '20', '--steps', '6',
                      '--methods', 'gd', 'smooth-fista', 'cg']
    landscape = json.loads(run(landscape_args + ['--format', 'json'], work, env))
    landscape_page = run(landscape_args, work, env)
    if (extract_record(landscape_page) != landscape or landscape_page.count('<svg') < 6
            or set(landscape['methods']) != {'gd', 'smooth-fista', 'cg'}):
        raise RuntimeError('landscape evidence differs from computed JSON')

    reproduce_args = [cli, 'reproduce', 'shewchuk-1994', '--steps', '6']
    reproduction = json.loads(run(reproduce_args + ['--format', 'json'], work, env))
    html = run(reproduce_args + ['--lang', 'ko'], work, env)
    validate_reproduction(reproduction)
    if extract_record(html) != reproduction or html.count('data-repro-case=') != 10:
        raise RuntimeError('published-example HTML differs from installed calculations')

    geometry_args = [cli, 'geometry', 'frank-wolfe', '--steps', '8']
    geometry = json.loads(run(geometry_args + ['--format', 'json'], work, env))
    html = run(geometry_args + ['--lang', 'ko'], work, env)
    validate_simplex_geometry(geometry)
    if extract_record(html) != geometry or html.count('data-fw-case=') != 12:
        raise RuntimeError('simplex geometry HTML differs from installed calculations')

    return {'learning':'matched','sweep':'matched','replay':'matched','gd_tight':'matched',
            'stress':'matched','landscape':'matched','shewchuk_reproduction':'matched',
            'simplex_geometry':'matched', 'inspectable_stress':'matched'}


def validate_stress_sample(topic, row):
    """Independent installed checks for smooth-FISTA and paired diagonal LASSO cases."""
    inputs = row['inputs']
    digest = hashlib.sha256()
    for name in sorted(inputs):
        value = inputs[name]
        shape = [len(value), len(value[0])] if isinstance(value[0], list) else [len(value)]
        flat = [x for values in value for x in values] if len(shape) == 2 else value
        if not all(math.isfinite(v) for v in flat):
            raise RuntimeError('nonfinite stress input')
        digest.update(name.encode('ascii')+b'\0')
        digest.update(json.dumps(shape, separators=(',', ':')).encode('ascii')+b'\0')
        digest.update(struct.pack('<'+str(len(flat))+'d', *flat))
    if digest.hexdigest() != row['instance_sha256'] or inputs['update_budget'] != [row['steps']]:
        raise RuntimeError('stress input fingerprint or budget differs')
    if topic == 'nesterov-1983':
        q, sol = inputs['Q'], inputs['x_star']
        def gap(x):
            e = [a-b for a, b in zip(x, sol)]
            return sum(e[i]*sum(v*y for v, y in zip(q[i], e)) for i in range(len(e)))/2
    elif topic == 'ista-vs-fista':
        a, b, lam = inputs['a'], inputs['b'], inputs['lam'][0]
        sol = [math.copysign(max(abs(v*w)-lam, 0), v*w)/(v*v) for v, w in zip(a, b)]
        def gap(x):
            return sum(.5*(v*(xi-si))**2 + lam*(abs(xi)-abs(si))
                       + v*(v*si-w)*(xi-si) for v, w, xi, si in zip(a, b, x, sol))
    else:
        raise RuntimeError('unsupported independent installed stress validator')
    for run in row['runs'].values():
        if (run['iterates'][0] != inputs['x0'] or len(run['iterates']) != len(run['gaps'])
                or run['updates'] != len(run['iterates'])-1):
            raise RuntimeError('invalid stress trajectory')
        for x, actual in zip(run['iterates'], run['gaps']):
            if (len(x) != row['dim'] or not all(math.isfinite(v) for v in x)
                    or not math.isfinite(actual) or actual < 0
                    or not math.isclose(actual, gap(x), rel_tol=1e-9, abs_tol=1e-12)):
                raise RuntimeError('stress gap differs from the actual inputs and iterates')
    if topic == 'nesterov-1983':
        radius2 = sum((x-y)**2 for x, y in zip(inputs['x0'], sol))
        expected = [2*row['parameters']['L']*radius2/(k+1)**2 for k in range(1, row['steps']+1)]
        series = row['curve']['series']
        if series[0]['values'] != row['runs']['smooth-fista']['gaps']:
            raise RuntimeError('stress curve differs from its run')
        if any(not math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-14)
               for a, b in zip(expected, series[1]['values'])):
            raise RuntimeError('stress bound uses the wrong initial radius')
        metric = max(g/b for g, b in zip(series[0]['values'][1:], expected)) if radius2 else None
    else:
        gi, gf = row['runs']['ista']['gaps'][-1], row['runs']['fista']['gaps'][-1]
        if row['threshold'] is not None:
            raise RuntimeError('informational stress must not have a threshold')
        metric = gf/gi if gi > 1e-28 else None
    if metric is None:
        if row['metric'] is not None or row['status'] != 'unresolved' or not row['reason']:
            raise RuntimeError('undefined stress ratio was reported as measured')
    elif (row['status'] != 'measured' or row['metric'] is None
          or not math.isclose(metric, row['metric'], rel_tol=1e-12, abs_tol=1e-14)):
        raise RuntimeError('stress metric differs from the recorded trajectory')


def validate_simplex_geometry(result):
    """Recompute certificates and transitions with scalar arithmetic, outside the package."""
    if (result['kind'] != 'chainbench.simplex-geometry'
            or result['evidence_level'] != 'controlled-geometric-illustrations'):
        raise RuntimeError('invalid simplex evidence identity')
    targets = ((.2, .3, .5), (.7, .3, 0.), (.84, .1, .06))
    starts = ((1., 0., 0.), (0., 1., 0.), (0., 0., 1.), (1/3, 1/3, 1/3))
    cases, steps = result['cases'], result['parameters']['steps']
    if (len(cases) != 12 or {(tuple(c['target']), tuple(c['start'])) for c in cases}
            != {(t, s) for t in targets for s in starts}
            or result['problem']['curvature'] != 2):
        raise RuntimeError('simplex case design differs')
    if result['bound'] != {'iterations': list(range(1, steps+1)),
                           'values': [4/(k+2) for k in range(1, steps+1)]}:
        raise RuntimeError('simplex theorem curve differs')
    for case in cases:
        target, rows = case['target'], case['rows']
        digest = hashlib.sha256(struct.pack('<6d', *target, *case['start'])).hexdigest()
        if (case['input_sha256'] != digest or len(rows) != steps+1
                or case['updates'] != steps or case['termination'] != 'fixed_budget'
                or rows[0]['x'] != case['start']):
            raise RuntimeError('simplex input fingerprint or budget differs')
        for k, row in enumerate(rows):
            x = row['x']
            if (len(x) != 3 or not all(math.isfinite(v) and v >= 0 for v in x)
                    or not math.isclose(sum(x), 1, abs_tol=1e-14)):
                raise RuntimeError('iterate is not in the simplex')
            gradient = [v-t for v, t in zip(x, target)]
            index = min(range(3), key=lambda i: gradient[i])
            vertex = [float(i == index) for i in range(3)]
            gap = sum(v*v for v in gradient)/2
            dual = sum(g*v for g, v in zip(gradient, x)) - min(gradient)
            gamma = 2/(k+2) if k < steps else None
            if (row['iteration'] != k or row['vertex_index'] != index
                    or row['vertex'] != vertex or row['gradient'] != gradient
                    or row['gamma'] != gamma or row['support'] != sum(v > 0 for v in x)
                    or not math.isclose(row['gap'], gap, abs_tol=1e-14)
                    or not math.isclose(row['dual_gap'], dual, abs_tol=1e-14)
                    or gap > dual + 1e-14 or (k >= 1 and gap > 4/(k+2) + 1e-14)):
                raise RuntimeError('simplex oracle, metric or certificate differs')
            if gamma is not None:
                expected = [(1-gamma)*v + gamma*s for v, s in zip(x, vertex)]
                if any(not math.isclose(a, b, abs_tol=1e-14)
                       for a, b in zip(expected, rows[k+1]['x'])):
                    raise RuntimeError('simplex update differs from the convex combination')


def validate_reproduction(result):
    """Independent scalar checks; no imports from the package being tested."""
    p = result['problem']
    if (result['kind'] != 'chainbench.reproduction' or p['A'] != [[3, 2], [2, 6]]
            or p['b'] != [2, -8] or p['x_star'] != [2, -2] or p['f_star'] != -10):
        raise RuntimeError('published problem setup differs')
    cases = result['cases']
    if (len(cases) != 10 or cases[0]['start'] != [-2, -2]
            or {tuple(c['start']) for c in cases[1:]} != {
                (x, y) for x in [-3, 0, 3] for y in [-4, 0, 3]}):
        raise RuntimeError('published example or complete start grid missing')
    cg = cases[0]['runs']['cg']
    if (cg['updates'] != 2 or cg['termination'] != 'converged'
            or len(cg['rows']) != 3
            or not math.isclose(cg['rows'][1]['x'][0], 2/25, abs_tol=1e-13)
            or not math.isclose(cg['rows'][1]['x'][1], -46/75, abs_tol=1e-13)):
        raise RuntimeError('CG differs from independent first-step calculation')
    for case in cases:
        digest = hashlib.sha256(struct.pack('<9d', 3, 2, 2, 6, 2, -8, 0, *case['start'])).hexdigest()
        if case['input_sha256'] != digest:
            raise RuntimeError('input fingerprint differs from actual inputs')
        for method in ('sd', 'cg'):
            trace = case['runs'][method]
            rows = trace['rows']
            if (trace['updates'] != len(rows)-1 or rows[0]['x'] != case['start']
                    or trace['termination'] not in ('converged', 'max_steps')):
                raise RuntimeError('invalid reproduction trajectory')
            for k, row in enumerate(rows):
                x, y = row['x']
                gap = (3*(x-2)**2 + 4*(x-2)*(y+2) + 6*(y+2)**2)/2
                norm = math.hypot(2-3*x-2*y, -8-2*x-6*y)
                if (row['iteration'] != k
                        or not math.isclose(row['gap'], gap, rel_tol=1e-12, abs_tol=1e-25)
                        or not math.isclose(row['energy_error'], math.sqrt(2*gap), abs_tol=1e-13)
                        or not math.isclose(row['residual_norm'], norm, abs_tol=1e-13)):
                    raise RuntimeError('reproduction metric is not tied to the iterates')
            converged = rows[-1]['residual_norm'] <= 1e-12*rows[0]['residual_norm']
            if (trace['termination'] == 'converged') != converged:
                raise RuntimeError('reproduction termination differs from true residual')
