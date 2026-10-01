"""Small byte fixtures for transport tests; real numerical/PDF audits run in CI."""
import hashlib
import itertools
import json

import pytest


@pytest.fixture
def reading_factory(tmp_path):
    from scripts import reading_release as reading

    numbers = itertools.count()

    def make(version='0.6.0', sha='a'*40):
        root = tmp_path/f'reading-{next(numbers)}'
        root.mkdir()
        tour, review, assets = root/'tour', root/'review', root/'assets'
        tour.mkdir()
        review.mkdir()
        for name in reading.HTML_NAMES:
            (tour/name).write_text(f'<html lang="ko"><title>{name}</title>검토용 바이트 예제</html>', encoding='utf8')

        def record(path):
            data = path.read_bytes()
            return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

        manifest = {'kind': 'chainbench.offline-tour', 'schema_version': 1,
                    'start': 'index.html', 'language': 'ko', 'extensions': reading.EXTENSIONS,
                    'environment': {'chainbench': version},
                    'artifacts': [dict(path=name, **record(tour/name)) for name in sorted(reading.HTML_NAMES)]}
        (tour/'manifest.json').write_text(json.dumps(manifest), encoding='utf8')
        (review/reading.PDF_NAME).write_bytes(b'%PDF-1.4\ntransport fixture, not a rendered PDF\n%%EOF\n')
        (review/'review.html').write_text('<html>PDF transport fixture</html>', encoding='utf8')
        for index in (1, 2):
            (review/f'page-{index}.png').write_bytes(b'PNG transport fixture '+str(index).encode())
        proof = {'source_commit': sha, 'run_url': 'https://github.com/chocoemong17/chainbench/actions/runs/1',
                 'manifest_sha256': record(tour/'manifest.json')['sha256'],
                 'renderer_sha256': record(reading.ROOT/'scripts/render_review_packet.py')['sha256'],
                 'html_pages': 25, 'numerical_records': 24, 'pdf_pages': 2,
                 'geometry': [dict(bottom=80, footer=100, left=0, right=120, width=120)]*2,
                 'pdf_fonts': [[{'type': 'Type3', 'embedded_bytes': 12, 'glyph_programs': 1}]]*2,
                 'files': {name: record(review/name) for name in sorted(reading.REVIEW_OUTPUTS)}}
        (review/'evidence.json').write_text(json.dumps(proof), encoding='utf8')
        (review/'source-commit.txt').write_text(sha+'\n', encoding='ascii')
        (review/'environment.txt').write_text('transport-test-fixture\n', encoding='utf8')
        reading.prepare(tour, review, assets, version, sha)
        return reading, tour, review, assets, version, sha

    return make
