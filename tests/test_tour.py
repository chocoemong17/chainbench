import importlib.util
import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from chainbench.cli import main
from chainbench.tour import build_tour


def validator():
    spec = importlib.util.spec_from_file_location('tour_smoke',
        Path(__file__).resolve().parents[1]/'scripts/smoke_workflows.py')
    module = importlib.util.module_from_spec(spec)
    import sys
    from unittest.mock import patch
    with patch.object(sys, 'path', [str(Path(__file__).resolve().parents[1]/'scripts'), *sys.path]):
        spec.loader.exec_module(module)
        importlib.import_module('smoke_deblurring')
        importlib.import_module('smoke_heavy_ball_cycle')
        importlib.import_module('smoke_wavelet')
        importlib.import_module('smoke_fw_sparsity')
        importlib.import_module('smoke_kaczmarz')
        importlib.import_module('smoke_nonuniform')
        importlib.import_module('smoke_cg_spectrum')
        importlib.import_module('smoke_adam_counterexample')
        importlib.import_module('smoke_admm_geometry')
        importlib.import_module('smoke_admm_tour')
        importlib.import_module('smoke_backtracking_tour')
        importlib.import_module('smoke_fista_backtracking')
        importlib.import_module('smoke_spectral')
        importlib.import_module('smoke_proximal_dual')
        importlib.import_module('smoke_learning_paths')
    return module.validate_tour


@pytest.fixture(scope='module')
def tour_folder(tmp_path_factory):
    folder = tmp_path_factory.mktemp('offline-tour')/'tour'
    build_tour(folder, 'ko')
    return folder


def test_generated_tour_hashes_links_coverage_and_independent_numerics(tour_folder):
    records = validator()(tour_folder)
    assert len(records) == 16
    assert records['landscape.html']['methods'] == ['gd', 'smooth-fista', 'heavy-ball', 'cg', 'proximal-point']
    assert records['heavy-ball.html']['parameters']['steps'] == 50
    assert len(records['atlas.html']['results']) == 8
    assert records['deblur.html']['parameters']['full_paper_budget']
    assert len(records['deblur.html']['runs']['fista']['rows']) == 10001
    assert records['tight-gd.html']['matches_target']
    assert records['tight-gd.html']['observed_ratio'] == pytest.approx(1.)
    assert '<html lang="ko">' in (tour_folder/'index.html').read_text(encoding='utf8')


def test_validator_rejects_missing_or_changed_artifact(tour_folder):
    path = tour_folder/'atlas.html'
    raw = path.read_bytes()
    try:
        path.write_bytes(raw+b'changed')
        with pytest.raises(RuntimeError, match='hash'):
            validator()(tour_folder)
    finally:
        path.write_bytes(raw)
    path = tour_folder/'manifest.json'
    raw = path.read_bytes()
    try:
        manifest = json.loads(raw)
        manifest['artifacts'].pop()
        path.write_text(json.dumps(manifest), encoding='utf8')
        with pytest.raises(RuntimeError, match='coverage'):
            validator()(tour_folder)
    finally:
        path.write_bytes(raw)


def test_existing_destination_is_preserved_before_computation(tmp_path, monkeypatch):
    import chainbench.tour as tour
    marker = tmp_path/'keep.txt'
    marker.write_text('keep')
    monkeypatch.setattr(tour, '_reports', lambda _: pytest.fail('must check destination first'))
    with pytest.raises(FileExistsError):
        build_tour(tmp_path)
    assert marker.read_text() == 'keep'
    with pytest.raises(SystemExit) as error:
        main(['tour', '--output', str(tmp_path)])
    assert error.value.code == 2
    assert marker.read_text() == 'keep'


def test_failed_calculation_leaves_no_destination_or_staging_folder(tmp_path, monkeypatch):
    import chainbench.tour as tour
    def failed(_):
        yield 'atlas.html', '<main>partial</main>', {'layer': 'test'}
        raise FloatingPointError('injected numerical failure')
    monkeypatch.setattr(tour, '_reports', failed)
    with pytest.raises(FloatingPointError, match='injected'):
        build_tour(tmp_path/'result')
    assert list(tmp_path.iterdir()) == []


def test_failed_destination_write_cleans_only_created_files(tmp_path, monkeypatch):
    import chainbench.tour as tour
    monkeypatch.setattr(tour, '_index', lambda *_: '<main>test index</main>')
    monkeypatch.setattr(tour, '_reports', lambda _: iter([
        ('atlas.html', '<main>test</main>', {'layer': 'test'})]))
    original_open = Path.open
    destination = tmp_path/'result'
    def fail(self, *args, **kwargs):
        if self == destination/'manifest.json':
            raise OSError('injected destination write failure')
        return original_open(self, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail)
    with pytest.raises(OSError, match='injected'):
        build_tour(destination)
    assert list(tmp_path.iterdir()) == []


def test_tour_rejects_invalid_language_or_missing_parent_before_creating_output(tmp_path):
    with pytest.raises(ValueError, match='lang'):
        build_tour(tmp_path/'result', 'fr')
    with pytest.raises(ValueError, match='parent'):
        build_tour(tmp_path/'absent'/'result')
    assert list(tmp_path.iterdir()) == []


@pytest.fixture(scope='module')
def extended_folder(tmp_path_factory):
    folder = tmp_path_factory.mktemp('extended-tour')/'tour'
    build_tour(folder, 'ko', extended=True)
    return folder


def test_extended_tour_preserves_base_records_and_reproduction_metadata(tour_folder, extended_folder):
    # The strict validators cover all arrays/recurrences, including declared noise.
    records = validator()(extended_folder)
    assert len(records) == 24
    assert records['wavelet.html']['parameters']['full_paper_budget']
    assert records['wavelet.html']['problem']['f_star'] is None
    assert records['fw-sparsity.html']['parameters']['steps'] == 40
    assert all(records[name] == record for name, record in validator()(tour_folder).items())
    assert records['kaczmarz.html']['parameters']['trials'] == 64
    assert json.loads((extended_folder/'manifest.json').read_text())['extensions'] == ['fista-wavelet','fw-sparsity','kaczmarz-expectation','kaczmarz-sampling','cg-spectrum','reddi-2018','admm-lasso','fista-backtracking']
    assert json.loads((tour_folder/'manifest.json').read_text())['extensions'] == []
    assert 'wavelet.html' not in (tour_folder/'index.html').read_text()
    assert 'fw-sparsity.html' not in (tour_folder/'index.html').read_text()
    assert 'kaczmarz.html' not in (tour_folder/'index.html').read_text()
    assert 'sampling.html' not in (tour_folder/'index.html').read_text()
    assert 'cg-spectrum.html' not in (tour_folder/'index.html').read_text()
    assert 'adam.html' not in (tour_folder/'index.html').read_text()
    assert 'admm.html' not in (tour_folder/'index.html').read_text()
    assert 'backtracking.html' not in (tour_folder/'index.html').read_text()
    from chainbench.kaczmarz import run_kaczmarz
    assert records['kaczmarz.html'] == run_kaczmarz(40,64)
    from chainbench.nonuniform_sampling import run_nonuniform_sampling
    assert records['sampling.html'] == run_nonuniform_sampling()
    from chainbench.cg_spectrum import run_cg_spectrum
    assert records['cg-spectrum.html'] == run_cg_spectrum()
    from chainbench.adam_counterexample import run_adam_counterexample
    assert records['adam.html'] == run_adam_counterexample()
    from chainbench.admm_geometry import run_admm_geometry
    assert records['admm.html'] == run_admm_geometry()
    from chainbench.fista_backtracking import run_fista_backtracking
    assert records['backtracking.html'] == run_fista_backtracking()


def test_adam_preview_retains_the_slow_case_and_actual_regret_quantity(extended_folder):
    import base64
    import re

    report = (extended_folder/'adam.html').read_text()
    case = report.split('<details data-adam-case="c3-a0.1">',1)[1].split('<details data-adam-case=',1)[0]
    expected = re.search(r'<svg\b[^>]*data-adam-chart="average_regret".*?</svg>',case,flags=re.S)[0]
    index = (extended_folder/'index.html').read_text()
    card = re.search(r'<a class="tour-card" href="adam.html">.*?</a>',index,flags=re.S)[0]
    encoded = re.search(r'src="data:image/svg\+xml;base64,([^"]+)"',card)[1]
    assert base64.b64decode(encoded).decode()==expected
    assert 'AMSGrad is still far from' in index
    assert 'T=0 average is undefined' in index
    assert 'guarantees do not transfer' in index
    assert 'period-101 Figure 1' in index
    assert 'href="heavy-ball.html" data-tour-regret' in report
    assert 'data-tour-lesson' not in report  # No false ninth fixed-suite topic.
    for filename in ('heavy-ball.html','atlas.html'):
        assert 'href="adam.html" data-tour-regret' in (extended_folder/filename).read_text()


def test_admm_preview_is_the_actual_surface_and_notation_bridge_is_scoped(extended_folder):
    import base64
    import re
    import xml.etree.ElementTree as ET

    report = (extended_folder/'admm.html').read_text()
    case = report.split('data-admm-case="coupled-lambda0.1-zero-rho1"',1)[1].split('data-admm-case=',1)[0]
    expected = re.search(r'<svg\b[^>]*data-admm-primal="surface".*?</svg>',case,flags=re.S)[0]
    index = (extended_folder/'index.html').read_text()
    card = re.search(r'<a class="tour-card" href="admm.html">.*?</a>',index,flags=re.S)[0]
    raw = base64.b64decode(re.search(r'src="data:image/svg\+xml;base64,([^"]+)"',card)[1]).decode()
    assert raw==expected
    assert ET.fromstring(raw).tag=='{http://www.w3.org/2000/svg}svg'
    assert 'not numerical trajectories or new experiments' in index
    assert 'The proximal report names y−∇f(y)/L as z' in index
    assert 'y=ρu is dual memory in feature coordinates' in index
    assert 'not a same-input, equal-work speed comparison' in index
    assert 'FISTA’s envelope is not transferred' in index
    assert 'href="proximal.html" data-tour-splitting' in report
    assert 'data-tour-lesson' not in report
    for filename in ('proximal.html','atlas.html'):
        assert 'href="admm.html" data-tour-splitting' in (extended_folder/filename).read_text()


@pytest.mark.parametrize('missing',['case','surface'])
def test_admm_preview_never_falls_through_to_another_case_or_contour(missing):
    from chainbench.tour import _admm_thumbnail
    html = '<details data-admm-case="coupled-lambda0.1-zero-rho1"><svg data-admm-primal="surface"></svg></details><details data-admm-case="other"><svg data-admm-primal="surface"></svg></details>'
    html = html.replace('coupled-lambda0.1-zero-rho1','absent',1) if missing=='case' else html.replace('data-admm-primal="surface"','data-admm-primal="contour"',1)
    with pytest.raises(ValueError,match='actual coupled'):
        _admm_thumbnail(html)


@pytest.mark.parametrize('fault',['steps','dimension','layer','source','cases','input_sha256','metric','variant','preview','command'])
def test_admm_tour_binds_original_metric_full_inputs_and_split_variant(extended_folder,fault):
    path = extended_folder/'manifest.json'
    original = path.read_bytes()
    try:
        manifest = json.loads(original)
        artifact = next(a for a in manifest['artifacts'] if a['path']=='admm.html')
        if fault=='cases':
            artifact['cases'].pop()
        elif fault=='source':
            artifact['source']['role'] = 'new algorithm introduced in 2011'
        elif fault=='input_sha256':
            artifact['input_sha256'][artifact['cases'][0]] = '0'*64
        elif fault=='variant':
            artifact['variant']['initial_x'] = [0,0]
        elif fault=='preview':
            artifact['preview']['height'] = 'split objective minus optimum'
        elif fault=='command':
            artifact['command'][3] = '1'
        else:
            artifact[fault] = {'steps':1,'dimension':3,'layer':'published-figure-reproduction','metric':'split objective gap'}[fault]
        path.write_text(json.dumps(manifest))
        with pytest.raises(RuntimeError,match='ADMM tour metadata'):
            validator()(extended_folder)
    finally:
        path.write_bytes(original)


@pytest.mark.parametrize('fault',['preview','flow','meaning','link','guide'])
def test_admm_tour_rejects_rehashed_wrong_preview_or_missing_comparison(extended_folder,fault):
    import hashlib
    import re

    path = extended_folder/('admm.html' if fault in ('link','guide') else 'index.html')
    manifest_path = extended_folder/'manifest.json'
    before,manifest_before = path.read_bytes(),manifest_path.read_bytes()
    try:
        text = before.decode()
        if fault=='preview':
            text = re.sub(r'(<a class="tour-card" href="admm.html">.*?<img[^>]*src=")[^"]+',r'\1data:image/svg+xml;base64,PHN2Zy8+',text,count=1,flags=re.S)
        elif fault=='flow':
            text = text.replace('class="split-flow" data-split-method="admm"','class="split-flow" data-other-method="admm"',1)
        elif fault=='meaning':
            text = text.replace('data-split-meaning="y"','data-other-meaning="y"',1)
        elif fault=='link':
            text = text.replace('data-tour-splitting>','data-other-link>',1)
        else:
            text = text.replace('data-tour-splitting-guide>','data-other-guide>',1)
        assert text!=before.decode()
        raw = text.encode()
        path.write_bytes(raw)
        manifest = json.loads(manifest_before)
        artifact = next(a for a in manifest['artifacts'] if a['path']==path.name)
        artifact.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        manifest_path.write_text(json.dumps(manifest))
        with pytest.raises(RuntimeError,match='ADMM tour'):
            validator()(extended_folder)
    finally:
        path.write_bytes(before)
        manifest_path.write_bytes(manifest_before)


@pytest.mark.parametrize('missing',['case','metric'])
def test_adam_preview_does_not_fall_through_to_another_case(missing):
    from chainbench.tour import _adam_thumbnail
    html = '<details data-adam-case="c3-a0.1"><svg data-adam-chart="x"></svg></details><details data-adam-case="c3-a0.5"><svg data-adam-chart="average_regret"></svg></details>'
    if missing=='case':
        html = html.replace('c3-a0.1','absent')
    with pytest.raises(ValueError,match='actual c3-a0.1'):
        _adam_thumbnail(html)


@pytest.mark.parametrize('fault',['steps','methods','C_values','alpha_fractions','source','cases','metric','variant','preview','command'])
def test_adam_extension_binds_variant_loss_metric_and_complete_case_selection(extended_folder,fault):
    path = extended_folder/'manifest.json'
    original = path.read_bytes()
    try:
        manifest = json.loads(original)
        artifact = next(a for a in manifest['artifacts'] if a['path']=='adam.html')
        if fault in ('methods','C_values','alpha_fractions','cases'):
            artifact[fault].pop()
        elif fault=='steps':
            artifact['steps'] = 30
        elif fault=='source':
            artifact['source']['counterexample'] = 'Figure 1'
        elif fault=='metric':
            artifact['metric'] = 'objective gap'
        elif fault=='variant':
            artifact['variant']['bias_correction'] = True
        elif fault=='preview':
            artifact['preview']['case'] = 'c3-a0.9'
        else:
            artifact['command'][3] = '30'
        path.write_text(json.dumps(manifest))
        with pytest.raises(RuntimeError,match='Adam tour metadata'):
            validator()(extended_folder)
    finally:
        path.write_bytes(original)


def test_cg_spectrum_preview_uses_the_actual_three_spectrum_overview(extended_folder):
    import base64
    import re

    report = (extended_folder/'cg-spectrum.html').read_text()
    expected = re.search(r'<details data-cg-overview><summary>hadamard · equal-energy</summary>.*?(<svg\b.*?</svg>)',report,flags=re.S)[1]
    index = (extended_folder/'index.html').read_text()
    card = re.search(r'<a class="tour-card" href="cg-spectrum.html">.*?</a>',index,flags=re.S)[0]
    encoded = re.search(r'src="data:image/svg\+xml;base64,([^"]+)"',card)[1]
    assert base64.b64decode(encoded).decode()==expected
    assert 'relative A-norm, not squared error' in index
    assert 'not a reproduction of Figure 31(d)' in index
    assert 'href="shewchuk.html" data-tour-spectrum' in report
    assert 'href="atlas.html#hestenes-stiefel-1952" data-tour-lesson' in report
    for filename in ('shewchuk.html','atlas.html','stress-hestenes-stiefel-1952.html'):
        assert 'href="cg-spectrum.html" data-tour-spectrum' in (extended_folder/filename).read_text()


@pytest.mark.parametrize('fault',['steps','dimension','rtol','source','cases','metric','preview','command'])
def test_spectral_extension_binds_inputs_stop_metric_and_preview(extended_folder,fault):
    path = extended_folder/'manifest.json'
    original = path.read_bytes()
    try:
        manifest = json.loads(original)
        artifact = next(a for a in manifest['artifacts'] if a['path']=='cg-spectrum.html')
        if fault=='steps':
            artifact['steps'] = 1
        elif fault=='dimension':
            artifact['dimension'] = 2
        elif fault=='rtol':
            artifact['rtol'] = 1e-6
        elif fault=='source':
            artifact['source']['scope'] = 'original Figure 31 data'
        elif fault=='cases':
            artifact['cases'].pop()
        elif fault=='metric':
            artifact['metric'] = 'squared error'
        elif fault=='preview':
            artifact['preview']['start_profile'] = 'single-mode'
        else:
            artifact['command'][3] = '1'
        path.write_text(json.dumps(manifest))
        with pytest.raises(RuntimeError,match='CG spectrum tour metadata'):
            validator()(extended_folder)
    finally:
        path.write_bytes(original)


def test_sampling_preview_is_the_actual_first_case_weighted_snapshot(extended_folder):
    import base64
    import re

    report = (extended_folder/'sampling.html').read_text()
    expected = re.search(r'<details data-sampling-gallery="weighted-100">.*?(<svg\b.*?</svg>)', report, flags=re.S)[1]
    index = (extended_folder/'index.html').read_text()
    card = re.search(r'<a class="tour-card" href="sampling.html">.*?</a>', index, flags=re.S)[0]
    encoded = re.search(r'src="data:image/svg\+xml;base64,([^"]+)"',card)[1]
    assert base64.b64decode(encoded).decode() == expected
    assert 'k=100' in index
    assert 'not an expectation' in index
    assert 'data-tour-sampling' in report
    assert 'href="sampling.html" data-tour-sampling' in (extended_folder/'kaczmarz.html').read_text()


@pytest.mark.parametrize('fault',['steps','seeds','dimension','source','metric','preview','command'])
def test_sampling_extension_binds_inputs_budget_metric_and_preview(extended_folder,fault):
    path = extended_folder/'manifest.json'
    original = path.read_bytes()
    try:
        manifest = json.loads(original)
        artifact = next(a for a in manifest['artifacts'] if a['path']=='sampling.html')
        if fault=='steps':
            artifact['steps'] = 100
        elif fault=='seeds':
            artifact['seeds'] = [1,2]
        elif fault=='dimension':
            artifact['dimension'] = 100
        elif fault=='source':
            artifact['source']['version'] = 'unsupported version'
        elif fault=='metric':
            artifact['metric'] = 'expected squared error'
        elif fault=='preview':
            artifact['preview']['iteration'] = 15000
        else:
            artifact['command'][3] = '100'
        path.write_text(json.dumps(manifest))
        with pytest.raises(RuntimeError,match='nonuniform sampling tour metadata'):
            validator()(extended_folder)
    finally:
        path.write_bytes(original)


@pytest.mark.parametrize('fault',['trials','seeds','source','metric','cases','command'])
def test_randomized_extension_binds_all_metadata(extended_folder,fault):
    path = extended_folder/'manifest.json'
    original = path.read_bytes()
    try:
        manifest = json.loads(original)
        artifact = next(a for a in manifest['artifacts'] if a['path']=='kaczmarz.html')
        if fault=='trials':
            artifact['trials'] = 63
        elif fault=='seeds':
            artifact['seeds'] = list(range(1,65))
        elif fault=='source':
            artifact['source']['theorem'] = 'unsupported claim'
        elif fault=='metric':
            artifact['metric'] = 'every single trajectory'
        elif fault=='cases':
            artifact['cases'].pop()
        else:
            artifact['command'][5] = '1'
        path.write_text(json.dumps(manifest))
        with pytest.raises(RuntimeError,match='randomized tour extension'):
            validator()(extended_folder)
    finally:
        path.write_bytes(original)


@pytest.mark.parametrize('extension_count',[2,3,4,5,6,7])
def test_previous_two_to_seven_extension_manifests_remain_readable(extended_folder,tmp_path,extension_count):
    import hashlib
    import re
    import shutil

    folder = tmp_path/'legacy'
    shutil.copytree(extended_folder,folder)
    include_randomized, include_sampling = extension_count>=3, extension_count>=4
    include_spectrum = extension_count>=5
    include_adam = extension_count>=6
    include_admm = extension_count>=7
    removed = ['backtracking.html'] + ([] if include_admm else ['admm.html']) + ([] if include_adam else ['adam.html']) + ([] if include_spectrum else ['cg-spectrum.html']) + ([] if include_sampling else ['sampling.html']) + ([] if include_randomized else ['kaczmarz.html'])
    for filename in removed:
        (folder/filename).unlink()
    manifest = json.loads((folder/'manifest.json').read_text())
    manifest['extensions'] = ['fista-wavelet','fw-sparsity'] + (['kaczmarz-expectation'] if include_randomized else []) + (['kaczmarz-sampling'] if include_sampling else []) + (['cg-spectrum'] if include_spectrum else []) + (['reddi-2018'] if include_adam else []) + (['admm-lasso'] if include_admm else [])
    manifest['artifacts'] = [a for a in manifest['artifacts'] if a['path'] not in removed]
    for a in manifest['artifacts']:
        p = folder/a['path']
        text = p.read_text()
        text = re.sub(r'<section id="step-selection">.*?</section>','',text,flags=re.S)
        text = re.sub(r'<a href="#step-selection">.*?</a>','',text,flags=re.S)
        text = re.sub(r'<nav aria-label="FISTA step selection">.*?</nav>','',text,flags=re.S)
        if not include_admm:
            text = re.sub(r'<section id="variable-splitting">.*?</section>','',text,flags=re.S)
            text = re.sub(r'<a href="#variable-splitting">.*?</a>','',text,flags=re.S)
            text = re.sub(r'<nav aria-label="Splitting comparison">.*?</nav>','',text,flags=re.S)
        if not include_adam:
            text = re.sub(r'<section id="online-regret">.*?</section>','',text,flags=re.S)
            text = re.sub(r'<a href="#online-regret">.*?</a>','',text,flags=re.S)
            text = re.sub(r'<nav aria-label="Changing-loss comparison">.*?</nav>','',text,flags=re.S)
        if not include_spectrum:
            text = re.sub(r'<section id="cg-spectrum">.*?</section>','',text,flags=re.S)
            text = re.sub(r'<a href="#cg-spectrum">.*?</a>','',text,flags=re.S)
            text = re.sub(r'<nav aria-label="CG spectral comparison">.*?</nav>','',text,flags=re.S)
        if not include_sampling:
            text = re.sub(r'<section id="sampling">.*?</section>','',text,flags=re.S)
            text = re.sub(r'<a href="#sampling">.*?</a>','',text,flags=re.S)
            text = re.sub(r'<nav aria-label="Sampling comparison">.*?</nav>','',text,flags=re.S)
        if not include_randomized:
            text = re.sub(r'<section id="randomized">.*?</section>','',text,flags=re.S)
            text = re.sub(r'<a href="#randomized">.*?</a>','',text,flags=re.S)
            text = re.sub(r'<nav aria-label="Expectation comparison">.*?</nav>','',text,flags=re.S)
        raw = text.encode()
        p.write_bytes(raw)
        a.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    (folder/'manifest.json').write_text(json.dumps(manifest))
    assert len(validator()(folder)) == 16+extension_count


@pytest.mark.parametrize('bad', [1, None, 'yes'])
def test_invalid_extended_option_is_rejected_before_writes(tmp_path, bad):
    with pytest.raises(ValueError, match='boolean'):
        build_tour(tmp_path/'bad', extended=bad)
    assert list(tmp_path.iterdir()) == []


def test_extension_failure_cleans_the_staged_base_too(tmp_path, monkeypatch):
    import chainbench.tour as tour
    monkeypatch.setattr(tour, '_reports', lambda _, **kwargs: iter([('atlas.html','<main>partial</main>',{'layer':'test'})]))
    def failed(_):
        raise FloatingPointError('extension failure')
        yield  # Keep this a lazy generator, like the actual report stream.
    monkeypatch.setattr(tour, '_extended_reports', failed)
    with pytest.raises(FloatingPointError, match='extension failure'):
        build_tour(tmp_path/'result', extended=True)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('fault', ['unknown', 'unadvertised', 'command', 'optimum'])
def test_extended_manifest_must_describe_actual_computations(extended_folder, fault):
    path = extended_folder/'manifest.json'
    raw = path.read_bytes()
    try:
        manifest = json.loads(raw)
        wavelet = next(a for a in manifest['artifacts'] if a['path'] == 'wavelet.html')
        if fault == 'unknown':
            manifest['extensions'] = ['invented']
        elif fault == 'unadvertised':
            manifest['extensions'] = []
        elif fault == 'command':
            wavelet['command'][5] = '1'
        else:
            wavelet['f_star'] = 0
        path.write_text(json.dumps(manifest))
        with pytest.raises(RuntimeError, match='extension|coverage|workflow'):
            validator()(extended_folder)
    finally:
        path.write_bytes(raw)


@contextmanager
def changed_evidence(folder, filename, change):
    """Rehash an altered numerical record, so the numerical audit must detect it."""
    import hashlib
    import re
    from html import escape, unescape

    path, manifest_path = folder/filename, folder/'manifest.json'
    before, manifest_before = path.read_bytes(), manifest_path.read_bytes()
    try:
        text = before.decode()
        pattern = r'(<pre id="chainbench-evidence">)(.*?)(</pre>)'
        match = re.search(pattern, text, re.S)
        record = json.loads(unescape(match[2]))
        change(record)
        replacement = escape(json.dumps(record, allow_nan=False))
        raw = (text[:match.start(2)]+replacement+text[match.end(2):]).encode()
        path.write_bytes(raw)
        manifest = json.loads(manifest_before)
        artifact = next(a for a in manifest['artifacts'] if a['path']==filename)
        artifact.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        manifest_path.write_text(json.dumps(manifest))
        yield
    finally:
        path.write_bytes(before)
        manifest_path.write_bytes(manifest_before)


@pytest.mark.parametrize('filename', ['sampling.html', 'wavelet.html'])
def test_late_extension_metadata_fails_before_presentation_or_numerical_audits(
        extended_folder, monkeypatch, filename):
    import sys

    check = validator()
    def unexpected(*args, **kwargs):
        pytest.fail('expensive audit ran before a known contract mismatch')
    monkeypatch.setattr(sys.modules['smoke_learning_paths'], 'validate_learning_paths', unexpected)
    monkeypatch.setattr(sys.modules['smoke_adam_counterexample'], 'validate_adam_counterexample', unexpected)
    path = extended_folder/'manifest.json'
    before = path.read_bytes()
    try:
        manifest = json.loads(before)
        artifact = next(a for a in manifest['artifacts'] if a['path']==filename)
        artifact['steps'] = 1
        path.write_text(json.dumps(manifest))
        with pytest.raises(RuntimeError, match='tour metadata|tour extension settings'):
            check(extended_folder)
    finally:
        path.write_bytes(before)


def test_rehashed_wrong_image_budget_fails_before_recomputing(extended_folder, monkeypatch):
    import sys

    check = validator()
    def unexpected(*args, **kwargs):
        pytest.fail('an independent audit ran before the image budget contract')
    monkeypatch.setattr(sys.modules['smoke_learning_paths'], 'validate_learning_paths', unexpected)
    monkeypatch.setattr(sys.modules['smoke_deblurring'], 'validate_deblurring', unexpected)
    with changed_evidence(extended_folder, 'deblur.html',
                          lambda d:d['parameters'].update(steps=1)):
        with pytest.raises(RuntimeError, match='full published image budget'):
            check(extended_folder)


def test_rehashed_numerical_edit_still_reaches_the_independent_audit(extended_folder):
    def corrupt(record):
        record['cases'][0]['rows'][1]['x'][0] += .125
    with changed_evidence(extended_folder, 'admm.html', corrupt):
        with pytest.raises(RuntimeError, match='ADMM geometry: numeric value differs'):
            validator()(extended_folder)


@pytest.mark.parametrize('missing', ['case', 'model', 'duplicate'])
def test_backtracking_preview_requires_the_named_first_rejected_model(missing):
    from chainbench.tour import _backtracking_thumbnail
    svg = '<svg><path data-bt-dynamic="model_gap"/></svg>'
    source = '<section data-bt-case="lambda0.8-zero-L1">'+svg+'</section><section data-bt-case="other">'+svg+'</section>'
    if missing=='case':
        source = source.replace('lambda0.8-zero-L1','absent')
    elif missing=='model':
        source = source.replace('model_gap','other',1)
    else:
        source = source.replace(svg,svg+svg,1)
    with pytest.raises(ValueError,match='actual lambda0.8-zero-L1'):
        _backtracking_thumbnail(source)


@pytest.mark.parametrize('fault', ['steps','source','cases','input_sha256','variant','gate','preview','command'])
def test_backtracking_metadata_cannot_relabel_or_reduce_the_experiment(extended_folder,fault):
    path = extended_folder/'manifest.json'
    original = path.read_bytes()
    try:
        manifest = json.loads(original)
        artifact = next(a for a in manifest['artifacts'] if a['path']=='backtracking.html')
        if fault=='cases':
            artifact['cases'].pop()
        elif fault=='input_sha256':
            artifact['input_sha256'][artifact['cases'][0]] = '0'*64
        elif fault=='variant':
            artifact['variant']['carry'] = 'reset each step'
        elif fault=='preview':
            artifact['preview']['accepted'] = True
        elif fault=='command':
            artifact['command'][3] = '1'
        else:
            artifact[fault] = 'changed'
        path.write_text(json.dumps(manifest))
        with pytest.raises(RuntimeError,match='Backtracking tour: metadata'):
            validator()(extended_folder)
    finally:
        path.write_bytes(original)


@pytest.mark.parametrize('fault', ['preview','flow','meaning','caption','link','guide'])
def test_backtracking_presentation_rejects_rehashed_missing_or_misleading_content(extended_folder,fault):
    import hashlib
    import re
    validator()  # Load the independent script with its sibling modules available.
    from smoke_backtracking_tour import validate_backtracking_tour_presentation
    path = extended_folder/('backtracking.html' if fault in ('link','guide') else 'index.html')
    manifest_path = extended_folder/'manifest.json'
    before, manifest_before = path.read_bytes(), manifest_path.read_bytes()
    try:
        text = before.decode()
        if fault=='preview':
            text = re.sub(r'(<a class="tour-card" href="backtracking.html">.*?<img[^>]*src=")[^"]+',r'\1data:image/svg+xml;base64,PHN2Zy8+',text,count=1,flags=re.S)
        elif fault=='flow':
            text = text.replace('L=L_{k−1}', 'L=L₀',1)
        elif fault=='meaning':
            text = text.replace('36R²/(k+1)², α=η=2, all L₀≤9','18R²/(k+1)², α=1',1)
        elif fault=='caption':
            text = text.replace('163.84&gt;0','0≤0',1)
        elif fault=='link':
            text = text.replace('data-tour-backtracking>','data-other-link>',1)
        else:
            text = text.replace('data-tour-backtracking-guide>','data-other-guide>',1)
        assert text!=before.decode()
        raw = text.encode()
        path.write_bytes(raw)
        manifest = json.loads(manifest_before)
        artifact = next(a for a in manifest['artifacts'] if a['path']==path.name)
        artifact.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        manifest_path.write_text(json.dumps(manifest))
        with pytest.raises(RuntimeError,match='Backtracking tour:'):
            validate_backtracking_tour_presentation(extended_folder)
    finally:
        path.write_bytes(before)
        manifest_path.write_bytes(manifest_before)
