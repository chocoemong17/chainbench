"""Recorded Fourier projection stages; the kernel is an analytical comparison."""

from html import escape

import numpy as np

from ._pages import bi

CSS = """.projection-figure{overflow:auto;margin:12px 0}.projection-figure svg{display:block;width:100%;min-width:660px;height:auto}
.projection-response{margin:20px 0;border:1px solid #cfdae3;border-radius:12px;padding:16px}
.projection-frame{margin:12px 0}.sampling-js .projection-frame{display:none}.sampling-js .projection-frame.is-current{display:block}
.projection-readout{font-family:monospace;overflow-wrap:anywhere;font-size:12px;line-height:1.65}"""


def _panel(grid, series, limits, top, height, name, title, note, node):
    low, high = limits
    bottom = top + height
    body = f'<g data-response-axis="{name}" data-low="{low!r}" data-high="{high!r}" data-top="{top}" data-height="{height}">'
    body += f'<text x="24" y="{top - 38}" font-size="17">{escape(title)}</text><text x="24" y="{top - 17}" font-size="12">{escape(note)}</text>'
    body += f'<rect x="80" y="{top}" width="800" height="{height}" fill="white" stroke="#cbd8e1"/>'
    for value in np.linspace(low, high, 3):
        y = bottom - height * (value - low) / (high - low)
        body += f'<path d="M80 {y:.4f} H880" stroke="#e3e9ee"/><text x="71" y="{y + 4:.4f}" text-anchor="end" font-size="11">{value:.2e}</text>'
    for t in (0, 0.25, 0.5, 0.75, 1):
        x = 80 + 800 * t
        body += f'<text x="{x}" y="{bottom + 19}" text-anchor="middle" font-size="11">{t:g}</text>'
    x = 80 + 800 * node
    body += f'<path data-response-node="" d="M{x:.4f} {top} V{bottom}" stroke="#a18462" stroke-dasharray="3 4"/>'
    for key, values, color, dashed in series:
        points = " ".join(
            f"{80 + 800 * t:.4f},{bottom - height * (v - low) / (high - low):.4f}"
            for t, v in zip(grid, values)
        )
        body += (
            f'<polyline data-response-curve="{key}" points="{points}" fill="none" stroke="{color}" stroke-width="2"'
            + (' stroke-dasharray="5 4"' if dashed else "")
            + "/>"
        )
    return body + "</g>"


def response_svg(projection, limits):
    record = projection["signal_update"]
    grid = record["grid"]
    node = projection["node"]
    actual = record["correction_signal"]["real"]
    ideal = record["ideal_signal_correction"]["real"]
    amplitude = max(abs(v) for v in actual + ideal)
    radius = 1.08 * amplitude if amplitude else 1.0
    body = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 780" role="img" aria-label="Actual before and after waveforms, analytical unit kernel, and real signal correction">'
    body += '<rect width="960" height="780" rx="16" fill="#f7fafb"/>'
    body += _panel(
        grid,
        [
            ("before", record["previous_signal"]["real"], "#647488", True),
            ("after", record["next_signal"]["real"], "#ba5135", False),
        ],
        limits,
        70,
        160,
        "waveforms",
        "1 · Actual previous and completed waveforms",
        "Grey dashed: previous · orange: completed · same case-wide vertical scale as the main waveform",
        node,
    )
    body += _panel(
        grid,
        [("kernel", record["normalized_kernel"], "#2866b5", False)],
        (-0.3, 1.1),
        330,
        130,
        "kernel",
        "2 · Unit response from the finite Fourier sum",
        "K(t − t_j) = Σ exp(2π i q(t − t_j)) / 101 · fixed scale · K(0) = 1",
        node,
    )
    body += _panel(
        grid,
        [("actual", actual, "#ba5135", False), ("ideal", ideal, "#2866b5", True)],
        (-radius, radius),
        570,
        130,
        "correction",
        "3 · Real part of the signal change",
        "Orange: actual coefficient difference · blue dashed: exact-arithmetic kernel prediction",
        node,
    )
    body += (
        '<text x="24" y="744" font-size="12">'
        + escape(
            f"Correction axis rescales at each selection: ±{radius:.6e}; "
            + (
                "the real correction is exactly zero."
                if not amplitude
                else "height alone does not compare update size across steps."
            )
        )
        + "</text>"
    )
    body += '<text x="24" y="765" font-size="12">Vertical dashed line: actual selected node · display samples include that node · all curves show real parts</text></svg>'
    return body


def _number(value):
    return f"{value['real']:.6e} {value['imag']:+.6e}i"


def response_html(case, limits, selected_k):
    body = (
        '<details class="projection-response" open><summary>'
        + bi(
            "관측 하나에 맞추면 신호 전체가 어떻게 바뀔까?",
            "How does fitting one observation change the whole signal?",
        )
        + "</summary><p>"
        + bi(
            "투영은 선택한 관측만 덮어쓰는 것이 아니라 101개 계수를 함께 바꿉니다. 이 변화는 Fourier 합의 주기적 반응으로 퍼집니다. 첫 투영 버튼이나 위 반복점 선택으로 이전 파형과 실제 변화량을 확인하세요.",
            "A projection changes all 101 coefficients, rather than overwriting one observation. The finite Fourier sum spreads this change across the period. Use the first-projection button or snapshot selector to inspect the actual previous waveform and change.",
        )
        + '</p><p class="formula">'
    )
    body += (
        'Δc = (fⱼ − vⱼc) conj(vⱼ) / ‖vⱼ‖²<br>Δf(t) = (fⱼ − vⱼc) · 101 / ‖vⱼ‖² · K(t − tⱼ)</p><p class="small">'
        + bi(
            "두 번째 식은 정확한 산술에서의 유도식입니다. 실제 계수 차이와 그 파형을 따로 저장하며, 작아진 변화에서는 반올림 오차가 모양에 보일 수 있습니다. 파랑은 별도 알고리즘의 경로가 아닙니다. JavaScript 없이도 아래의 모든 단계 설명을 열 수 있습니다.",
            "The second formula is an exact-arithmetic derivation. Actual coefficient differences and their waveforms are stored separately; rounding may become visible when updates are tiny. Blue is not another algorithm. Every stage below remains available without JavaScript.",
        )
        + "</p>"
    )
    for method, run in case["runs"].items():
        for snapshot in run["snapshots"]:
            k = snapshot["iteration"]
            current = method == "weighted" and k == selected_k
            body += (
                '<details class="projection-frame'
                + (" is-current" if current else "")
                + f'" data-projection-frame="{method}-{k}"'
                + (" open" if current else "")
                + f"><summary>{method} · "
                + ("k=0" if not k else f"{k - 1} → {k}")
                + "</summary>"
            )
            projection = snapshot["last_projection"]
            if projection is None:
                body += (
                    "<p>"
                    + bi(
                        "초기값에는 완료한 투영이나 이전 파형이 없습니다.",
                        "The initial point has no completed projection or previous waveform.",
                    )
                    + "</p>"
                )
            else:
                record = projection["signal_update"]
                body += (
                    '<div class="projection-figure">' + response_svg(projection, limits) + "</div>"
                )
                body += (
                    '<p class="projection-readout" data-response-readout>'
                    + escape(
                        f"row {projection['row']} · t={projection['node']:.9f} · ‖vⱼ‖²={record['row_norm_squared']:.9f}"
                    )
                    + "<br>"
                    + escape(
                        f"prediction before: {_number(projection['prediction_before'])} · observed: {_number(projection['observed'])}"
                    )
                    + "<br>"
                    + escape(
                        f"prediction after: {_number(projection['prediction_after'])} · residual before: {_number(record['projection_residual'])}"
                    )
                    + "<br>"
                    + escape(
                        f"max |actual Δf − kernel prediction|={record['kernel_comparison_error_inf']:.6e} · max |(f_after − f_before) − Δf|={record['linearity_residual_inf']:.6e}"
                    )
                    + "</p>"
                )
            body += "</details>"
    return body + "</details>"
