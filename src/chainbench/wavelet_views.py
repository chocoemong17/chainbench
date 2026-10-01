"""Inspectable noisy-image restoration, with coefficient-space operations."""

from __future__ import annotations

import json
from html import escape

import numpy as np

from ._pages import bi, page
from ._wavelet_duality_views import duality_html
from .deblur_views import CSS as IMAGE_CSS
from .deblur_views import image_uri
from .visuals import ChartSpec, LineSeries, render_line_chart

SCRIPT = """(()=>{
 const picker=document.querySelector('[data-wavelet-select]');
 const data=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 document.documentElement.classList.add('deblur-js');
 picker.addEventListener('change',()=>{
  const k=Number(picker.value);
  for(const panel of document.querySelectorAll('[data-dual-snapshot]'))panel.hidden=Number(panel.dataset.dualSnapshot)!==k;
  for(const m of ['ista','fista']){
   document.querySelector('[data-wavelet-image="'+m+'"]').src=document.querySelector('[data-snapshot="'+m+'-'+k+'"]').src;
   document.querySelector('[data-wavelet-coeff="'+m+'"]').src=document.querySelector('[data-coeff-snapshot="'+m+'-'+k+'"]').src;
   const row=data.runs[m].rows[k],s=data.runs[m].snapshots.find(x=>x.iteration===k);
   document.querySelector('[data-wavelet-metrics="'+m+'"]').textContent='k='+k+' · F='+row.objective.toExponential(6)+' = residual² '+row.squared_residual.toExponential(6)+' + λ‖c‖₁ '+row.penalty.toExponential(6)+' · RMSE='+row.image_rmse.toExponential(6)+' · zero coefficients='+row.zero_coefficients+'/65536 · ‖G_L(c)‖₂='+s.proximal_gradient_norm.toExponential(6);
  }
 });
})();"""


def haar_layout():
    """Exact three-level storage layout, with ranges in the 256² coefficient grid."""
    svg = '<svg viewBox="0 0 292 286" role="img" aria-label="Three-stage Haar coefficient layout: recurse only on the top-left average block">'
    svg += '<rect width="292" height="286" rx="16" fill="#f3f6fa"/>'
    colors = ("#e0eaff", "#daeae5", "#f6e5cf")
    for stage, size in enumerate((256, 128, 64), start=1):
        half = size // 2
        for x, y, label, color in [
            (half, 0, "x", colors[0]),
            (0, half, "y", colors[1]),
            (half, half, "xy", colors[2]),
        ]:
            svg += f'<rect x="{18 + x}" y="{18 + y}" width="{half}" height="{half}" fill="{color}" stroke="#687b92"/>'
            svg += f'<text x="{18 + x + half / 2}" y="{18 + y + half / 2 + 4}" text-anchor="middle" font-size="{10 if stage == 3 else 13}">{label}{stage}</text>'
    svg += '<rect x="18" y="18" width="32" height="32" fill="#163859"/><text x="34" y="38" text-anchor="middle" fill="white" font-size="11">LL3</text>'
    legend = '<div class="small">'
    for ko, en in [
        ("LL3: 32×32 평균", "LL3: 32×32 averages"),
        ("3단계: 32×32 세부 계수", "Level 3: 32×32 details"),
        ("2단계: 64×64 세부 계수", "Level 2: 64×64 details"),
        ("1단계: 128×128 세부 계수", "Level 1: 128×128 details"),
        (
            "x: 가로 차이, y: 세로 차이, xy: 양 방향 차이",
            "x: horizontal differences; y: vertical; xy: both",
        ),
        ("왼쪽 위 평균 블록에만 3단계 반복", "Repeat only on the top-left average block"),
        ("65,536개 계수 모두 벌점 적용", "All 65,536 coefficients are penalized"),
    ]:
        legend += "<p>" + bi(ko, en) + "</p>"
    return '<div class="haar-grid">' + svg + "</svg>" + legend + "</div></div>"


def _metrics(k, row, snapshot):
    return (
        f"k={k} · F={row['objective']:.6e} = residual² {row['squared_residual']:.6e}"
        f" + λ‖c‖₁ {row['penalty']:.6e} · RMSE={row['image_rmse']:.6e}"
        f" · zero coefficients={row['zero_coefficients']}/65536"
        f" · ‖G_L(c)‖₂={snapshot['proximal_gradient_norm']:.6e}"
    )


def wavelet_html(result, lang="en"):
    p, params = result["problem"], result["parameters"]
    steps = params["steps"]
    maximum = max(
        float(np.max(np.abs(s["coefficients"])))
        for r in result["runs"].values()
        for s in r["snapshots"]
    )

    def coeff_uri(values):
        return image_uri(np.log1p(np.abs(values)) / np.log1p(maximum))

    body = (
        "<style>"
        + IMAGE_CSS
        + ".wavelet-layout{max-width:760px}.wavelet-layout svg{width:100%;max-width:320px}.haar-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;align-items:center}.wavelet-pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}.wavelet-pair small{display:block;text-align:center}.wavelet-pair img{max-width:256px}.wavelet-steps>p{padding:16px;border-left:3px solid #2864d7;background:#f3f6fa}.wavelet-steps b{display:block}@media(max-width:650px){.haar-grid{grid-template-columns:1fr}}</style>"
    )
    body += (
        '<section><span class="badge">Beck–Teboulle (2009) · §5.2 / Figure 4 · declared noise draw</span><h2>'
        + bi("잡음이 있으면 무엇을 남기고 지울까?", "With noise, what should restoration keep?")
        + "</h2><p>"
        + bi(
            "흐린 관측을 맞추면서 작은 Haar 계수를 줄이는 두 알고리즘을 같은 입력에서 계산합니다. 깨끗한 영상은 오차 평가에만 사용하며, 복원 알고리즘에는 전달하지 않습니다.",
            "Both methods fit the same blurred observation while shrinking small Haar coefficients. The clean image is used to evaluate reconstruction error; it is not supplied to the optimization algorithm.",
        )
        + "</p>"
    )
    body += (
        '<div class="deblur-settings"><b>256 × 256 · 65,536 coefficients · λ=10⁻⁴ · L=2 · step=½ · threshold=5×10⁻⁵</b><br>'
        + bi(
            "3단계 직교 Haar · 9×9 Gaussian σ=4 · 대칭 경계 · 가산 Gaussian 잡음 σ=0.001",
            "Three-stage orthonormal Haar · 9×9 Gaussian σ=4 · symmetric boundary · additive Gaussian noise σ=0.001",
        )
        + f"<br>PCG64 seed={params['seed']} · {steps} updates / method · "
        + bi(
            "논문의 200회 예산 전체" if steps == 200 else "축소한 미리보기 예산",
            "Full 200-update paper budget" if steps == 200 else "Short preview budget",
        )
        + "</div>"
    )
    body += '<div class="formula">b = R u_clean + noise\nF(c) = ‖R W c − b‖² + λ‖c‖₁ ; u = W c ; c₀ = Wᵀ b\nF* = unknown</div><div class="deblur-inputs">'
    for key, ko, en in [
        ("clean_image", "평가용 원본", "Clean reference for evaluation"),
        ("observed_image", "알고리즘의 입력: 흐림 + 잡음", "Algorithm input: blur + noise"),
    ]:
        body += (
            '<figure class="deblur-image"><h3>'
            + bi(ko, en)
            + '</h3><img alt="'
            + en
            + '" src="'
            + image_uri(p[key])
            + '"><figcaption>'
            + bi("공통 회색조 [0,1]: 검정 0, 흰색 1.", "Shared grayscale [0,1]: black 0, white 1.")
            + "</figcaption></figure>"
        )
    body += (
        '</div><p class="small">'
        + bi(
            "원문은 잡음 표본을 제공하지 않습니다. 선언한 시드로 새로 생성한 잡음이며, Figure 4의 원래 픽셀·최종 수치와 일치한다고 주장하지 않습니다. 원본, 잡음, 관측과 해시는 아래 JSON에 포함됩니다.",
            "The source supplies no noise samples. This rerun generates new noise from the declared seed and does not assert a match to Figure 4 pixels or endpoint values. The clean image, noise, observation and hashes are included in the JSON below.",
        )
        + "</p></section>"
    )
    body += (
        "<section><h2>"
        + bi("영상 → Haar 계수 → 축소 → 영상", "Image → Haar coefficients → shrinkage → image")
        + '</h2><div class="wavelet-steps"><p><b>1 · '
        + bi("평균과 차이로 바꾸기", "Separate averages and differences")
        + "</b>"
        + bi(
            "이웃한 두 값 a,b를 (a+b)/√2와 (a−b)/√2로 바꿉니다. 가로·세로에 적용한 뒤 평균 블록에만 반복합니다. 큰 윤곽과 여러 크기의 세부 정보가 분리되지만 전체 에너지는 보존됩니다.",
            "Transform each adjacent pair a,b into (a+b)/√2 and (a−b)/√2. Apply across rows and columns, then repeat only on the average block. Coarse structure and details at several scales separate while total energy is preserved.",
        )
        + '</p><div class="wavelet-layout">'
        + haar_layout()
        + "</div>"
    )
    body += (
        "<p><b>2 · "
        + bi("관측을 맞추는 방향으로 이동", "Move toward fitting the observation")
        + "</b><code>z = y − ½ [2 Wᵀ Rᵀ(R W y − b)]</code><br>"
        + bi(
            "잔차는 흐린 영상 공간에서 계산한 뒤 Rᵀ와 Wᵀ로 계수 공간에 돌려보냅니다. 대칭 커널과 이 경계 규칙에서 Rᵀ=R입니다.",
            "Compute the residual in blurred image space, then map it back with Rᵀ and Wᵀ. For this symmetric kernel and boundary rule, Rᵀ=R.",
        )
        + "</p>"
    )
    body += (
        "<p><b>3 · "
        + bi(
            "작은 계수는 0으로, 큰 계수도 조금 줄이기",
            "Zero small coefficients; shrink large ones too",
        )
        + "</b><code>c_next = sign(z) max(|z| − 0.00005, 0)</code><br>"
        + bi(
            "임계값은 λ/L입니다. 영상 픽셀을 잘라내는 연산이 아니며, 가장 큰 평균 블록도 벌점에 포함합니다.",
            "The threshold is λ/L. This acts on wavelet coefficients, including the coarse average block; it is not pixel clipping.",
        )
        + "</p>"
    )
    body += (
        "<p><b>4 · "
        + bi("다음 평가점 선택", "Choose the next evaluation point")
        + "</b>"
        + bi(
            "ISTA는 방금 얻은 계수에서 다시 시작합니다. FISTA는 이전 계수와의 차이를 이용해 외삽합니다. t₀=1, t_next=(1+√(1+4t²))/2, y_next=c_next+(t−1)/t_next·(c_next−c). 두 방법 모두 같은 gradient와 축소 연산을 씁니다.",
            "ISTA starts again from the new coefficients. FISTA extrapolates using their change: t₀=1, t_next=(1+√(1+4t²))/2, y_next=c_next+(t−1)/t_next·(c_next−c). Both use the same gradient and shrinkage operation.",
        )
        + "</p></div>"
    )
    body += (
        "<h3>"
        + bi("첫 갱신의 실제 계수 세 개", "Three actual coefficients at the first update")
        + '</h3><p class="small">'
        + bi(
            "두 방법의 첫 갱신은 같습니다. z의 절댓값이 가장 작은 값, 가장 큰 값, 임계값에 가장 가까운 값을 선택했습니다. 전체 계수의 대표 표본은 아닙니다. 인덱스는 행 우선 0부터 시작합니다.",
            "Both methods have the same first update. Selected by smallest |z|, largest |z| and proximity to the threshold. These illustrate operations, not a representative sample. Indices are zero-based, row-major.",
        )
        + '</p><div class="scroll"><table><thead><tr><th>index</th><th>c₀</th><th>∇f(c₀)</th><th>z=c₀−∇f/2</th><th>soft(z, λ/2)</th></tr></thead><tbody>'
    )
    for item in result["first_step"]:
        body += (
            "<tr>"
            + "".join(
                "<td>" + (str(item[k]) if k == "index" else f"{item[k]:.9e}") + "</td>"
                for k in ("index", "coefficient", "gradient", "before_threshold", "after_threshold")
            )
            + "</tr>"
        )
    body += (
        "</tbody></table></div></section><section><h2>"
        + bi(
            "동일한 반복점의 복원과 계수", "Reconstructions and coefficients at the same iteration"
        )
        + '</h2><div class="deblur-controls"><label for="wavelet-snapshot">'
        + bi("저장한 반복점", "Stored snapshot")
        + '</label><select id="wavelet-snapshot" data-wavelet-select>'
    )
    for k in params["snapshot_iterations"]:
        body += f'<option value="{k}"' + (" selected" if k == steps else "") + f">k = {k}</option>"
    body += '</select></div><div class="deblur-outputs">'
    for method, run in result["runs"].items():
        s, row = run["snapshots"][-1], run["rows"][-1]
        body += (
            '<figure class="deblur-image"><h3>'
            + method.upper()
            + '</h3><div class="wavelet-pair"><div><img data-wavelet-image="'
            + method
            + '" alt="'
            + method.upper()
            + ' reconstruction" src="'
            + image_uri(s["image"])
            + '"><small>'
            + bi("복원 영상", "Reconstruction")
            + '</small></div><div><img data-wavelet-coeff="'
            + method
            + '" alt="'
            + method.upper()
            + ' coefficient magnitude" src="'
            + coeff_uri(s["coefficients"])
            + '"><small>'
            + bi("계수 절댓값", "Coefficient magnitude")
            + '</small></div></div><figcaption class="deblur-metrics" data-wavelet-metrics="'
            + method
            + '">'
            + _metrics(steps, row, s)
            + "</figcaption></figure>"
        )
    body += (
        "</div><p>"
        + bi(
            "영상은 표시할 때만 [0,1]로 클리핑합니다. 모든 계산은 클리핑 전 값을 사용합니다. 계수 그림은 부호를 숨긴 절댓값으로, 작은 값도 보이도록 log(1+|c|)를 사용합니다.",
            "Only displayed image pixels are clipped to [0,1]; all computations use unclipped values. Coefficient panels show unsigned magnitudes with log(1+|c|) scaling to reveal small values.",
        )
        + f" <code>gray=log(1+|c|)/log(1+{maximum:.9g})</code> "
        + bi(
            "모든 저장점과 두 방법에 같은 척도를 적용합니다. 검정=0, 흰색=위 최댓값.",
            "The same scale applies to every snapshot and both methods: black=0, white=the maximum above.",
        )
        + '</p><p class="small">'
        + bi(
            "G_L(c)=L[c−soft(c−∇f(c)/L,λ/L)]는 proximal gradient mapping입니다. 그 노름은 정지성 관측값이며 알려지지 않은 최적값과의 차이는 아닙니다.",
            "G_L(c)=L[c−soft(c−∇f(c)/L,λ/L)] is the proximal gradient mapping. Its norm is a stationarity observation, not a gap to the unknown optimum.",
        )
        + "</p>"
    )
    body += (
        '<details class="deblur-gallery"><summary>'
        + bi(
            "모든 저장점 보기 — JavaScript 없이도 사용 가능",
            "Every stored snapshot — also available without JavaScript",
        )
        + '</summary><div class="deblur-gallery-grid">'
    )
    for j, k in enumerate(params["snapshot_iterations"]):
        for method, run in result["runs"].items():
            s = run["snapshots"][j]
            for key, attr, uri in [
                ("image", "data-snapshot", image_uri),
                ("coefficients", "data-coeff-snapshot", coeff_uri),
            ]:
                body += (
                    f'<figure><img {attr}="{method}-{k}" alt="{method.upper()} {key} at {k}" src="'
                    + uri(s[key])
                    + f'"><figcaption>{method.upper()} · k={k} · {key}</figcaption></figure>'
                )
    body += (
        "</div></details></section>"
        + duality_html(result)
        + "<section><h2>"
        + bi(
            "작은 목적함수와 정확한 영상은 같은 질문이 아니다",
            "Objective value and image accuracy answer different questions",
        )
        + "</h2><p>"
        + bi(
            "F는 관측 잔차 제곱합과 계수 벌점의 합입니다. RMSE는 이 합성 실험에서만 알려진 원본과 비교합니다. F*를 모르므로 아래 F 곡선은 최적성 오차가 아닙니다.",
            "F adds the squared observation residual and the coefficient penalty. RMSE compares with the clean reference available in this synthetic experiment. Since F* is unknown, the F curve is not an optimality gap.",
        )
        + "</p>"
    )
    for field, title, label in [
        ("objective", "Computed objective (unknown F*)", "F(c_k)"),
        ("squared_residual", "Fit to the noisy observation", "squared residual"),
        ("penalty", "Coefficient penalty", "lambda * l1 norm"),
        ("image_rmse", "Error against the clean reference", "image RMSE"),
    ]:
        chart = ChartSpec(
            title,
            "iteration k",
            label,
            tuple(
                LineSeries(
                    m.upper(),
                    tuple(r["iteration"] for r in run["rows"]),
                    tuple(r[field] for r in run["rows"]),
                )
                for m, run in result["runs"].items()
            ),
        )
        body += '<div class="plot">' + render_line_chart(chart) + "</div>"
    body += (
        '<p class="small">'
        + bi(
            "0회부터 모든 반복을 표시합니다. 한 잡음 표본의 유한한 관측으로 모든 문제에서의 방법 순위를 정할 수 없습니다. 외삽은 매 반복의 단조 감소를 보장하지 않습니다.",
            "Every iteration from k=0 is shown. One noise draw cannot establish a universal ranking. Extrapolation does not ensure monotone decrease at each iteration.",
        )
        + "</p></section><section><h2>"
        + bi("출처와 재현 범위", "Source and scope")
        + '</h2><a href="'
        + escape(result["source"]["url"], quote=True)
        + '#page=17">Beck–Teboulle (2009), §5.2 / Figure 4</a><ul>'
        + "".join("<li>" + escape(x) + "</li>" for x in result["differences"] + result["limits"])
        + "</ul><p>"
        + bi(
            "원본 생성기는 Hansen Regularization Tools 4.1 (2008)의 허가된 영상 부분을 이식했습니다. 원문은 정확한 버전 해시를 지정하지 않습니다.",
            "The image generator is an attributed, permitted port of the image subset in Hansen Regularization Tools 4.1 (2008). The paper does not specify its exact version hash.",
        )
        + "</p><details><summary>Image-generator attribution and permission notice</summary><pre>"
        + escape(result["source"]["image_permission_notice"])
        + "</pre></details></section>"
    )
    # Compact storage avoids indentation multiplying a 65,536-variable evidence file.
    body += (
        '<details class="panel"><summary>'
        + bi(
            "원본 배열·저장점·모든 반복 수치·환경 확인",
            "Exact arrays, snapshots, every iteration and environment",
        )
        + '</summary><button type="button" data-download="chainbench-evidence" data-filename="chainbench-fista-wavelet.json">'
        + bi("JSON 저장", "Save JSON")
        + '</button><pre id="chainbench-evidence">'
        + escape(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
        + "</pre></details><script>"
        + SCRIPT
        + "</script>"
    )
    return page(
        "FISTA · noisy images and wavelet shrinkage",
        bi(
            "공개 실험 조건 · 실제 Haar 계수 · 선언한 잡음 표본",
            "Published protocol · actual Haar coefficients · declared noise draw",
        ),
        body,
        lang=lang,
    )
