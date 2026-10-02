"""Independent scalar/byte audit of numeric instances from installed CLI outputs."""
from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from html import unescape

from instance_evidence import CASES, require_stored_instances
from smoke_workflows import extract_record


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def require(condition, message='Stored-instance numeric or provenance audit failed'):
    if not condition:
        raise RuntimeError(message)


def raw_cases():
    return {
        'imported-quadratic': {'schema_version': 1, 'problem': {'kind': 'quadratic',
            'Q': [[2, 1], [1, 2]], 'b': [1, -1], 'x_star': [1, -1]}, 'x0': [2, -1],
            'run': {'steps': 2, 'include_iterates': True}},
        'imported-psd': {'schema_version': 1, 'problem': {'kind': 'quadratic',
            'Q': [[0, 0], [0, 2]], 'b': [0, -2], 'x_star': [4, -1]}, 'x0': [0, 1],
            'run': {'steps': 2, 'include_iterates': True, 'methods': ['gd', 'smooth-fista', 'proximal-point']}},
        'imported-lasso': {'schema_version': 1, 'problem': {'kind': 'diagonal-lasso',
            'a': [2, -1], 'b': [1, 1], 'lam': .5}, 'x0': [1, -1],
            'run': {'steps': 2, 'include_iterates': True}},
        'imported-simplex': {'schema_version': 1, 'problem': {'kind': 'simplex', 'target': [.25, .75]},
            'x0': [.5, .5], 'run': {'steps': 2, 'include_iterates': True}},
    }


def audit_instance_result(record, manifest, html=None):
    """No ChainBench or NumPy imports: recompute hashes and every row's four metrics."""
    require(record['kind'] == 'chainbench.instance-experiment')
    require(canonical(record['instance']) == canonical(manifest))
    require(manifest['manifest_sha256'] == hashlib.sha256(canonical(
        {k: v for k, v in manifest.items() if k != 'manifest_sha256'}).encode()).hexdigest())
    p, x0 = manifest['problem'], manifest['x0']
    family, d = p['kind'], len(x0)
    fields = {'quadratic': ['Q', 'b', 'x_star'], 'diagonal-lasso': ['a', 'b', 'lam'], 'simplex': ['target']}[family]
    digest = hashlib.sha256(b'chainbench.numeric-input.v1\0' + family.encode() + b'\0')
    for name, value in [(k, p[k]) for k in fields] + [('x0', x0)]:
        if name == 'Q':
            shape, values = [d, d], [v for row in value for v in row]
        elif name == 'lam':
            shape, values = [], [value]
        else:
            shape, values = [d], value
        digest.update(canonical({'name': name, 'shape': shape}).encode() + b'\0')
        digest.update(struct.pack('<'+'d'*len(values), *values))
    require(digest.hexdigest() == manifest['input_sha256'] == record['fixture']['input_sha256'])
    def close(a, b):
        require(type(a) in (float, int) and math.isfinite(a) and math.isfinite(b)
                and math.isclose(a, b, rel_tol=1e-9, abs_tol=2e-11))
    def dot(a, b):
        return math.fsum(x*y for x, y in zip(a, b))
    def soft(v, threshold):
        return math.copysign(max(abs(v)-threshold, 0), v)
    if family == 'quadratic':
        star = p['x_star']
        def multiply(x):
            return [dot(row, x) for row in p['Q']]
        for a, b in zip(multiply(star), p['b']):
            close(a, b)
        def objective(x):
            return .5*dot(x, multiply(x)) - dot(p['b'], x)
    elif family == 'diagonal-lasso':
        star = [soft(a*b, p['lam'])/(a*a) for a, b in zip(p['a'], p['b'])]
        def objective(x):
            return .5*math.fsum((a*v-b)**2 for a, v, b in zip(p['a'], x, p['b'])) + p['lam']*math.fsum(map(abs, x))
        close(record['fixture']['L'], max(a*a for a in p['a']))
    else:
        star = p['target']
        def objective(x):
            return .5*math.fsum((a-b)**2 for a, b in zip(x, star))
        close(record['fixture']['L'], 1.)
    for a, b in zip(record['fixture']['x_star'], star):
        close(a, b)
    fstar = objective(star)
    close(record['fixture']['f_star'], fstar)
    require([r['method'] for r in record['runs']] == manifest['run']['methods'])
    count = 0
    for run in record['runs']:
        require(len(run['rows']) == run['updates']+1)
        require(canonical(run['rows'][0]['iterate']) == canonical(x0))
        for k, row in enumerate(run['rows']):
            x = row['iterate']
            require(row['iteration'] == k and type(row['iteration']) is int and len(x) == d)
            close(row['objective'], objective(x))
            close(row['distance_to_reference'], math.hypot(*(a-b for a, b in zip(x, star))))
            if family == 'quadratic':
                e = [a-b for a, b in zip(x, star)]
                gap = .5*dot(e, multiply(e))
                stationarity = math.hypot(*(a-b for a, b in zip(multiply(x), p['b'])))
            elif family == 'diagonal-lasso':
                gap = objective(x)-fstar
                L = max(a*a for a in p['a'])
                stationarity = math.hypot(*(L*(v-soft(v-a*(a*v-b)/L, p['lam']/L))
                    for a, v, b in zip(p['a'], x, p['b'])))
            else:
                gap = objective(x)
                gradient = [a-b for a, b in zip(x, star)]
                stationarity = max(0., dot(gradient, x) - min(gradient))
                close(math.fsum(x), 1.)
                require(all(v >= 0 for v in x))
            close(row['gap'], gap)
            close(row['stationarity'], stationarity)
            count += 1
    if html is not None:
        require(canonical(extract_record(html)) == canonical(record))
        charts = [json.loads(unescape(s)) for s in re.findall(r'<metadata>(.*?)</metadata>', html, re.S)]
        require(len(charts) == 3)
        for chart, field in zip(charts, ('gap', 'stationarity', 'distance_to_reference')):
            require(chart['y_scale'] == ('linear' if field == 'distance_to_reference' else 'log'))
            require(len(chart['series']) == len(record['runs']))
            for curve, run in zip(chart['series'], record['runs']):
                require(curve['x'] == [r['iteration'] for r in run['rows']])
                require(curve['y'] == [r[field] for r in run['rows']])
                require(curve['label'] == run['method'] and curve['role'] == 'observed')
    return count


def exercise_instances(cli, work, env, run):
    summaries = []
    for name, family, methods, expected_rows in CASES:
        manifest_path, report_path = work/f'{name}-input.json', work/f'{name}-result.json'
        if name.startswith('generated-'):
            run([cli, 'instance', 'generate', family, '--dimension', '4', '--seed', name.rsplit('-', 1)[1],
                 '--steps', '6', '--include-iterates', '--output', str(manifest_path)], work, env)
        else:
            raw = work/f'{name}-raw.json'
            raw.write_text(json.dumps(raw_cases()[name]), encoding='utf8')
            run([cli, 'instance', 'import', str(raw), '--output', str(manifest_path)], work, env)
        manifest = json.loads(manifest_path.read_text(encoding='utf8'))
        run([cli, 'instance', 'run', str(manifest_path), '--output', str(report_path)], work, env)
        record = json.loads(report_path.read_text(encoding='utf8'))
        html = run([cli, 'instance', 'run', str(manifest_path), '--format', 'html', '--lang', 'ko'], work, env)
        (work/f'{name}.html').write_text(html, encoding='utf8')
        rows = audit_instance_result(record, manifest)
        # HTML is a separate numerical execution. Audit its own complete record,
        # never require cross-process floating-point trajectories to be bit-identical.
        html_rows = audit_instance_result(extract_record(html), manifest, html)
        require(html_rows == rows)
        replay = json.loads(run([cli, 'instance', 'replay', str(report_path)], work, env))
        require(replay['status'] == 'MATCH' and replay['same_input_bytes'] is True
                and replay['mismatch_count'] == 0 and replay['numeric_samples_compared'] > 0)
        require(canonical(replay['replayed']['instance']) == canonical(manifest))
        require(rows == expected_rows)
        summaries.append({'case': name, 'family': family, 'methods': methods, 'rows': rows,
                          'numeric_audit': True, 'exact_inputs': True, 'html_samples': True, 'replay': 'MATCH',
                          'input_sha256': manifest['input_sha256'], 'manifest_sha256': manifest['manifest_sha256']})
    require_stored_instances(summaries)
    return summaries
