"""Opt-in, memory-only loopback service for bounded teaching experiments."""
from __future__ import annotations

import hmac
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from .experiments import METHODS, _bounded, _choice, _object
from .instances import parse_json
from .studio_page import CSP, studio_html

MAX_REQUEST_BYTES = 4096
MAX_RESPONSE_BYTES = 8_000_000
COMPUTE_TIMEOUT = 20
SOCKET_TIMEOUT = 3


def integer(value, name, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f'{name} must be an integer from {lower} to {upper}')
    return value


def normalize_request(value):
    """Validate before starting a worker; no user-controlled paths or commands."""
    common = {'family', 'dimension', 'seed', 'steps', 'methods', 'lang'}
    _object(value, common | {'L', 'condition_number', 'lam'}, common, 'studio request')
    family = _choice(value['family'], tuple(METHODS), 'family')
    extra = {'L', 'condition_number'} if family == 'quadratic' else {'lam'} if family == 'diagonal-lasso' else set()
    _object(value, common | extra, common | extra, 'studio request')
    result = dict(value)
    for key, lower, upper in [('dimension', 2, 16), ('seed', 0, 2**32-1), ('steps', 0, 200)]:
        result[key] = integer(value[key], key, lower, upper)
    result['lang'] = _choice(value['lang'], ('en', 'ko'), 'lang')
    methods = value['methods']
    if (type(methods) is not list or not 1 <= len(methods) <= len(METHODS[family])
            or any(type(m) is not str or m not in METHODS[family] for m in methods)
            or len(set(methods)) != len(methods)):
        raise ValueError('select distinct supported methods for this family')
    result['methods'] = list(methods)
    for key, lower, upper in [('L', .001, 1000), ('condition_number', 1, 10000), ('lam', 0, 10)]:
        if key in extra:
            result[key] = _bounded(value[key], key, lower, upper)
    return result


def run_worker(request, *, timeout=COMPUTE_TIMEOUT):
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    # Small dense teaching examples need no BLAS thread pool per request.
    env.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    result = subprocess.run(
        [sys.executable, '-m', 'chainbench.studio_worker'],
        input=json.dumps(request, allow_nan=False).encode('utf8'),
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, timeout=timeout,
        check=False,
    )
    # subprocess.run kills and waits for the direct child when communication times out.
    if result.returncode or not result.stdout or len(result.stdout) > MAX_RESPONSE_BYTES:
        raise RuntimeError('The calculation could not produce a bounded result')
    value = json.loads(result.stdout)
    if type(value) is not dict or set(value) != {'kind', 'request', 'result', 'input_json', 'result_json', 'html'}:
        raise RuntimeError('Invalid calculation response')
    if value['kind'] != 'chainbench.studio-result' or value['request'] != request:
        raise RuntimeError('Calculation settings changed')
    return result.stdout


class StudioServer(HTTPServer):
    """One request/worker at a time, with bounded socket and worker lifetimes."""
    allow_reuse_address = False
    request_queue_size = 4

    def __init__(self, *, port=0, lang='en', idle_timeout=900):
        integer(port, 'port', 0, 65535)
        integer(idle_timeout, 'idle_timeout', 10, 3600)
        _choice(lang, ('en', 'ko'), 'lang')
        self.lang = lang
        self.idle_timeout = idle_timeout
        self.token = secrets.token_urlsafe(32)
        self.stopping = False
        self.last_activity = time.monotonic()
        super().__init__(('127.0.0.1', port), StudioHandler)
        self.timeout = .25
        self.authority = f'127.0.0.1:{self.server_port}'
        self.origin = f'http://{self.authority}'

    @property
    def launch_url(self):
        return self.origin + '/#' + self.token

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(SOCKET_TIMEOUT)
        return connection, address

    def handle_error(self, request, client_address):
        # Do not log tokens, bodies, user environment or socket tracebacks.
        pass

    def run(self):
        try:
            while not self.stopping and time.monotonic() - self.last_activity < self.idle_timeout:
                self.handle_request()
        finally:
            self.server_close()


class StudioHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def log_message(self, format, *args):
        pass

    def reply(self, code, content, content_type='application/json; charset=utf-8'):
        self.close_connection = True
        data = content if type(content) is bytes else json.dumps(content).encode('utf8')
        self.send_response_only(code)
        for key, value in [('Content-Type', content_type), ('Content-Length', str(len(data))),
                           ('Connection', 'close'), ('Cache-Control', 'no-store'),
                           ('Referrer-Policy', 'no-referrer'), ('X-Content-Type-Options', 'nosniff'),
                           ('X-Frame-Options', 'DENY'), ('Content-Security-Policy', CSP)]:
            self.send_header(key, value)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(data)

    def send_error(self, code, message=None, explain=None):
        self.reply(code, {'error': 'Unsupported or malformed HTTP request'})

    def one_header(self, name):
        values = self.headers.get_all(name, [])
        return values[0] if len(values) == 1 else None

    def permitted(self, *, post=False):
        server = self.server
        if self.client_address[0] != '127.0.0.1' or self.one_header('Host') != server.authority:
            return False
        origins = self.headers.get_all('Origin', [])
        if origins and (len(origins) != 1 or origins[0] != server.origin):
            return False
        sites = self.headers.get_all('Sec-Fetch-Site', [])
        if sites and (len(sites) != 1 or sites[0] not in ('same-origin', 'none')):
            return False
        if post:
            token = self.one_header('X-ChainBench-Token')
            if (origins != [server.origin] or token is None or not token.isascii()
                    or not hmac.compare_digest(token, server.token)):
                return False
        return True

    def do_GET(self):
        if not self.permitted():
            self.reply(403, {'error': 'This session only accepts its own loopback origin'})
        elif self.path != '/':
            self.reply(404, {'error': 'No such studio route'})
        else:
            self.reply(200, studio_html(self.server.lang).encode('utf8'), 'text/html; charset=utf-8')

    def do_POST(self):
        if not self.permitted(post=True):
            self.reply(403, {'error': 'Invalid studio origin or session'})
            return
        if self.path not in ('/api/run', '/api/shutdown'):
            self.reply(404, {'error': 'No such studio route'})
            return
        length = self.one_header('Content-Length')
        if (self.headers.get_all('Transfer-Encoding') or self.headers.get_all('Content-Encoding')
                or self.headers.get_all('Expect') or length is None
                or not length.isascii() or not length.isdecimal() or len(length) > 6
                or self.one_header('Content-Type') != 'application/json'):
            self.reply(400, {'error': 'Send one JSON body with an explicit byte length'})
            return
        size = int(length)
        if not 1 <= size <= MAX_REQUEST_BYTES:
            self.reply(413, {'error': 'Studio request must contain 1 to 4096 bytes'})
            return
        try:
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise ValueError('Incomplete request body')
            value = parse_json(raw.decode('utf8'))
            if self.path == '/api/shutdown':
                if value != {} or type(value) is not dict:
                    raise ValueError('Shutdown requires an empty JSON object')
                self.server.stopping = True
                self.reply(200, {'status': 'stopped'})
                return
            request = normalize_request(value)
            self.server.last_activity = time.monotonic()
            data = run_worker(request)
            self.server.last_activity = time.monotonic()
            self.reply(200, data)
        except (ValueError, UnicodeError, OverflowError) as exc:
            self.reply(400, {'error': str(exc)[:240]})
        except (TimeoutError, socket.timeout):
            self.reply(408, {'error': 'Request body timed out'})
        except subprocess.TimeoutExpired:
            self.reply(504, {'error': 'Calculation exceeded 20 seconds; reduce dimension, steps or methods'})
        except (RuntimeError, OSError):
            self.reply(500, {'error': 'Calculation failed; reduce the requested experiment'})


def add_studio_parser(sub):
    parser = sub.add_parser('studio', help='start an opt-in browser experiment on 127.0.0.1')
    parser.add_argument('--port', type=int, default=0, help='local port; 0 selects an available port')
    parser.add_argument('--lang', choices=('en', 'ko'), default='en')
    parser.add_argument('--idle-timeout', type=int, default=900, help='idle seconds, from 10 to 3600')


def execute_studio(args):
    server = StudioServer(port=args.port, lang=args.lang, idle_timeout=args.idle_timeout)
    print(f'ChainBench studio: {server.launch_url}', flush=True)
    print('Open this URL locally. Stop in the browser or press Ctrl+C.', flush=True)
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    print('ChainBench studio stopped.', flush=True)
    return 0
