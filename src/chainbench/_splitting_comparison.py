"""Notation and subproblem bridge between the two existing LASSO reports."""
from ._pages import bi


def splitting_comparison():
    body = '''<div class="split-bridge" data-splitting-comparison><style>
    .split-bridge{margin-top:24px}.split-flows{display:grid;grid-template-columns:1fr 1fr;gap:20px}
    .split-flow{margin:0;padding:0;list-style:none;counter-reset:split-step}
    .split-flow li{position:relative;counter-increment:split-step;margin:9px 0;padding:12px 14px 12px 48px;border:1px solid #d9e2ec;border-radius:12px;background:#f7faff}
    .split-flow li:before{content:counter(split-step);position:absolute;left:15px;top:12px;color:#2563eb;font-weight:800}
    .split-flow[data-split-method="admm"] li{background:#f0f8f5}.split-flow[data-split-method="admm"] li:before{color:#0f766e}
    .split-flow code{font-size:13px;white-space:normal}.split-table th,.split-table td{min-width:160px;white-space:normal}
    .split-bridge .scroll:focus-visible{outline:3px solid #ef9f47;outline-offset:3px}
    @media(max-width:760px){.split-flows{grid-template-columns:1fr}.split-table{min-width:650px}}
    </style>'''
    body += '<h3>'+bi('같은 축소 연산, 다른 하위 문제', 'Same shrinkage operator, different subproblems')+'</h3>'
    body += '<p>'+bi('두 보고서는 모두 ½||Aw−b||²+λ||w||₁을 다룹니다. 하지만 soft threshold 앞에 어떤 점을 넣고, 뒤에 어떤 상태를 남기는지가 다릅니다. 아래 흐름은 기호로 설명하는 순서이며, 실제 점의 경로나 새 실험이 아닙니다.',
        'Both reports study ½||Aw−b||²+λ||w||₁. What enters soft thresholding, and which state survives it, differ. The flows below are symbolic update sequences, not numerical trajectories or new experiments.')+'</p>'
    body += '<div class="split-flows"><div><h3><a href="proximal.html">ISTA / FISTA</a></h3><ol class="split-flow" data-split-method="proximal">'
    for ko,en,formula in [
        ('기울기를 계산할 점을 고르기','Choose the gradient evaluation point','y=x (ISTA); y=extrapolate(x,x_old) (FISTA)'),
        ('기울기만큼 이동','Take a gradient step','v=y−∇f(y)/L'),
        ('같은 v에서 좌표 축소','Shrink coordinates at v','x_new=soft(v,λ/L)'),
        ('다음 원래 변수로 이동','Keep the next original variable','x ← x_new'),
    ]:
        body += '<li>'+bi(ko,en)+'<br><code>'+formula+'</code></li>'
    body += '</ol></div><div><h3><a href="admm.html">ADMM</a></h3><ol class="split-flow" data-split-method="admm">'
    for ko,en,formula in [
        ('벌점을 포함한 이차 문제 풀기','Solve the penalized quadratic','(AᵀA+ρI)x=Aᵀb+ρ(z_old−u_old)'),
        ('이전 불일치 기억 더하기','Add the previous disagreement memory','v=x+u_old'),
        ('다른 문턱으로 좌표 축소','Shrink at a different threshold','z_new=soft(v,λ/ρ)'),
        ('두 변수의 차이를 누적','Accumulate the two variables’ difference','u_new=u_old+x−z_new'),
    ]:
        body += '<li>'+bi(ko,en)+'<br><code>'+formula+'</code></li>'
    body += '</ol></div></div><p class="formula">soft(v,τ)ᵢ=sign(vᵢ) max(|vᵢ|−τ,0)</p>'
    body += '<p class="small">'+bi('작은 화면에서는 아래 표를 좌우로 이동하세요. 키보드로 표 영역에 초점을 맞춘 뒤 화살표 키를 사용할 수 있습니다.',
        'On small screens, scroll the table sideways. Keyboard users can focus the table region and use arrow keys.')+'</p>'
    body += '<div class="scroll" tabindex="0" aria-label="Compare variable meanings / 변수 의미 비교"><table class="split-table"><thead><tr><th>'+bi('읽을 항목','Read this')+'</th><th>ISTA / FISTA</th><th>ADMM</th></tr></thead><tbody>'
    rows = [
        ('y',('기울기를 계산할 점. FISTA에서는 외삽점입니다.','Gradient evaluation point; extrapolated in FISTA.'),
             ('y=ρu는 특성 좌표의 쌍대 기억입니다. 위 흐름의 v와도 다릅니다.','y=ρu is dual memory in feature coordinates, also distinct from v above.')),
        ('z',('기존 proximal 그림의 z는 y−∇f(y)/L입니다. 위 비교에서는 v라고 썼습니다.','The proximal report names y−∇f(y)/L as z; the flow above calls it v.'),
             ('축소 뒤의 희소 복사 변수. x=z가 되어야 분할 제약을 만족합니다.','Sparse copy after shrinkage. The split constraint requires x=z.')),
        ('threshold',('λ/L. 고정 L=9인 이 보고서의 기울기 모델에서 나옵니다.','λ/L, from this report’s gradient model with fixed L=9.'),
                     ('λ/ρ. 이차 벌점이 있는 z 하위 문제에서 나옵니다.','λ/ρ, from the quadratically penalized z subproblem.')),
        ('objective',('원래 변수의 F(x)를 읽습니다.','Read F(x) at the original variable.'),
                     ('F(z)와 f(x)+g(z)를 구분합니다. x≠z의 혼합 값은 원래 간극이 아닙니다.','Distinguish F(z) from f(x)+g(z). With x≠z, the split value is not an original-primal gap.')),
        ('dual geometry',('측정 잔차로 만든 ν는 실행점에서 구성한 하계 후보입니다.','Measurement-residual ν supplies a candidate lower bound from a recorded iterate.'),
                        ('y=ρu는 갱신에 사용하는 상태입니다. 상자 그림 자체가 하계 인증서는 아닙니다.','y=ρu is a state used in the recurrence. Its box alone is not a lower-bound certificate.')),
    ]
    for name,left,right in rows:
        body += '<tr data-split-meaning="'+name+'"><th scope="row">'+name+'</th><td>'+bi(*left)+'</td><td>'+bi(*right)+'</td></tr>'
    body += '</tbody></table></div><p class="callout caution">'+bi(
        '현재 보고서의 입력 격자도 다릅니다. ISTA/FISTA는 대각 A에서 λ∈{0.1,0.8,1.8}, 18회입니다. ADMM은 두 A에서 λ/||Aᵀb||∞∈{0.1,0.6,1.1}, 60회입니다. 같은 입력·같은 비용의 속도 비교가 아닙니다. 한 번의 선형계 풀기와 한 번의 기울기 계산도 같은 작업량으로 세지 않습니다.',
        'These reports use different input grids: ISTA/FISTA has diagonal A, λ∈{0.1,0.8,1.8} and 18 updates; ADMM has two matrices, λ/||Aᵀb||∞∈{0.1,0.6,1.1} and 60 updates. This is not a same-input, equal-work speed comparison. One linear solve and one gradient evaluation do not count as equal work.')+'</p>'
    body += '<p>'+bi('연결할 질문: 같은 soft threshold를 쓰는데도, ADMM은 왜 원래 목적함수 간극 외에 x−z와 z의 변화를 검사할까요? ADMM 보고서에서 λ/λ_max=1.1, zero 시작을 선택해 보세요. 초기 기억과 첫 축소 뒤의 최적성 조건도 구분합니다.',
        'Connecting question: with the same soft threshold, why does ADMM check x−z and the change in z as well as the original gap? Select λ/λ_max=1.1 with a zero start in the ADMM report. Distinguish the initial memory from optimality conditions after the first shrink step.')+'</p>'
    body += '<p class="small"><a href="https://www.tau.ac.il/~becka/FISTA.pdf">Beck–Teboulle (2009), Eqs. (2.5)–(2.6), (3.1), (4.1)–(4.3)</a> · <a href="https://web.stanford.edu/~boyd/papers/pdf/admm_distr_stats.pdf">Boyd et al. (2011), §6.4 / Eq. (6.2); §3.3 / Eq. (3.12)</a>. '+bi(
        '각 보고서의 ½ 제곱 손실 관례와 가정을 유지합니다. ADMM을 2011년에 처음 제안한 알고리즘으로 소개하거나 FISTA의 상계를 이 경로에 옮기지 않습니다.',
        'Keep each report’s half-squared-loss convention and assumptions. ADMM predates the 2011 review; FISTA’s envelope is not transferred to its path.')+'</p></div>'
    return body
