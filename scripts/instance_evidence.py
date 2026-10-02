"""Standard-library publication contract for installed exact-input workflows."""
from __future__ import annotations

import re

FAMILIES = {
    'quadratic': ['gd', 'smooth-fista', 'heavy-ball', 'cg', 'proximal-point'],
    'diagonal-lasso': ['ista', 'fista'], 'simplex': ['frank-wolfe'],
}
CASES = [(f'generated-{family}-{seed}', family, methods, {'quadratic': 33, 'diagonal-lasso': 14, 'simplex': 7}[family])
         for family, methods in FAMILIES.items() for seed in (0, 7)] + [
    ('imported-quadratic', 'quadratic', FAMILIES['quadratic'], 15),
    ('imported-psd', 'quadratic', ['gd', 'smooth-fista', 'proximal-point'], 9),
    ('imported-lasso', 'diagonal-lasso', FAMILIES['diagonal-lasso'], 6),
    ('imported-simplex', 'simplex', FAMILIES['simplex'], 3),
]


def require_stored_instances(value):
    """Require every named case and exact typed outcomes, not truthy success labels."""
    if type(value) is not list or len(value) != len(CASES):
        raise RuntimeError('Missing installed stored-instance evidence')
    summaries = []
    for item, (name, family, methods, rows) in zip(value, CASES):
        expected = {'case': name, 'family': family, 'methods': methods, 'rows': rows,
                    'numeric_audit': True, 'exact_inputs': True, 'html_samples': True, 'replay': 'MATCH'}
        if type(item) is not dict or set(item) != set(expected) | {'input_sha256', 'manifest_sha256'}:
            raise RuntimeError('Incomplete stored-instance case evidence')
        for key, wanted in expected.items():
            if type(item[key]) is not type(wanted) or item[key] != wanted:
                raise RuntimeError('Invalid installed stored-instance outcome')
        if any(type(item[k]) is not str or re.fullmatch('[0-9a-f]{64}', item[k]) is None
               for k in ('input_sha256', 'manifest_sha256')):
            raise RuntimeError('Missing stored-instance input binding')
        # Generated arrays can differ between numerical environments. Each was
        # audited against its own exact bytes; compare scope, not cross-build RNG bytes.
        summaries.append(expected)
    return summaries
