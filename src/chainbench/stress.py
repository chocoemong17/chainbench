"""Inspectable finite stress samples; unresolved measurements stay in the record."""
from __future__ import annotations

import json
import math
import platform
from html import escape

import numpy as np

from . import __version__
from ._pages import bi, evidence, page
from .learning import LESSONS
from .reporting import SOURCE_LINKS
from .stress_cases import DIMENSIONS, SAMPLER, TOPICS, trial, validate_seed
from .visuals import ChartSpec, LineSeries, render_line_chart

MAX_TRIALS = 64


def _environment():
    return {'chainbench': __version__, 'numpy': np.__version__, 'python': platform.python_version()}


def _source(topic):
    return {'selected_reference': SOURCE_LINKS[topic],
            'implemented_recurrence': LESSONS[topic]['recurrence'],
            'assumptions': LESSONS[topic]['assumptions'][1],
            'scope': LESSONS[topic]['limit'][1],
            'implementation_source': SOURCE_LINKS['beck-teboulle-2009']
            if topic in ('gd-baseline', 'nesterov-1983', 'ista-vs-fista') else SOURCE_LINKS[topic]}


def _context_html(topic):
    lesson = LESSONS[topic]
    source = _source(topic)
    return ('<section><h2>'+escape(lesson['name'])+'</h2><p>'+bi(*lesson['mechanism'])
            +'</p><p>'+bi(*lesson['assumptions'])+'</p><pre>'+escape(lesson['recurrence'])
            +'</pre><p class="small">'+bi(*lesson['limit'])+'</p><a href="'
            +source['implementation_source']+'">'+bi('실제 갱신식의 문헌 출처', 'Source of the implemented recurrence')+'</a></section>')


def run_stress_case(topic: str, seed: int = 0) -> dict:
    return {'kind': 'chainbench.stress-case', 'schema_version': 2, 'sampler': SAMPLER,
            'topic': topic, 'case': trial(topic, seed), 'source': _source(topic), 'environment': _environment()}


def run_stress(topic: str, trials: int = 24, seed: int = 0) -> dict:
    if topic not in TOPICS:
        raise ValueError('unknown stress topic')
    validate_seed(seed)
    if type(trials) is not int or not 2 <= trials <= MAX_TRIALS:
        raise ValueError(f'trials must be an integer between 2 and {MAX_TRIALS}')
    validate_seed(seed+trials-1)
    rows = [trial(topic, seed+i) for i in range(trials)]
    threshold = rows[0]['threshold']
    if any(r['threshold'] != threshold for r in rows):
        raise ValueError('stress trials disagree on threshold semantics')
    measured = [(i, r) for i, r in enumerate(rows) if r['metric'] is not None]
    for r in rows:
        if (r['status'] == 'unresolved') != (r['metric'] is None):
            raise ValueError('stress measurement status disagrees')
    metrics = np.asarray([r['metric'] for _, r in measured], dtype=float)
    if not np.all(np.isfinite(metrics)) or np.any(metrics < 0):
        raise FloatingPointError('invalid stress metric')
    summary = {
        'min': float(np.min(metrics)) if metrics.size else None,
        'median': float(np.median(metrics)) if metrics.size else None,
        'p90': float(np.quantile(metrics, .9)) if metrics.size else None,
        'max': float(np.max(metrics)) if metrics.size else None,
        'unique_instances': len({r['instance_sha256'] for r in rows}),
        'measured': len(measured), 'unresolved': trials-len(measured), 'trials': trials,
    }
    if threshold is not None:
        summary['within_threshold'] = int(np.count_nonzero(metrics <= threshold+1e-10))
        summary['above_threshold'] = len(measured)-summary['within_threshold']
    ranked = sorted(measured, key=lambda pair: (pair[1]['metric'], pair[1]['seed']))
    selected = {}
    if ranked:
        for name, quantile in (('median-ranked', .5), ('p90-ranked', .9), ('maximum-observed', 1.)):
            rank = max(1, math.ceil(quantile*len(ranked)))
            i, row = ranked[rank-1]
            selected[name] = {'trial': i+1, 'seed': row['seed'], 'metric': row['metric'], 'rank': rank}
    result = {
        'kind': 'chainbench.stress', 'schema_version': 2, 'sampler': SAMPLER,
        'topic': topic, 'seed': seed, 'trials': trials, 'threshold': threshold,
        'summary': summary, 'rows': rows, 'selected': selected,
        'selection_rule': 'nearest rank ceil(q*n) among measured cases, ties by seed; no omissions',
        'sampling': {'dimensions': list(DIMENSIONS),
                     'design': 'seed%4 selects dimension; (seed//4)%2 rotation; (seed//8)%2 start',
                     'coverage': '16 consecutive seeds cover all dimension/rotation/start strata for quadratics',
                     'within_strata': 'PCG64 draws spectra, reference points and L; LASSO draws a,b,lambda; simplex draws target',
                     'limits': 'diagonal LASSO and simplex have no rotation stratum; smooth tests keep kappa=1e5'},
        'input_hash_encoding': 'sorted named arrays, ASCII name+NUL, JSON shape+NUL, little-endian float64 bytes',
        'environment': _environment(), 'source': _source(topic),
        'notice': 'Finite synthetic sampling is not representative real data, a theorem proof or a worst-case certificate. Unresolved ratios remain visible and excluded from measured-only quantiles.',
    }
    json.dumps(result, allow_nan=False)
    return result


def _number(value):
    return '—' if value is None else f'{value:.5g}'


def _stress_chart(result):
    rows = [(i, r['metric']) for i, r in enumerate(result['rows'], 1) if r['metric'] is not None]
    if not rows:
        return '<p class="callout caution">' + bi('측정 가능한 비율이 없어 분포 곡선을 그리지 않습니다.',
            'No resolved ratios: there is no measured distribution to plot.') + '</p>'
    x, y = zip(*rows)
    series = [LineSeries('resolved metric (unresolved omitted)', x, y, 'samples')]
    if result['threshold'] is not None:
        series.append(LineSeries('threshold', (1, result['trials']),
                                 (result['threshold'], result['threshold']), 'bound'))
    label = {'polyak-1964': 'relative tail deviation from rho',
             'hestenes-stiefel-1952': 'max energy error / bound',
             'rockafellar-1976': 'max error ratio / bound',
             'ista-vs-fista': 'final FISTA gap / ISTA gap'}.get(result['topic'], 'max objective gap / bound')
    return render_line_chart(ChartSpec('Measured ratios across declared instances', 'trial index',
                                       label, tuple(series), 'linear'))


def _case_html(topic, row):
    body = '<div class="case-data"><p class="formula">seed=' + escape(str(row['seed']))
    body += ' · n=' + escape(str(row['dim'])) + ' · ' + escape(row['orientation'])
    body += ' · start=' + escape(row['start_kind']) + ' · budget=' + str(row['steps']) + '\n'
    body += escape(', '.join(f'{key}={_number(value)}' for key, value in row['parameters'].items()))+'</p>'
    body += '<p><strong>' + escape(row['measurement']['definition']) + '</strong>: ' + _number(row['metric'])+'</p>'
    if row['reason']:
        body += '<p class="callout caution">UNRESOLVED · ' + escape(row['reason']) + '</p>'
    series = tuple(LineSeries(s['label'], tuple(s['iterations']), tuple(s['values']), s['role'])
                   for s in row['curve']['series'] if s['iterations'])
    if series:
        body += '<div class="plot">'+render_line_chart(ChartSpec(
            f'{topic} · seed {row["seed"]}', 'completed updates k', row['curve']['units'],
            series, row['curve']['scale']))+'</div>'
    else:
        body += '<p>'+bi('바닥값 기준을 넘는 비율 표본이 없습니다.', 'No ratio samples exceed the denominator floor.')+'</p>'
    if row['evidence_kind'] == 'empirical':
        body += '<p class="small">'+bi('마지막 유효 비율 최대 20개의 중앙값과 ρ를 비교한 경험적 회귀 통계입니다. 8%는 정리의 보장이 아닙니다.',
            'This empirical regression statistic compares the median of up to the last 20 valid ratios with rho. The 8% threshold is not a theorem guarantee.')+'</p>'
    elif row['evidence_kind'] == 'informational':
        body += '<p class="small">'+bi('같은 반복 예산의 최종 gap 비율입니다. 통과/실패 기준과 보편적 우열 주장은 없습니다.',
            'The ratio compares final gaps at equal iteration budgets. It has no pass/fail threshold or universal ranking claim.')+'</p>'
    body += '<details><summary>'+bi('모든 반복점·실제 입력·측정 규칙', 'Every iterate, actual input and measurement rule')+'</summary>'
    body += '<div class="scroll"><table><tr><th>method</th><th>k</th><th>gap</th><th>x</th></tr>'
    for name, run in row['runs'].items():
        for k, (x, gap) in enumerate(zip(run['iterates'], run['gaps'])):
            body += f'<tr><td>{escape(name)}</td><td>{k}</td><td>{gap:.6g}</td>'
            body += '<td><details><summary>'+bi('좌표', 'Coordinates')+'</summary><code>'
            body += escape(json.dumps(x))+'</code></details></td></tr>'
    body += '</table></div><pre>'+escape(json.dumps({'inputs': row['inputs'],
             'measurement': row['measurement'], 'instance_sha256': row['instance_sha256']},
             indent=2, allow_nan=False))+'</pre></details>'
    body += '<p class="small">input SHA-256: <code>'+escape(row['instance_sha256'])+'</code></p>'
    body += '<pre>python -m chainbench stress-case '+escape(topic)+' --seed '+escape(str(row['seed']))
    body += ' --lang ko --output case.html</pre></div>'
    return body


def stress_case_html(result, lang='en'):
    if result.get('kind') != 'chainbench.stress-case' or result.get('schema_version') != 2:
        raise ValueError('not a schema-2 stress case')
    body = '<div class="evidence-banner">'+bi('버전 2 생성기의 개별 합성 표본입니다. 대표 사례나 최악 사례로 인증된 것이 아닙니다.',
        'One synthetic sample from sampler v2, not a certified representative or worst case.')+'</div>'
    body += _context_html(result['topic'])+'<section>'+_case_html(result['topic'], result['case'])+'</section>'+evidence(result, 'stress-case.json')
    return page('One sampled instance, fully inspectable',
                bi('요약 통계를 실제 입력과 수렴 곡선으로 되짚습니다.',
                   'Trace a summary measurement back to its actual input and convergence curve.'), body, lang=lang)


SCRIPT = '''document.querySelectorAll('[data-case-link]').forEach(a=>a.addEventListener('click',()=>{
 const panel=document.getElementById(a.dataset.caseLink);if(panel)panel.open=true;
}));'''


def stress_html(result: dict, lang: str = 'en') -> str:
    if result.get('kind') != 'chainbench.stress' or result.get('schema_version') != 2:
        raise ValueError('not a schema-2 stress report')
    topic, s, threshold = result['topic'], result['summary'], result['threshold']
    if threshold is None:
        verdict = bi('이 항목은 통과/실패 정리가 아닌 설명용 분포입니다.',
                     'This topic is descriptive; there is no theorem pass/fail threshold.')
    else:
        label = 'empirical regression threshold' if topic == 'polyak-1964' else 'selected theoretical envelope'
        verdict = bi(f'전체 {s["trials"]}개: 기준 안 {s["within_threshold"]}개 · 기준 밖 {s["above_threshold"]}개 · 측정 불가 {s["unresolved"]}개.',
                     f'{s["trials"]} total: {s["within_threshold"]} within the {label}, {s["above_threshold"]} above, {s["unresolved"]} unresolved.')
    cards = '<div class="metric-grid">'
    for title, value in (('median · measured only', s['median']), ('p90 · measured only', s['p90']),
                         ('maximum observed', s['max']), ('unresolved / total', None)):
        text = f'{s["unresolved"]} / {s["trials"]}' if value is None and title.startswith('unresolved') else _number(value)
        cards += '<div class="metric"><span>'+title+'</span><strong>'+text+'</strong></div>'
    cards += '</div>'
    body = '<div class="evidence-banner"><span class="evidence-tag">MULTI-INSTANCE STRESS</span>'
    body += bi('모든 연속 seed의 실제 입력·경로를 보존합니다. 측정 불가 표본도 빠뜨리지 않습니다. 유한 합성 표본이며 정리의 증명은 아닙니다.',
               'Every consecutive seed retains its actual inputs and paths, including unresolved cases. Finite synthetic sampling is not proof.')+'</div>'+cards+_context_html(topic)
    body += '<section><h2>'+bi('분포에서 개별 곡선으로', 'From the distribution to an individual curve')+'</h2><p>'+verdict+'</p>'
    body += '<div class="plot">'+_stress_chart(result)+'</div><div class="cards">'
    for label, selected in result['selected'].items():
        case_id = 'sample-'+str(selected['trial'])
        body += f'<a class="card" href="#{case_id}" data-case-link="{case_id}"><strong>{label}</strong>'
        body += f'<span>seed {selected["seed"]} · trial {selected["trial"]} · metric {selected["metric"]:.5g}</span></a>'
    body += '</div><p class="small">'+bi('카드는 측정 가능 표본의 nearest rank ceil(q·n)를 선택합니다(동률은 seed 순). 표시된 median·p90 요약값은 보간 분위수이므로 카드의 실제 관측값과 다를 수 있습니다. 최댓값은 관측 최댓값이며 인증된 최악 사례가 아닙니다.',
        'Cards use nearest rank ceil(q·n) among measured samples, ties by seed. The summary median/p90 are interpolated quantiles and may differ from the selected actual observation. Maximum observed is not a certified worst case.')+'</p></section>'
    body += '<section><h2>'+bi('생성 규칙과 실제 범위', 'Sampling design and actual coverage')+'</h2><p>'
    body += bi('차원은 seed % 4로 6·12·24·40을 순환합니다. 이차함수는 다음 비트로 대각/회전과 영점/임의 시작을 선택합니다. 16개 연속 seed는 전체 조합을 포함합니다. LASSO는 대각 구조를 유지하며 심플렉스 시작점은 실행 가능합니다.',
        'Dimensions cycle through 6, 12, 24, 40 by seed % 4. Quadratic orientation and start use the next bits; 16 consecutive seeds cover all strata. LASSO stays diagonal and simplex starts remain feasible.')+'</p>'
    body += '<p class="small">'+bi('버전 2 생성기입니다. v0.5.0의 동일 seed와 입력이 다를 수 있습니다. 실제 배열·시작점·갱신 예산을 해시하며, JSON에 환경과 생성기 버전을 남깁니다. 부드러운 볼록 검사에서는 조건수 10⁵를 고정합니다.',
        'Sampler v2 changes the input associated with a v0.5.0 seed. Actual arrays, start and update budget are hashed; JSON records environment and sampler version. Smooth convex checks retain condition number 10^5.')+'</p>'
    body += '<div class="scroll"><table><tr><th>trial</th><th>seed</th><th>n</th><th>orientation / start</th><th>metric</th><th>status</th></tr>'
    for i, row in enumerate(result['rows'], 1):
        body += f'<tr><td><a href="#sample-{i}" data-case-link="sample-{i}">{i}</a></td>'
        body += f'<td>{row["seed"]}</td><td>{row["dim"]}</td><td>{escape(row["orientation"])} / {escape(row["start_kind"])}</td>'
        body += f'<td>{_number(row["metric"])}</td><td>{escape(row["status"])}</td></tr>'
    body += '</table></div></section><section><h2>'+bi('전체 표본 열어보기', 'Open every sampled instance')+'</h2>'
    for i, row in enumerate(result['rows'], 1):
        body += f'<details class="stress-case" id="sample-{i}"><summary>#{i} · seed {row["seed"]} · n={row["dim"]} · '
        body += f'{escape(row["status"])} · {_number(row["metric"])}</summary>'+_case_html(topic, row)+'</details>'
    body += '</section><p class="callout caution">'+bi('합성 표본의 범위를 넓혔지만 실제 데이터의 대표성이나 보편적 성능 순위를 주장하지 않습니다. 기준 밖 또는 측정 불가인 표본을 성공으로 세지 않습니다.',
        'This broadens declared synthetic coverage, not real-data representativeness or universal performance rankings. Above-threshold and unresolved cases are not counted as successes.')+'</p>'
    body += evidence(result, f'stress-{topic}.json')+'<script>'+SCRIPT+'</script>'
    return page('Every sample has a story',
        bi('분포 · 분위수 사례 · 개별 수렴 곡선 · 보존된 입력',
           'Distribution · ranked cases · individual convergence curves · retained inputs'), body, lang=lang)
