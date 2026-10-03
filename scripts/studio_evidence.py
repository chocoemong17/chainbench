"""Strict standard-library publication scope for both installed studio commands."""
from __future__ import annotations

import re

FAMILIES = {'quadratic': ['gd', 'smooth-fista', 'heavy-ball', 'cg', 'proximal-point'],
            'diagonal-lasso': ['ista', 'fista'], 'simplex': ['frank-wolfe']}
REJECTIONS = {'host': 403, 'origin': 403, 'token': 403, 'missing-origin': 403,
              'dimension': 400, 'steps': 400, 'unknown-path': 404, 'unknown-field': 400}


def case_request(family, seed):
    value = {'family': family, 'dimension': 4, 'seed': seed, 'steps': 2,
             'methods': FAMILIES[family], 'lang': 'ko'}
    if family == 'quadratic':
        value.update(L=2., condition_number=10.)
    if family == 'diagonal-lasso':
        value['lam'] = .3
    return value


def require_studio(value):
    fixed = {'bind': '127.0.0.1', 'ephemeral_port': True, 'shutdown': True,
             'no_server_files': True, 'no_session_material_in_outputs': True, 'rejections': REJECTIONS}
    if type(value) is not dict or set(value) != set(fixed) | {'cases'}:
        raise RuntimeError('Missing installed studio evidence')
    for key, wanted in fixed.items():
        if type(value[key]) is not type(wanted) or value[key] != wanted:
            raise RuntimeError('Invalid installed studio boundary evidence')
    if any(type(v) is not int for v in value['rejections'].values()):
        raise RuntimeError('Invalid studio rejection types')
    cases = value['cases']
    expected = [(family, seed) for family in FAMILIES for seed in (0, 7)]
    if type(cases) is not list or len(cases) != len(expected):
        raise RuntimeError('Incomplete installed studio cases')
    scope = []
    for item, (family, seed) in zip(cases, expected):
        want = {'family': family, 'seed': seed, 'methods': FAMILIES[family], 'dimension': 4, 'steps': 2,
                'rows': 3*len(FAMILIES[family]), 'numeric_audit': True, 'exact_html': True}
        if type(item) is not dict or set(item) != set(want) | {'input_sha256', 'manifest_sha256'}:
            raise RuntimeError('Incomplete installed studio case')
        if any(type(item[k]) is not type(v) or item[k] != v for k, v in want.items()):
            raise RuntimeError('Invalid installed studio numerical outcome')
        if any(type(item[k]) is not str or not re.fullmatch('[0-9a-f]{64}', item[k])
               for k in ('input_sha256', 'manifest_sha256')):
            raise RuntimeError('Missing studio input binding')
        scope.append(want)
    return {**fixed, 'cases': scope}
