"""Self-contained image and curve views of the computed Figure-5 subset."""

from __future__ import annotations

import base64
import struct
import zlib
from html import escape

import numpy as np

from ._pages import bi, evidence, page
from .visuals import ChartSpec, LineSeries, render_line_chart


def image_uri(values):
    """Encode the fixed [0,1] grayscale display; numerical iterates are untouched."""
    pixels = np.floor(np.clip(np.asarray(values), 0, 1) * 255 + 0.5).astype("uint8")
    height, width = pixels.shape

    def chunk(kind, data):
        return (
            struct.pack("!I", len(data))
            + kind
            + data
            + struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + row.tobytes() for row in pixels)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", width, height, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


CSS = ".deblur-inputs,.deblur-outputs{display:grid;grid-template-columns:1fr 1fr;gap:24px}.deblur-image{margin:0;padding:18px;background:#edf3f5;border-radius:16px}.deblur-image img{display:block;width:100%;max-width:320px;margin:auto;image-rendering:pixelated;border:1px solid #b8c9d5}.deblur-image figcaption{margin-top:12px;font-size:13px}.deblur-image h3{margin:0 0 12px}.deblur-settings{background:#eff7f4;padding:18px;border-left:4px solid #0f766e}.deblur-controls{display:none;margin:18px 0;padding:16px;background:#142841;color:white;border-radius:12px;gap:18px;align-items:center;flex-wrap:wrap}.deblur-js .deblur-controls{display:flex}.deblur-metrics{font-family:monospace;font-size:13px;overflow-wrap:anywhere}.deblur-gallery-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.deblur-gallery-grid img{width:100%;image-rendering:pixelated}.deblur-gallery-grid figure{margin:0}.deblur-note{border-left:4px solid #c08436;padding:14px;background:#fff7eb}@media(max-width:650px){.deblur-inputs,.deblur-outputs{grid-template-columns:1fr}.deblur-gallery-grid{grid-template-columns:1fr 1fr}}@media print{.deblur-controls{display:none!important}}"

SCRIPT = """(()=>{
 const select=document.querySelector('[data-deblur-select]');if(!select)return;
 const slider=document.querySelector('[data-deblur-slider]'),play=document.querySelector('[data-deblur-play]'),label=document.querySelector('[data-deblur-label]');
 const result=JSON.parse(document.getElementById('chainbench-evidence').textContent);
 const checkpoints=result.parameters.snapshot_iterations;let timer=null;
 document.documentElement.classList.add('deblur-js');
 const update=()=>{
  const k=Number(select.value);
  slider.value=String(checkpoints.indexOf(k));label.textContent='k = '+k.toLocaleString('en-US');
  slider.setAttribute('aria-valuetext','Iteration '+k+'; stored snapshot '+(Number(slider.value)+1)+' of '+checkpoints.length);
  for(const method of ['ista','fista']){
   document.querySelector('[data-deblur-image="'+method+'"]').src=document.querySelector('[data-snapshot="'+method+'-'+k+'"]').src;
   const row=result.runs[method].rows[k];
   document.querySelector('[data-deblur-metrics="'+method+'"]').textContent='k='+k+' · F='+row.objective.toExponential(6)+' · image RMSE='+row.image_rmse.toExponential(6);
  }
 };
 const stop=()=>{clearInterval(timer);timer=null;play.setAttribute('aria-pressed','false');play.querySelector('[data-play-icon]').textContent='▶';};
 select.addEventListener('change',()=>{stop();update();});
 slider.addEventListener('input',()=>{stop();select.value=String(checkpoints[Number(slider.value)]);update();});
 play.addEventListener('click',()=>{
  if(timer){stop();return;}
  if(Number(slider.value)===checkpoints.length-1){select.value='0';update();}
  play.setAttribute('aria-pressed','true');play.querySelector('[data-play-icon]').textContent='Ⅱ';
  timer=setInterval(()=>{
   const next=Number(slider.value)+1;
   if(next>=checkpoints.length){stop();return;}
   select.value=String(checkpoints[next]);update();
  },900);
 });
 document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
 update();
})();"""


def deblur_html(result, lang="en"):
    p, params = result["problem"], result["parameters"]
    steps = params["steps"]
    body = (
        "<style>"
        + CSS
        + '</style><section><span class="badge">Beck–Teboulle (2009) · Figure 5 · ISTA/FISTA subset</span><h2>'
        + bi(
            "잡음 없는 역문제: 관측값을 맞추면 원본도 같아질까?",
            "A noiseless inverse problem: does fitting data recover the image?",
        )
        + "</h2>"
    )
    body += (
        "<p>"
        + bi(
            "공개 실험 조건으로 다시 계산한 결과입니다. 원 논문의 그림을 복사하거나 마지막 수치를 동일하게 맞춘 자료가 아닙니다.",
            "An independent rerun of the published experiment protocol. These are newly computed figures; no exact match to the original endpoint values is asserted.",
        )
        + "</p>"
    )
    body += (
        '<div class="deblur-settings"><b>64 × 64 · 4096 variables · no noise · λ=0 · L=2 · step=½</b><br>'
        + bi(
            "9×9 Gaussian, σ=4. 가장자리 값을 반복하는 대칭 경계. 시작 영상은 관측된 흐린 영상.",
            "9×9 Gaussian, σ=4. Symmetric boundary repeats the edge pixel. Start: observed blurred image.",
        )
        + f"<br><b>{steps:,} updates / method</b> · "
        + bi(
            "논문 예산 10,000회 전체"
            if steps == 10000
            else "축소한 미리보기 예산 — Figure 5 전체가 아님",
            "Full paper budget of 10,000"
            if steps == 10000
            else "Short preview budget — not the full Figure-5 run",
        )
        + "</div>"
    )
    body += '<div class="formula">clean image → Gaussian blur R → observed b → ISTA / FISTA → reconstructed image\nF(u) = ‖R u − b‖² ; b = R u_clean ; F* = 0</div><div class="deblur-inputs">'
    for key, ko, en in [
        ("clean_image", "입력: 깨끗한 합성 영상", "Input: clean procedural image"),
        ("observed_image", "관측: 흐려진 영상", "Observation: blurred image"),
    ]:
        body += (
            '<figure class="deblur-image"><h3>'
            + bi(ko, en)
            + '</h3><img alt="'
            + en
            + '" src="'
            + image_uri(p[key])
            + '"><figcaption>'
            + bi(
                "모든 영상은 같은 [0,1] 회색조: 0=검정, 1=흰색.",
                "Every image uses the same [0,1] grayscale: 0=black, 1=white.",
            )
            + "</figcaption></figure>"
        )
    body += (
        '</div><p class="small">'
        + bi(
            "입력 생성 규칙: Hansen Regularization Tools 4.1 (2008)의 blur.m 영상 부분을 허가 조건과 함께 이식했습니다. 원 논문은 도구의 정확한 버전 해시를 명시하지 않습니다.",
            "Image generator: attributed port of the image subset in Hansen Regularization Tools 4.1 (2008), with its permission notice retained. The paper does not identify a toolbox version hash.",
        )
        + "</p></section>"
    )
    body += (
        "<section><h2>"
        + bi(
            "동일한 반복 수에서 두 복원 보기", "Inspect both reconstructions at the same iteration"
        )
        + '</h2><p>'
        + bi('슬라이더를 끌거나 재생해 보세요. 각 위치는 실제 저장한 반복점이며 간격은 균일하지 않습니다.',
             'Drag the timeline or press Play. Each stop is a recorded iteration; the intervals are not uniform.')
        + '</p><div class="deblur-controls"><button type="button" data-deblur-play aria-pressed="false"><span data-play-icon>▶</span> '
        + bi('재생 / 일시정지', 'Play / pause')
        + '</button><label for="deblur-timeline">'
        + bi('반복 횟수', 'Iteration')
        + '</label><input id="deblur-timeline" type="range" data-deblur-slider min="0" max="'
        + str(len(params['snapshot_iterations']) - 1)
        + '" step="1" value="' + str(len(params['snapshot_iterations']) - 1)
        + '" style="flex:1;min-width:160px"><output data-deblur-label for="deblur-timeline"></output></div>'
        + '<div class="deblur-controls"><label for="deblur-snapshot">'
        + bi("저장한 반복점", "Stored snapshot")
        + '</label><select id="deblur-snapshot" data-deblur-select>'
    )
    for k in params["snapshot_iterations"]:
        body += (
            '<option value="'
            + str(k)
            + '"'
            + (" selected" if k == steps else "")
            + ">k = "
            + str(k)
            + "</option>"
        )
    body += '</select></div><div class="deblur-outputs">'
    for method, run in result["runs"].items():
        row, snapshot = run["rows"][-1], run["snapshots"][-1]
        body += (
            '<figure class="deblur-image"><h3>'
            + method.upper()
            + '</h3><img data-deblur-image="'
            + method
            + '" alt="'
            + method.upper()
            + ' reconstruction" src="'
            + image_uri(snapshot["image"])
            + '"><figcaption class="deblur-metrics" data-deblur-metrics="'
            + method
            + '">'
            + f"k={steps} · F={row['objective']:.6e} · image RMSE={row['image_rmse']:.6e}"
            + "</figcaption></figure>"
        )
    body += (
        "</div><p>"
        + bi(
            "F는 흐린 관측과의 잔차 제곱합, RMSE는 깨끗한 원본과의 픽셀 오차입니다. 이 문제에서 최적 F=0은 알려져 있지만, 작은 F가 정확한 영상 복원을 뜻하지는 않습니다.",
            "F is the squared residual to the blurred observation; RMSE measures pixel error against the clean image. The optimal F=0 is known here, but small F need not mean exact reconstruction.",
        )
        + '</p><p class="small">'
        + bi(
            "화면에만 [0,1] 클리핑을 적용합니다. 저장한 반복점과 F·RMSE는 클리핑하지 않습니다. JavaScript 없이도 아래 모든 저장 영상을 열 수 있습니다.",
            "Only display pixels are clipped to [0,1]. Stored iterates, F and RMSE are unclipped. All snapshots below remain available without JavaScript.",
        )
        + '</p><details class="deblur-gallery"><summary>'
        + bi("모든 저장 영상을 비교", "Compare every stored snapshot")
        + '</summary><div class="deblur-gallery-grid">'
    )
    for snapshot_index, k in enumerate(params["snapshot_iterations"]):
        for method, run in result["runs"].items():
            snapshot = run["snapshots"][snapshot_index]
            body += (
                '<figure><img data-snapshot="'
                + method
                + "-"
                + str(k)
                + '" alt="'
                + method.upper()
                + " at "
                + str(k)
                + '" src="'
                + image_uri(snapshot["image"])
                + '"><figcaption>'
                + method.upper()
                + f" · k={k}</figcaption></figure>"
            )
    body += (
        "</div></details></section><section><h2>"
        + bi(
            "목적함수 오차와 복원 오차를 분리해 읽기",
            "Read objective error and reconstruction error separately",
        )
        + "</h2>"
    )
    for field, title, label in [
        ("objective", "Computed objective error; F*=0", "F(u_k) − F*"),
        ("image_rmse", "Reconstruction error against the clean image", "image RMSE"),
    ]:
        chart = ChartSpec(
            title,
            "iteration k",
            label,
            tuple(
                LineSeries(
                    method.upper(),
                    tuple(r["iteration"] for r in run["rows"]),
                    tuple(r[field] for r in run["rows"]),
                )
                for method, run in result["runs"].items()
            ),
        )
        body += '<div class="plot">' + render_line_chart(chart) + "</div>"
    body += (
        '<p class="small">'
        + bi(
            "위 설정에서 실제 계산한 모든 반복의 값입니다. 첫 점 k=0도 포함합니다. 원 논문의 곡선을 추출한 것이 아닙니다.",
            "Every computed iteration from the setup above is included, including k=0. These are not digitized curves from the paper.",
        )
        + "</p></section>"
    )
    body += (
        "<section><h2>"
        + bi("원문과 연결되는 범위", "Connection to the source")
        + '</h2><p><a href="'
        + escape(result["source"]["url"], quote=True)
        + '#page=17">Section 5.2 / Figure 5 · PDF pages 17, 19</a></p>'
    )
    body += (
        "<p>"
        + bi(
            "원문 본문은 10,000회 후 ISTA 약 10⁻³, FISTA 약 10⁻⁷ 수준을 설명합니다. 이는 반올림한 서술이며 이 구현의 정답 또는 통과 기준으로 사용하지 않습니다.",
            "The source text describes approximately 10⁻³ for ISTA and 10⁻⁷ for FISTA after 10,000 steps. These are contextual approximate magnitudes, not exact reference values or pass thresholds.",
        )
        + '</p><div class="deblur-note">'
        + bi(
            "이 실험은 λ=0입니다. Haar 변환 W가 직교이면 u=Wx에서 ISTA/FISTA 갱신과 외삽이 동일하게 대응합니다. 코드는 영상 좌표에서 같은 계산을 수행합니다. 양의 λ에서 필요한 계수 shrinkage를 재현한 실험은 아닙니다.",
            "This experiment has λ=0. With orthonormal Haar W, the transformation u=Wx commutes with the ISTA/FISTA updates and extrapolation. The code computes in image coordinates. This run does not exercise coefficient shrinkage at positive λ.",
        )
        + "</div>"
    )
    body += (
        "<h3>"
        + bi("재현 범위와 차이", "Scope and differences")
        + "</h3><ul>"
        + "".join("<li>" + escape(x) + "</li>" for x in result["differences"] + result["limits"])
        + "</ul></section>"
    )
    body += (
        '<details class="panel"><summary>Image-generator attribution and permission notice</summary><pre>'
        + escape(result["source"]["image_permission_notice"])
        + "</pre></details>"
    )
    body += evidence(result, "chainbench-fista-deblurring.json") + "<script>" + SCRIPT + "</script>"
    return page(
        "FISTA · the noiseless image experiment",
        bi(
            "공개 실험 프로토콜 · 실제 복원 영상 · 두 종류의 오차",
            "Published protocol · computed reconstructions · two distinct errors",
        ),
        body,
        lang=lang,
    )
