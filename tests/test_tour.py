import importlib.util
import json
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
    return module.validate_tour


@pytest.fixture(scope='module')
def tour_folder(tmp_path_factory):
    folder = tmp_path_factory.mktemp('offline-tour')/'tour'
    build_tour(folder, 'ko')
    return folder


def test_generated_tour_hashes_links_coverage_and_independent_numerics(tour_folder):
    records = validator()(tour_folder)
    assert len(records) == 14
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
