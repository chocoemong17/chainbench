"""Computation-derived context for the existing fixed-suite demonstrations."""
from __future__ import annotations

import json
from html import escape

import numpy as np

from ._pages import bi
from ._sources import SOURCE_LINKS
from .problems import DiagonalLassoProblem, QuadraticProblem
from .stories import STORIES
from .stress_cases import input_digest


def instance_record(slug, problem, budget, runs, parameters):
    """Capture the very problem and traces used to draw the chart."""
    starts = [trace.iterates[0] for trace in runs.values()]
    if not starts or not all(np.array_equal(starts[0], x) for x in starts[1:]):
        raise ValueError('canonical runs must share their actual start')
    constants = {'L': float(problem.L) if hasattr(problem, 'L') else 1.}
    if isinstance(problem, QuadraticProblem):
        arrays = {'Q': problem.Q.tolist(), 'b': problem.b.tolist(), 'x_star': problem.x_star.tolist()}
        family, objective = 'quadratic', 'f(x)=0.5*x^T Q x-b^T x'
        constants.update(mu=problem.mu, condition_number=problem.L/problem.mu if problem.mu > 0 else None)
    elif isinstance(problem, DiagonalLassoProblem):
        arrays = {'a': problem.a.tolist(), 'b': problem.b.tolist(), 'lam': [problem.lam]}
        family, objective = 'diagonal-lasso', 'F(x)=0.5*||diag(a)x-b||^2+lambda*||x||_1'
        constants.update({'lambda': problem.lam, 'mu_smooth': float(np.min(problem.a**2))})
    else:
        arrays = {'target': problem.target.tolist()}
        family, objective = 'simplex-quadratic', 'f(x)=0.5*||x-target||^2; x>=0, sum(x)=1'
        constants['curvature'] = problem.curvature_upper_bound
    arrays['x0'] = starts[0].tolist()
    error = starts[0]-problem.x_star
    constants['radius_squared'] = float(error @ error)
    return {
        'kind': 'canonical-fixed-instance', 'topic': slug, 'family': family,
        'source_url': SOURCE_LINKS[slug], 'selected_claim': STORIES[slug].claim,
        'objective': objective, 'dimension': problem.dim,
        'sampling': 'deterministic formula; no random seed', 'seed': None,
        'budget': budget, 'constants': constants, 'method_parameters': parameters,
        'inputs': arrays, 'input_sha256': input_digest(arrays),
        'input_hash_format': 'sorted names + NUL + compact shape JSON + NUL + little-endian float64 C-order bytes',
        'optimizer': problem.x_star.tolist(), 'f_star': float(problem.f_star),
        'runs': {method: {'updates': len(t.iterates)-1,
                         'termination': t.termination or 'fixed_budget',
                         'true_residual_norm': t.residual_norm} for method, t in runs.items()},
        'scope': 'one constructed illustration; not a paper figure, sampled breadth or theorem proof',
    }


def caption_lines(instance):
    """Short English context also stays visible in a standalone SVG."""
    c = instance['constants']
    names = {'mu': 'μ', 'lambda': 'λ', 'mu_smooth': 'μ(smooth)',
             'condition_number': 'κ', 'radius_squared': 'R²', 'curvature': 'C_f'}
    constants = ', '.join(f'{names.get(k, k)}={v:.6g}' for k, v in c.items() if v is not None)
    if c.get('mu') == 0:
        constants += ', kappa undefined (mu=0)'
    start = instance['inputs']['x0']
    start_text = 'zero vector' if not any(start) else ('e1' if start == [1.]+[0.]*(len(start)-1) else 'recorded vector')
    runs = '; '.join(f'{m}: {r["updates"]} updates, {r["termination"]}' for m, r in instance['runs'].items())
    methods = []
    for method, parameters in instance['method_parameters'].items():
        settings = ', '.join(k+'='+ (f'{v:.6g}' if isinstance(v, (int, float)) else v)
                             for k, v in parameters.items())
        methods.append(method+': '+settings)
    return ['CANONICAL ILLUSTRATION · '+instance['family']+' · n='+str(instance['dimension']),
            instance['objective'], constants,
            f'x0={start_text}; budget={instance["budget"]}; deterministic, no seed', runs,
            *methods]


CSS = '''.instance-context{border:1px solid #d7e2ed;border-radius:14px;background:#f3f7fb;padding:16px;margin:18px 0;min-width:0}
.instance-context h3{font-size:15px;margin:0 0 10px}.instance-context p{font-size:12px;line-height:1.65;margin:5px 0;overflow-wrap:anywhere}
.instance-context pre{font-size:11px;max-height:360px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere}
.instance-context summary{font-size:13px}.instance-context code{overflow-wrap:anywhere}'''


def context_html(instance, *, bilingual=True):
    label = bi if bilingual else lambda ko, en: escape(en)
    body = '<aside class="instance-context" data-instance="'+escape(instance['topic'])+'"><h3>'
    body += label('이 곡선을 만든 실제 문제', 'The actual instance behind this curve')+'</h3>'
    for line in caption_lines(instance):
        body += '<p>'+escape(line)+'</p>'
    body += '<p>'+label('아래는 계산에 사용한 입력과 방법 설정입니다. 무작위 표본이나 원 논문 그림의 재현이 아닙니다.',
        'Inputs and method settings below come from this calculation. This is neither a random sample nor an original-paper figure reproduction.')+'</p>'
    body += '<details><summary>'+label('전체 입력·방법 설정·입력 해시', 'Full inputs, method settings and input hash')+'</summary><pre>'
    body += escape(json.dumps(instance, indent=2, ensure_ascii=False, allow_nan=False))+'</pre></details></aside>'
    return body
