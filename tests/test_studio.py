"""Loopback boundaries, actual computation, resource cleanup and exact report binding."""
from __future__ import annotations

import copy
import http.client
import json
import socket
import subprocess
import threading
import time

import pytest

from chainbench import studio
from chainbench.instances import replay_instance
from chainbench.studio_worker import calculate


def request():
    return {'family': 'quadratic', 'dimension': 2, 'seed': 0, 'steps': 2,
            'methods': ['gd'], 'lang': 'en', 'L': 2, 'condition_number': 4}


@pytest.fixture
def server():
    instance = studio.StudioServer()
    thread = threading.Thread(target=instance.run)
    thread.start()
    try:
        yield instance
    finally:
        instance.stopping = True
        thread.join(timeout=5)
        assert not thread.is_alive()


def http(server, *, method='POST', path='/api/run', body=None, replace=None, omit=(), extra=()):
    if body is None:
        body = json.dumps(request()).encode()
    headers = {'Host': server.authority, 'Origin': server.origin, 'X-ChainBench-Token': server.token,
               'Content-Type': 'application/json', 'Content-Length': str(len(body))}
    headers.update(replace or {})
    for key in omit:
        headers.pop(key)
    connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=30)
    try:
        connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        for name, value in [*headers.items(), *extra]:
            connection.putheader(name, value)
        connection.endheaders(body)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


@pytest.mark.parametrize('field,value', [
    ('dimension', 1), ('dimension', 17), ('dimension', True), ('dimension', 2.),
    ('steps', -1), ('steps', 201), ('steps', False), ('seed', -1), ('seed', 2**32),
    ('methods', []), ('methods', ['gd','gd']), ('methods', ['ista']), ('methods', ['../../anything']),
    ('methods', [None]), ('methods', 'gd'), ('family', 'unknown'), ('lang', 'xx'),
    ('L', 0), ('L', True), ('L', float('inf')), ('L', '2'), ('condition_number', 10001),
    ('path', 'anything'), ('url', 'https://example.com')])
def test_invalid_request_is_rejected_before_worker(server, monkeypatch, field, value):
    called = []
    monkeypatch.setattr(studio, 'run_worker', lambda _: called.append(True))
    payload = {**request(), field: value}
    assert http(server, body=json.dumps(payload).encode())[0] == 400
    assert not called


@pytest.mark.parametrize('options,status', [
    ({'replace': {'Host': 'localhost'}}, 403),
    ({'replace': {'Host': 'attacker.invalid'}}, 403),
    ({'replace': {'Origin': 'null'}}, 403),
    ({'replace': {'Origin': 'http://127.0.0.1:1'}}, 403),
    ({'replace': {'X-ChainBench-Token': 'wrong'}}, 403),
    ({'replace': {'X-ChainBench-Token': 'é'}}, 403),
    ({'replace': {'Sec-Fetch-Site': 'cross-site'}}, 403),
    ({'omit': ['Origin']}, 403), ({'omit': ['Host']}, 403),
    ({'omit': ['X-ChainBench-Token']}, 403),
    ({'extra': [('Host', 'duplicate')]}, 403),
    ({'extra': [('Origin', 'duplicate')]}, 403),
    ({'extra': [('X-ChainBench-Token', 'duplicate')]}, 403),
    ({'replace': {'Content-Type': 'text/plain'}}, 400),
    ({'extra': [('Content-Type', 'application/json')]}, 400),
    ({'extra': [('Content-Length', '1')]}, 400),
    ({'replace': {'Content-Length': '-1'}}, 400),
    ({'replace': {'Content-Length': '+2'}}, 400),
    ({'replace': {'Content-Length': '0'}}, 413),
    ({'replace': {'Content-Length': '4097'}}, 413),
    ({'omit': ['Content-Length']}, 400),
    ({'extra': [('Transfer-Encoding', 'chunked')]}, 400),
    ({'extra': [('Content-Encoding', 'gzip')]}, 400),
    ({'extra': [('Expect', '100-continue')]}, 400),
    ({'path': '/api/run?token=anything'}, 404),
    ({'path': '/api/files'}, 404), ({'method': 'OPTIONS'}, 501),
])
def test_http_boundaries_never_compute(server, monkeypatch, options, status):
    called = []
    monkeypatch.setattr(studio, 'run_worker', lambda _: called.append(True))
    code, headers, _ = http(server, **options)
    assert code == status and headers['Cache-Control'] == 'no-store'
    assert 'Access-Control-Allow-Origin' not in headers and not called


@pytest.mark.parametrize('body', [b'{}', b'[]', b'null', b'{', b'\xff',
                                 b'{"family": "quadratic", "family": "simplex"}'])
def test_malformed_json_never_computes(server, monkeypatch, body):
    called = []
    monkeypatch.setattr(studio, 'run_worker', lambda _: called.append(True))
    assert http(server, body=body)[0] == 400
    assert not called


def test_page_does_not_disclose_token_or_serve_files(server):
    code, headers, data = http(server, method='GET', path='/', body=b'')
    assert code == 200 and b'Experiment studio' in data and server.token.encode() not in data
    assert 'frame-ancestors' in headers['Content-Security-Policy']
    for path in ['/etc/passwd', '/../README.md', '/?token=x', '/favicon.ico']:
        assert http(server, method='GET', path=path, body=b'')[0] == 404


def test_real_request_replays_stored_inputs_and_shutdown_closes_port(server):
    code, _, raw = http(server)
    value = json.loads(raw)
    assert code == 200 and value['request'] == request()
    assert server.token not in raw.decode() and server.origin not in value['html']
    assert replay_instance(value['result'])['status'] == 'MATCH'
    assert http(server, path='/api/shutdown', body=b'{"path":"x"}')[0] == 400
    assert http(server, path='/api/shutdown', body=b'{}')[0] == 200
    assert server.stopping


def test_timed_out_worker_is_reaped_and_next_request_can_succeed(monkeypatch):
    children = []
    original = subprocess.Popen
    def track(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(studio.subprocess, 'Popen', track)
    with pytest.raises(subprocess.TimeoutExpired):
        studio.run_worker(request(), timeout=.000001)
    assert children and all(c.poll() is not None for c in children)
    assert json.loads(studio.run_worker(request()))['result']['instance']['run']['steps'] == 2


def test_worker_timeout_and_failure_are_explicit_http_errors(server, monkeypatch):
    def timed_out(_):
        raise subprocess.TimeoutExpired('fixed-worker', 20)
    monkeypatch.setattr(studio, 'run_worker', timed_out)
    assert http(server)[0] == 504
    def failed(_):
        raise RuntimeError('private path must not leak')
    monkeypatch.setattr(studio, 'run_worker', failed)
    code, _, raw = http(server)
    assert code == 500 and b'private path' not in raw
    assert not server.stopping


def test_incomplete_body_times_out_then_accepts_another_connection(server, monkeypatch):
    monkeypatch.setattr(studio, 'SOCKET_TIMEOUT', .05)
    code, _, _ = http(server, replace={'Content-Length': '300'}, body=b'{}')
    assert code == 408
    assert http(server, method='GET', path='/', body=b'')[0] == 200


def test_idle_expiry_releases_socket():
    instance = studio.StudioServer(idle_timeout=10)
    port = instance.server_port
    instance.last_activity = time.monotonic() - 11
    instance.run()
    with pytest.raises(OSError), socket.create_connection(('127.0.0.1', port), timeout=.1):
        pass


def test_each_session_has_an_independent_token():
    with studio.StudioServer() as first, studio.StudioServer() as second:
        assert first.token != second.token and first.server_address[0] == second.server_address[0] == '127.0.0.1'


@pytest.mark.parametrize('kwargs', [{'port': -1}, {'port': 65536}, {'port': True},
                                   {'idle_timeout': 9}, {'idle_timeout': 3601}, {'lang': 'xx'}])
def test_invalid_listener_options_are_rejected(kwargs):
    with pytest.raises(ValueError):
        studio.StudioServer(**kwargs)


def test_settings_and_seed_affect_the_actual_computed_record():
    first = calculate(request())
    other = calculate({**request(), 'seed': 7, 'steps': 0})
    assert first['result']['instance']['input_sha256'] != other['result']['instance']['input_sha256']
    assert len(other['result']['runs'][0]['rows']) == 1
    assert len(first['result']['runs'][0]['rows']) == 3
    damaged = copy.deepcopy(first['result'])
    damaged['runs'][0]['rows'][1]['gap'] += 1
    assert replay_instance(damaged)['status'] == 'MISMATCH'


def test_largest_studio_case_stays_within_output_cap():
    value = {**request(), 'dimension': 16, 'steps': 200, 'methods': list(studio.METHODS['quadratic'])}
    data = studio.run_worker(value)
    result = json.loads(data)['result']
    assert len(data) <= studio.MAX_RESPONSE_BYTES
    assert all(len(run['rows']) == run['updates']+1 <= 201 for run in result['runs'])
    assert result['instance']['run']['include_iterates'] is True
