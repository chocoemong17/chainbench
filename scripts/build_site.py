"""Build an English-first website from this run's audited bilingual tour.

Run on GitHub Actions; no published release asset is modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

from chainbench.landscape import run_landscape

ROOT = Path(__file__).resolve().parents[1]


def build(tour: Path, output: Path, source: str):
    if not re.fullmatch('[0-9a-f]{40}', source):
        raise ValueError('A complete source commit is required')
    if output.exists():
        raise ValueError('Use a new website output directory')
    manifest = json.loads((tour / 'manifest.json').read_text(encoding='utf8'))
    artifacts = manifest['artifacts']
    if len(artifacts) != 25 or manifest['language'] not in ('en', 'ko'):
        raise ValueError('Expected the complete audited bilingual tour')
    # Verify the source bytes before any intentional presentation transformation.
    for item in artifacts:
        path = tour / item['path']
        if path.parent != tour or path.is_symlink():
            raise ValueError('Unsafe tour path')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Tour digest mismatch: ' + item['path'])
    shutil.copytree(ROOT / 'web', output)
    reports = output / 'reports'
    reports.mkdir()
    for item in artifacts:
        text = (tour / item['path']).read_text(encoding='utf8')
        text = text.replace('<html lang="ko">', '<html lang="en">', 1)
        text = text.replace('<main>', '<main><nav aria-label="Website"><a href="../">'
                            '<span lang="en">← Explore ChainBench</span>'
                            '<span lang="ko">← ChainBench 둘러보기</span></a></nav>', 1)
        (reports / item['path']).write_text(text, encoding='utf8')
    for name in ('deblur-preview.svg', 'tour-proximal.svg', 'tour-simplex.svg'):
        shutil.copyfile(ROOT / 'docs' / 'images' / name, output / name)
    cases = [run_landscape(condition, angle, 60, ('gd', 'smooth-fista'))
             for condition, angle in ((3., 0.), (20., 32.), (80., -35.))]
    (output / 'explorer-data.json').write_text(json.dumps({
        'kind': 'chainbench.browser-reference', 'source': source, 'cases': cases,
    }, ensure_ascii=False, allow_nan=False, separators=(',', ':')), encoding='utf8')
    (output / '.nojekyll').touch()
    inventory = {}
    for path in sorted(output.rglob('*')):
        if path.is_file():
            data = path.read_bytes()
            inventory[path.relative_to(output).as_posix()] = {
                'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    (output / 'site-manifest.json').write_text(json.dumps({
        'kind': 'chainbench.website', 'source': source, 'default_language': 'en',
        'languages': ['en', 'ko'], 'source_tour': manifest,
        'transformations': ['English initial language', 'website return navigation'],
        'files': inventory,
    }, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    print(json.dumps({'website_files': len(inventory), 'reports': len(artifacts),
                      'bytes': sum(item['bytes'] for item in inventory.values()),
                      'source': source, 'default_language': 'en'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tour', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--source', required=True)
    args = parser.parse_args()
    build(args.tour, args.output, args.source)
