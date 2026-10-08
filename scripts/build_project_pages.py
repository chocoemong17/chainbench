"""Publish a small, bilingual project route from existing aggregate evidence."""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://chocoemong17.github.io/chainbench/'
SUMMARY_ROWS = (
    (2, (3, 4), 'Understood most or almost all', '대부분 또는 거의 다 이해했다고 느낌'),
    (5, (3, 4), 'Found the motion easy to follow', '영상의 움직임을 따라가기 쉬웠음'),
    (4, (3, 4), 'Found the content interesting', '내용이 재미있었음'),
    (9, (3, 4), 'Wanted another topic', '다른 주제도 배우고 싶었음'),
)


def build_project_pages(output: Path, source: str):
    if not re.fullmatch('[0-9a-f]{40}', source):
        raise ValueError('A complete source commit is required')
    aggregate = ROOT / 'docs/data/classroom-survey-150.json'
    data = json.loads(aggregate.read_text(encoding='utf8'))
    n = data['respondent_records']
    questions = {q['number']: q for q in data['questions']}
    rows = []
    for number, selected, en, ko in SUMMARY_ROWS:
        q = questions[number]
        if q['denominator'] != n or sum(q['counts']) != n:
            raise ValueError('Invalid survey denominator')
        count = sum(q['counts'][i] for i in selected)
        rows.append(f'<tr data-question="{number}"><th scope="row">'
                    f'<span lang="en">{html.escape(en)}</span>'
                    f'<span lang="ko">{html.escape(ko)}</span></th>'
                    f'<td data-count="{count}">{count} / {n}</td>'
                    f'<td>{100 * count / n:.1f}%</td></tr>')
    path = output / 'about/index.html'
    page = path.read_text(encoding='utf8')
    page = page.replace('<!-- CLASSROOM_ROWS -->', '\n'.join(rows))
    page = page.replace('<!-- SOURCE -->', source).replace('<!-- SOURCE_SHORT -->', source[:12])
    path.write_text(page, encoding='utf8')
    shutil.copyfile(aggregate, output / 'about/classroom-survey-150.json')
    # Share links refer to the existing locally served poster; no tracking or CDN.
    routes = ['index.html', 'about/index.html', 'papers/index.html']
    routes += [f'papers/{slug}/index.html' for slug in
               ('adam', 'attention', 'resnet', 'backprop', 'cnn', 'dropout')]
    urls = []
    for route in routes:
        path = output / route
        page = path.read_text(encoding='utf8')
        title = re.search(r'<title>(.*?)</title>', page).group(1)
        description = re.search(r'<meta name="description" content="([^"]+)"', page).group(1)
        url = BASE + route.removesuffix('index.html')
        slug = route.split('/')[1] if route.count('/') == 2 else 'backprop'
        poster = BASE + f'papers/{slug}/poster.jpg'
        metadata = (f'<link rel="canonical" href="{url}">'
                    '<meta property="og:type" content="website">'
                    f'<meta property="og:title" content="{html.escape(html.unescape(title), quote=True)}">'
                    f'<meta property="og:description" content="{description}">'
                    f'<meta property="og:url" content="{url}">'
                    f'<meta property="og:image" content="{poster}">'
                    '<meta name="twitter:card" content="summary_large_image">')
        page = page.replace('</head>', metadata + '</head>', 1)
        path.write_text(page, encoding='utf8')
        urls.append(url)
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += '\n'.join(f'<url><loc>{html.escape(url)}</loc></url>' for url in urls)
    (output / 'sitemap.xml').write_text(sitemap + '\n</urlset>\n', encoding='utf8')
