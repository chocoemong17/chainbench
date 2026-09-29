"""Offline views of the published example and its explicitly separate variations."""
from __future__ import annotations

import json
from html import escape

import numpy as np

from ._pages import bi, evidence, page
from .reproductions import SOURCE_URL
from .visuals import ChartSpec, LineSeries, render_line_chart

COLORS = {"sd": "#bc541d", "cg": "#176b91"}
LEVELS = (.5, 2., 5., 10., 20., 40., 80., 140., 220.)
CSS = """
.repro svg{display:block;width:100%;height:auto}.repro .plot svg{min-width:640px}
.repro .geometry{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.repro .geometry figure{margin:0;min-width:0}.repro figcaption{font-size:13px;color:#56657b}
.repro .legend{display:flex;gap:18px;flex-wrap:wrap;font-size:14px;font-weight:650}
.repro .legend span:first-child{color:#bc541d}.repro .legend span:last-child{color:#176b91}
.repro .readout{background:#eff4f8;border-radius:12px;padding:12px 16px;font-size:14px;
font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.repro .readout p{margin:4px 0}
.repro .player{display:none;gap:14px;align-items:center;flex-wrap:wrap;margin:18px 0}
.repro-js .repro .player{display:flex}
.repro .player input{flex:1;min-width:120px;padding:0}.repro .player label{font-weight:650}
.repro .source-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.repro details.case{border-top:1px solid #ded9cf;padding:12px 0}
.repro .formula{line-height:1.8}.repro .plot{margin-top:24px}
@media(max-width:900px){.repro .geometry,.repro .source-grid{grid-template-columns:1fr}}
@media print{.repro .player{display:none}.repro details.case{break-inside:avoid}}
"""
SCRIPT = """
(() => {
 document.documentElement.classList.add('repro-js');
 const record = JSON.parse(document.getElementById('chainbench-evidence').textContent);
 document.querySelectorAll('[data-repro-case]').forEach(panel => {
  const c = record.cases.find(c => c.id === panel.dataset.reproCase);
  const slider = panel.querySelector('input[type=range]');
  const play = panel.querySelector('[data-play]');
  let timer = null;
  const update = () => {
   const k = Number(slider.value);
   panel.querySelector('[data-step]').textContent = `k = ${k}`;
   panel.querySelectorAll('[data-points]').forEach(el => {
    const points = el.dataset.points.split('|').map(p => p.split(',').map(Number));
    const index = Math.min(k, points.length - 1);
    if(el.tagName.toLowerCase() === 'polyline')
     el.setAttribute('points', points.slice(0,index+1).map(p=>p.join(',')).join(' '));
    else {el.setAttribute('cx',points[index][0]);el.setAttribute('cy',points[index][1]);}
   });
   for(const method of ['sd','cg']) {
    const run=c.runs[method], row=run.rows[Math.min(k,run.updates)];
    const held=k>run.updates ? ' (last computed / 마지막 계산점)' : '';
    panel.querySelector(`[data-readout="${method}"]`).textContent =
     `${method.toUpperCase()} · k=${row.iteration}${held} · x=(${row.x.map(v=>v.toPrecision(5)).join(', ')})`
     + ` · f−f*=${row.gap.toExponential(3)} · ||r||₂=${row.residual_norm.toExponential(3)}`;
   }
  };
  const stop=()=>{clearInterval(timer);timer=null;play.textContent='▶';play.setAttribute('aria-pressed','false');};
  slider.addEventListener('input',()=>{stop();update();});
  play.addEventListener('click',()=>{
   if(timer){stop();return;}
   if(Number(slider.value)===Number(slider.max)) slider.value='0';
   play.textContent='Ⅱ';play.setAttribute('aria-pressed','true');update();
   timer=setInterval(()=>{if(Number(slider.value)>=Number(slider.max)){stop();return;}
    slider.value=String(Number(slider.value)+1);update();},700);
  });
  const details=panel.closest('details');
  if(details) details.addEventListener('toggle',()=>{if(!details.open) stop();});
  document.addEventListener('visibilitychange',()=>{if(document.hidden) stop();});
  update();
 });
})();
"""


def _svg_open(label: str) -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 550" '
            f'role="img" aria-label="{escape(label, quote=True)}">'
            '<rect width="560" height="550" rx="16" fill="#fbfaf7"/>')


def _text(x: float, y: float, text: str, size: int = 12, anchor: str = "start") -> str:
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" '
            f'fill="#334155" text-anchor="{anchor}">{escape(text)}</text>')


def _trajectory(case: dict, project) -> str:
    parts = []
    for method, run in case["runs"].items():
        points = [project(*row["x"], row["gap"]) for row in run["rows"]]
        encoded = "|".join(f"{x:.3f},{y:.3f}" for x, y in points)
        path = " ".join(f"{x:.3f},{y:.3f}" for x, y in points)
        dash = ' stroke-dasharray="7 4"' if method == "cg" else ""
        parts.append(f'<polyline data-method="{method}" data-points="{encoded}" '
                     f'points="{path}" fill="none" stroke="{COLORS[method]}" '
                     f'stroke-width="3"{dash}/>')
        for k, (x, y) in enumerate(points[:3]):
            parts.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="3" '
                         f'fill="{COLORS[method]}"><title>{method} k={k}</title></circle>')
        x, y = points[-1]
        parts.append(f'<circle data-method="{method}" data-points="{encoded}" '
                     f'cx="{x:.3f}" cy="{y:.3f}" r="6" fill="{COLORS[method]}" '
                     'stroke="white" stroke-width="2"/>')
    return "".join(parts)


def contour_svg(problem: dict, case: dict) -> str:
    """Equal coordinate scales preserve the visible angle of exact line search."""
    def project(x, y, z=0):
        return 70 + (x + 4) * 42, 466 - (y + 6) * 42
    clip = "clip-" + case["id"]
    parts = [_svg_open("x1 / x2 contours and computed paths; equal coordinate scales"),
             _text(28, 28, "Coordinate paths · equal aspect", 17),
             f'<defs><clipPath id="{clip}"><rect x="70" y="46" width="420" '
             'height="420"/></clipPath></defs>',
             '<rect x="70" y="46" width="420" height="420" fill="white" stroke="#d6d1c7"/>']
    eig, vec = np.linalg.eigh(np.array(problem["A"]))
    theta = np.linspace(0, 2 * np.pi, 220)
    parts.append(f'<g clip-path="url(#{clip})">')
    for level in LEVELS:
        coords = (vec @ (np.sqrt(2 * level / eig)[:, None]
                         * np.array([np.cos(theta), np.sin(theta)]))).T + problem["x_star"]
        points = " ".join(f"{project(x,y)[0]:.3f},{project(x,y)[1]:.3f}" for x, y in coords)
        parts.append(f'<polyline points="{points}" fill="none" stroke="#d0d5d7">'
                     f'<title>f(x)−f* = {level:g}</title></polyline>')
    parts.append(_trajectory(case, project))
    sx, sy = project(*case["start"])
    parts.append(f'<circle cx="{sx}" cy="{sy}" r="4" fill="#172238"/>'
                 + _text(sx - 8, sy - 12, "x₀", anchor="end"))
    sx, sy = project(*problem["x_star"])
    parts.append(_text(sx + 9, sy + 18, "x* = (2, −2)"))
    parts.append('</g>')
    for x in range(-4, 7, 2):
        sx, _ = project(x, -6)
        parts.append(_text(sx, 488, str(x), anchor="middle"))
    for y in range(-6, 5, 2):
        _, sy = project(-4, y)
        parts.append(_text(58, sy + 4, str(y), anchor="end"))
    parts.extend((_text(280, 514, "x₁", 15, "middle"), _text(27, 260, "x₂", 15),
                  _text(28, 541, "Contours: f−f* = 0.5, 2, 5, 10, 20, 40, 80, 140, 220", 11),
                  '</svg>'))
    return ''.join(parts)


def surface_svg(problem: dict, case: dict) -> str:
    """Oblique projection of the same coordinates and their actual objective gaps."""
    a = np.array(problem["A"])
    star = np.array(problem["x_star"])

    def gap(x, y):
        e = np.array([x, y]) - star
        return float(.5 * e @ a @ e)

    def project(x, y, z):
        return 280 + 21 * (x - y - 2), 449 - 10 * (x + y + 10) - 1.10 * z

    parts = [_svg_open("Projected 3D surface; x1, x2, z = objective gap f minus f star"),
             _text(28, 28, "Same paths · objective height", 17)]
    for fixed in np.linspace(-4, 6, 17):
        points = [project(fixed, y, gap(fixed, y)) for y in np.linspace(-6, 4, 40)]
        parts.append('<polyline fill="none" stroke="#ccd6dc" points="'
                     + ' '.join(f'{x:.3f},{y:.3f}' for x, y in points) + '"/>')
    for fixed in np.linspace(-6, 4, 17):
        points = [project(x, fixed, gap(x, fixed)) for x in np.linspace(-4, 6, 40)]
        parts.append('<polyline fill="none" stroke="#ccd6dc" points="'
                     + ' '.join(f'{x:.3f},{y:.3f}' for x, y in points) + '"/>')
    parts.append(_trajectory(case, project))
    origin = project(-4, -6, 0)
    for end, label, dx, dy in ((project(6, -6, 0), "x₁ = 6", 0, 22),
                               (project(-4, 4, 0), "x₂ = 4", 0, 22),
                               (project(-4, -6, 180), "f−f* = 180", 0, -12)):
        parts.append(f'<line x1="{origin[0]}" y1="{origin[1]}" x2="{end[0]}" '
                     f'y2="{end[1]}" stroke="#728391"/>')
        parts.append(_text(end[0] + dx, end[1] + dy, label, 12, "middle"))
    parts.append(_text(origin[0], origin[1] + 22, "(−4, −6, 0)", 12, "middle"))
    parts.append(_text(28, 522, "Oblique projection; z = f(x) − f* (f* = −10)", 12))
    parts.append(_text(28, 541, "Added view, not an original-paper figure; wireframe is transparent", 11))
    parts.append('</svg>')
    return ''.join(parts)


def _energy_chart(case: dict) -> str:
    series = [LineSeries(run["label"], tuple(r["iteration"] for r in run["rows"]),
                         tuple(r["energy_error"] for r in run["rows"]))
              for run in case["runs"].values()]
    series.append(LineSeries("CG envelope · Eq. (52)", tuple(range(1, len(case["cg_envelope"]))),
                             tuple(case["cg_envelope"][1:]), "bound"))
    return render_line_chart(ChartSpec("Energy error · same computed iterates",
                                      "completed updates k", "||x_k − x*||_A", tuple(series)),
                             colors=(COLORS["sd"], COLORS["cg"], "#64748b"))


def _case_view(problem: dict, case: dict, surface: bool = False) -> str:
    last = max(run["updates"] for run in case["runs"].values())
    cid = case["id"]
    body = f'<div data-repro-case="{cid}"><p class="legend">'
    body += '<span>━ SD · exact line search</span><span>┄ CG · conjugate directions</span></p>'
    body += '<div class="geometry"><figure>' + contour_svg(problem, case)
    body += '<figcaption>' + bi('같은 축척의 좌표 경로. 회색선은 같은 목적함숫값입니다.',
                               'Equal coordinate scales. Gray curves have equal objective values.')
    body += '</figcaption></figure><figure>'
    body += surface_svg(problem, case) if surface else _energy_chart(case)
    body += '<figcaption>' + bi('실제 계산된 반복점만 표시합니다. 오차는 작을수록 해에 가깝습니다.',
                               'Only computed iterates are shown. Smaller error means closer to the solution.')
    body += '</figcaption></figure></div>'
    body += (f'<div class="player"><button data-play type="button" aria-pressed="false" '
             'aria-label="Play or pause / 재생·정지">▶</button>'
             f'<label for="slider-{cid}">' + bi('반복 탐색', 'Inspect iteration') + '</label>'
             f'<input id="slider-{cid}" type="range" min="0" max="{last}" value="{last}">'
             f'<strong data-step>k = {last}</strong></div><div class="readout" aria-live="polite">')
    for method, run in case["runs"].items():
        row = run["rows"][-1]
        body += f'<p data-readout="{method}">{method.upper()} · k={run["updates"]} '
        body += f'· x={escape(str(row["x"]))} · f−f*={row["gap"]:.5g}</p>'
    body += '</div><p class="small">' + bi(
        '종료된 방법은 마지막 계산점에 머뭅니다. 반복 수는 실행 시간 비교가 아닙니다.',
        'A stopped method stays at its last computed point. Iterations are not timing measurements.')
    body += '</p>'
    if surface:
        body += '<div class="plot">' + _energy_chart(case) + '</div>'
    body += '<details><summary>' + bi('반복별 수치·종료 조건', 'Every computed iterate and termination')
    body += '</summary><div class="scroll"><table><thead><tr><th>method</th><th>k</th>'
    body += '<th>x₁</th><th>x₂</th><th>f(x)−f*</th><th>||r||₂</th></tr></thead><tbody>'
    for method, run in case["runs"].items():
        for row in run["rows"]:
            body += f'<tr><td>{method}</td><td>{row["iteration"]}</td>'
            body += ''.join(f'<td>{v:.8g}</td>' for v in (*row["x"], row["gap"], row["residual_norm"]))
            body += '</tr>'
    body += '</tbody></table></div><p>'
    body += ' · '.join(m.upper() + ': ' + (
        bi('잔차 기준 충족', 'residual tolerance reached') if r['termination'] == 'converged'
        else bi('반복 예산 소진', 'iteration budget exhausted')) + f' ({r["updates"]} updates)'
        for m, r in case["runs"].items())
    body += '</p></details><details><summary>' + bi('입력 지문', 'Input fingerprint')
    body += '</summary><code>' + case['input_sha256'] + '</code></details></div>'
    return body


def reproduction_html(result: dict, lang: str = "en") -> str:
    """Render an in-memory result. Saved-report importing is not supported."""
    if result.get("kind") != "chainbench.reproduction" or result.get("topic") != "shewchuk-1994":
        raise ValueError("not a Shewchuk reproduction result")
    json.dumps(result, allow_nan=False)
    p = result["problem"]
    original = result["cases"][0]
    body = '<style>' + CSS + '</style><div class="repro">'
    body += '<div class="evidence-banner"><span class="evidence-tag">PUBLISHED EXAMPLE</span>'
    body += bi('원 논문의 설정을 다시 계산한 경로입니다. 그림 픽셀을 복사하거나 추출한 것이 아닙니다.',
               'Recomputed paths from the published setup; no copied pixels or digitized curves.') + '</div>'
    body += '<nav><a href="#setup">01 · Setup</a><a href="#paths">02 · Paths</a>'
    body += '<a href="#mechanism">03 · Why</a><a href="#breadth">04 · All starts</a></nav>'
    body += '<section id="setup"><h2>' + bi('01 / 무엇을 재현했나', '01 / What was reproduced') + '</h2>'
    body += f'<p><a href="{SOURCE_URL}#page=14">Shewchuk (1994), Figure 8</a> · '
    body += f'<a href="{SOURCE_URL}#page=38">Figure 30</a> · Eq. (4), (10)–(12), (45)–(49)</p>'
    body += '<div class="source-grid"><div><p>' + bi(
        '최급강하법은 가장 가파른 방향을 따라 매번 최적 길이만큼 이동합니다. CG는 이전 방향의 정보를 더해 이미 해결한 방향을 되돌아가지 않도록 합니다.',
        'Steepest descent minimizes along the current downhill line. CG combines the residual with its previous direction to preserve progress in earlier directions.') + '</p>'
    body += '<p>' + bi('동일한 2차원 문제에서 두 경로가 어떻게 갈라지는지 직접 확인하세요.',
                       'Follow how the two paths diverge on the same two-dimensional problem.') + '</p></div>'
    body += '<div class="formula">f(x) = ½xᵀAx − bᵀx<br>A = [[3, 2], [2, 6]] · b = [2, −8]<br>'
    body += 'x₀ = [−2, −2] · x* = [2, −2] · f* = −10<br>n = 2 · μ = 2 · L = 7 · κ = 3.5</div></div>'
    body += '<p class="small">' + bi(
        f'최대 {result["parameters"]["steps"]}회 갱신 · 두 방법 모두 ||b−Ax||₂ ≤ 10⁻¹²||b−Ax₀||₂이면 종료 · 난수·정규화 항 없음.',
        f'Budget: {result["parameters"]["steps"]} updates · both stop at ||b−Ax||₂ ≤ 10⁻¹²||b−Ax₀||₂ · no randomness or regularizer.') + '</p>'
    body += '<p class="callout caution">' + bi(
        '독립 수치 재현: 같은 목적함수·시작점·갱신식. 축 범위는 원 그림과 같지만 등고선 간격·색상·반복 예산·종료 허용치는 여기서 명시한 설정입니다. 3D와 오차 그래프는 추가 설명입니다.',
        'Independent numerical reproduction: same objective, start and recurrences. Axis ranges match the source figures; contour levels, styling, budget and stopping tolerance are specified here. 3D and error plots are added explanations.') + '</p></section>'
    body += '<section id="paths"><h2>' + bi('02 / 같은 출발, 다른 두 번째 걸음',
                                             '02 / Same start, different second step') + '</h2>'
    body += _case_view(p, original, surface=True) + '</section>'
    body += '<section id="mechanism"><h2>' + bi('03 / 방향을 기억하는 이유',
                                                 '03 / Why remember a direction?') + '</h2><div class="deep-grid">'
    for title, ko, en in (
        ('01 · Residual → direction', 'r=b−Ax는 내려갈 방향입니다. SD는 r을 그대로 사용하고 α=(rᵀr)/(rᵀAr)로 선 위의 최솟값까지 갑니다. 고정 보폭 1/L의 GD와는 다릅니다.',
         'r=b−Ax points downhill. SD uses r and α=(rᵀr)/(rᵀAr) to minimize along that line. This is distinct from fixed-step GD at 1/L.'),
        ('02 · Direction → memory', '첫 걸음은 같습니다. 이후 CG는 d새=r새+βd이전, β=||r새||²/||r이전||²를 사용합니다. 정확한 산술에서 d이전ᵀAd새=0이 되어 이전 방향의 최소화를 보존합니다.',
         'The first step is shared. CG then uses d_new=r_new+βd_old, β=||r_new||²/||r_old||². In exact arithmetic d_oldᵀAd_new=0 preserves minimization along previous directions.'),
        ('03 · Memory → trade-off', 'SPD 선형계에서는 투영이나 전체 행렬 분해 없이 행렬–벡터 곱으로 진전할 수 있습니다. 유한 정밀도에서는 켤레성이 무너질 수 있어 실제 잔차를 확인합니다. 일반 비선형 목적함수에는 이 보장이 그대로 적용되지 않습니다.',
         'For SPD systems, matrix-vector products replace a full factorization. Finite precision can destroy conjugacy, so the implementation checks true residuals. The same guarantee does not extend to arbitrary nonlinear objectives.'),
    ):
        body += '<article><h3>' + title + '</h3><p>' + bi(ko, en) + '</p></article>'
    body += '</div><div class="formula">||eₖ||A ≤ 2ρᵏ||e₀||A · ρ = (√κ−1)/(√κ+1)<br>'
    body += '||e||A = √(eᵀAe) · f(x)−f* = ½||e||A² · Shewchuk Eq. (52)</div>'
    body += '<p>' + bi(
        '점선은 CG의 정확한 산술 상계입니다. 곡선이 점선 아래에 있다고 정리가 증명되는 것은 아닙니다. k=0은 비교에서 빼고, 수치적으로 종료한 뒤의 반복은 생성하지 않습니다.',
        'The dashed envelope is for CG in exact arithmetic. Agreement does not prove the theorem. The envelope starts at k=1; no extra iterates are invented after numerical termination.') + '</p>'
    body += '<p class="small">' + bi(
        '연결: Hestenes–Stiefel(1952)의 CG → Shewchuk(1994)의 기하 설명 → 전처리로 스펙트럼을 바꾸는 후속 학습. 이 페이지는 전처리 성능 실험을 포함하지 않습니다.',
        'Connection: Hestenes–Stiefel (1952) CG → Shewchuk (1994) geometric explanation → learning how preconditioning changes the spectrum. Preconditioner benchmarks are outside this page.') + '</p></section>'
    body += '<section id="breadth"><h2>' + bi('04 / 시작점을 바꾸면?', '04 / What if the start changes?') + '</h2>'
    body += '<p class="callout">' + bi(
        '아래 9개는 원 논문 그림이 아닌 통제된 추가 예시입니다. x₁∈{−3,0,3}, x₂∈{−4,0,3}의 모든 조합을 빠짐없이 표시합니다. A와 b는 동일합니다. 여러 차원이나 스펙트럼을 대표하는 표본은 아닙니다.',
        'These nine controlled additions are not paper figures. Every start in {−3,0,3} × {−4,0,3} is shown, without filtering. A and b stay fixed. This is not sampling across dimensions or spectra.') + '</p>'
    body += '<p>' + bi(
        '특히 (3,0)에서 오차 (1,2)는 A의 고유벡터입니다. 이때 두 방법 모두 한 걸음에 해에 도달합니다. 원문 예제의 두 걸음이 모든 시작점의 규칙은 아닙니다.',
        'At (3,0), the error (1,2) is an eigenvector of A: both methods reach the solution in one step. The paper example’s two steps are not a rule for every start.') + '</p>'
    body += '<div class="scroll"><table><thead><tr><th>start x₀</th><th>SD final gap</th>'
    body += '<th>CG final gap</th><th>SD / CG updates</th><th>inspect</th></tr></thead><tbody>'
    for case in result['cases'][1:]:
        sd, cg = case['runs']['sd'], case['runs']['cg']
        body += f'<tr><td>{case["start"]}</td><td>{sd["rows"][-1]["gap"]:.5g}</td>'
        body += f'<td>{cg["rows"][-1]["gap"]:.5g}</td><td>{sd["updates"]} / {cg["updates"]}</td>'
        body += f'<td><a href="#{case["id"]}">{case["id"]}</a></td></tr>'
    body += '</tbody></table></div>'
    for case in result['cases'][1:]:
        body += f'<details class="case" id="{case["id"]}"><summary>{case["id"]} · x₀ = {case["start"]}'
        body += ' · ' + bi('경로·수치 열기', 'Open paths and values') + '</summary>'
        body += _case_view(p, case) + '</details>'
    body += '</section><section><h2>' + bi('범위와 다시 실행하기', 'Limits and rerunning') + '</h2>'
    body += '<p>' + bi(
        '이 결과는 특정 논문의 교육용 2차원 예제 재현입니다. 실제 데이터 벤치마크, 최악 사례, 전체 논문 재현 또는 보편적 우열 비교가 아닙니다. CG의 스케일 조정과 실제 잔차 검사도 원문 그대로의 부동소수점 실행을 주장하지 않습니다.',
        'This reproduces a specific pedagogical 2D example. It is not a dataset benchmark, worst case, whole-paper reproduction or universal ranking. CG scaling and true-residual checks are not a claim of identical floating-point execution to the source.') + '</p>'
    body += '<pre>python -m chainbench reproduce shewchuk-1994 --steps '
    body += str(result['parameters']['steps']) + ' --lang ko --output shewchuk.html\n'
    body += 'python -m chainbench reproduce shewchuk-1994 --steps '
    body += str(result['parameters']['steps']) + ' --format json --output shewchuk.json</pre>'
    body += '<p class="small">' + bi(
        '아래 JSON에는 모든 좌표·오차·환경·원문 위치·입력 SHA-256이 포함됩니다. 외부 데이터나 코드를 내려받지 않습니다.',
        'The JSON below retains every coordinate, metric, environment, source location and input SHA-256. No external data or code is fetched.') + '</p></section>'
    body += evidence(result, 'shewchuk-1994-evidence.json') + '</div><script>' + SCRIPT + '</script>'
    return page('One published problem. Two paths.',
                bi('Shewchuk 1994 · 원 논문 예제 재현과 9개 시작점 변형',
                   'Shewchuk 1994 · published-example reproduction + nine controlled starts'),
                body, lang=lang)
