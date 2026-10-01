"""Installed CLI evidence for learning, one-factor sweeps, replay and a public case.

Called for both wheel and sdist by smoke_install, using its external venv.
No package imports from the checkout are used here.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from decimal import Decimal, localcontext
from html.parser import HTMLParser
from urllib.parse import urlsplit


class EvidenceDocument(HTMLParser):
    """Read links, fragment targets and escaped evidence in one HTML traversal."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.ids, self.links = set(), []
        self.active = False
        self.evidence_blocks = 0
        self.evidence_ids = 0
        self.chunks = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        ids = [value for key, value in attrs if key == 'id']
        if 'chainbench-evidence' in ids:
            # A different element or a repeated id attribute can disagree with
            # the browser's getElementById even when there is just one pre.
            self.evidence_ids += len(ids)
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])
        if tag == 'pre' and attrs.get('id') == 'chainbench-evidence':
            self.evidence_blocks += 1
            self.active = True

    def handle_endtag(self, tag):
        if tag == 'pre':
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.chunks.append(data)

    def take_record(self):
        if self.evidence_blocks != 1 or self.evidence_ids != 1:
            raise json.JSONDecodeError('Expected one unambiguous evidence block', '', 0)
        record = json.loads(''.join(self.chunks))
        self.chunks.clear()  # Keep links/ids, not a second copy of large JSON text.
        return record


def extract_record(text: str) -> dict:
    return EvidenceDocument(text).take_record()


def exercise_workflows(cli, work, env, version, run):
    path = work/'learning.html'
    run([cli, 'learn', '--lang', 'ko', '--output', str(path)], work, env)
    text = path.read_text(encoding='utf8')
    learning = extract_record(text)
    from smoke_learning_paths import validate_learning_paths
    validate_learning_paths(text)
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

    landscape_args = [cli, 'landscape', '--condition-number', '20', '--steps', '6']
    landscape = json.loads(run(landscape_args + ['--format', 'json'], work, env))
    validate_landscape(landscape)
    landscape_page = run(landscape_args, work, env)
    if (extract_record(landscape_page) != landscape or landscape_page.count('<svg') < 6
            or set(landscape['methods']) != {'gd', 'smooth-fista', 'heavy-ball', 'cg', 'proximal-point'}):
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
    validate_simplex_geometry(geometry, require_segment=True)
    if extract_record(html) != geometry or html.count('data-fw-case=') != 12:
        raise RuntimeError('simplex geometry HTML differs from installed calculations')

    proximal_args = [cli, 'geometry', 'ista-fista', '--steps', '6']
    proximal = json.loads(run(proximal_args + ['--format', 'json'], work, env))
    html = run(proximal_args + ['--lang', 'ko'], work, env)
    validate_proximal_geometry(proximal)
    from smoke_proximal_dual import validate_proximal_dual
    validate_proximal_dual(proximal, required=True)
    if extract_record(html) != proximal or html.count('data-prox-case=') != 9:
        raise RuntimeError('proximal geometry HTML differs from installed calculations')

    folder = work/'tour'
    run([cli, 'tour', '--lang', 'ko', '--output', str(folder)], work, env)
    tour_records = validate_tour(folder)
    for filename, command in [('shewchuk.html', ['reproduce', 'shewchuk-1994', '--steps', '12']),
                              ('landscape.html', ['landscape']),
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

    from smoke_wavelet import validate_wavelet
    wavelet_args = [cli, 'reproduce', 'fista-wavelet']
    wavelet = json.loads(run(wavelet_args + ['--format', 'json'], work, env))
    validate_wavelet(wavelet, require_duality=True)
    if wavelet['parameters']['steps'] != 200 or wavelet['parameters']['seed'] != 0:
        raise RuntimeError('installed noisy-image default differs from full declared protocol')
    if extract_record(run(wavelet_args + ['--lang', 'ko'], work, env)) != wavelet:
        raise RuntimeError('installed wavelet HTML differs from JSON')

    from smoke_fw_sparsity import validate_fw_sparsity
    sparse_args = [cli, 'case-study', 'fw-sparsity']
    sparsity = json.loads(run(sparse_args + ['--format', 'json'], work, env))
    validate_fw_sparsity(sparsity)
    if sparsity['parameters']['steps'] != 40:
        raise RuntimeError('installed sparsity construction default budget differs')
    if extract_record(run(sparse_args + ['--lang', 'ko'], work, env)) != sparsity:
        raise RuntimeError('installed sparsity HTML differs from JSON')

    from smoke_kaczmarz import exercise_kaczmarz
    exercise_kaczmarz(cli, work, env, run, extract_record)

    from smoke_nonuniform import exercise_nonuniform
    exercise_nonuniform(cli, work, env, run, extract_record)

    from smoke_cg_spectrum import exercise_cg_spectrum
    exercise_cg_spectrum(cli, work, env, run, extract_record)

    from smoke_adam_counterexample import exercise_adam_counterexample
    exercise_adam_counterexample(cli, work, env, run, extract_record)

    from smoke_admm_geometry import exercise_admm_geometry
    exercise_admm_geometry(cli, work, env, run, extract_record)

    from smoke_fista_backtracking import exercise_fista_backtracking
    exercise_fista_backtracking(cli, work, env, run, extract_record)

    extended_folder = work/'tour-extended'
    run([cli, 'tour', '--extended', '--lang', 'ko', '--output', str(extended_folder)], work, env)
    extended_records = validate_tour(extended_folder)
    if any(extended_records[name] != record for name, record in tour_records.items()):
        raise RuntimeError('extended tour changed a base computation')
    if extended_records['wavelet.html'] != wavelet or extended_records['fw-sparsity.html'] != sparsity:
        raise RuntimeError('extended tour differs from standalone image or sparsity calculations')
    randomized = json.loads(run([cli,'case-study','kaczmarz-expectation','--format','json'],work,env))
    if extended_records['kaczmarz.html'] != randomized:
        raise RuntimeError('extended tour differs from standalone randomized construction')
    sampling = json.loads(run([cli,'reproduce','kaczmarz-sampling','--format','json'],work,env))
    if extended_records['sampling.html'] != sampling:
        raise RuntimeError('extended tour differs from standalone nonuniform sampling')
    cg_spectrum = json.loads(run([cli,'case-study','cg-spectrum','--format','json'],work,env))
    if extended_records['cg-spectrum.html'] != cg_spectrum:
        raise RuntimeError('extended tour differs from standalone CG spectra')
    adam = json.loads(run([cli,'reproduce','reddi-2018','--format','json'],work,env))
    if extended_records['adam.html'] != adam:
        raise RuntimeError('extended tour differs from standalone Adam counterexample')
    admm = json.loads(run([cli,'geometry','admm-lasso','--format','json'],work,env))
    if extended_records['admm.html'] != admm:
        raise RuntimeError('extended tour differs from standalone ADMM geometry')
    backtracking = json.loads(run([cli,'geometry','fista-backtracking','--format','json'],work,env))
    if extended_records['backtracking.html'] != backtracking:
        raise RuntimeError('extended tour differs from standalone FISTA backtracking')

    return {'learning':'matched','sweep':'matched','replay':'matched','gd_tight':'matched',
            'stress':'matched','landscape':'matched','shewchuk_reproduction':'matched',
            'simplex_geometry':'matched', 'inspectable_stress':'matched', 'proximal_geometry':'matched',
            'offline_tour':'matched', 'fista_deblurring':'matched', 'heavy_ball_counterexample':'matched',
            'noisy_wavelet':'matched', 'fw_sparsity':'matched', 'extended_tour':'matched',
            'kaczmarz_expectation':'matched', 'nonuniform_sampling':'matched', 'cg_spectrum':'matched',
            'adam_counterexample':'matched', 'admm_geometry':'matched', 'fista_backtracking':'matched'}


def validate_tour(folder):
    """Read only the generated folder; verify hashes, links, coverage and raw records."""
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf8'))
    topics = {'gd-baseline', 'nesterov-1983', 'polyak-1964', 'hestenes-stiefel-1952',
              'jaggi-2013', 'rockafellar-1976', 'beck-teboulle-2009', 'ista-vs-fista'}
    expected = {'index.html', 'atlas.html', 'shewchuk.html', 'simplex.html', 'proximal.html', 'tight-gd.html', 'deblur.html', 'heavy-ball.html', 'landscape.html'}
    expected.update('stress-'+topic+'.html' for topic in topics)
    extensions = manifest.get('extensions', [])
    if extensions not in ([], ['fista-wavelet', 'fw-sparsity'],
                          ['fista-wavelet', 'fw-sparsity', 'kaczmarz-expectation'],
                          ['fista-wavelet', 'fw-sparsity', 'kaczmarz-expectation', 'kaczmarz-sampling'],
                          ['fista-wavelet', 'fw-sparsity', 'kaczmarz-expectation', 'kaczmarz-sampling', 'cg-spectrum'],
                          ['fista-wavelet', 'fw-sparsity', 'kaczmarz-expectation', 'kaczmarz-sampling', 'cg-spectrum', 'reddi-2018'],
                          ['fista-wavelet', 'fw-sparsity', 'kaczmarz-expectation', 'kaczmarz-sampling', 'cg-spectrum', 'reddi-2018', 'admm-lasso'],
                          ['fista-wavelet', 'fw-sparsity', 'kaczmarz-expectation', 'kaczmarz-sampling', 'cg-spectrum', 'reddi-2018', 'admm-lasso', 'fista-backtracking']):
        raise RuntimeError('tour extension selection differs')
    if extensions:
        expected.update({'wavelet.html', 'fw-sparsity.html'})
    if 'kaczmarz-expectation' in extensions:
        expected.add('kaczmarz.html')
    if 'kaczmarz-sampling' in extensions:
        expected.add('sampling.html')
    if 'cg-spectrum' in extensions:
        expected.add('cg-spectrum.html')
    if 'reddi-2018' in extensions:
        expected.add('adam.html')
    if 'admm-lasso' in extensions:
        expected.add('admm.html')
    if 'fista-backtracking' in extensions:
        expected.add('backtracking.html')
    if (manifest.get('kind') != 'chainbench.offline-tour' or manifest.get('start') != 'index.html'
            or manifest.get('schema_version') != 1 or manifest.get('language') not in ('ko', 'en')
            or len(manifest['artifacts']) != len(expected)
            or {a['path'] for a in manifest['artifacts']} != expected
            or {p.name for p in folder.iterdir()} != expected|{'manifest.json'}):
        raise RuntimeError('tour artifact coverage differs')
    parsed, records = {}, {}
    for artifact in manifest['artifacts']:
        name = artifact['path']
        raw = (folder/name).read_bytes()
        if len(raw) != artifact['bytes'] or hashlib.sha256(raw).hexdigest() != artifact['sha256']:
            raise RuntimeError('tour file hash differs')
        text = raw.decode('utf8')
        parsed[name] = EvidenceDocument(text)
        if name != 'index.html':
            if 'index.html' not in parsed[name].links:
                raise RuntimeError('tour report has no return link')
            records[name] = parsed[name].take_record()
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
    # Reject every cheap contract mismatch before numerical/presentation audits.
    if 'fista-backtracking' in extensions:
        from smoke_backtracking_tour import validate_backtracking_tour_metadata
        backtracking = records['backtracking.html']
        artifact = next(a for a in manifest['artifacts'] if a['path']=='backtracking.html')
        validate_backtracking_tour_metadata(artifact,backtracking,manifest['language'])
    if 'admm-lasso' in extensions:
        admm = records['admm.html']
        artifact = next(a for a in manifest['artifacts'] if a['path']=='admm.html')
        if (artifact['command'] != ['geometry','admm-lasso','--steps','60','--lang',manifest['language']]
                or artifact['source'] != admm['source'] or artifact['steps'] != 60
                or artifact['dimension'] != 2
                or artifact['layer'] != 'controlled geometric illustrations; newly declared 2D inputs'
                or artifact['cases'] != [c['id'] for c in admm['cases']]
                or artifact['input_sha256'] != {c['id']:c['input_sha256'] for c in admm['cases']}
                or artifact['metric'] != 'original-primal gap F(w)-F*'
                or artifact['variant'] != {'relaxation':1.,'penalty':'fixed rho','stopping':'fixed_budget','initial_x':None}
                or artifact['preview'] != {'case':'coupled-lambda0.1-zero-rho1','iteration':1,
                    'view':'surface','coordinates':['x','z'],'height':'stable algebraic F(w)-F*'}
                or admm['parameters']['steps'] != 60):
            raise RuntimeError('ADMM tour metadata differs')
    if 'reddi-2018' in extensions:
        adam = records['adam.html']
        artifact = next(a for a in manifest['artifacts'] if a['path']=='adam.html')
        if (artifact['command'] != ['reproduce','reddi-2018','--steps','3000','--lang',manifest['language']]
                or artifact['source'] != adam['source'] or artifact['steps'] != 3000
                or artifact['methods'] != ['adam','amsgrad']
                or artifact['C_values'] != [3,10,100] or artifact['alpha_fractions'] != [.1,.5,.9]
                or artifact['cases'] != [c['id'] for c in adam['cases']]
                or artifact['metric'] != 'average online regret R_t/t'
                or artifact['variant'] != {'beta1':0.,'bias_correction':False,'epsilon':0.,'period':3}
                or artifact['preview'] != {'case':'c3-a0.1','methods':['adam','amsgrad'],
                    'quantity':'average online regret over all rounds 1..3000',
                    'reference':'Adam lower reference at complete three-round blocks only'}
                or adam['parameters']['steps'] != 3000):
            raise RuntimeError('Adam tour metadata differs')
    if 'kaczmarz-expectation' in extensions:
        randomized = records['kaczmarz.html']
        artifact = next(a for a in manifest['artifacts'] if a['path']=='kaczmarz.html')
        params = randomized['parameters']
        if (params['steps'] != 40 or params['trials'] != 64
                or artifact['command'] != ['case-study','kaczmarz-expectation','--steps','40','--trials','64','--lang',manifest['language']]
                or artifact['source'] != randomized['source']
                or artifact['steps'] != 40 or artifact['trials'] != 64
                or artifact['seeds'] != list(range(64))
                or artifact['cases'] != [c['id'] for c in randomized['cases']]
                or artifact['metric'] != 'expected squared Euclidean error'):
            raise RuntimeError('randomized tour extension metadata differs')
    if 'kaczmarz-sampling' in extensions:
        sampling = records['sampling.html']
        artifact = next(a for a in manifest['artifacts'] if a['path']=='sampling.html')
        if (artifact['command'] != ['reproduce','kaczmarz-sampling','--steps','15000','--lang',manifest['language']]
                or artifact['source'] != sampling['source']
                or artifact['steps'] != 15000 or artifact['seeds'] != [0,1,2]
                or artifact['dimension'] != 101 or artifact['sample_count'] != 700
                or artifact['bandlimit'] != 50
                or artifact['cases'] != ['seed-0','seed-1','seed-2']
                or artifact['metric'] != 'coefficient L2 error'
                or artifact['preview'] != {'case':'seed-0','method':'weighted','iteration':100,
                                            'quantity':'real part of reconstructed signal'}
                or sampling['parameters']['steps'] != 15000):
            raise RuntimeError('nonuniform sampling tour metadata differs')
    if 'cg-spectrum' in extensions:
        spectrum = records['cg-spectrum.html']
        artifact = next(a for a in manifest['artifacts'] if a['path']=='cg-spectrum.html')
        if (artifact['command'] != ['case-study','cg-spectrum','--steps','32','--lang',manifest['language']]
                or artifact['source'] != spectrum['source']
                or artifact['steps'] != 32 or artifact['dimension'] != 16
                or artifact['rtol'] != 1e-12 or artifact['atol'] != 0
                or artifact['cases'] != [c['id'] for c in spectrum['cases']]
                or artifact['metric'] != 'relative A-norm error'
                or artifact['preview'] != {'basis':'hadamard','start_profile':'equal-energy',
                    'spectra':['two-values','two-clusters','spread'],
                    'quantity':'relative A-norm error over all completed updates'}
                or spectrum['parameters']['steps'] != 32):
            raise RuntimeError('CG spectrum tour metadata differs')
    if records['deblur.html']['parameters']['steps'] != 10000:
        raise RuntimeError('tour omitted the full published image budget')
    if records['heavy-ball.html']['parameters']['steps'] != 50:
        raise RuntimeError('tour omitted the counterexample source budget')
    if extensions:
        wavelet, sparsity = records['wavelet.html'], records['fw-sparsity.html']
        artifacts = {a['path']:a for a in manifest['artifacts']}
        w, s = artifacts['wavelet.html'], artifacts['fw-sparsity.html']
        language = manifest['language']
        if (wavelet['parameters']['steps'] != 200 or wavelet['parameters']['seed'] != 0
                or sparsity['parameters']['steps'] != 40
                or w['command'] != ['reproduce','fista-wavelet','--steps','200','--seed','0','--lang',language]
                or s['command'] != ['case-study','fw-sparsity','--steps','40','--lang',language]
                or w['source'] != wavelet['source'] or s['source'] != sparsity['source']
                or w['steps'] != 200 or w['dimension'] != 65536 or w['seed'] != 0
                or w['noise_std'] != .001 or w['lambda'] != .0001 or w['f_star'] is not None
                or s['steps'] != 40 or s['dimensions'] != [3,8,32,128]):
            raise RuntimeError('tour extension settings or reproduction command differ')
    info = records['stress-ista-vs-fista.html']
    if info['rows'][24]['metric'] is not None or info['rows'][24]['status'] != 'unresolved':
        raise RuntimeError('tour must retain the unresolved case')

    # A valid contract still requires every original independent audit. No
    # previous validation result is reused, including after a rehashed edit.
    from smoke_learning_paths import validate_learning_paths
    validate_learning_paths((folder/'atlas.html').read_text(encoding='utf8'), manifest['artifacts'])
    if 'fista-backtracking' in extensions:
        from smoke_backtracking_tour import validate_backtracking_tour_presentation
        from smoke_fista_backtracking import validate_fista_backtracking
        validate_backtracking_tour_presentation(folder)
        validate_fista_backtracking(backtracking)
    if 'admm-lasso' in extensions:
        from smoke_admm_geometry import validate_admm_geometry
        from smoke_admm_tour import validate_admm_tour_presentation
        validate_admm_tour_presentation(folder)
        validate_admm_geometry(admm)
    if 'reddi-2018' in extensions:
        from smoke_adam_counterexample import validate_adam_counterexample
        validate_adam_counterexample(adam)
    if 'cg-spectrum' in extensions:
        from smoke_cg_spectrum import validate_cg_spectrum
        validate_cg_spectrum(spectrum)
    validate_reproduction(records['shewchuk.html'])
    validate_landscape(records['landscape.html'])
    validate_simplex_geometry(records['simplex.html'])
    validate_proximal_geometry(records['proximal.html'])
    validate_tight_geometry(records['tight-gd.html'])
    from smoke_deblurring import validate_deblurring
    validate_deblurring(records['deblur.html'])
    from smoke_heavy_ball_cycle import validate_heavy_ball_cycle
    validate_heavy_ball_cycle(records['heavy-ball.html'])
    if extensions:
        from smoke_fw_sparsity import validate_fw_sparsity
        from smoke_wavelet import validate_wavelet
        validate_wavelet(wavelet)
        validate_fw_sparsity(sparsity)
    if 'kaczmarz-expectation' in extensions:
        from smoke_kaczmarz import validate_kaczmarz
        validate_kaczmarz(randomized)
    if 'kaczmarz-sampling' in extensions:
        from smoke_nonuniform import validate_nonuniform
        validate_nonuniform(sampling)
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
    validate_proximal_models(result)
    from smoke_proximal_dual import validate_proximal_dual
    validate_proximal_dual(result)


def validate_proximal_models(result):
    """Expand Q directly, independently of the production PSD-excess evaluation."""
    def require(condition):
        if not condition:
            raise RuntimeError('proximal upper model differs from its actual step')
    def close(actual, expected):
        require(math.isfinite(actual) and math.isclose(actual, expected, rel_tol=2e-12, abs_tol=5e-13))
    contract = result['upper_model']
    require(contract['kind'] == 'actual-proximal-upper-model-slices'
            and contract['parameter_interval'] == [-.25, 1.25] and contract['base_samples'] == 49)
    for case in result['cases']:
        lam = case['lambda']
        def value(point):
            a, b = point
            return .5*((a-1.4)**2+(3*b+2.4)**2)+lam*(abs(a)+abs(b))
        for run in case['runs'].values():
            for stage in run['stages']:
                model, y, nxt = stage['upper_model'], stage['y'], stage['next_x']
                d = [b-a for a, b in zip(y, nxt)]
                require(len(model['direction']) == 2 and type(model['zero_step']) is bool)
                for a, b in zip(model['direction'], d):
                    close(a, b)
                require(model['zero_step'] == (y == nxt))
                expected_t = set(-.25+i/32 for i in range(49)) | {0., 1.}
                for a, b in zip(y, d):
                    if b and -.25 < -a/b < 1.25:
                        expected_t.add(-a/b)
                ts = model['parameter']
                require(ts == sorted(expected_t))
                require(len(ts) == len(model['objective_gap']) == len(model['model_gap']))
                f_y = .5*((y[0]-1.4)**2+(3*y[1]+2.4)**2)
                grad = [y[0]-1.4, 9*y[1]+7.2]
                def q(point):
                    delta = [a-b for a, b in zip(point, y)]
                    return f_y+sum(a*b for a, b in zip(delta, grad))+4.5*sum(a*a for a in delta)+lam*sum(abs(a) for a in point)
                for t, f_gap, q_gap in zip(ts, model['objective_gap'], model['model_gap']):
                    u = [a+t*b for a, b in zip(y, d)]
                    close(f_gap, value(u)-case['f_star'])
                    close(q_gap, q(u)-case['f_star'])
                    require(q_gap >= f_gap-5e-13)
                for key, expected in [('previous_gap', value(stage['x'])-case['f_star']),
                                      ('anchor_gap', value(y)-case['f_star']),
                                      ('next_gap', value(nxt)-case['f_star']),
                                      ('model_next_gap', q(nxt)-case['f_star'])]:
                    close(model[key], expected)
                require(math.isclose(model['model_excess_next'], 4*d[0]**2, rel_tol=2e-12, abs_tol=1e-28))
                close(model['model_next_gap'], model['next_gap']+model['model_excess_next'])
                require(model['next_gap'] <= model['model_next_gap']+5e-13
                        and model['model_next_gap'] <= model['anchor_gap']+5e-13)


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


def validate_simplex_geometry(result, *, require_segment=False):
    """Recompute certificates and transitions with scalar arithmetic, outside the package."""
    if (result['kind'] != 'chainbench.simplex-geometry'
            or result['evidence_level'] != 'controlled-geometric-illustrations'):
        raise RuntimeError('invalid simplex evidence identity')
    validate_fw_segments(result, required=require_segment)
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


def validate_fw_segments(result, *, required=False):
    """Audit local quadratic profiles with 60-digit arithmetic; no package imports."""
    if 'segment_geometry' not in result:
        if required or any('segment' in row for c in result['cases'] for row in c['rows']):
            raise RuntimeError('missing Frank-Wolfe segment identity')
        return
    expected_metadata = {
        'kind': 'chainbench.frank-wolfe-segment-geometry', 'schema_version': 1,
        'source': {
            'url': 'https://proceedings.mlr.press/v28/jaggi13.pdf',
            'locator': 'Algorithm 3, PDF page 3: minimize f(x+gamma(s-x)) on [0,1]',
        },
        'scope': 'local segment diagnostic on the existing Algorithm 1 scheduled iterates',
        'curve': '65 uniform gamma samples union the scheduled gamma and analytic minimizer',
        'minimum': 'clip(-slope/||s-x||^2,0,1); choose 0 for a zero direction',
        'equal_value_gamma': 'unconstrained second root of phi(gamma)=phi(0); None for a zero direction',
        'limits': [
            'The alternative does not advance a second line-search trajectory.',
            'Derived quadratic geometry, not an original-paper experiment or a method ranking.',
            'Float64 values and raw quadratic-expansion discrepancies, not interval arithmetic.',
        ],
    }
    if result['segment_geometry'] != expected_metadata:
        raise RuntimeError('Frank-Wolfe segment source or scope differs')

    def close(actual, expected):
        if (type(actual) not in (int, float) or not math.isfinite(actual)
                or not math.isclose(actual, float(expected), rel_tol=0, abs_tol=3e-15)):
            raise RuntimeError('Frank-Wolfe segment value differs')

    def vector(actual, expected):
        if len(actual) != len(expected):
            raise RuntimeError('Frank-Wolfe segment dimension differs')
        for a, b in zip(actual, expected):
            close(a, b)

    fields = {'direction', 'direction_norm_squared', 'slope', 'minimum_gamma', 'minimum_index',
              'minimum_point', 'minimum_value', 'scheduled_index', 'equal_value_gamma',
              'parameter', 'points', 'objective', 'affine', 'quadratic', 'quadratic_roundoff_inf'}
    with localcontext() as context:
        context.prec = 60
        for case in result['cases']:
            rows = case['rows']
            if 'segment' not in rows[-1] or rows[-1]['segment'] is not None:
                raise RuntimeError('final iterate must have no unperformed segment update')
            for row, nxt in zip(rows, rows[1:]):
                p = row.get('segment')
                if not isinstance(p, dict) or set(p) != fields:
                    raise RuntimeError('missing or changed Frank-Wolfe segment fields')
                x, s, target = ([Decimal.from_float(float(v)) for v in values]
                                for values in (row['x'], row['vertex'], case['target']))
                d = [b-a for a, b in zip(x, s)]
                q = sum(v*v for v in d)
                slope = sum((a-b)*c for a, b, c in zip(x, target, d))
                minimum = min(Decimal(1), max(Decimal(0), -slope/q)) if q else Decimal(0)
                vector(p['direction'], d)
                close(p['direction_norm_squared'], q)
                close(p['slope'], slope)
                close(p['minimum_gamma'], minimum)
                if q:
                    close(p['equal_value_gamma'], -2*slope/q)
                elif p['equal_value_gamma'] is not None:
                    raise RuntimeError('a constant segment has no unique second root')
                grid = sorted({i/64 for i in range(65)} | {row['gamma'], p['minimum_gamma']})
                if (p['parameter'] != grid
                        or p['scheduled_index'] != grid.index(row['gamma'])
                        or p['minimum_index'] != grid.index(p['minimum_gamma'])
                        or any(len(p[key]) != len(grid) for key in ('points', 'objective', 'affine', 'quadratic'))):
                    raise RuntimeError('Frank-Wolfe segment grid or sample indices differ')
                value = sum((a-b)**2 for a, b in zip(x, target))/2
                for i, gamma in enumerate(grid):
                    g = Decimal.from_float(gamma)
                    point = [(1-g)*a+g*b for a, b in zip(x, s)]
                    f = sum((a-b)**2 for a, b in zip(point, target))/2
                    affine = value+g*slope
                    vector(p['points'][i], point)
                    close(p['objective'][i], f)
                    close(p['affine'][i], affine)
                    close(p['quadratic'][i], affine+g*g*q/2)
                i, j = p['scheduled_index'], p['minimum_index']
                if (p['points'][i] != nxt['x'] or p['objective'][i] != nxt['gap']
                        or p['minimum_point'] != p['points'][j]
                        or p['minimum_value'] != p['objective'][j]
                        or p['minimum_value'] > min(row['gap'], nxt['gap'])+3e-15
                        or p['quadratic_roundoff_inf'] != max(abs(a-b) for a, b in zip(p['objective'], p['quadratic']))):
                    raise RuntimeError('actual step, segment minimum or raw roundoff differs')


def validate_reproduction(result):
    """Independent scalar checks; no imports from the package being tested."""
    from smoke_spectral import validate_spectral
    validate_spectral(result)
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


def validate_landscape(result):
    """Independent scalar fixture, metrics, parameters and all five recurrences."""
    def require(condition):
        if not condition:
            raise RuntimeError('landscape evidence differs from actual inputs or recurrence')
    def close(a, b):
        require(math.isfinite(a) and math.isclose(a, b, rel_tol=2e-9, abs_tol=2e-11))
    p = result['problem']
    q, b, star = p['Q'], p['b'], p['x_star']
    require(result['kind'] == 'chainbench.landscape' and p['dimension'] == 2
            and star == [1., -.8] and p['start'] == [-1.55, 1.45]
            and p['c'] == 0 and p['seed'] is None and p['lambda'] is None)
    theta = math.radians(p['angle_degrees'])
    co, si, mu = math.cos(theta), math.sin(theta), 1/p['condition_number']
    expected = [[co*co*mu+si*si, co*si*(mu-1)], [co*si*(mu-1), si*si*mu+co*co]]
    for row, ref in zip(q, expected, strict=True):
        for a, v in zip(row, ref, strict=True):
            close(a, v)
    def product(x):
        return [sum(a*v for a, v in zip(row, x)) for row in q]
    def gradient(x):
        return [a-v for a, v in zip(product(x), b)]
    def dot(x, y):
        return sum(a*v for a, v in zip(x, y))
    for actual, expected in zip(b, product(star), strict=True):
        close(actual, expected)
    close(p['L'], 1.)
    close(p['mu'], mu)
    close(p['actual_condition_number'], p['L']/p['mu'])
    close(p['f_star'], -.5*dot(star, b))
    inputs = {'Q': q, 'b': b, 'x_star': star, 'x0': p['start']}
    digest = hashlib.sha256()
    for name in sorted(inputs):
        value = inputs[name]
        shape = [2, 2] if name == 'Q' else [2]
        flat = [v for row in value for v in row] if name == 'Q' else value
        digest.update(name.encode()+b'\0'+json.dumps(shape, separators=(',', ':')).encode()+b'\0')
        digest.update(struct.pack('<'+str(len(flat))+'d', *flat))
    require(digest.hexdigest() == result['input_sha256'])
    for method in result['methods']:
        xs, gaps, run = result['traces'][method], result['gaps'][method], result['runs'][method]
        settings = result['method_parameters'][method]
        require(xs[0] == p['start'] and run['updates'] == len(xs)-1
                and len(xs) == len(gaps) == len(run['residual_norms']))
        if method in ('gd', 'smooth-fista'):
            close(settings['step'], 1/p['L'])
        if method == 'smooth-fista':
            require(settings['t0'] == 1 and settings['y0'] == xs[0])
        if method == 'heavy-ball':
            close(settings['alpha'], 4/(math.sqrt(p['L'])+math.sqrt(p['mu']))**2)
            close(settings['beta'], ((math.sqrt(p['L'])-math.sqrt(p['mu']))/(math.sqrt(p['L'])+math.sqrt(p['mu'])))**2)
            require(settings['x_minus_1'] == xs[0])
        if method == 'proximal-point':
            require(settings['proximal_parameter'] == 1.)
        y, t = xs[0], 1.
        residual = [-v for v in gradient(xs[0])]
        direction = residual[:]
        for k, x in enumerate(xs):
            e = [a-v for a, v in zip(x, star)]
            require(gaps[k] >= 0)
            close(gaps[k], dot(e, product(e))/2)
            close(run['residual_norms'][k], math.hypot(*gradient(x)))
            if k == len(xs)-1:
                continue
            nxt = xs[k+1]
            if method == 'gd':
                expected = [a-g/p['L'] for a, g in zip(x, gradient(x))]
            elif method == 'smooth-fista':
                expected = [a-g/p['L'] for a, g in zip(y, gradient(y))]
                tn = (1+math.sqrt(1+4*t*t))/2
                y = [a+(t-1)/tn*(a-v) for a, v in zip(nxt, x)]
                t = tn
            elif method == 'heavy-ball':
                old = xs[max(k-1, 0)]
                expected = [a-settings['alpha']*g+settings['beta']*(a-v)
                            for a, g, v in zip(x, gradient(x), old)]
            elif method == 'proximal-point':
                # Check the implicit equation without using a matrix solver.
                expected = [a+v-w for a, v, w in zip(x, b, product(nxt))]
            elif method == 'cg':
                rr = dot(residual, residual)
                step = rr/dot(direction, product(direction))
                expected = [a+step*d for a, d in zip(x, direction)]
                new = [r-step*v for r, v in zip(residual, product(direction))]
                beta = dot(new, new)/rr
                direction = [r+beta*d for r, d in zip(new, direction)]
                residual = new
            else:
                raise RuntimeError('unsupported landscape method')
            for a, v in zip(nxt, expected, strict=True):
                close(a, v)
        if method == 'cg':
            require(settings['rtol'] == 1e-12 and settings['atol'] == 0.)
            converged = run['residual_norms'][-1] <= 1e-12*run['residual_norms'][0]
            require(run['termination'] == ('converged' if converged else 'max_steps'))
            require(converged or run['updates'] == result['steps'])
        else:
            require(run['termination'] == 'fixed_budget' and run['updates'] == result['steps'])
    validate_ppa_subproblems(result)


def validate_ppa_subproblems(result):
    """Independently check the small shifted system and its recorded gradient balance."""
    def require(condition):
        if not condition:
            raise RuntimeError('PPA subproblem evidence differs')
    def close(a, b, atol=2e-13):
        require(math.isfinite(a) and math.isclose(a,b,rel_tol=2e-12,abs_tol=atol))
    if 'proximal-point' not in result['methods']:
        require('proximal_subproblems' not in result)
        return
    record = result['proximal_subproblems']
    q, b = result['problem']['Q'], result['problem']['b']
    c = result['method_parameters']['proximal-point']['proximal_parameter']
    h = [[q[i][j]+(1/c if i == j else 0.) for j in range(2)] for i in range(2)]
    require(record['kind'] == 'exact-quadratic-ppa-subproblems' and record['parameter'] == c)
    require(len(record['hessian']) == 2 and all(len(row) == 2 for row in record['hessian']))
    for row, expected in zip(record['hessian'], h):
        for a, v in zip(row, expected):
            close(a,v)
    points = result['traces']['proximal-point']
    require(len(record['rows']) == len(points)-1)
    def dot(x,y):
        return sum(a*v for a,v in zip(x,y))
    for k, row in enumerate(record['rows'],1):
        previous, nxt = points[k-1:k+1]
        require(row['completed_update'] == k and row['previous'] == previous and row['next'] == nxt)
        require(type(row['unchanged_iterate']) is bool and row['unchanged_iterate'] == (previous == nxt))
        rhs = [a+v/c for a,v in zip(b,previous)]
        determinant = h[0][0]*h[1][1]-h[0][1]*h[1][0]
        ref = [(rhs[0]*h[1][1]-rhs[1]*h[0][1])/determinant,
               (rhs[1]*h[0][0]-rhs[0]*h[1][0])/determinant]
        gradient = [dot(qi,nxt)-v for qi,v in zip(q,b)]
        movement = [a-v for a,v in zip(nxt,previous)]
        penalty = [v/c for v in movement]
        for field, expected in [('rhs',rhs),('reference',ref),('objective_gradient',gradient),('penalty_gradient',penalty)]:
            require(len(row[field]) == 2)
            for a,v in zip(row[field],expected):
                close(a,v)
        # Norms use the stored floating gradients after checking their actual coordinates.
        balance = [a+v for a,v in zip(row['objective_gradient'],row['penalty_gradient'])]
        require(len(row['balance']) == 2)
        for a,v in zip(row['balance'],balance):
            close(a,v,atol=1e-28)
        residual = math.hypot(*balance)
        denominator = math.hypot(*row['objective_gradient'])+math.hypot(*row['penalty_gradient'])
        close(row['balance_norm'],residual,atol=1e-28)
        close(row['balance_denominator'],denominator,atol=1e-28)
        if denominator:
            close(row['relative_balance'],residual/denominator,atol=1e-28)
        else:
            require(row['relative_balance'] is None)
        require(len(row['reference_balance']) == 2)
        for a,v in zip(row['reference_balance'],[dot(hi,row['reference'])-v for hi,v in zip(h,rhs)]):
            close(a,v,atol=1e-14)
        close(row['movement_norm'],math.hypot(*movement),atol=1e-28)
        close(row['previous_objective_gap'],result['gaps']['proximal-point'][k-1])
        close(row['next_objective_gap'],result['gaps']['proximal-point'][k])
        value = dot(movement,movement)/(2*c)
        close(row['penalty_value'],value,atol=1e-28)
        close(row['subproblem_value_above_f_star'],row['next_objective_gap']+value)
        error = [a-v for a,v in zip(nxt,row['reference'])]
        close(row['reference_error_energy'],.5*sum(e*dot(hi,error) for e,hi in zip(error,h)),atol=1e-28)
