"""Actual objective curves along the existing Frank–Wolfe oracle direction."""

from html import escape

from ._pages import bi


def scale(case):
    profiles = [row["segment"] for row in case["rows"][:-1]]
    low = min(min(p["affine"]) for p in profiles)
    high = max(max(p["objective"]) for p in profiles)
    span = high - low or 1.0
    return low - 0.06 * span, high + 0.06 * span


def xy(limits, gamma, value):
    low, high = limits
    return 86 + 460 * gamma, 302 - 210 * (value - low) / (high - low)


def pairs(points):
    return " ".join(f"{x:.5f},{y:.5f}" for x, y in points)


def ray_elements(case, project, *, curve):
    profiles = [row["segment"] for row in case["rows"][:-1]]
    body = []
    if curve:
        frames = [
            pairs([project(x, value) for x, value in zip(p["points"], p["objective"])])
            for p in profiles
        ]
        body.append(
            f'<polyline data-segment-ray="" data-segment-frames="{escape("|".join(frames), quote=True)}" points="{frames[0]}" fill="none" stroke="#8454a6" stroke-width="2.3"/>'
        )
    coords = [project(p["minimum_point"], p["minimum_value"]) for p in profiles]
    frames = "|".join(f"{x:.5f},{y:.5f}" for x, y in coords)
    x, y = coords[0]
    body.append(
        f'<circle data-segment-marker="minimum" data-fw-attrs="cx,cy" data-frames="{frames}" cx="{x:.5f}" cy="{y:.5f}" r="9" stroke="#8454a6" fill="none" stroke-width="2.2"/>'
    )
    return "".join(body)


def profile_svg(case):
    profiles = [row["segment"] for row in case["rows"][:-1]]
    low, high = scale(case)
    body = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 405" role="img" aria-label="Objective along the chosen feasible segment">',
        '<rect width="620" height="405" rx="16" fill="#fbfaf7"/>',
        '<text x="20" y="28" font-size="16" fill="#172238">How far along the chosen direction?</text>',
        '<text x="20" y="50" font-size="11" fill="#475569">Purple: actual objective · grey dashed: affine prediction</text>',
        '<rect x="86" y="92" width="460" height="210" fill="white" stroke="#cbd5e1"/>',
    ]
    for f in (0, 0.5, 1):
        value = low + f * (high - low)
        y = 302 - 210 * f
        body.append(
            f'<path d="M86 {y} H546" stroke="#e2e8f0"/><text x="78" y="{y + 4}" text-anchor="end" font-size="11" fill="#475569">{value:.3g}</text>'
        )
    for gamma in (0, 0.25, 0.5, 0.75, 1):
        x = 86 + 460 * gamma
        body.append(
            f'<text x="{x}" y="324" text-anchor="middle" font-size="11" fill="#475569">{gamma:g}</text>'
        )
    for key, color, dash in [("affine", "#768495", "5 4"), ("objective", "#8454a6", "none")]:
        frames = [
            pairs([xy((low, high), g, v) for g, v in zip(p["parameter"], p[key])]) for p in profiles
        ]
        body.append(
            f'<polyline data-segment-curve="{key}" data-segment-frames="{escape("|".join(frames), quote=True)}" points="{frames[0]}" fill="none" stroke="{color}" stroke-width="2.5" stroke-dasharray="{dash}"/>'
        )
    for key, color, radius in [
        ("current", "#287698", 4.5),
        ("scheduled", "#148365", 5),
        ("minimum", "#8454a6", 8),
    ]:
        coords = []
        for row, p in zip(case["rows"][:-1], profiles):
            index = (
                0
                if key == "current"
                else p["scheduled_index"]
                if key == "scheduled"
                else p["minimum_index"]
            )
            coords.append(xy((low, high), p["parameter"][index], p["objective"][index]))
        frames = "|".join(f"{x:.5f},{y:.5f}" for x, y in coords)
        x, y = coords[0]
        body.append(
            f'<circle data-segment-marker="{key}" data-fw-attrs="cx,cy" data-frames="{frames}" cx="{x:.5f}" cy="{y:.5f}" r="{radius}" stroke="{color}" fill="{"none" if key == "minimum" else color}" stroke-width="2"/>'
        )
    body.extend(
        [
            '<text x="316" y="348" text-anchor="middle" font-size="12" fill="#334155">γ: fraction of the feasible segment [0,1]</text>',
            '<text x="20" y="375" font-size="11" fill="#475569">Blue: current · green: scheduled next · purple ring: segment minimum</text>',
            '<text x="20" y="394" font-size="11" fill="#475569">Same value scale across this case; the local alternative does not advance a second run.</text>',
            "</svg>",
        ]
    )
    return "".join(body)


def segment_html(case):
    if "segment" not in case["rows"][0]:
        return ""
    first = case["rows"][0]
    p = first["segment"]
    body = (
        '<section class="fw-segment"><h3>'
        + bi(
            "방향을 골랐다면, 얼마나 이동할까?",
            "After choosing a direction, how far should we move?",
        )
        + "</h3>"
    )
    body += (
        "<p>"
        + bi(
            "기존 경로의 현재 점과 오라클 꼭짓점 사이에서 목적함수를 직접 계산했습니다. 보라색 곡선은 실제 목적값, 회색 점선은 접하는 선형 근사입니다. 3D 그림의 보라색 선도 같은 선분의 실제 목적함수 높이를 보여줍니다.",
            "Evaluate the objective between this recorded iterate and its oracle vertex. Purple is the actual objective; grey dashed is its affine prediction. The purple curve in the 3D view shows these same feasible points at their actual objective heights.",
        )
        + "</p>"
    )
    body += '<p class="small fw-segment-scroll-cue">' + bi(
        '그림을 좌우로 움직여 전체 구간을 볼 수 있습니다.',
        'Scroll the diagram horizontally to inspect the whole segment.',
    ) + '</p>'
    body += ('<div class="fw-segment-figure" tabindex="0" role="region" '
             'aria-label="Feasible-segment profile; scroll horizontally on narrow screens">'
             + profile_svg(case) + "</div>")
    body += '<div class="formula">d=s−x ; q=‖d‖² ; slope=∇f(x)ᵀd=−g_FW(x)<br>φ(γ)=f(x)+γ·slope+½γ²q ; 0≤γ≤1<br>γ_min=clip(−slope/q,0,1) ; q=0 → choose γ_min=0</div>'
    body += '<p data-segment-values class="fw-readout">' + readout(first, case["rows"][1]) + "</p>"
    body += (
        "<p>"
        + bi(
            "보라색 고리는 이 선분에서 수식으로 구한 최저점입니다. 초록 점은 원래 고정 규칙 γₖ=2/(k+2)로 실제 계산한 다음 점입니다. 고리의 점에서 새 반복을 시작하지 않으므로 두 알고리즘의 전체 성능 비교가 아닙니다.",
            "The purple ring is the analytic minimum of this one segment. Green is the actual next point from the original schedule γ_k=2/(k+2). We do not advance a new run from the ring; this is not a comparison of two complete algorithms.",
        )
        + "</p>"
    )
    body += (
        '<p class="small">'
        + bi(
            "q>0이면 변화량은 γ·slope+½γ²q입니다. 음수인 초기 기울기만으로 큰 보폭의 감소까지 보장하지 않습니다. 세로축은 같은 사례의 모든 단계에서 고정됩니다. 부동소수점에서 전개식과 직접 계산이 다른 원래 차이도 JSON에 남깁니다.",
            "For q>0 the change is γ·slope+½γ²q. A negative initial slope does not ensure descent for a large step. The value scale is fixed across this case. JSON retains raw differences between the quadratic expansion and direct floating-point evaluation.",
        )
        + "</p>"
    )
    body += (
        '<p class="small"><a href="https://proceedings.mlr.press/v28/jaggi13.pdf">Jaggi (2013), Algorithm 3 · PDF page 3</a> · '
        + bi("이 이차함수에 대한 유도된 설명", "Derived explanation for this quadratic family")
        + "</p>"
    )
    body += (
        "<details><summary>"
        + bi(
            "모든 선분의 실제 보폭과 국소 최저점", "Every scheduled step and local segment minimum"
        )
        + '</summary><div class="scroll"><table><tr><th>k</th><th>γ scheduled</th><th>γ_min</th><th>f(current)</th><th>f(actual next)</th><th>f(segment min)</th><th>slope</th><th>q</th></tr>'
    )
    for row, nxt in zip(case["rows"], case["rows"][1:]):
        p = row["segment"]
        body += f'<tr data-segment-row="{row["iteration"]}"><td>{row["iteration"]}</td>'
        for value in (
            row["gamma"],
            p["minimum_gamma"],
            row["gap"],
            nxt["gap"],
            p["minimum_value"],
            p["slope"],
            p["direction_norm_squared"],
        ):
            body += f"<td>{value:.6g}</td>"
        body += "</tr>"
    body += "</table></div></details></section>"
    return body


def readout(row, nxt):
    p = row["segment"]
    return (
        f"k={row['iteration']} · γ={row['gamma']:.6g} · γ_min={p['minimum_gamma']:.6g}"
        f" · f(current)={row['gap']:.6g} · f(actual next)={nxt['gap']:.6g}"
        f" · f(segment min)={p['minimum_value']:.6g}"
    )
