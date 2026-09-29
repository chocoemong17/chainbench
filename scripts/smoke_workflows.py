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
from urllib.parse import urlsplit


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
    maps = learning.get('mechanism_maps', {})
    if (maps.get('kind') != 'symbolic-process-maps'
            or set(maps.get('topics', {})) != {r['slug'] for r in actual}
            or text.count('class="method-flow"') != 8
            or text.count('data-mechanism=') != 8):
        raise RuntimeError('learning mechanism maps are missing from the installed report')
    if text.count('class="instance-context"') != 8 or any(
            chart.get('instance', {}).get('kind') != 'canonical-fixed-instance' for chart in learning['charts'].values()):
        raise RuntimeError('learning canonical inputs are missing from the installed report')
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
    validate_tight_geometry(case)
    html = run([cli,'case-study','gd-tight','--horizon','1'],work,env)
    if extract_record(html) != case:
        raise RuntimeError('case-study HTML differs from computed JSON')
    large = json.loads(run([cli, 'case-study', 'gd-tight', '--horizon', '500', '--format', 'json'], work, env))
    validate_tight_geometry(large)
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

    proximal_args = [cli, 'geometry', 'ista-fista', '--steps', '6']
    proximal = json.loads(run(proximal_args + ['--format', 'json'], work, env))
    html = run(proximal_args + ['--lang', 'ko'], work, env)
    validate_proximal_geometry(proximal)
    if extract_record(html) != proximal or html.count('data-prox-case=') != 9:
        raise RuntimeError('proximal geometry HTML differs from installed calculations')

    folder = work/'tour'
    run([cli, 'tour', '--lang', 'ko', '--output', str(folder)], work, env)
    tour_records = validate_tour(folder)
    for filename, command in [('shewchuk.html', ['reproduce', 'shewchuk-1994', '--steps', '12']),
                              ('proximal.html', ['geometry', 'ista-fista', '--steps', '18'])]:
        direct = json.loads(run([cli, *command, '--format', 'json'], work, env))
        if direct != tour_records[filename]:
            raise RuntimeError('tour page differs from the installed standalone workflow')
    unresolved = json.loads(run([cli, 'stress-case', 'ista-vs-fista', '--seed', '24', '--format', 'json'], work, env))
    if tour_records['stress-ista-vs-fista.html']['rows'][24] != unresolved['case']:
        raise RuntimeError('tour dropped or changed the unresolved sampled case')

    from smoke_deblurring import validate_deblurring
    deblur_args = [cli, 'reproduce', 'fista-deblurring']
    deblur = json.loads(run(deblur_args + ['--format', 'json'], work, env))
    validate_deblurring(deblur)
    if deblur != tour_records['deblur.html']:
        raise RuntimeError('tour deblurring differs from the installed standalone command')
    deblur_html = run(deblur_args + ['--lang', 'ko'], work, env)
    if extract_record(deblur_html) != deblur or deblur['parameters']['steps'] != 10000:
        raise RuntimeError('installed deblurring HTML differs from the full published budget')

    from smoke_heavy_ball_cycle import validate_heavy_ball_cycle
    cycle_args = [cli, 'reproduce', 'lessard-2016']
    cycle = json.loads(run(cycle_args + ['--format', 'json'], work, env))
    validate_heavy_ball_cycle(cycle)
    if cycle != tour_records['heavy-ball.html'] or cycle['parameters']['steps'] != 50:
        raise RuntimeError('tour counterexample differs from the source-budget standalone run')
    if extract_record(run(cycle_args + ['--lang', 'ko'], work, env)) != cycle:
        raise RuntimeError('installed counterexample HTML differs from JSON')

    return {'learning':'matched','sweep':'matched','replay':'matched','gd_tight':'matched',
            'stress':'matched','landscape':'matched','shewchuk_reproduction':'matched',
            'simplex_geometry':'matched', 'inspectable_stress':'matched', 'proximal_geometry':'matched',
            'offline_tour':'matched', 'fista_deblurring':'matched', 'heavy_ball_counterexample':'matched'}


def validate_tour(folder):
    """Read only the generated folder; verify hashes, links, coverage and raw records."""
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf8'))
    topics = {'gd-baseline', 'nesterov-1983', 'polyak-1964', 'hestenes-stiefel-1952',
              'jaggi-2013', 'rockafellar-1976', 'beck-teboulle-2009', 'ista-vs-fista'}
    expected = {'index.html', 'atlas.html', 'shewchuk.html', 'simplex.html', 'proximal.html', 'tight-gd.html', 'deblur.html', 'heavy-ball.html'}
    expected.update('stress-'+topic+'.html' for topic in topics)
    if (manifest.get('kind') != 'chainbench.offline-tour' or manifest.get('start') != 'index.html'
            or len(manifest['artifacts']) != len(expected)
            or {a['path'] for a in manifest['artifacts']} != expected
            or {p.name for p in folder.iterdir()} != expected|{'manifest.json'}):
        raise RuntimeError('tour artifact coverage differs')
    class Links(HTMLParser):
        def __init__(self, text):
            super().__init__()
            self.ids, self.links = set(), []
            self.feed(text)
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if 'id' in attrs:
                self.ids.add(attrs['id'])
            if tag == 'a' and 'href' in attrs:
                self.links.append(attrs['href'])
    parsed, records = {}, {}
    for artifact in manifest['artifacts']:
        name = artifact['path']
        raw = (folder/name).read_bytes()
        if len(raw) != artifact['bytes'] or hashlib.sha256(raw).hexdigest() != artifact['sha256']:
            raise RuntimeError('tour file hash differs')
        text = raw.decode('utf8')
        parsed[name] = Links(text)
        if name != 'index.html':
            if 'index.html' not in parsed[name].links:
                raise RuntimeError('tour report has no return link')
            records[name] = extract_record(text)
        if name.startswith('stress-'):
            result = records[name]
            topic = name[len('stress-'):-len('.html')]
            if (result['topic'] != topic or artifact['topic'] != topic
                    or result['seed'] != 0 or result['trials'] != 32
                    or [r['seed'] for r in result['rows']] != list(range(32))
                    or result['summary'] != artifact['summary']):
                raise RuntimeError('tour omitted or changed sampled cases')
    for name, document in parsed.items():
        for link in document.links:
            url = urlsplit(link)
            if url.scheme in ('https', 'http'):
                continue
            if url.scheme or url.netloc or url.query:
                raise RuntimeError('unexpected tour link')
            target = url.path or name
            if target == 'manifest.json' and not url.fragment:
                continue
            if target not in parsed or (url.fragment and url.fragment not in parsed[target].ids):
                raise RuntimeError('tour local link has no target')
    validate_reproduction(records['shewchuk.html'])
    validate_simplex_geometry(records['simplex.html'])
    validate_proximal_geometry(records['proximal.html'])
    validate_tight_geometry(records['tight-gd.html'])
    from smoke_deblurring import validate_deblurring
    validate_deblurring(records['deblur.html'])
    if records['deblur.html']['parameters']['steps'] != 10000:
        raise RuntimeError('tour omitted the full published image budget')
    from smoke_heavy_ball_cycle import validate_heavy_ball_cycle
    validate_heavy_ball_cycle(records['heavy-ball.html'])
    if records['heavy-ball.html']['parameters']['steps'] != 50:
        raise RuntimeError('tour omitted the counterexample source budget')
    info = records['stress-ista-vs-fista.html']
    if info['rows'][24]['metric'] is not None or info['rows'][24]['status'] != 'unresolved':
        raise RuntimeError('tour must retain the unresolved case')
    return records


def validate_tight_geometry(result):
    c, geometry = result['config'], result.get('geometry')
    if not geometry or geometry.get('kind') != 'huber-function-geometry':
        raise RuntimeError('tight-GD geometry is missing')
    n, L, R, h = c['horizon'], c['L'], c['R'], c['h']
    a = R/(2*n*h+1)
    def close(x,y):
        if not math.isfinite(x) or not math.isfinite(y) or not math.isclose(x,y,rel_tol=2e-10,abs_tol=0.):
            raise RuntimeError('tight-GD geometry disagrees with the public construction')
    def value(x):
        return L*(x*x/2 if abs(x)<=a else a*abs(x)-a*a/2)
    close(result['transition'], a)
    close(geometry['x_scale'], a)
    close(geometry['value_scale'], L*a*a)
    points = result['charts']['function']['series'][0]
    if (len(points['x']) != len(points['y']) or -a not in points['x'] or a not in points['x']
            or sum(-a<=x<=a for x in points['x']) < 81):
        raise RuntimeError('tight-GD curve does not resolve its quadratic centre')
    for x,y in zip(points['x'],points['y']):
        close(y,value(x))
    u, values = geometry['normalized_x'], geometry['normalized_value']
    if (len(u) != len(values) or len(u) < 81 or not {-2.,-1.,0.,1.,2.}.issubset(u)
            or any(y<=x for x,y in zip(u,u[1:]))):
        raise RuntimeError('tight-GD normalized coordinates are missing')
    for x,y in zip(u,values):
        close(y, x*x/2 if abs(x)<=1 else abs(x)-.5)
    joins = geometry.get('transition_points', [])
    if len(joins) != 2:
        raise RuntimeError('tight-GD transition evidence is missing')
    for sign, join in zip((-1,1), joins):
        close(join['x'], sign*a)
        close(join['value'], L*a*a/2)
        close(join['gradient'], sign*L*a)
    rows = result['rows']
    if len(rows) != n+1 or [r['iteration'] for r in rows] != list(range(n+1)):
        raise RuntimeError('tight-GD recorded steps are incomplete')
    for r in rows:
        close(r['x'], R-r['iteration']*h*a)
        close(r['gradient'], L*a)
        close(r['gap'], value(r['x']))
        if r['x'] <= a:
            raise RuntimeError('tight-GD point left the affine construction')
    close(result['rows'][-1]['gap'], L*R*R/(4*n*h+2))


def validate_proximal_geometry(result):
    """Scalar reconstruction of complete proximal stages, gaps and envelopes."""
    if (result['kind'] != 'chainbench.proximal-geometry'
            or result['problem']['a'] != [1., 3.] or result['problem']['b'] != [1.4, -2.4]
            or result['problem']['L'] != 9):
        raise RuntimeError('proximal problem setup differs')
    cases, steps = result['cases'], result['parameters']['steps']
    expected = {(lam, start) for lam in (.1, .8, 1.8)
                for start in ((-1.8, 1.2), (0., 0.), (2., -1.4))}
    if len(cases) != 9 or {(c['lambda'], tuple(c['start'])) for c in cases} != expected:
        raise RuntimeError('proximal case design differs')
    def close(a, b):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-13)
    for c in cases:
        lam = c['lambda']
        star = [max(1.4-lam, 0), -max(7.2-lam, 0)/9]
        def objective(point):
            x, y = point
            return ((x-1.4)**2+(3*y+2.4)**2)/2+lam*(abs(x)+abs(y))
        radius2 = sum((x-y)**2 for x, y in zip(c['start'], star))
        digest = hashlib.sha256(struct.pack('<7d', 1, 3, 1.4, -2.4, lam, *c['start'])).hexdigest()
        if (c['input_sha256'] != digest or not all(close(a, b) for a, b in zip(c['x_star'], star))
                or not close(c['f_star'], objective(star)) or not close(c['radius_squared'], radius2)):
            raise RuntimeError('proximal reference or fingerprint differs')
        for method in ('ista', 'fista'):
            run = c['runs'][method]
            if (len(run['rows']) != steps+1 or len(run['stages']) != steps
                    or run['rows'][0]['x'] != c['start'] or run['updates'] != steps):
                raise RuntimeError('proximal trajectory budget differs')
            t, beta, y = 1., 0., c['start'][:]
            for k, row in enumerate(run['rows']):
                if (row['iteration'] != k or not close(row['objective'], objective(row['x']))
                        or not close(row['gap'], objective(row['x'])-objective(star))):
                    raise RuntimeError('proximal objective is not tied to its iterate')
                if k:
                    bound = 9*radius2/(2*k) if method == 'ista' else 18*radius2/(k+1)**2
                    if not close(c['bounds'][method][k-1], bound):
                        raise RuntimeError('proximal envelope differs')
                if k == steps:
                    continue
                stage, x = run['stages'][k], row['x']
                if method == 'ista':
                    y = x[:]
                gradient = [y[0]-1.4, 9*y[1]+7.2]
                z = [v-g/9 for v, g in zip(y, gradient)]
                xn = [v-lam/9 if v > lam/9 else v+lam/9 if v < -lam/9 else 0. for v in z]
                for field, values in (('x', x), ('y', y), ('gradient', gradient), ('z', z), ('next_x', xn)):
                    if not all(close(a, b) for a, b in zip(stage[field], values)):
                        raise RuntimeError('proximal stage differs from independent calculation')
                if (not all(close(a, b) for a, b in zip(xn, run['rows'][k+1]['x']))
                        or not close(stage['momentum'], beta) or not close(stage['t'], t)
                        or not close(stage['threshold'], lam/9)
                        or stage['zeroed'] != [abs(v) <= lam/9 for v in z]):
                    raise RuntimeError('proximal update or threshold differs')
                if method == 'fista':
                    tn = (1+math.sqrt(1+4*t*t))/2
                    beta = (t-1)/tn
                    y = [a+beta*(a-b) for a, b in zip(run['rows'][k+1]['x'], x)]
                    t = tn


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
            cert = row.get('certificate', {})
            affine = [gap + sum(g*((1. if i == j else 0.)-v)
                               for i, (g, v) in enumerate(zip(gradient, x)))
                      for j in range(3)]
            actual = cert.get('affine_vertices', [])
            lower, upper = cert.get('lower'), cert.get('upper')
            if (len(actual) != 3 or lower is None or upper is None
                    or not all(math.isfinite(v) for v in [*actual, lower, upper])
                    or any(not math.isclose(a, b, abs_tol=1e-14) for a, b in zip(actual, affine))
                    or not math.isclose(lower, min(affine), abs_tol=1e-14)
                    or not math.isclose(upper, gap, abs_tol=1e-14)
                    or not math.isclose(upper-lower, dual, abs_tol=1e-14)
                    or lower > 1e-14 or upper < 0):
                raise RuntimeError('simplex affine model or optimal-value bracket differs')
            if gamma is not None:
                expected = [(1-gamma)*v + gamma*s for v, s in zip(x, vertex)]
                if any(not math.isclose(a, b, abs_tol=1e-14)
                       for a, b in zip(expected, rows[k+1]['x'])):
                    raise RuntimeError('simplex update differs from the convex combination')


def validate_reproduction(result):
    """Independent scalar checks; no imports from the package being tested."""
    validate_metric_geometry(result)
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


def validate_metric_geometry(result):
    """Recompute the fixed 2x2 transform and all displacement measurements."""
    def close(actual, expected):
        if expected is None:
            if actual is not None:
                raise RuntimeError('undefined metric pair became evidence')
        elif not isinstance(actual, (int, float)) or not math.isfinite(actual) or not math.isclose(
                actual, expected, rel_tol=2e-10, abs_tol=2e-13):
            raise RuntimeError('metric geometry differs from actual coordinates')
    root = math.sqrt(14)
    scale = math.sqrt(9+2*root)
    t = [[(3+root)/scale, 2/scale], [2/scale, (6+root)/scale]]
    for actual, expected in zip(result['metric_geometry']['transform'], t, strict=True):
        for a, b in zip(actual, expected, strict=True):
            close(a, b)
    def transform(v):
        return [sum(a*b for a, b in zip(row, v)) for row in t]
    def dot(u, v):
        return sum(a*b for a, b in zip(u, v))
    for case in result['cases']:
        for run in case['runs'].values():
            rows = run['rows']
            for k, row in enumerate(rows):
                expected = transform([row['x'][0]-2, row['x'][1]+2])
                for a, b in zip(row['metric_coordinates'], expected, strict=True):
                    close(a, b)
                close(dot(expected, expected)/2, row['gap'])
                pair = row['step_pair']
                if k < 2:
                    close(pair, None)
                    continue
                u = [a-b for a, b in zip(rows[k-1]['x'], rows[k-2]['x'])]
                v = [a-b for a, b in zip(row['x'], rows[k-1]['x'])]
                tu, tv = transform(u), transform(v)
                for key, vec in [('previous', u), ('current', v),
                                 ('transformed_previous', tu), ('transformed_current', tv)]:
                    for a, b in zip(pair[key], vec, strict=True):
                        close(a, b)
                dot2, dota = dot(u, v), dot(u, [3*v[0]+2*v[1], 2*v[0]+6*v[1]])
                close(pair['euclidean_dot'], dot2)
                close(pair['a_dot'], dota)
                den2, dena = math.hypot(*u)*math.hypot(*v), math.hypot(*tu)*math.hypot(*tv)
                close(pair['cos_euclidean'], dot2/den2 if den2 else None)
                close(pair['cos_a'], dota/dena if dena else None)
