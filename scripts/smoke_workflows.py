"""Installed CLI evidence for learning, one-factor sweeps, replay and a public case.

Called for both wheel and sdist by smoke_install, using its external venv.
No package imports from the checkout are used here.
"""
from __future__ import annotations

import json
import math
from html.parser import HTMLParser


def extract_record(text: str) -> dict:
    class Parser(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.active = False
            self.chunks = []
        def handle_starttag(self, tag, attrs):
            if tag == 'pre' and dict(attrs).get('id') == 'chainbench-evidence':
                self.active = True
        def handle_endtag(self, tag):
            if tag == 'pre':
                self.active = False
        def handle_data(self, data):
            if self.active:
                self.chunks.append(data)
    parser = Parser()
    parser.feed(text)
    return json.loads(''.join(parser.chunks))


def exercise_workflows(cli, work, env, version, run):
    path = work/'learning.html'
    run([cli, 'learn', '--lang', 'ko', '--output', str(path)], work, env)
    text = path.read_text(encoding='utf8')
    learning = extract_record(text)
    actual = json.loads(run([cli, 'check', 'all', '--json'], work, env))
    converted = []
    for r in learning['results']:
        row = dict(r)
        state = row.pop('consistent')
        row['status'] = 'INFO' if state is None else 'CONSISTENT' if state else 'NOT CONSISTENT'
        converted.append(row)
    if (learning['kind'] != 'chainbench.learning' or converted != actual
            or learning['environment']['chainbench'] != version or text.count('data-search=') != 16):
        raise RuntimeError('learning report disagrees with installed checks')
    # Selected default-normalized curves independently reproduce bound ratios.
    for slug in ('gd-baseline', 'nesterov-1983', 'beck-teboulle-2009', 'jaggi-2013'):
        figure = learning['charts'][slug]
        expected = [a/b for a,b in zip(figure['series'][0]['y'], figure['series'][1]['y'])]
        if expected != learning['normalized_charts'][slug]['series'][0]['y']:
            raise RuntimeError('learning normalized plot differs from samples')

    args = [cli, 'sweep', '--preset', 'quadratic', '--parameter', 'condition_number',
            '--values', '10', '100', '--dimension', '6', '--steps', '8', '--methods', 'gd', 'cg']
    sweep = json.loads(run(args+['--format', 'json'], work, env))
    html = run(args+['--format', 'html'], work, env)
    if extract_record(html) != sweep:
        raise RuntimeError('sweep HTML differs from computed JSON')
    for exp, condition in zip(sweep['experiments'], (10., 100.)):
        config = work/f'sweep-{condition}-config.json'
        config.write_text(json.dumps(exp['config']), encoding='utf8')
        rerun = json.loads(run([cli, 'experiment', '--config', str(config)], work, env))
        if exp != rerun or exp['config']['problem']['condition_number'] != condition:
            raise RuntimeError('sweep did not execute the saved one-field configuration')
    original = sweep['experiments'][0]
    saved = work/'saved-experiment.json'
    saved.write_text(json.dumps(original),encoding='utf8')
    replay = json.loads(run([cli,'replay',str(saved),'--format','json'],work,env))
    if (replay['status'] != 'MATCH' or replay['mismatch_count'] != 0
            or replay['replayed'] != original or replay['numeric_samples_compared'] <= 0):
        raise RuntimeError('saved experiment replay is missing or inconsistent')
    replay_html = run([cli,'replay',str(saved)],work,env)
    if extract_record(replay_html) != replay:
        raise RuntimeError('replay HTML evidence differs')

    case = json.loads(run([cli,'case-study','gd-tight','--horizon','1','--format','json'],work,env))
    if (not math.isclose(case['rows'][-1]['gap'], 1/6, abs_tol=1e-14)
            or not math.isclose(case['rows'][-1]['x'], 2/3, abs_tol=1e-14)
            or not math.isclose(case['observed_ratio'],1,abs_tol=1e-12)):
        raise RuntimeError('public Huber case failed independent N=1 calculation')
    html = run([cli,'case-study','gd-tight','--horizon','1'],work,env)
    if extract_record(html) != case:
        raise RuntimeError('case-study HTML differs from computed JSON')
    return {'learning':'matched','sweep':'matched','replay':'matched','gd_tight':'matched'}
