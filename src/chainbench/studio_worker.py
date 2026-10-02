"""Private fixed worker protocol; stdin contains only a small parameter object."""
from __future__ import annotations

import json
import sys

from .instance_reporting import instance_html
from .instances import generate_instance, parse_json, run_instance
from .studio import MAX_REQUEST_BYTES, MAX_RESPONSE_BYTES, normalize_request


def calculate(value):
    request = normalize_request(value)
    instance = generate_instance(request['family'], dimension=request['dimension'], seed=request['seed'],
        run={'steps': request['steps'], 'methods': request['methods'], 'include_iterates': True},
        **{k: request[k] for k in ('L', 'condition_number', 'lam') if k in request})
    result = run_instance(instance)
    return {'kind': 'chainbench.studio-result', 'request': request, 'result': result,
            'html': instance_html(result, request['lang'])}


def main():
    raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError('Studio request exceeds its byte limit')
    value = calculate(parse_json(raw.decode('utf8')))
    data = json.dumps(value, allow_nan=False, separators=(',', ':')).encode('utf8')
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError('Studio response exceeds its byte limit')
    sys.stdout.buffer.write(data)


if __name__ == '__main__':
    main()
