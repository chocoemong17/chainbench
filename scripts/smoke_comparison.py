"""Independently audit saved comparisons from each installed distribution."""
from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from itertools import combinations

from smoke_workflows import extract_record


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def validate_comparison(result, originals, html=None):
    def require(condition):
        if not condition:
            raise RuntimeError('Comparison provenance, diagnostics or plotted samples differ')
    require(result['kind'] == 'chainbench.comparison' and result['schema_version'] == 1)
    ids = list('ABCD'[:len(originals)])
    require([r['id'] for r in result['records']] == ids)
    for item, source in zip(result['records'], originals):
        require(canonical(item['experiment']) == canonical(source))
        require(item['record_sha256'] == hashlib.sha256(canonical(source).encode()).hexdigest())
    pairs = list(combinations(range(len(originals)), 2))
    require(len(result['pairs']) == len(pairs))
    expected_shared = True
    for pair, (i, j) in zip(result['pairs'], pairs):
        a, b = originals[i], originals[j]
        same_problem = (canonical(a['fixture']) == canonical(b['fixture'])
                        and canonical(a['config']['problem']) == canonical(b['config']['problem']))
        expected_shared = expected_shared and same_problem
        require(pair['left'] == ids[i] and pair['right'] == ids[j])
        require(pair['same_config'] is (canonical(a['config']) == canonical(b['config'])))
        require(pair['same_input_digest'] is (a['fixture']['input_sha256'] == b['fixture']['input_sha256']))
        require(pair['same_recorded_problem'] is same_problem)
        require(pair['same_environment'] is (a['environment'] == b['environment']))
        require(pair['identical_record'] is (canonical(a) == canonical(b)))
        require(pair['shared_methods'] == [m for m in a['config']['methods'] if m in b['config']['methods']])
        for name, left, right in [
            ('config', a['config'], b['config']), ('fixture', a['fixture'], b['fixture']),
            ('environment', a['environment'], b['environment']),
            ('parameter', {r['method']: r['parameters'] for r in a['runs']},
             {r['method']: r['parameters'] for r in b['runs']}),
        ]:
            expected = [{'field': k, 'left': left.get(k), 'right': right.get(k)}
                        for k in sorted(left.keys() | right.keys())
                        if k not in left or k not in right or canonical(left[k]) != canonical(right[k])]
            require(canonical(pair[name+'_differences']) == canonical(expected))
    require(result['shared_recorded_problem'] is expected_shared)
    expected = [('record-'+ident, [(ident, run) for run in source['runs']])
                for ident, source in zip(ids, originals)]
    if expected_shared:
        methods = list(dict.fromkeys(run['method'] for source in originals for run in source['runs']))
        for method in methods:
            selected = [(ident, run) for ident, source in zip(ids, originals)
                        for run in source['runs'] if run['method'] == method]
            if len(selected) > 1:
                expected.append(('shared-'+method, selected))
    require(len(result['charts']) == len(expected))
    for item, (ident, selected) in zip(result['charts'], expected):
        require(item['id'] == ident)
        require(item['records'] == list(dict.fromkeys(i for i, _ in selected)))
        series = item['chart']['series']
        require(len(series) == len(selected))
        for curve, (label, run) in zip(series, selected):
            require(curve['label'] == label+' · '+run['method'] and curve['role'] == 'observed')
            require(curve['x'] == [row['iteration'] for row in run['rows']])
            require(curve['y'] == [row[result['metric']] for row in run['rows']])
    if html is not None:
        require(canonical(extract_record(html)) == canonical(result))
        plots = [json.loads(unescape(s)) for s in re.findall(r'<metadata>(.*?)</metadata>', html, re.S)]
        ordered = ([c['chart'] for c in result['charts'] if c['id'].startswith('shared-')]
                   + [c['chart'] for c in result['charts'] if c['id'].startswith('record-')])
        require(canonical(plots) == canonical(ordered))
    return {'metric': result['metric'], 'records': len(originals),
            'pairs': len(pairs), 'plots': len(expected),
            'retained_samples': 'exact', 'shared_recorded_problem': expected_shared}


def exercise_comparison(cli, work, env, run):
    originals, paths = [], []
    for name, family, steps, extra in [
        ('a', 'quadratic', 8, ['--methods', 'gd', 'cg']),
        ('b', 'quadratic', 12, ['--methods', 'gd', 'cg']),
        ('c', 'quadratic', 8, ['--condition-number', '100', '--methods', 'gd', 'cg']),
        ('d', 'diagonal-lasso', 8, []),
    ]:
        path = work/f'compare-{name}.json'
        run([cli, 'experiment', '--preset', family, '--dimension', '4', '--steps', str(steps),
             *extra, '--output', str(path)], work, env)
        originals.append(json.loads(path.read_text(encoding='utf8')))
        paths.append(str(path))
    outcomes = []
    for count in (2, 3, 4):
        for metric in ('gap', 'stationarity', 'distance_to_reference'):
            args = [cli, 'compare', *paths[:count], '--metric', metric]
            record = json.loads(run(args+['--format', 'json'], work, env))
            if record.get('metric') != metric:
                raise RuntimeError('Comparison did not preserve the requested metric')
            html = run(args+['--lang', 'ko'], work, env)
            outcomes.append(validate_comparison(record, originals[:count], html))
    if not outcomes[0]['shared_recorded_problem'] or outcomes[-1]['shared_recorded_problem']:
        raise RuntimeError('Expected matching and different problem diagnostics')
    return outcomes
