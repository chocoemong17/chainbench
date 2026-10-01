"""Actual objective intervals at the saved noisy-image iterates."""

from ._pages import bi


def duality_html(result):
    if "duality" not in result:
        return ""
    last = result["parameters"]["steps"]
    body = (
        "<section data-wavelet-duality><h2>"
        + bi(
            "최적값을 몰라도 얼마나 남았는지 가늠하기",
            "Bound the remaining objective improvement without knowing the optimum",
        )
        + "</h2><p>"
        + bi(
            "현재 복원값 F는 최적값의 위쪽에 있습니다. 잔차로 만든 쌍대 가능점 ν의 값 D는 아래쪽에 있습니다. 따라서 남은 개선량 F−F*는 F−D보다 클 수 없습니다. 실제 최적값의 위치는 여전히 모릅니다.",
            "The current objective F lies above the optimum. A feasible dual point ν gives a lower value D. Remaining improvement F−F* cannot exceed F−D; the location of the optimum is still unknown.",
        )
        + '</p><div class="formula">A = R W ; r = A c − b\nν = 2 s r ; ‖Aᵀν‖∞ ≤ λ\nD(ν) = −¼‖ν‖² − bᵀν\nD ≤ F* ≤ F ; 0 ≤ F − F* ≤ F − D</div><p>'
        + bi(
            "s는 잔차를 쌍대 제약 안으로 줄이는 값입니다. 원문의 쌍대식에서 유도한 보수적 변형으로, 1보다 키우지 않고 1−10⁻¹²의 여유를 둡니다. 최적화 반복이나 영상에는 적용하지 않습니다.",
            "The scale s shrinks the residual into the dual constraint. This conservative variant derived from the source dual problem caps the scale at 1 and adds a factor 1−10⁻¹². It does not modify the optimization iterates or images.",
        )
        + '</p><div class="formula">h = ‖2 Aᵀr‖∞\ns = (1−10⁻¹²) min(1, λ/h) ; h=0: s=1−10⁻¹²</div><p>'
        + bi(
            "영상 위의 저장점 선택과 함께 바뀝니다. 두 방법은 같은 가로 척도를 사용하고, 저장점을 바꾸면 척도를 다시 잡습니다. 구간의 폭은 확률이나 영상 오차가 아닙니다.",
            "Follows the snapshot selector above. Both methods share one horizontal scale, rescaled at each snapshot. Interval width is neither a probability nor an image error.",
        )
        + "</p><div data-dual-bracket-view>"
    )
    for k in result["parameters"]["snapshot_iterations"]:
        bounds = [
            (m, next(s["dual_bound"] for s in run["snapshots"] if s["iteration"] == k))
            for m, run in result["runs"].items()
        ]
        lo = min(0.0, *(d["lower_bound"] for _, d in bounds))
        hi = max(d["primal_objective"] for _, d in bounds)
        # Only an all-zero interval uses a display extent of one; values remain exact.
        span = hi - lo or 1.0

        def x(value):
            return 90 + 450 * (value - lo) / span

        body += f'<div data-dual-snapshot="{k}"' + ("" if k == last else " hidden") + ">"
        body += f"<p><b>k={k} · D ≤ F* ≤ F</b> · " + bi("공통 척도", "Shared scale")
        body += f': [{lo:.6e}, {hi:.6e}]</p><div class="scroll"><svg width="620" height="170" viewBox="0 0 620 170" role="img" aria-label="Dual lower bound to primal upper bound, optimum position unknown">'
        for j, (method, d) in enumerate(bounds):
            y = 45 + j * 75
            left, right = x(d["lower_bound"]), x(d["primal_objective"])
            body += f'<g data-dual-method="{method}" data-axis-min="{lo!r}" data-axis-span="{span!r}"><text x="12" y="{y + 5}" font-size="13">{method.upper()}</text>'
            body += f'<line x1="90" y1="{y}" x2="540" y2="{y}" stroke="#dce4ed"/>'
            body += f'<line data-dual-interval x1="{left:.10f}" x2="{right:.10f}" y1="{y}" y2="{y}" stroke="#507cb7" stroke-width="8"/>'
            for pos, color, label, value in [
                (left, "#25806c", "D", d["lower_bound"]),
                (right, "#b45d24", "F", d["primal_objective"]),
            ]:
                body += f'<circle cx="{pos:.10f}" cy="{y}" r="5" fill="{color}"/><text x="{pos:.10f}" y="{y - 14 if label == "D" else y + 25}" text-anchor="middle" font-size="11">{label}={value:.4e}</text>'
            body += "</g>"
        body += "</svg></div>"
        for method, d in bounds:
            body += f'<p data-dual-readout="{method}"><b>{method.upper()}</b> · F−D={d["suboptimality_upper_bound"]:.9e} · ‖Aᵀν‖∞={d["dual_adjoint_inf"]:.12e} ≤ λ=1.000000000000e−04 · s={d["scale"]:.9e}</p>'
        body += "</div>"
    body += (
        "</div><p>"
        + bi(
            "F−D은 알려지지 않은 F−F*의 상한입니다. 하한 D는 단조 증가하지 않을 수 있으며, 모든 저장점의 원래 값을 아래에 남깁니다. 작은 구간만이 작은 목적함수 오차를 뜻합니다. 부동소수점 가능성 검사이며 구간연산에 의한 엄밀 인증은 아닙니다.",
            "F−D bounds the unknown F−F*. D need not increase monotonically; the original values at every snapshot appear below. Only a small interval implies a small objective error. Feasibility is checked in floating point, not certified by interval arithmetic.",
        )
        + "</p><details data-dual-table><summary>"
        + bi("모든 저장점의 상·하한과 가능성 검사", "Every snapshot: bounds and feasibility")
        + '</summary><div class="scroll"><table><thead><tr><th>Method</th><th>k</th><th>D</th><th>F</th><th>F−D</th><th>‖Aᵀν‖∞</th><th>λ−‖Aᵀν‖∞</th><th>s</th></tr></thead><tbody>'
    )
    for method, run in result["runs"].items():
        for s in run["snapshots"]:
            d = s["dual_bound"]
            body += f"<tr data-dual-table-row><td>{method.upper()}</td><td>{s['iteration']}</td>"
            body += (
                "".join(
                    f"<td>{d[key]:.12e}</td>"
                    for key in (
                        "lower_bound",
                        "primal_objective",
                        "suboptimality_upper_bound",
                        "dual_adjoint_inf",
                        "feasibility_margin",
                        "scale",
                    )
                )
                + "</tr>"
            )
    body += (
        '</tbody></table></div></details><p><a href="https://web.stanford.edu/~boyd/papers/pdf/l1_ls.pdf#page=4">Kim et al. (2007), §III-B, Eqs. (10), (12), p.609</a> · '
        + bi(
            "기존 Beck–Teboulle 실험을 해석하는 추가 진단입니다. Kim 등의 내부점 알고리즘이나 MRI 실험을 재현한 것은 아닙니다.",
            "An added diagnostic for the existing Beck–Teboulle experiment. This does not reproduce Kim et al.’s interior-point algorithm or MRI experiments.",
        )
        + "</p></section>"
    )
    return body
