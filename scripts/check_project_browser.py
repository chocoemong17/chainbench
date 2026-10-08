"""Check the project route against aggregate evidence and real browser behavior."""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import threading
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import expect, sync_playwright


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = set()
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])


def check(args):
    args.output.mkdir(parents=True, exist_ok=True)
    site = args.site.resolve()
    data = json.loads((site / 'about/classroom-survey-150.json').read_text(encoding='utf8'))
    original = Path(__file__).resolve().parents[1] / 'docs/data/classroom-survey-150.json'
    assert (site / 'about/classroom-survey-150.json').read_bytes() == original.read_bytes()
    page_source = (site / 'about/index.html').read_text(encoding='utf8')
    assert '<!-- CLASSROOM_ROWS -->' not in page_source and '<!-- SOURCE' not in page_source
    inspected_links = []
    for name in ('about/index.html', 'papers/index.html'):
        doc = Document((site / name).read_text(encoding='utf8'))
        for href in doc.links:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                continue
            path = (site / name).parent / unquote(url.path) if url.path else site / name
            if path.is_dir():
                path /= 'index.html'
            assert path.resolve().is_relative_to(site) and path.is_file(), (name, href)
            if url.fragment:
                assert url.fragment in Document(path.read_text(encoding='utf8')).ids, (name, href)
            inspected_links.append([name, href])
    urls = ET.parse(site / 'sitemap.xml').findall('{*}url/{*}loc')
    assert len(urls) == 9 and len({u.text for u in urls}) == 9
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
        functools.partial(QuietHandler, directory=str(site)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
    proof = {'views': [], 'errors': [], 'external_requests': [], 'internal_links': inspected_links}
    questions = {q['number']: q for q in data['questions']}
    try:
        with sync_playwright() as pw:
            for engine in ('chromium', 'webkit'):
                browser = getattr(pw, engine).launch()
                for width in (1440, 390, 320):
                    context = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')
                    page = context.new_page()
                    page.on('pageerror', lambda e: proof['errors'].append(str(e)))
                    page.on('request', lambda r: proof['external_requests'].append(r.url)
                            if not r.url.startswith(origin + '/') else None)
                    assert page.goto(origin + '/about/', wait_until='networkidle').status == 200
                    expect(page.locator('html')).to_have_attribute('lang', 'en')
                    page.keyboard.press('Tab')
                    expect(page.locator('.skip')).to_be_focused()
                    page.keyboard.press('Enter')
                    expect(page.locator('#main')).to_be_focused()
                    for lang in ('en', 'ko'):
                        if lang == 'ko':
                            page.locator('#language').focus()
                            page.keyboard.press('Enter')
                        expect(page.locator('html')).to_have_attribute('lang', lang)
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                        for n in (2, 5, 4, 9):
                            q = questions[n]
                            count = q['counts'][3] + q['counts'][4]
                            row = page.locator(f'tr[data-question="{n}"]')
                            expect(row.locator('td').nth(0)).to_have_text(f'{count} / {data["respondent_records"]}')
                            expect(row.locator('td').nth(1)).to_have_text(f'{100 * count / data["respondent_records"]:.1f}%')
                        expect(page.locator('h1')).to_contain_text('See the idea.' if lang == 'en' else '아이디어를 보고')
                        page.locator('summary').click()
                        expect(page.locator('details')).to_have_attribute('open', '')
                        page.locator('summary').click()
                        page.screenshot(path=str(args.output / f'about-{engine}-{lang}-{width}.png'), full_page=True)
                        proof['views'].append({'engine': engine, 'width': width, 'language': lang})
                    # An explicit language link overrides the saved preference.
                    page.goto(origin + '/about/?lang=en', wait_until='networkidle')
                    expect(page.locator('html')).to_have_attribute('lang', 'en')
                    assert page.locator('link[rel=canonical]').get_attribute('href') == 'https://chocoemong17.github.io/chainbench/about/'
                    page.goto(origin + '/papers/', wait_until='networkidle')
                    page.locator('a[href="../about/"]').click()
                    expect(page.locator('html')).to_have_attribute('lang', 'ko')
                    context.close()
                context = browser.new_context(java_script_enabled=False)
                page = context.new_page()
                page.goto(origin + '/about/')
                expect(page.locator('h1')).to_contain_text('See the idea.')
                expect(page.locator('tr[data-question="2"]')).to_contain_text('139 / 150')
                page.locator('summary').click()
                expect(page.locator('details')).to_have_attribute('open', '')
                context.close()
                browser.close()
        assert not proof['errors'] and not proof['external_requests'], proof
        proof['passed'] = True
        (args.output / 'proof.json').write_text(json.dumps(proof, indent=2), encoding='utf8')
        print(json.dumps(proof))
    finally:
        server.shutdown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    check(parser.parse_args())
