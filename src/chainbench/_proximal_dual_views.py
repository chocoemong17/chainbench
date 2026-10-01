"""Feasible dual coordinates and the height of the same residual candidates."""

from html import escape

import numpy as np

from ._pages import bi


def _value(w, geometry):
    nu = np.asarray(w) * geometry["box_half_width"]
    return float(-0.5 * (nu @ nu) - np.array([1.4, -2.4]) @ nu)


def _project(w, value, geometry, surface):
    u, v = w
    if surface:
        z = (value - geometry["surface_minimum"]) / (
            geometry["surface_maximum"] - geometry["surface_minimum"]
        )
        return 310 + 145 * u + 70 * v, 320 - 35 * u + 65 * v - 150 * z
    return 310 + 155 * u, 245 - 155 * v


def _points(points):
    return " ".join(",".join(f"{v:.5f}" for v in xy) for xy in points)


def _frames(points):
    return "|".join(",".join(f"{v:.5f}" for v in xy) for xy in points)


def dual_svg(case, *, surface=False):
    g = case["dual_geometry"]

    def project(w):
        return _project(w, _value(w, g), g, surface)

    title = "Dual height D(ν) over the feasible box" if surface else "Feasible dual box: |aᵢνᵢ| ≤ λ"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 490" role="img" aria-label="{title}" data-dual-space="{"surface" if surface else "plane"}">',
        '<rect width="620" height="490" rx="16" fill="#f4f8fa"/>',
        f'<text x="20" y="28" font-size="16" fill="#172238">{title}</text>',
        '<text x="20" y="50" font-size="11" fill="#44556a">wᵢ = νᵢ / (λ/|aᵢ|) · normalized coordinates, not original equal units</text>',
    ]
    if surface:
        for axis in (0, 1):
            for fixed in np.linspace(-1, 1, 13):
                coords = [
                    project([fixed, free] if axis == 0 else [free, fixed])
                    for free in np.linspace(-1, 1, 33)
                ]
                parts.append(
                    '<polyline data-dual-mesh="" points="'
                    + _points(coords)
                    + '" fill="none" stroke="#b6cbd2"/>'
                )
        parts.append('<path d="M95 290 V140" stroke="#526e83" stroke-width="1.5"/>')
        parts.append(
            '<text x="85" y="130" font-size="12">D(ν)</text><text x="83" y="146" text-anchor="end" font-size="10">D*</text><text x="83" y="295" text-anchor="end" font-size="10">D_min</text>'
        )
        floor = [
            _project(w, g["surface_minimum"], g, True)
            for w in [(-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1)]
        ]
        parts.append(
            '<polyline points="'
            + _points(floor)
            + '" fill="none" stroke="#8397a7" stroke-dasharray="4 4"/>'
        )
        parts.append(
            f'<text x="20" y="445" font-size="11">Height scale: D_min={g["surface_minimum"]:.5g} to D*={g["surface_maximum"]:.5g}</text>'
        )
        parts.append(
            '<text x="20" y="464" font-size="11">Same box and height scale for every step within this λ; chords join samples.</text>'
        )
        parts.append(
            '<text x="444" y="381" font-size="12">w₁</text><text x="225" y="428" font-size="12">w₂</text>'
        )
    else:
        clip = "dual-box-" + case["id"]
        parts.append(
            f'<defs><clipPath id="{clip}"><rect x="155" y="90" width="310" height="310"/></clipPath></defs>'
        )
        parts.append(
            '<rect x="155" y="90" width="310" height="310" fill="white" stroke="#3d8297" stroke-width="2"/>'
        )
        parts.append(f'<g clip-path="url(#{clip})">')
        center = np.array([-1.4, 2.4])
        offset = np.linalg.norm(np.asarray(g["reference"]) - center) ** 2
        theta = np.linspace(0, 2 * np.pi, 1025)
        for deficit in g["contour_deficits"]:
            radius = np.sqrt(offset + 2 * deficit)
            nu = center + radius * np.column_stack((np.cos(theta), np.sin(theta)))
            coords = [_project(w, 0, g, False) for w in nu / np.asarray(g["box_half_width"])]
            parts.append(
                f'<polyline data-dual-contour="{deficit!r}" points="'
                + _points(coords)
                + '" fill="none" stroke="#bbd0d7"/>'
            )
        parts.append("</g>")
        parts.append(
            '<path d="M155 245 H465 M310 90 V400" stroke="#b7c4d1" stroke-dasharray="4 4"/>'
        )
        for v in (-1, 0, 1):
            parts.append(
                f'<text x="{310 + 155 * v}" y="420" font-size="12" text-anchor="middle">{v}</text>'
            )
            parts.append(
                f'<text x="142" y="{249 - 155 * v}" font-size="12" text-anchor="end">{v}</text>'
            )
        parts.append(
            '<text x="483" y="249" font-size="13">w₁</text><text x="310" y="78" text-anchor="middle" font-size="13">w₂</text>'
        )
        parts.append(
            '<text x="20" y="445" font-size="11">Contours: D*−D = 10%, 30%, 60%, 90% of this box’s value range</text>'
        )
        parts.append(
            '<text x="20" y="464" font-size="11">Green ν* is a known diagonal reference; current candidate is orange.</text>'
        )
    for method, color in (("ista", "#236e9a"), ("fista", "#bd4c34")):
        coords = [
            _project(d["normalized"], d["lower_bound"], g, surface) for d in g["runs"][method]
        ]
        parts.append(
            f'<polyline data-dual-path="{method}" data-points="{_frames(coords)}" points="{_points(coords)}" fill="none" stroke="{color}" stroke-width="2.2" stroke-dasharray="{"none" if method == "ista" else "6 4"}"/>'
        )
    star = _project(g["reference_normalized"], g["reference_value"], g, surface)
    if surface:
        base = _project(g["reference_normalized"], g["surface_minimum"], g, True)
        parts.append(
            f'<line x1="{base[0]:.5f}" y1="{base[1]:.5f}" x2="{star[0]:.5f}" y2="{star[1]:.5f}" stroke="#137f69" stroke-dasharray="3 4"/>'
        )
        frames = {
            m: [
                (
                    *_project(d["normalized"], g["surface_minimum"], g, True),
                    *_project(d["normalized"], d["lower_bound"], g, True),
                )
                for d in points[1:]
            ]
            for m, points in g["runs"].items()
        }
        attrs = " ".join(f'data-{m}="{_frames(coords)}"' for m, coords in frames.items())
        x1, y1, x2, y2 = frames["fista"][0]
        parts.append(
            f'<line data-dual-height="" data-prox-attrs="x1,y1,x2,y2" {attrs} x1="{x1:.5f}" y1="{y1:.5f}" x2="{x2:.5f}" y2="{y2:.5f}" stroke="#b57821" stroke-dasharray="3 4"/>'
        )
    parts.append(
        f'<circle data-dual-reference="" cx="{star[0]:.5f}" cy="{star[1]:.5f}" r="6" fill="#137f69" stroke="white"/>'
    )
    parts.append(f'<text x="{star[0] + 9:.5f}" y="{star[1] - 8:.5f}" font-size="12">ν*</text>')
    for key, offset, color in (("previous", 0, "#4c6174"), ("next", 1, "#d18a24")):
        frames = {
            m: [
                _project(d["normalized"], d["lower_bound"], g, surface)
                for d in points[offset : len(points) - 1 + offset]
            ]
            for m, points in g["runs"].items()
        }
        attrs = " ".join(f'data-{m}="{_frames(coords)}"' for m, coords in frames.items())
        x, y = frames["fista"][0]
        parts.append(
            f'<circle data-dual-marker="{key}" data-prox-attrs="cx,cy" {attrs} cx="{x:.5f}" cy="{y:.5f}" r="4.5" fill="{color}" stroke="white"/>'
        )
    return "".join(parts) + "</svg>"


def dual_html(case):
    if "dual_geometry" not in case:
        return ""
    g = case["dual_geometry"]
    first = g["runs"]["fista"][1]
    body = (
        '<section class="prox-dual"><h3>'
        + bi("잔차에서 쌍대 하한으로", "From the residual to a dual lower bound")
        + "</h3><p>"
        + bi(
            "위 단계에서 완성한 다음 점 xₖ₊₁의 잔차를 사용합니다. ν=sr를 쌍대 제약 안으로 줄이면, 그 점의 높이 D(ν)가 최적값 F*의 하한이 됩니다. 이 점들은 별도의 쌍대 최적화 알고리즘이 만든 경로가 아니라 기존 반복점의 진단값입니다.",
            "Use the residual of the next iterate xₖ₊₁ completed by the selected stage. Shrink ν=sr into the dual constraint; its height D(ν) is a lower bound on the optimum. These points diagnose existing primal iterates; they are not a separate dual optimizer’s path.",
        )
        + "</p>"
    )
    body += '<div class="formula">F(x)=½‖Ax−b‖²+λ‖x‖₁ ; r=Ax−b\nν=s r ; ‖Aᵀν‖∞≤λ ; D(ν)=−½‖ν‖²−bᵀν\nD(ν) ≤ F* ≤ F(x)</div>'
    body += (
        "<p>"
        + bi(
            "여기서는 제곱 손실 앞에 ½가 있습니다. 영상 실험의 ν=2sr, −¼‖ν‖²와 계수가 다릅니다. s=(1−10⁻¹²)min(1, λ/‖Aᵀr‖∞)이며 분모가 0이면 min 항은 1입니다.",
            "This fixture has a half-squared loss. Its factors differ from the image experiment’s ν=2sr and −¼‖ν‖². Here s=(1−10⁻¹²)min(1, λ/‖Aᵀr‖∞); a zero denominator uses a min term of 1.",
        )
        + "</p>"
    )
    body += (
        '<div class="dual-visual-grid"><div class="prox-dual-figure">'
        + dual_svg(case)
        + '</div><div class="prox-dual-figure">'
        + dual_svg(case, surface=True)
        + "</div></div>"
    )
    body += (
        '<p class="small">'
        + bi(
            "파랑 ISTA · 빨강 FISTA · 회색 이전 후보 · 주황 다음 후보 · 초록 ν*. 직사각형을 보기 쉽게 wᵢ=νᵢ/(λ/|aᵢ|)로 정규화했습니다. 원래 ν 좌표의 가로·세로 단위는 서로 다릅니다. 좁은 화면에서는 그림과 표를 가로로 스크롤할 수 있습니다.",
            "Blue ISTA · red FISTA · grey previous candidate · orange next candidate · green ν*. Coordinates wᵢ=νᵢ/(λ/|aᵢ|) normalize the rectangle; original ν units differ between axes. Figures and tables scroll horizontally on narrow screens.",
        )
        + "</p>"
    )
    body += '<p class="formula" data-dual-values>' + _readout("fista", first) + "</p>"
    body += (
        "<p>"
        + bi(
            "이 대각 예제에서는 ν*=clip(−b, −λ/|a|, λ/|a|)를 독립적으로 압니다. D=½‖b‖²−½‖ν+b‖²이므로, 직사각형에서 −b에 가장 가까운 점이 최고점을 이룹니다. 초록 점은 이 계산으로 얻은 참조값이며 알고리즘이 수렴했다고 가정한 값이 아닙니다.",
            "For this diagonal fixture, ν*=clip(−b, −λ/|a|, λ/|a|) is independently known. Since D=½‖b‖²−½‖ν+b‖², the feasible point nearest −b has the greatest height. The green point is this analytic reference, not an assumed converged iterate.",
        )
        + "</p>"
    )
    body += (
        '<div class="formula">F−D = (F−F*) + (D*−D)\n'
        + bi(
            "실제 primal 오차 + 쌍대 후보에 남은 오차",
            "Actual primal error + deficit of the dual candidate",
        )
        + "</div><p>"
        + bi(
            "상한 F−D에는 두 오차가 합쳐집니다. 그래서 복원점의 실제 오차보다 클 수 있습니다. 알려진 참조값은 이 설명과 안정적인 수치 대조에만 사용하며, 잔차 후보 ν를 만드는 데 쓰지 않습니다. 원래 잔차는 아래 표에 그대로 남깁니다.",
            "F−D contains both errors, so it can exceed the actual primal error. The known references support this explanation and stable numerical comparison; they are not used to construct ν. The unscaled residual remains in the table.",
        )
        + "</p>"
    )
    body += (
        "<details><summary>"
        + bi("모든 반복점의 잔차·후보·하한", "Every iterate: residual, candidate and lower bound")
        + '</summary><div class="scroll"><table><tr><th>method / k</th><th>r</th><th>ν</th><th>s</th><th>D</th><th>F−F*</th><th>D*−D</th><th>F−D</th></tr>'
    )
    for method, points in g["runs"].items():
        for d in points:
            body += f'<tr data-dual-row="{method}-{d["iteration"]}"><td>{method.upper()} / {d["iteration"]}</td>'
            for key in ("residual", "nu"):
                body += "<td>" + escape(str([float(f"{v:.8g}") for v in d[key]])) + "</td>"
            body += (
                "".join(
                    f"<td>{d[key]:.9e}</td>"
                    for key in (
                        "scale",
                        "lower_bound",
                        "primal_gap",
                        "dual_deficit",
                        "suboptimality_upper_bound",
                    )
                )
                + "</tr>"
            )
    body += (
        '</table></div></details><p class="small"><a href="https://web.stanford.edu/~boyd/papers/pdf/l1_ls.pdf#page=4">Kim et al. (2007), §III-B / Eqs. (10), (12)</a> · '
        + bi(
            "½ 제곱 손실로 환산한 쌍대식과 별도의 보수적 잔차 스케일입니다. 부동소수점 검사이며 구간연산 인증은 아닙니다. 원 논문의 내부점 알고리즘·실험을 재현한 것은 아닙니다.",
            "The dual is rescaled to half-squared loss, with an added conservative residual scale. Checks use floating point, not interval certification. This does not reproduce the source interior-point solver or experiments.",
        )
        + "</p></section>"
    )
    return body


def _readout(method, d):
    return f"{method.upper()} · completed k={d['iteration']} · D={d['lower_bound']:.6g} · F−F*={d['primal_gap']:.6g} · D*−D={d['dual_deficit']:.6g} · F−D={d['suboptimality_upper_bound']:.6g}"
