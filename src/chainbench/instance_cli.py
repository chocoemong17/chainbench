"""CLI routing for bounded numeric inputs; no data, code or network import hooks."""
from __future__ import annotations

import json
from pathlib import Path

from .instance_reporting import instance_html
from .instances import (
    MAX_INPUT_BYTES,
    MAX_REPORT_BYTES,
    generate_instance,
    import_instance,
    parse_json,
    replay_instance,
    run_instance,
)


def add_instance_parser(sub) -> None:
    parser = sub.add_parser('instance', help='generate, import, run and replay exact numeric inputs')
    commands = parser.add_subparsers(dest='instance_command', required=True)
    for name in ('generate', 'import', 'run', 'replay'):
        cmd = commands.add_parser(name)
        cmd.add_argument('--output', type=Path)
        cmd.add_argument('--force', action='store_true')
        if name == 'generate':
            cmd.add_argument('family', choices=('quadratic', 'diagonal-lasso', 'simplex'))
            cmd.add_argument('--dimension', type=int, default=6)
            cmd.add_argument('--seed', type=int, default=0)
            cmd.add_argument('--steps', type=int, default=30)
            cmd.add_argument('--methods', nargs='+')
            cmd.add_argument('--include-iterates', action='store_true')
            cmd.add_argument('--L', type=float)
            cmd.add_argument('--condition-number', type=float)
            cmd.add_argument('--lam', type=float)
        else:
            cmd.add_argument('input', type=Path)
        if name in ('run', 'replay'):
            cmd.add_argument('--format', choices=('json', 'html'), default='json')
            cmd.add_argument('--lang', choices=('en', 'ko'), default='en')
        if name == 'replay':
            cmd.add_argument('--rtol', type=float, default=1e-7)
            cmd.add_argument('--atol', type=float, default=1e-12)


def execute_instance(args, write) -> int:
    name = args.instance_command
    if args.output is not None and args.output.exists() and not args.force:
        raise ValueError('output exists; use --force to replace it')
    if name != 'generate':
        if args.output is not None and (args.input.resolve() == args.output.resolve()
                or (args.output.exists() and args.output.samefile(args.input))):
            raise ValueError('instance output must not replace its input')
        limit = MAX_REPORT_BYTES if name == 'replay' else MAX_INPUT_BYTES
        with args.input.open('rb') as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError(f'instance input exceeds {limit} byte limit')
        value = parse_json(raw.decode('utf-8'), report=name == 'replay')
    if name == 'generate':
        settings = {'steps': args.steps, 'include_iterates': args.include_iterates}
        if args.methods is not None:
            settings['methods'] = args.methods
        result = generate_instance(args.family, dimension=args.dimension, seed=args.seed,
                                   run=settings, L=args.L, condition_number=args.condition_number, lam=args.lam)
    elif name == 'import':
        result = import_instance(value)
    elif name == 'run':
        result = run_instance(value)
    else:
        result = replay_instance(value, rtol=args.rtol, atol=args.atol)
    if getattr(args, 'format', 'json') == 'html':
        text = instance_html(result if name == 'run' else result['replayed'], args.lang,
                             replay=result if name == 'replay' else None)
    else:
        # Compact transport stays inside the declared byte budget, including near-limit reports.
        text = json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n'
    write(args.output, text, args.force)
    return 1 if name == 'replay' and result['status'] != 'MATCH' else 0
