"""Exercise reading delivery byte integrity; these fixtures are not scientific evidence."""
import copy
import hashlib
import json
import stat
import zipfile

import pytest

from scripts import reading_release as reading


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf8')


def rebind_zip(assets, version):
    zip_name, _, proof_name = reading.asset_names(version)
    proof = json.loads((assets/proof_name).read_bytes())
    data = (assets/zip_name).read_bytes()
    proof['assets'][zip_name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    dump(assets/proof_name, proof)


def rewrite_zip(assets, version, mutate):
    path = assets/reading.asset_names(version)[0]
    with zipfile.ZipFile(path) as archive:
        contents = [(info, archive.read(info)) for info in archive.infolist()]
    mutate(contents)
    with zipfile.ZipFile(path, 'w') as archive:
        for info, data in contents:
            archive.writestr(info, data)
    rebind_zip(assets, version)


def test_round_trip_keeps_every_original_byte(reading_factory):
    module, tour, review, assets, version, sha = reading_factory()
    output = assets.parent/'extracted'
    result = module.extract_verified(assets, output, version, sha)
    assert result['source_commit'] == sha
    assert len(list(output.glob('*.html'))) == 25
    for original in tour.iterdir():
        assert (output/original.name).read_bytes() == original.read_bytes()
    for original in review.iterdir():
        assert (output/'review'/original.name).read_bytes() == original.read_bytes()
    assert (assets/module.asset_names(version)[1]).read_bytes() == (review/module.PDF_NAME).read_bytes()
    index = json.loads((output/module.BUNDLE_MANIFEST).read_bytes())
    for name, info in index['files'].items():
        raw = (output/name).read_bytes()
        assert info == {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    assert sha in (output/'README.txt').read_text(encoding='utf8')


def test_identical_audited_inputs_produce_identical_archive(reading_factory):
    module, tour, review, assets, version, sha = reading_factory()
    second = assets.parent/'second'
    module.prepare(tour, review, second, version, sha)
    for name in module.asset_names(version):
        assert (assets/name).read_bytes() == (second/name).read_bytes()


@pytest.mark.parametrize('change', ['content', 'missing', 'extra', 'duplicate', 'traversal', 'absolute', 'symlink'])
def test_rehashed_archive_still_rejects_wrong_members(reading_factory, change):
    module, _, _, assets, version, sha = reading_factory()

    def mutate(items):
        pos = next(i for i, (info, _) in enumerate(items) if info.filename == 'index.html')
        info, data = items[pos]
        if change == 'content':
            items[pos] = (info, data+b'changed')
        elif change == 'missing':
            items.pop(pos)
        elif change == 'duplicate':
            items.append((copy.copy(info), data))
        else:
            info = copy.copy(info)
            if change == 'extra':
                info.filename = 'extra.html'
                items.append((info, data))
            elif change == 'traversal':
                info.filename = '../outside.html'
                items[pos] = (info, data)
            elif change == 'absolute':
                info.filename = '/outside.html'
                items[pos] = (info, data)
            else:
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                items[pos] = (info, data)

    if change == 'duplicate':
        with pytest.warns(UserWarning, match='Duplicate name'):
            rewrite_zip(assets, version, mutate)
    else:
        rewrite_zip(assets, version, mutate)
    with pytest.raises(RuntimeError):
        module.verify_assets(assets, version, sha)
    output = assets.parent/'rejected-extraction'
    with pytest.raises(RuntimeError):
        module.extract_verified(assets, output, version, sha)
    assert not output.exists()


@pytest.mark.parametrize('field,value', [
    ('source_commit', 'b'*40), ('manifest_sha256', '0'*64), ('renderer_sha256', '1'*64),
    ('html_pages', 24), ('numerical_records', True), ('pdf_pages', 1),
    ('geometry', []), ('pdf_fonts', [[], []]), ('run_url', 'https://example.com/1'),
])
def test_source_audit_must_match(reading_factory, field, value):
    module, tour, review, assets, version, sha = reading_factory()
    path = review/'evidence.json'
    proof = json.loads(path.read_bytes())
    proof[field] = value
    dump(path, proof)
    output = assets.parent/'rejected'
    with pytest.raises(RuntimeError):
        module.prepare(tour, review, output, version, sha)
    assert not output.exists()


@pytest.mark.parametrize('target', ['tour', 'pdf', 'source', 'environment', 'extra'])
def test_changed_audited_inputs_are_rejected(reading_factory, target):
    module, tour, review, assets, version, sha = reading_factory()
    path = {'tour': tour/'index.html', 'pdf': review/module.PDF_NAME,
            'source': review/'source-commit.txt', 'environment': review/'environment.txt',
            'extra': tour/'unlisted.txt'}[target]
    path.write_bytes(b'' if target == 'environment' else b'changed input')
    with pytest.raises(RuntimeError):
        module.prepare(tour, review, assets.parent/'rejected', version, sha)


@pytest.mark.parametrize('change', ['version', 'source', 'asset', 'manifest', 'pdf-copy', 'extra-field-hash'])
def test_asset_evidence_cannot_hide_mismatch(reading_factory, change):
    module, _, _, assets, version, sha = reading_factory()
    _, pdf_name, proof_name = module.asset_names(version)
    path = assets/proof_name
    proof = json.loads(path.read_bytes())
    if change == 'version':
        proof['version'] = '9.9.9'
    elif change == 'source':
        proof['source_commit'] = 'b'*40
    elif change == 'asset':
        proof['assets'][pdf_name]['sha256'] = '0'*64
    elif change == 'manifest':
        proof['bundle_manifest_sha256'] = '0'*64
    elif change == 'extra-field-hash':
        proof['assets'][pdf_name]['unverified'] = True
    else:
        data = b'%PDF-1.4\ndifferent standalone copy'
        (assets/pdf_name).write_bytes(data)
        proof['assets'][pdf_name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    dump(path, proof)
    with pytest.raises(RuntimeError):
        module.verify_assets(assets, version, sha)


def test_existing_outputs_are_preserved(reading_factory):
    module, tour, review, assets, version, sha = reading_factory()
    before = {p.name: p.read_bytes() for p in assets.iterdir()}
    with pytest.raises(RuntimeError, match='new directory'):
        module.prepare(tour, review, assets, version, sha)
    with pytest.raises(RuntimeError, match='new directory'):
        module.extract_verified(assets, tour, version, sha)
    assert {p.name: p.read_bytes() for p in assets.iterdir()} == before


def test_metadata_rejects_duplicates_and_nonfinite_values():
    for data in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'[]'):
        with pytest.raises(RuntimeError):
            reading.read_json(data)


def test_archive_size_limit_precedes_extraction(reading_factory, monkeypatch):
    module, _, _, assets, version, sha = reading_factory()
    monkeypatch.setattr(module, 'MAX_ZIP', 1)
    with pytest.raises(RuntimeError, match='Oversized reading ZIP'):
        module.verify_assets(assets, version, sha)


def test_expanded_size_limit_precedes_member_reads(reading_factory, monkeypatch):
    module, _, _, assets, version, sha = reading_factory()
    zip_name, _, _ = module.asset_names(version)
    # Keep individual asset sizes valid while lowering the aggregate expansion cap.
    with zipfile.ZipFile(assets/zip_name) as archive:
        total = sum(info.file_size for info in archive.infolist())
    monkeypatch.setattr(module, 'MAX_EXPANDED', total-1)
    with pytest.raises(RuntimeError, match='Oversized expanded'):
        module.verify_assets(assets, version, sha)
