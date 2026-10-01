"""Validate that reading cards lead to the declared, available computations."""
from __future__ import annotations

import json
from html.parser import HTMLParser

EXPECTED = {
    'gd-baseline': ['tight-gd', 'landscape'],
    'nesterov-1983': ['landscape', 'proximal'],
    'polyak-1964': ['cycle', 'landscape'],
    'hestenes-stiefel-1952': ['shewchuk', 'landscape'],
    'jaggi-2013': ['simplex', 'sparsity'],
    'rockafellar-1976': ['landscape'],
    'beck-teboulle-2009': ['proximal', 'deblur', 'wavelet'],
    'ista-vs-fista': ['proximal', 'deblur', 'wavelet'],
}
COMMANDS = {
    'tight-gd': ('tight-gd.html', ['case-study', 'gd-tight', '--horizon', '20', '--h', '1', '--L', '1', '--R', '1']),
    'landscape': ('landscape.html', ['landscape', '--condition-number', '20', '--angle', '32', '--steps', '18']),
    'cycle': ('heavy-ball.html', ['reproduce', 'lessard-2016', '--steps', '50']),
    'shewchuk': ('shewchuk.html', ['reproduce', 'shewchuk-1994', '--steps', '12']),
    'simplex': ('simplex.html', ['geometry', 'frank-wolfe', '--steps', '18']),
    'sparsity': ('fw-sparsity.html', ['case-study', 'fw-sparsity', '--steps', '40']),
    'proximal': ('proximal.html', ['geometry', 'ista-fista', '--steps', '18']),
    'deblur': ('deblur.html', ['reproduce', 'fista-deblurring', '--steps', '10000']),
    'wavelet': ('wavelet.html', ['reproduce', 'fista-wavelet', '--steps', '200', '--seed', '0']),
}


def validate_learning_paths(html, artifacts=()):
    def require(condition):
        if not condition:
            raise RuntimeError('learning workflow links or declared commands differ')
    class Parse(HTMLParser):
        def __init__(self):
            super().__init__()
            self.topic = self.active = self.language = None
            self.record_active = self.command_active = False
            self.record, self.cards = [], {}
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'html':
                self.language = attrs.get('lang')
            if tag == 'section':
                self.topic = attrs.get('id')
            if tag == 'article' and 'data-workflow' in attrs:
                self.active = (self.topic, attrs['data-workflow'])
                require(self.active not in self.cards)
                self.cards[self.active] = {'links': [], 'command': []}
            if self.active and tag == 'a':
                self.cards[self.active]['links'].append((attrs.get('data-workflow-link'), attrs.get('href')))
            if tag == 'pre':
                self.record_active = attrs.get('id') == 'chainbench-evidence'
                self.command_active = self.active is not None
        def handle_endtag(self, tag):
            if tag == 'section':
                self.topic = None
            if tag == 'article':
                self.active = None
            if tag == 'pre':
                self.record_active = self.command_active = False
        def handle_data(self, data):
            if self.record_active:
                self.record.append(data)
            if self.command_active:
                self.cards[self.active]['command'].append(data)
    parsed = Parse()
    parsed.feed(html)
    require(parsed.language in ('ko', 'en'))
    record = json.loads(''.join(parsed.record))
    guides = record['workflow_guides']
    topics = [r['slug'] for r in record['results']]
    require(guides['kind'] == 'curated-reading-paths' and set(guides['topics']) == set(topics)
            and set(topics) <= set(EXPECTED))
    files = {a['path']: a for a in artifacts}
    pairs = set()
    for slug in topics:
        items = guides['topics'][slug]
        require([i['id'] for i in items] == EXPECTED[slug]+['stress-'+slug])
        for item in items:
            key = item['id']
            if key.startswith('stress-'):
                name, command = key+'.html', ['stress', slug, '--trials', '32', '--seed', '0']
            else:
                name, command = COMMANDS[key]
            require(item['report'] == name and item['command'] == command)
            require(all(len(item[field]) == 2 and all(isinstance(s, str) and s for s in item[field])
                        for field in ('question', 'scope')) and bool(item['label']))
            pair = (slug, key)
            pairs.add(pair)
            require(pair in parsed.cards)
            card = parsed.cards[pair]
            full = [*command, '--lang', parsed.language]
            require(''.join(card['command']).strip() == 'python -m chainbench '+' '.join([*full, '--output', name]))
            require(card['links'] == ([(key, name)] if name in files else []))
            if name in files:
                require(files[name]['command'] == full)
    require(set(parsed.cards) == pairs)
    return len(pairs)
