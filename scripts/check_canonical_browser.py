"""Check fixed-suite context, full inputs and standalone captioned SVG offline."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--learning', type=Path, required=True)
    parser.add_argument('--svg', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    evidence = {'viewports': [], 'network_requests': [], 'javascript_errors': []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        evidence['browser'] = browser.version
        for width in (1440, 390):
            context = browser.new_context(viewport={'width': width, 'height': 1000}, offline=True)
            page = context.new_page()
            page.on('pageerror', lambda e: evidence['javascript_errors'].append(str(e)))
            page.on('request', lambda r: evidence['network_requests'].append(r.url)
                    if r.url.startswith(('http:', 'https:')) else None)
            checked = {}
            for name in ('report', 'learning'):
                page.goto(getattr(args, name).resolve().as_uri())
                record = json.loads(page.locator('#chainbench-evidence').text_content())
                assert page.locator('[data-instance]').count() == len(record['charts'])
                for slug, chart in record['charts'].items():
                    panel = page.locator(f'[data-instance="{slug}"]')
                    assert panel.is_visible()
                    assert f'n={chart["instance"]["dimension"]}' in panel.text_content()
                    panel.locator('summary').click()
                    assert json.loads(panel.locator('pre').text_content()) == chart['instance']
                    assert panel.locator('pre').is_visible()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    panel.locator('summary').click()
                selected = page.locator('[data-instance="beck-teboulle-2009"]')
                selected.screenshot(path=str(args.output/f'{name}-context-{width}.png'))
                if name == 'learning':
                    page.locator('#beck-teboulle-2009 .plot').first.screenshot(path=str(args.output/f'curve-{width}.png'))
                checked[name] = len(record['charts'])
            page.goto(args.svg.resolve().as_uri())
            svg = page.locator('svg')
            data = json.loads(page.locator('metadata').text_content())
            assert data['instance']['topic'] == 'nesterov-1983'
            assert 'CANONICAL ILLUSTRATION' in svg.text_content()
            assert 'n=80' in svg.text_content()
            assert 'kappa undefined (mu=0)' in svg.text_content()
            # Text boxes must remain inside the actual viewBox, including the caption.
            assert svg.evaluate('''el => {
              const box=el.viewBox.baseVal;
              return Array.from(el.querySelectorAll('text:not([transform])')).every(t=>{
                const b=t.getBBox(); return b.x>=-1 && b.y>=-1 && b.x+b.width<=box.width+1 && b.y+b.height<=box.height+1;
              });
            }''')
            if width == 1440:
                svg.screenshot(path=str(args.output/'standalone.png'))
            evidence['viewports'].append({'width': width, 'matched_contexts': checked,
                                          'expanded_inputs': 'matched', 'standalone_caption': 'passed',
                                          'overflow': False})
            context.close()
        context = browser.new_context(java_script_enabled=False, offline=True,
                                      viewport={'width': 390, 'height': 1000})
        page = context.new_page()
        page.goto(args.learning.resolve().as_uri())
        panel = page.locator('[data-instance="beck-teboulle-2009"]')
        panel.locator('summary').click()
        assert panel.locator('pre').is_visible()
        evidence['no_script'] = 'visible context and full input details'
        context.close()
        browser.close()
    assert not evidence['network_requests'], evidence['network_requests']
    assert not evidence['javascript_errors'], evidence['javascript_errors']
    (args.output/'browser-verification.json').write_text(json.dumps(evidence, indent=2)+'\n', encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
