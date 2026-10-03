"""Exercise the real installed loopback CLI; never print or retain session tokens."""
from __future__ import annotations

import http.client
import json
import queue
import subprocess
import threading
from contextlib import contextmanager
from urllib.parse import urlsplit

from smoke_instances import audit_instance_result, canonical, require
from studio_evidence import FAMILIES, REJECTIONS, case_request, require_studio


@contextmanager
def studio_session(command, work, env):
    child = subprocess.Popen([*command, 'studio', '--lang', 'ko', '--idle-timeout', '60'],
        cwd=work, env={**env, 'PYTHONDONTWRITEBYTECODE': '1'}, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding='utf8')
    lines = queue.Queue()
    reader = threading.Thread(target=lambda: lines.put(child.stdout.readline()), daemon=True)
    reader.start()
    try:
        first = lines.get(timeout=30)
        prefix = 'ChainBench studio: '
        require(first.startswith(prefix), 'Studio did not announce its loopback session')
        url = urlsplit(first[len(prefix):].strip())
        require(url.scheme == 'http' and url.hostname == '127.0.0.1' and url.port and len(url.fragment) == 43)
        yield {'origin': f'http://{url.netloc}', 'authority': url.netloc, 'port': url.port,
               'token': url.fragment, 'url': first[len(prefix):].strip(), 'process': child}
    finally:
        if child.poll() is None:
            child.terminate()
        child.communicate(timeout=30)
        reader.join(timeout=1)


def send(session, path, value, *, replace=None, remove=()):
    body = json.dumps(value, allow_nan=False).encode('utf8')
    headers = {'Host': session['authority'], 'Origin': session['origin'],
               'X-ChainBench-Token': session['token'], 'Content-Type': 'application/json'}
    headers.update(replace or {})
    for key in remove:
        headers.pop(key)
    connection = http.client.HTTPConnection('127.0.0.1', session['port'], timeout=35)
    try:
        connection.request('POST', path, body, headers)
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def audit_response(value, request):
    require(value['kind'] == 'chainbench.studio-result' and value['request'] == request)
    result, html = value['result'], value['html']
    instance = result['instance']
    require(value['input_json'] == canonical(instance) and value['result_json'] == canonical(result),
            'Download JSON changed original numeric representation')
    require(instance['origin']['parameters']['seed'] == request['seed'])
    require(instance['run']['steps'] == request['steps'] and len(instance['x0']) == request['dimension'])
    require(instance['run']['methods'] == request['methods'] and instance['run']['include_iterates'] is True)
    parameters = instance['origin']['parameters']
    for key in ('L', 'condition_number', 'lam'):
        if key in request:
            require(parameters[key] == request[key])
    rows = audit_instance_result(result, instance, html)
    return {'family': request['family'], 'seed': request['seed'], 'methods': request['methods'],
            'dimension': request['dimension'], 'steps': request['steps'], 'rows': rows,
            'numeric_audit': True, 'exact_html': True,
            'input_sha256': instance['input_sha256'], 'manifest_sha256': instance['manifest_sha256']}


def exercise_studio(cli, work, env):
    before = {p.relative_to(work) for p in work.rglob('*')}
    proof = {'bind': '127.0.0.1', 'ephemeral_port': True, 'cases': [], 'rejections': {}}
    with studio_session([cli], work, env) as session:
        for family in FAMILIES:
            for seed in (0, 7):
                request = case_request(family, seed)
                status, value = send(session, '/api/run', request)
                require(status == 200, 'Installed studio calculation failed')
                require(session['token'] not in json.dumps(value) and session['origin'] not in value['html'])
                proof['cases'].append(audit_response(value, request))
        request = case_request('quadratic', 0)
        cases = [
            ('host', request, '/api/run', {'replace': {'Host': 'attacker.invalid'}}),
            ('origin', request, '/api/run', {'replace': {'Origin': 'https://attacker.invalid'}}),
            ('token', request, '/api/run', {'replace': {'X-ChainBench-Token': 'wrong'}}),
            ('missing-origin', request, '/api/run', {'remove': ['Origin']}),
            ('dimension', {**request, 'dimension': 17}, '/api/run', {}),
            ('steps', {**request, 'steps': 201}, '/api/run', {}),
            ('unknown-path', request, '/api/files', {}),
            ('unknown-field', {**request, 'path': 'anything'}, '/api/run', {}),
        ]
        for name, value, path, kwargs in cases:
            code, _ = send(session, path, value, **kwargs)
            require(code == REJECTIONS[name], 'Studio boundary rejection failed')
            proof['rejections'][name] = code
        status, value = send(session, '/api/shutdown', {})
        require(status == 200 and value == {'status': 'stopped'})
        require(session['process'].wait(timeout=10) == 0)
        proof['shutdown'] = True
    require(before == {p.relative_to(work) for p in work.rglob('*')}, 'Studio wrote files on the server')
    proof.update(no_server_files=True, no_session_material_in_outputs=True)
    require_studio(proof)
    return proof
