"""Package and verify the complete offline tour; all generation runs in CI.

The ZIP binds exact audited bytes to a source revision. It is not an independent
reproduction, signature or substitute for the release workflow's full test gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_ZIP = 128_000_000
MAX_EXPANDED = 512_000_000
MAX_METADATA = 2_000_000
TOPICS = ('gd-baseline', 'nesterov-1983', 'polyak-1964', 'hestenes-stiefel-1952',
          'rockafellar-1976', 'beck-teboulle-2009', 'jaggi-2013', 'ista-vs-fista')
EXTENSIONS = ['fista-wavelet', 'fw-sparsity', 'kaczmarz-expectation', 'kaczmarz-sampling',
              'cg-spectrum', 'reddi-2018', 'admm-lasso', 'fista-backtracking']
HTML_NAMES = frozenset(
    ['index.html', 'atlas.html', 'shewchuk.html', 'deblur.html', 'heavy-ball.html',
     'simplex.html', 'proximal.html', 'landscape.html', 'tight-gd.html', 'wavelet.html',
     'fw-sparsity.html', 'kaczmarz.html', 'sampling.html', 'cg-spectrum.html',
     'adam.html', 'admm.html', 'backtracking.html']
    + [f'stress-{topic}.html' for topic in TOPICS]
)
PDF_NAME = 'ChainBench_FISTA_review.pdf'
REVIEW_OUTPUTS = frozenset([PDF_NAME, 'review.html', 'page-1.png', 'page-2.png'])
REVIEW_NAMES = REVIEW_OUTPUTS | {'evidence.json', 'source-commit.txt', 'environment.txt'}
MEMBERS = HTML_NAMES | {'manifest.json', 'README.txt'} | {f'review/{p}' for p in REVIEW_NAMES}
BUNDLE_MANIFEST = 'bundle-manifest.json'


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def read_json(raw):
    require(len(raw) <= MAX_METADATA, 'Oversized reading metadata')

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate reading metadata key')
            result[key] = value
        return result

    def number(value):
        parsed = float(value)
        require(math.isfinite(parsed), 'Nonfinite reading metadata')
        return parsed

    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_float=number,
                           parse_constant=lambda _: require(False, 'Nonfinite reading metadata'))
    except (ValueError, UnicodeError) as exc:
        raise RuntimeError('Invalid reading metadata JSON') from exc
    require(isinstance(value, dict), 'Expected reading metadata object')
    return value


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)+'\n').encode('utf8')


def asset_names(version):
    require(isinstance(version, str) and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version),
            'Invalid reading release version')
    return (f'chainbench-{version}-reading.zip', f'chainbench-{version}-review.pdf',
            'reading-verification.json')


def fingerprint(path):
    require(not path.is_symlink() and path.is_file(), 'Reading source must be a regular file')
    size = path.stat().st_size
    require(0 < size <= MAX_EXPANDED, 'Invalid reading file size')
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            result.update(block)
    return {'bytes': size, 'sha256': result.hexdigest()}


def valid_fingerprint(value):
    return (isinstance(value, dict) and set(value) == {'bytes', 'sha256'}
            and type(value['bytes']) is int and 0 < value['bytes'] <= MAX_EXPANDED
            and isinstance(value['sha256'], str) and re.fullmatch('[0-9a-f]{64}', value['sha256']))


def validate_records(read, files, version, sha):
    """Bind existing tour/PDF audit records to the bytes actually being shipped."""
    require(isinstance(sha, str) and re.fullmatch('[0-9a-f]{40}', sha), 'Invalid source revision')
    tour = read_json(read('manifest.json'))
    require(tour.get('kind') == 'chainbench.offline-tour' and type(tour.get('schema_version')) is int
            and tour['schema_version'] == 1 and tour.get('start') == 'index.html'
            and tour.get('language') == 'ko' and tour.get('extensions') == EXTENSIONS,
            'Expected complete Korean/English extended tour')
    require(isinstance(tour.get('environment'), dict) and tour['environment'].get('chainbench') == version,
            'Tour version differs from release')
    artifacts = tour.get('artifacts')
    require(isinstance(artifacts, list) and len(artifacts) == len(HTML_NAMES)
            and all(isinstance(a, dict) and isinstance(a.get('path'), str) for a in artifacts)
            and {a['path'] for a in artifacts} == HTML_NAMES, 'Incomplete tour file inventory')
    for item in artifacts:
        require({'bytes': item.get('bytes'), 'sha256': item.get('sha256')} == files[item['path']]
                and type(item.get('bytes')) is int, 'Tour file differs from audited manifest')
    proof = read_json(read('review/evidence.json'))
    require(proof.get('source_commit') == sha
            and proof.get('manifest_sha256') == files['manifest.json']['sha256']
            and proof.get('renderer_sha256') == fingerprint(ROOT/'scripts/render_review_packet.py')['sha256']
            and isinstance(proof.get('run_url'), str)
            and re.fullmatch(r'https://github\.com/chocoemong17/chainbench/actions/runs/[0-9]+', proof['run_url']),
            'PDF audit source, renderer or tour binding differs')
    for field, expected in [('html_pages', 25), ('numerical_records', 24), ('pdf_pages', 2)]:
        require(type(proof.get(field)) is int and proof[field] == expected, 'Incomplete reading/PDF audit')
    outputs = proof.get('files')
    require(isinstance(outputs, dict) and set(outputs) == REVIEW_OUTPUTS, 'Incomplete PDF output inventory')
    for name, value in outputs.items():
        require(valid_fingerprint(value) and value == files['review/'+name], 'PDF output differs from its audit')
    geometry = proof.get('geometry')
    require(isinstance(geometry, list) and len(geometry) == 2, 'Missing PDF layout audit')
    for page in geometry:
        require(isinstance(page, dict) and set(page) == {'bottom', 'footer', 'left', 'right', 'width'}
                and all(type(v) in (int, float) and math.isfinite(v) for v in page.values()), 'Invalid PDF geometry')
        require(page['bottom']+7 < page['footer'] and page['left'] >= 0
                and page['width'] > 0 and page['right'] <= page['width']+1, 'PDF content overflows')
    fonts = proof.get('pdf_fonts')
    require(isinstance(fonts, list) and len(fonts) == 2, 'Missing PDF font audit')
    for page_fonts in fonts:
        require(isinstance(page_fonts, list) and page_fonts
                and all(isinstance(f, dict) and type(f.get('embedded_bytes')) is int
                        and f['embedded_bytes'] > 0 for f in page_fonts), 'Missing embedded PDF font evidence')
    require(read('review/source-commit.txt').strip() == sha.encode('ascii'), 'Source file differs from audit')
    require(read('review/environment.txt').strip(), 'Missing reading environment')
    require(read('review/'+PDF_NAME).startswith(b'%PDF-'), 'Invalid reviewed PDF header')
    return proof


def verify_assets(directory, version, sha):
    """Read-only verification, also used before release network writes."""
    zip_name, pdf_name, proof_name = asset_names(version)
    require(directory.is_dir() and not directory.is_symlink(), 'Invalid reading asset directory')
    proof_path = directory/proof_name
    require(proof_path.is_file() and not proof_path.is_symlink()
            and proof_path.stat().st_size <= MAX_METADATA, 'Invalid reading verification file')
    proof = read_json(proof_path.read_bytes())
    require(proof.get('kind') == 'chainbench.reading-assets' and type(proof.get('schema_version')) is int
            and proof['schema_version'] == 1 and proof.get('version') == version
            and proof.get('source_commit') == sha, 'Reading assets belong to another source/version')
    assets = proof.get('assets')
    require(isinstance(assets, dict) and set(assets) == {zip_name, pdf_name}, 'Incomplete reading asset inventory')
    for name, expected in assets.items():
        require(valid_fingerprint(expected) and fingerprint(directory/name) == expected,
                'Reading release asset changed after verification')
    require(assets[zip_name]['bytes'] <= MAX_ZIP, 'Oversized reading ZIP')
    with zipfile.ZipFile(directory/zip_name) as archive:
        entries = archive.infolist()
        require(len(entries) == len(MEMBERS)+1 and {i.filename for i in entries} == MEMBERS | {BUNDLE_MANIFEST},
                'Unexpected, duplicate or missing ZIP member')
        require(sum(i.file_size for i in entries) <= MAX_EXPANDED, 'Oversized expanded reading bundle')
        for entry in entries:
            require(not entry.is_dir() and not (entry.flag_bits & 1)
                    and stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFREG
                    and entry.compress_type == zipfile.ZIP_DEFLATED and entry.file_size > 0,
                    'Invalid reading ZIP member type')

        def read(name):
            require(archive.getinfo(name).file_size <= MAX_METADATA, 'Oversized reading metadata member')
            return archive.read(name)

        manifest = read_json(read(BUNDLE_MANIFEST))
        require(manifest.get('kind') == 'chainbench.reading-bundle'
                and type(manifest.get('schema_version')) is int and manifest['schema_version'] == 1
                and manifest.get('version') == version and manifest.get('source_commit') == sha,
                'ZIP source/version differs')
        files = manifest.get('files')
        require(isinstance(files, dict) and set(files) == MEMBERS
                and all(valid_fingerprint(v) for v in files.values()), 'Invalid ZIP content manifest')
        for name, expected in files.items():
            require(archive.getinfo(name).file_size == expected['bytes'], 'ZIP member size differs')
            digest = hashlib.sha256()
            with archive.open(name) as stream:
                for block in iter(lambda: stream.read(1024*1024), b''):
                    digest.update(block)
            require(digest.hexdigest() == expected['sha256'], 'ZIP member bytes differ')
        validate_records(read, files, version, sha)
        require(files['review/'+PDF_NAME] == assets[pdf_name], 'Standalone PDF differs from ZIP PDF')
        require(proof.get('bundle_manifest_sha256') == hashlib.sha256(read(BUNDLE_MANIFEST)).hexdigest(),
                'ZIP manifest differs from asset verification')
    return proof


def prepare(tour, review, output, version, sha):
    """Preserve the complete renderer-audited tour and its PDF, without recomputing it."""
    zip_name, pdf_name, proof_name = asset_names(version)
    require(not output.exists() and not output.is_symlink() and output.parent.is_dir(),
            'Reading output must be a new directory')
    require(tour.is_dir() and not tour.is_symlink()
            and {p.name for p in tour.iterdir()} == HTML_NAMES | {'manifest.json'}, 'Unexpected tour input files')
    require(review.is_dir() and not review.is_symlink()
            and {p.name for p in review.iterdir()} == REVIEW_NAMES, 'Unexpected review input files')
    sources = {name: tour/name for name in HTML_NAMES | {'manifest.json'}}
    sources.update({f'review/{name}': review/name for name in REVIEW_NAMES})
    with tempfile.TemporaryDirectory(prefix='.reading-release-', dir=output.parent) as temp:
        stage = Path(temp)/'assets'
        stage.mkdir()
        guide = Path(temp)/'README.txt'
        guide.write_text(
            f'ChainBench {version} / source {sha}\n\n'
            '폴더 전체를 압축 해제한 뒤 index.html을 브라우저로 여세요.\n'
            'Python 설치나 서버 연결 없이 25개 설명 페이지를 읽을 수 있습니다.\n'
            '한국어/영어 전환과 원본 수치 기록은 각 페이지에 있습니다.\n'
            '먼저 review/ChainBench_FISTA_review.pdf에서 2쪽 안내를 읽어도 좋습니다.\n\n'
            'Extract the whole folder, then open index.html in a browser.\n'
            'No Python installation or network connection is needed to read the 25 pages.\n'
            'Keep every file together so the local links continue to work.\n'
            'The PDF is a two-page reading guide, not a substitute for the complete reports.\n\n'
            'Published protocols, changed inputs, illustrations, finite samples and sharp\n'
            'constructions are labelled separately. Recorded examples are not proofs,\n'
            'universal rankings or independent outside review. Source links are optional.\n'
            'manifest.json binds the original tour files; bundle-manifest.json binds\n'
            'all retained files except itself. review/evidence.json retains the PDF audit.\n'
            'Hashes bind bytes; they do not authenticate independent scientific results.\n',
            encoding='utf8',
        )
        sources['README.txt'] = guide
        files = {name: fingerprint(path) for name, path in sorted(sources.items())}
        require(sum(f['bytes'] for f in files.values()) < MAX_EXPANDED-MAX_METADATA,
                'Oversized reading inputs')

        def read(name):
            require(files[name]['bytes'] <= MAX_METADATA, 'Oversized reading metadata input')
            return sources[name].read_bytes()

        validate_records(read, files, version, sha)
        manifest = encoded({'kind': 'chainbench.reading-bundle', 'schema_version': 1,
                            'version': version, 'source_commit': sha, 'files': files})
        with zipfile.ZipFile(stage/zip_name, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(MEMBERS | {BUNDLE_MANIFEST}):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                if name == BUNDLE_MANIFEST:
                    archive.writestr(info, manifest)
                else:
                    with sources[name].open('rb') as src, archive.open(info, 'w') as dst:
                        shutil.copyfileobj(src, dst, length=1024*1024)
        shutil.copyfile(review/PDF_NAME, stage/pdf_name)
        proof = {'kind': 'chainbench.reading-assets', 'schema_version': 1,
                 'version': version, 'source_commit': sha,
                 'bundle_manifest_sha256': hashlib.sha256(manifest).hexdigest(),
                 'assets': {name: fingerprint(stage/name) for name in (zip_name, pdf_name)}}
        (stage/proof_name).write_bytes(encoded(proof))
        verify_assets(stage, version, sha)
        stage.rename(output)
    return proof


def extract_verified(directory, output, version, sha):
    """Extract only the verified, fixed member inventory into a fresh directory."""
    proof = verify_assets(directory, version, sha)
    require(not output.exists() and not output.is_symlink() and output.parent.is_dir(),
            'Extraction output must be a new directory')
    with tempfile.TemporaryDirectory(prefix='.reading-extract-', dir=output.parent) as temp:
        stage = Path(temp)/'contents'
        stage.mkdir()
        (stage/'review').mkdir()
        with zipfile.ZipFile(directory/asset_names(version)[0]) as archive:
            for name in sorted(MEMBERS | {BUNDLE_MANIFEST}):
                with archive.open(name) as src, (stage/name).open('xb') as dst:
                    shutil.copyfileobj(src, dst, length=1024*1024)
        stage.rename(output)
    return proof


def attach(directory, dist, version, sha):
    """Add reading assets after clean-install verification; preserve distributions."""
    proof = verify_assets(directory, version, sha)
    names = asset_names(version)
    require({p.name for p in directory.iterdir()} == set(names), 'Unexpected reading asset files')
    expected = {f'chainbench-{version}-py3-none-any.whl', f'chainbench-{version}.tar.gz',
                'verification.json', 'SHA256SUMS', 'build-environment.txt'}
    require(dist.is_dir() and not dist.is_symlink() and {p.name for p in dist.iterdir()} == expected,
            'Expected clean-install artifacts before attaching reading files')
    for path in dist.iterdir():
        fingerprint(path)
    install = read_json((dist/'verification.json').read_bytes())
    require(install.get('source_commit') == sha, 'Installation and reading sources differ')
    for name in names:
        with (directory/name).open('rb') as src, (dist/name).open('xb') as dst:
            shutil.copyfileobj(src, dst, length=1024*1024)
    verify_assets(dist, version, sha)
    sums = ''.join(f"{fingerprint(p)['sha256']}  {p.name}\n"
                   for p in sorted(dist.iterdir()) if p.name != 'SHA256SUMS')
    (dist/'SHA256SUMS').write_text(sums, encoding='utf8')
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'verify', 'extract', 'attach'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--source', required=True)
        cmd.add_argument('--version')
        if name == 'prepare':
            cmd.add_argument('--tour', type=Path, required=True)
            cmd.add_argument('--review', type=Path, required=True)
        else:
            cmd.add_argument('--directory', type=Path, required=True)
        if name in ('prepare', 'extract'):
            cmd.add_argument('--output', type=Path, required=True)
        if name == 'attach':
            cmd.add_argument('--dist', type=Path, required=True)
    args = parser.parse_args()
    version = args.version or read_json((ROOT/'release-manifest.json').read_bytes())['version']
    if args.command == 'prepare':
        result = prepare(args.tour, args.review, args.output, version, args.source)
    elif args.command == 'extract':
        result = extract_verified(args.directory, args.output, version, args.source)
    elif args.command == 'attach':
        result = attach(args.directory, args.dist, version, args.source)
    else:
        result = verify_assets(args.directory, version, args.source)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
