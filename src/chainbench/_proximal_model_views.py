"""Display the upper model and actual objective on the same recorded step line."""
from __future__ import annotations

from html import escape

from ._pages import bi


def _frames(case, function):
    return {method: [function(stage['upper_model']) for stage in run['stages']]
            for method, run in case['runs'].items()}


def _scale(model):
    maximum = max(*model['model_gap'], model['previous_gap'])
    return 1.1*maximum if maximum else 1.


def _xy(model, t, value):
    return 86+(t+.25)*460/1.5, 292-value/_scale(model)*210


def _data(frames):
    return ' '.join(f'data-{method}="{escape("|".join(values), quote=True)}"'
                    for method, values in frames.items())


def model_svg(case):
    body = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 380" '
            'role="img" aria-label="Actual objective and proximal upper model on the update line">',
            '<rect width="620" height="380" rx="16" fill="#fbfaf7"/>',
            '<text x="20" y="27" font-size="15" fill="#172238" data-model-step="">FISTA · k=0 → 1 · actual update line</text>',
            '<text x="20" y="49" font-size="11" fill="#334155">F−F* black · Q_L−F* purple dashed · previous F(x_k)−F* grey</text>',
            '<text x="20" y="66" font-size="11" fill="#334155">u(t) = y + t(x_next − y) · L=9 · λ='+str(case['lambda'])+'</text>',
            '<rect x="86" y="82" width="460" height="210" fill="white" stroke="#d4dce4"/>']
    for fraction in (0., .5, 1.):
        y = 292-210*fraction
        frames = _frames(case, lambda model: f'{fraction*_scale(model):.3g}')
        body.append(f'<line x1="86" x2="546" y1="{y}" y2="{y}" stroke="#e5eaf0"/>')
        body.append(f'<text x="78" y="{y+4}" font-size="11" text-anchor="end" '
                    f'data-model-text="" {_data(frames)}>{frames["fista"][0]}</text>')
    for t in (-.25, 0., .5, 1., 1.25):
        x = 86+(t+.25)*460/1.5
        body.append(f'<line x1="{x}" x2="{x}" y1="82" y2="292" stroke="#e5eaf0"/>')
        body.append(f'<text x="{x}" y="312" font-size="11" text-anchor="middle">{t:g}</text>')
    for key, color, dash in [('model_gap', '#8454a6', '7 4'), ('objective_gap', '#172238', 'none')]:
        frames = _frames(case, lambda model: ' '.join(
            ','.join(f'{v:.3f}' for v in _xy(model, t, gap))
            for t, gap in zip(model['parameter'], model[key])))
        body.append(f'<polyline data-model-points="{key}" {_data(frames)} points="{frames["fista"][0]}" '
                    f'fill="none" stroke="{color}" stroke-width="2.4" stroke-dasharray="{dash}"/>')
    frames = _frames(case, lambda m: ','.join([f'{_xy(m, 0, m["previous_gap"])[1]:.3f}']*2))
    y = frames['fista'][0].split(',')[0]
    body.append(f'<line data-model-previous="" data-prox-attrs="y1,y2" {_data(frames)} '
                f'x1="86" x2="546" y1="{y}" y2="{y}" stroke="#768495" stroke-dasharray="3 4"/>')
    for key, t, color, fill in [('anchor_gap', 0, '#8454a6', '#8454a6'),
                               ('model_next_gap', 1, '#ce8b20', 'white'),
                               ('next_gap', 1, '#13856a', '#13856a')]:
        frames = _frames(case, lambda model: ','.join(f'{v:.3f}' for v in _xy(model, t, model[key])))
        x, y = frames['fista'][0].split(',')
        body.append(f'<circle data-model-marker="{key}" data-prox-attrs="cx,cy" {_data(frames)} '
                    f'cx="{x}" cy="{y}" r="4.5" stroke="{color}" fill="{fill}" stroke-width="2"/>')
    body.extend(['<text x="316" y="337" font-size="12" text-anchor="middle">t=0: y · t=1: actual next iterate</text>',
                 '<text x="20" y="360" font-size="11" fill="#475569">Linear height scale changes with the selected step; grey line is a value reference.</text></svg>'])
    return ''.join(body)


def model_html(case):
    first = case['runs']['fista']['stages'][0]['upper_model']
    body = '<section class="prox-model"><h3>'+bi('다음 점이 최소화하는 곡선', 'The curve minimized by the next point')+'</h3>'
    body += '<p>'+bi('현재 단계의 y와 다음 점을 잇는 직선 위에서, 실제 목적함수 F와 근사함수 Q_L을 같은 높이 기준으로 비교합니다. 보라색 곡선은 y에서 F에 닿으며 모든 점에서 F 이상입니다.',
                    'On the line through this step’s y and next iterate, compare the actual objective F with its model Q_L using the same height reference. The purple curve touches F at y and stays above it.')+'</p>'
    body += '<div class="prox-model-figure">'+model_svg(case)+'</div>'
    body += '<p class="formula">Q_L(u,y)=f(y)+∇f(y)ᵀ(u−y)+(L/2)||u−y||²+g(u)<br>'
    body += 'F(x_next) ≤ Q_L(x_next,y) ≤ Q_L(y,y) = F(y)</p>'
    body += '<p class="small">'+bi('이 이차 문제에서는 Q_L(u,y)−F(u)=4(u₁−y₁)²입니다. 이는 L=9가 두 곡률 1,9 이상이기 때문입니다.',
        'For this quadratic, Q_L(u,y)−F(u)=4(u₁−y₁)² because L=9 bounds both curvatures 1 and 9.')
    body += ' <a href="https://www.tau.ac.il/~becka/FISTA.pdf">Beck–Teboulle: Eqs. (2.5)–(2.7), p.189 / PDF 7; Remark 3.1, p.191 / PDF 9</a></p>'
    body += '<p class="prox-model-values" data-model-values>'
    body += f'F(x_next)−F*={first["next_gap"]:.6g} · Q_L(x_next,y)−F*={first["model_next_gap"]:.6g} · F(y)−F*={first["anchor_gap"]:.6g}</p>'
    body += '<p data-model-reference>'+bi('ISTA는 y=x_k이므로 이 관계가 이전 목적값과의 비교입니다. FISTA에서는 외삽점 y가 다르므로 F(x_k)보다 감소한다는 보장은 여기서 나오지 않습니다.',
        'ISTA has y=x_k, so this compares with the previous objective. FISTA can use a different extrapolated y; this relation does not ensure descent from F(x_k).')+'</p>'
    increases = [k for k, s in enumerate(case['runs']['fista']['stages'])
                 if s['upper_model']['next_gap'] > s['upper_model']['previous_gap']+1e-12]
    if increases:
        body += f'<button type="button" class="prox-increase" data-model-increase="{increases[0]}">'+bi(
            '이 사례에서 처음 기록된 FISTA 목적값 증가 보기', 'Inspect this case’s first recorded FISTA objective increase')+'</button>'
        body += '<p class="small">'+bi('이동 기준: 저장된 순서에서 gap 증가가 10⁻¹²를 넘는 첫 단계. 아래 표에는 그보다 작은 변화도 그대로 남깁니다.',
            'Jump rule: the first saved step whose gap increases by more than 10⁻¹². Smaller changes remain in the table.')+'</p>'
    body += '<p class="small">'+bi('가로축 t는 갱신 횟수가 아니라 한 직선의 위치입니다. y→다음 점의 바깥도 일부 표시하며, 이 선은 추가 최적화 경로가 아닙니다. 세로축은 F*만큼 공통 이동한 선형 축이며 단계마다 범위를 다시 잡습니다. 회색 선은 이전 목적값의 높이일 뿐 이전 점의 위치가 아닙니다.',
        'The horizontal t locates points on one line; it is not an iteration count. The range extends beyond y and the next point and is not another optimization trajectory. Both heights are shifted by F* on a linear scale fitted per step. The grey line marks the previous objective value, not the location of the previous point.')+'</p>'
    body += '<details><summary>'+bi('모든 단계의 근사함수와 비교 기준', 'Upper model and reference values at every step')+'</summary><div class="scroll"><table><tr><th>method / k</th><th>F(x_k)−F*</th><th>F(y)−F*</th><th>Q_L(next,y)−F*</th><th>F(next)−F*</th><th>Q−F at next</th><th>y = next</th></tr>'
    for method, run in case['runs'].items():
        for k, s in enumerate(run['stages']):
            m = s['upper_model']
            body += f'<tr><td>{method.upper()} / {k}</td>'
            body += ''.join(f'<td>{m[key]:.8g}</td>' for key in ('previous_gap', 'anchor_gap', 'model_next_gap', 'next_gap', 'model_excess_next'))
            body += f'<td>{str(m["zero_step"]).lower()}</td></tr>'
    return body+'</table></div></details></section>'
