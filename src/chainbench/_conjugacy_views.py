"""Actual metric paths and unit-direction comparisons, without another solver."""
from __future__ import annotations

import math
from html import escape

from ._pages import bi

COLORS = {'sd': '#bc541d', 'cg': '#176b91'}


def _text(x, y, label, size=12, anchor='start'):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="#334155" '
            f'text-anchor="{anchor}">{escape(label)}</text>')


def _open(label, kind):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 550" '
            f'data-metric-view="{kind}" role="img" aria-label="{label}">'
            '<rect width="560" height="550" rx="16" fill="#fbfaf7"/>')


def metric_path_svg(case):
    """Equal scales in z1,z2; every point is saved T(x-x*)."""
    parts = [_open('Same computed paths in z = A^(1/2)(x-x*); equal scales', 'path'),
             _text(28, 28, 'Same iterates · circular level sets', 17)]
    parts.append('<rect x="70" y="46" width="420" height="420" fill="white" stroke="#d6d1c7"/>')
    for level in (.5, 2, 5, 10, 20, 40, 80):
        radius = 15*math.sqrt(2*level)
        parts.append(f'<circle cx="280" cy="256" r="{radius:.3f}" fill="none" stroke="#d0d5d7">'
                     f'<title>f(x)−f* = {level:g}</title></circle>')
    for method, run in case['runs'].items():
        points = [(280+15*r['metric_coordinates'][0], 256-15*r['metric_coordinates'][1])
                  for r in run['rows']]
        encoded = '|'.join(f'{x:.3f},{y:.3f}' for x, y in points)
        dash = ' stroke-dasharray="7 4"' if method == 'cg' else ''
        parts.append(f'<polyline data-method="{method}" data-points="{encoded}" '
                     f'points="{encoded.replace("|", " ")}" fill="none" stroke="{COLORS[method]}" '
                     f'stroke-width="3"{dash}/>')
        x, y = points[-1]
        parts.append(f'<circle data-method="{method}" data-points="{encoded}" '
                     f'cx="{x:.3f}" cy="{y:.3f}" r="6" fill="{COLORS[method]}" '
                     'stroke="white" stroke-width="2"/>')
    parts.append(_text(291, 277, 'z* = 0'))
    for value in (-14, -7, 0, 7, 14):
        parts.append(_text(280+15*value, 489, str(value), anchor='middle'))
        parts.append(_text(58, 260-15*value, str(value), anchor='end'))
    parts.extend([_text(280, 514, 'z₁', 15, 'middle'), _text(27, 260, 'z₂', 15),
                  _text(28, 539, 'z = T(x−x*) · TᵀT = A · same objective values', 12), '</svg>'])
    return ''.join(parts)


def direction_svg(case):
    parts = [_open('Previous and current displacement; unit lengths in each metric', 'directions'),
             _text(28, 28, 'Which inner product makes a right angle?', 17)]
    for i, method in enumerate(('sd', 'cg')):
        pair = case['runs'][method]['rows'][-1]['step_pair']
        for j, metric in enumerate(('euclidean', 'a')):
            cx, cy = 150+260*j, 159+229*i
            parts.append(_text(cx, cy-91, method.upper()+' · '+('x coordinates' if j == 0 else 'T coordinates'),
                               14, 'middle'))
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="68" fill="white" stroke="#d0d5d7"/>')
            parts.append(f'<path d="M{cx-73} {cy}H{cx+73} M{cx} {cy-73}V{cy+73}" '
                         'stroke="#d0d5d7" fill="none"/>')
            for name in ('previous', 'current'):
                key = ('transformed_' if j else '')+name
                vector = pair[key] if pair else [0., 0.]
                norm = math.hypot(*vector)
                x, y = (cx+68*vector[0]/norm, cy-68*vector[1]/norm) if norm else (cx, cy)
                dash = ' stroke-dasharray="5 3"' if name == 'previous' else ''
                attrs = f'data-direction="{method}-{metric}-{name}" data-origin="{cx},{cy}"'
                parts.append(f'<line {attrs} x1="{cx}" y1="{cy}" x2="{x:.3f}" y2="{y:.3f}" '
                             f'stroke="{COLORS[method]}" stroke-width="3"{dash}/>')
                parts.append(f'<circle {attrs} cx="{x:.3f}" cy="{y:.3f}" r="4" '
                             f'fill="{COLORS[method]}" visibility="{"visible" if norm else "hidden"}"/>')
            value = pair['cos_'+metric] if pair else None
            label = 'pair unavailable' if value is None else f'cos = {value:.3e}'
            parts.append(f'<text x="{cx}" y="{cy+91}" font-size="12" text-anchor="middle" '
                         f'fill="#334155" data-cosine="{method}-{metric}">{label}</text>')
    parts.extend([_text(28, 514, 'Dashed: previous step · solid: current step', 12),
                  _text(28, 539, 'Each vector normalized in its own view · cos = 0 means 90°', 11), '</svg>'])
    return ''.join(parts)


def metric_section(case):
    body = '<details class="metric-details" open><summary>'+bi(
        '타원을 원으로: 같은 걸음을 다른 내적으로 보기',
        'From ellipses to circles: the same steps in another inner product')+'</summary>'
    body += '<p>'+bi(
        '왼쪽은 z=T(x−x*)로 변환한 실제 경로입니다. 오른쪽은 최근 두 걸음을 같은 원점에서 그립니다. 각 화살선의 길이를 1로 바꿔 각도만 비교합니다. cos=0이면 직각입니다.',
        'Left: actual paths transformed by z=T(x−x*). Right: the last two completed steps share an origin. Each vector is scaled to unit length to compare angles. cos=0 means a right angle.')+'</p>'
    body += '<div class="geometry">'+metric_path_svg(case)+direction_svg(case)+'</div>'
    body += '<p class="small">'+bi(
        'SD는 x 좌표에서 연속 걸음이 직교하고, CG는 T 좌표에서 직교합니다(정확한 산술). 두 걸음이 없으면 각도를 만들지 않습니다. 작은 걸음의 뺄셈은 반올림 오차에 민감하며, 표시값을 0으로 보정하지 않습니다.',
        'Successive SD steps are orthogonal in x; CG steps are orthogonal in T coordinates (exact arithmetic). No pair is invented before two updates. Tiny-step subtraction is sensitive to rounding; observed cosines are not forced to zero.')+'</p>'
    body += '<details><summary>'+bi('모든 걸음의 내적과 각도 수치', 'Every displacement product and cosine')+'</summary>'
    body += '<div class="scroll"><table><thead><tr><th>method</th><th>k</th><th>uᵀv</th>'
    body += '<th>uᵀAv</th><th>cos₂</th><th>cosA</th></tr></thead><tbody>'
    for method, run in case['runs'].items():
        for row in run['rows']:
            body += f'<tr><td>{method}</td><td>{row["iteration"]}</td>'
            pair = row['step_pair']
            for field in ('euclidean_dot', 'a_dot', 'cos_euclidean', 'cos_a'):
                value = pair[field] if pair else None
                body += '<td>'+('—' if value is None else f'{value:.6g}')+'</td>'
            body += '</tr>'
    return body+'</tbody></table></div></details></details>'
