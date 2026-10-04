"""Four-stage, review-only explanations; calculations/rendering run in Actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image
from render_method_concepts import (
    BLUE,
    DELTA,
    GRAY,
    GREEN,
    INK,
    INPUT,
    LINE,
    NAMES,
    PALE,
    PLACES,
    RED,
    Board,
    attention,
    residual,
    verify,
)


def stage(lang, method, number, en, ko):
    return Board(lang, f"{method}  /  {number} of 4", ko if lang == "ko" else en)


def note(b, first, second, third=None):
    b.box((36, 672, 1164, 785), fill=PALE)
    b.text(first, 56, 688, 23, width=1088)
    b.text(second, 56, 728, 20, width=1088, color=GRAY)
    if third:
        b.text(third, 36, 807, 16, width=1128, color=GRAY)


def attention_roles(lang):
    ko = lang == "ko"
    b = stage(
        lang, "Attention", 1, "What do Q, K and V actually do?", "Q·K·V는 각각 무엇을 하나요?"
    )
    b.box((36, 240, 339, 436), fill="#edf4ff", outline=BLUE)
    b.text("Q · Query", 57, 263, 28, width=260, color=BLUE)
    b.text("찾으려는 것" if ko else "What I am looking for", 57, 310, 24, width=260)
    b.text("Mia의 위치는?" if ko else "Where is Mia?", 57, 371, 29, width=260)
    b.text("K · Key", 536, 206, 28, center=True, width=270)
    b.text(
        "맞춰 볼 이름표" if ko else "What to match against", 536, 250, 20, center=True, width=300
    )
    b.text("V · Value", 970, 206, 28, center=True, width=320, color=GREEN)
    b.text("가져올 내용" if ko else "Information to retrieve", 970, 250, 20, center=True, width=330)
    for i, name in enumerate(NAMES):
        y = 325 + 103 * i
        color = BLUE if i == 2 else LINE
        b.arrow([(340, 390), (397, y), (430, y)], color, 6 if i == 2 else 2)
        b.box((433, y - 30, 640, y + 30), outline=color)
        b.text(name, 536, y - 16, 25, width=190, center=True)
        b.arrow([(645, y), (801, y)], color, 4 if i == 2 else 2)
        b.box((805, y - 30, 1136, y + 30), outline=GREEN if i == 2 else LINE)
        b.text(PLACES[lang][i], 970, y - 16, 25, width=290, center=True)
    b.text("Q와 K를 비교" if ko else "Compare Q with each K", 378, 588, 23, width=350, center=True)
    b.text(
        "점수로 V의 비중을 정함" if ko else "Scores control how much V to use",
        910,
        588,
        23,
        width=500,
        center=True,
        color=GREEN,
    )
    note(
        b,
        "이름표 K와 실제 내용 V는 역할이 다릅니다."
        if ko
        else "The matching key and the returned value have different jobs.",
        "다음: “Mia와 얼마나 관련 있나?”를 숫자로 계산합니다."
        if ko
        else "Next: turn “how relevant to Mia?” into numerical scores.",
        "이름·위치 벡터를 지정한 설명용 예시입니다."
        if ko
        else "Teaching example with assigned name/location vectors.",
    )
    return b.image


def attention_scores(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "Attention",
        2,
        "Similarity scores become a share of attention.",
        "관련도 점수를 “얼마나 참고할지”로 바꿉니다.",
    )
    b.text("Q = √3 × [0, 0, 4]  ·  Mia", 55, 199, 28, width=1090, color=BLUE)
    heads = ["Key (K)", "Q·K / √3", "Softmax → 비중" if ko else "Softmax → weight"]
    for x, text in zip((260, 633, 997), heads):
        b.text(text, x, 267, 23, width=320, center=True)
    weights, _ = attention(2)
    for i in range(3):
        y = 338 + i * 88
        vec = ", ".join("1" if j == i else "0" for j in range(3))
        b.box((55, y - 15, 1160, y + 53), fill="#edf4ff" if i == 2 else PALE)
        b.text(f"{NAMES[i]}   [{vec}]", 80, y, 24, width=380)
        b.text(str(4 if i == 2 else 0), 633, y, 26, width=200, center=True)
        b.text(
            f"{weights[i]:.1%}", 996, y, 28, width=250, center=True, color=BLUE if i == 2 else GRAY
        )
    b.text(
        "e⁰ : e⁰ : e⁴  →  1 : 1 : 54.6  →  1.8% : 1.8% : 96.5%",
        600,
        610,
        24,
        width=1100,
        center=True,
    )
    note(
        b,
        "Softmax: 큰 점수에 더 큰 비중을 주고, 합을 1로 맞춥니다."
        if ko
        else "Softmax favors larger scores and makes the weights add to one.",
        "√3은 Key 차원 수의 제곱근입니다. 차원이 클 때 점수 크기를 조절합니다."
        if ko
        else "Divide by √3, the square root of the key dimension, to control the score scale.",
        "표시값은 반올림했습니다. 비중은 정답 확률이 아닙니다."
        if ko
        else "Rounded weights; these are not answer-confidence probabilities.",
    )
    return b.image


def attention_values(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "Attention",
        3,
        "Use the weights to combine information, not just pick a row.",
        "비중만큼 내용을 모읍니다. 한 줄만 고르는 것은 아닙니다.",
    )
    weights, value = attention(2)
    b.text(
        "위치 벡터 순서: 도서관 / 정원 / 작업실"
        if ko
        else "Location coordinates: Library / Garden / Studio",
        55,
        194,
        23,
        width=1090,
        color=GRAY,
    )
    for i in range(3):
        y = 267 + 76 * i
        vec = ", ".join("1" if j == i else "0" for j in range(3))
        b.text(f"{weights[i]:.1%} × [{vec}]", 80, y, 29, width=580, color=BLUE if i == 2 else INK)
        b.text(PLACES[lang][i], 520, y, 24, width=300)
    b.d.line((70, 482, 815, 482), fill=LINE, width=2)
    b.text("Σ", 70, 508, 30, width=60, color=GREEN)
    b.text("[" + ", ".join(f"{v:.3f}" for v in value) + "]", 138, 508, 32, width=665, color=GREEN)
    b.box((843, 267, 1145, 558), fill=PALE)
    b.text("출력 특징" if ko else "Output features", 994, 287, 23, width=270, center=True)
    for i, v in enumerate(value):
        y = 346 + 63 * i
        b.text(PLACES[lang][i], 862, y - 4, 19, width=116)
        b.d.rectangle((982, y, 1124, y + 24), fill=LINE)
        b.d.rectangle((982, y, 982 + 142 * v, y + 24), fill=BLUE)
    b.text("Q를 Ava로 바꾸면 → [0.965, 0.018, 0.018]", 80, 605, 25, width=1080) if ko else b.text(
        "Change Q to Ava → [0.965, 0.018, 0.018]", 80, 605, 25, width=1080
    )
    note(
        b,
        "Mia와 관련 있는 작업실 정보가 출력에 가장 크게 반영됩니다."
        if ko
        else "The output now contains mostly the Studio information relevant to Mia.",
        "실제 모델에서는 다음 층이 이렇게 모은 특징을 사용합니다."
        if ko
        else "In a model, the next layer uses these aggregated features.",
        "O = softmax(QKᵀ / √dₖ)V · 모든 V의 가중합입니다."
        if ko
        else "O = softmax(QKᵀ / √dₖ)V. Every V contributes to the weighted sum.",
    )
    return b.image


def attention_context(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "Attention",
        4,
        "Self-attention: every token gets to ask its own question.",
        "Self-attention: 각 단어가 자기 질문으로 맥락을 모읍니다.",
    )
    b.box((40, 215, 345, 442), fill=PALE)
    b.text("토큰 표현 X" if ko else "Token representations X", 192, 237, 25, width=280, center=True)
    for i, token in enumerate(["The", "cat", "sleeps"]):
        b.text(token, 95, 296 + 43 * i, 23, width=210)
    for i, (label, color) in enumerate([("Q = XWq", BLUE), ("K = XWk", INK), ("V = XWv", GREEN)]):
        y = 242 + 84 * i
        b.arrow([(349, 329), (415, y + 25)], LINE, 2)
        b.box((420, y, 655, y + 58), outline=color)
        b.text(label, 537, y + 14, 25, width=210, center=True, color=color)
    b.arrow([(660, 325), (760, 325)], GRAY)
    b.box((765, 215, 1160, 464), fill="#edf4ff", outline=BLUE)
    b.text("각 Q ↔ 모든 K" if ko else "Each Q ↔ all keys", 962, 237, 26, width=360, center=True)
    for i, text in enumerate(
        ["The → Σ weights × V", "cat → Σ weights × V", "sleeps → Σ weights × V"]
    ):
        b.text(text, 789, 304 + i * 45, 22, width=340)
    b.text(
        "같은 X에서 Q·K·V를 만들기 때문에 “Self”입니다."
        if ko
        else "“Self” means Q, K and V come from the same sequence.",
        600,
        500,
        23,
        width=1110,
        center=True,
    )
    for x, label in [(45, "Head 1"), (412, "Head 2"), (779, "Head 3")]:
        b.box((x, 550, x + 348, 626), outline=GREEN)
        b.text(
            label + " · " + ("다른 W" if ko else "different W"),
            x + 174,
            564,
            22,
            width=320,
            center=True,
        )
        b.text("Q/K/V → Attention", x + 174, 596, 19, width=320, center=True, color=GRAY)
    note(
        b,
        "여러 head가 서로 다른 변환으로 정보를 모으고, 결과를 합칩니다."
        if ko
        else "Heads use different projections; their results are concatenated and projected.",
        "W는 학습으로 조정됩니다. 먼 단어도 한 층에서 직접 참고할 수 있습니다."
        if ko
        else "Training adjusts W. Even distant tokens can interact directly within a layer.",
        "구조 설명도입니다. 이 문장의 실제 학습된 가중치를 표시한 것은 아닙니다."
        if ko
        else "Architecture schematic, not measured attention weights for this sentence.",
    )
    return b.image


def resnet_goal(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "ResNet",
        1,
        "Why learn a correction instead of a whole new mapping?",
        "왜 전체 결과 대신 “수정분”을 배우나요?",
    )
    _, target = residual(1)
    for x, data, label in [
        (65, INPUT, "입력 x" if ko else "Input x"),
        (518, target, "원하는 H(x)" if ko else "Desired H(x)"),
        (942, DELTA, "차이 H(x) − x" if ko else "Difference H(x) − x"),
    ]:
        b.grid(data, x, 245, cell=19, signed=data is DELTA)
        b.text(label, x + 85, 201, 23, width=305, center=True)
    b.arrow([(247, 330), (500, 330)], GRAY, 3)
    b.text(
        "바꿀 부분은 3칸" if ko else "Only 3 cells change",
        825,
        442,
        24,
        width=550,
        center=True,
        color=GREEN,
    )
    b.box((40, 487, 566, 624), fill=PALE)
    b.text("직접 매핑" if ko else "Direct mapping", 63, 508, 25, width=475)
    b.text("학습할 목표: H(x)" if ko else "Learning target: H(x)", 63, 557, 28, width=475)
    b.box((604, 487, 1161, 624), fill="#ecf6f1", outline=GREEN)
    b.text("잔차 매핑 + 지름길" if ko else "Residual mapping + shortcut", 628, 508, 25, width=500)
    b.text(
        "학습할 목표: F(x) = H(x) − x" if ko else "Learning target: F(x) = H(x) − x",
        628,
        557,
        26,
        width=500,
    )
    note(
        b,
        "잘 작동하는 정보를 유지하려면, 추가 블록의 수정분은 0이면 됩니다."
        if ko
        else "To preserve useful features, an added residual block can learn zero correction.",
        "깊게 쌓아도 학습이 더 어려워지는 문제를 줄이려는 설계입니다."
        if ko
        else "This reformulation addresses the optimization difficulty of increasing depth.",
        "격자는 잔차 목표를 설명하는 모형입니다. 이미지 복원 학습 결과가 아닙니다."
        if ko
        else "The grids illustrate learning targets; they are not trained image-restoration results.",
    )
    return b.image


def block_numbers(x=2.0, w1=1.0, b1=0.0, w2=-0.1, b2=0.3, target=2.2):
    h = max(0.0, w1 * x + b1)
    f = w2 * h + b2
    z = x + f
    y = max(0.0, z)
    loss = 0.5 * (y - target) ** 2
    g = (y - target) * (z > 0)
    slope = w2 * w1 * (h > 0)
    return dict(
        x=x,
        h=h,
        f=f,
        y=y,
        loss=loss,
        incoming=g,
        shortcut=g,
        branch=g * slope,
        total=g * (1 + slope),
        w2_grad=g * h,
    )


def block_layout(b, backwards=False):
    color = RED if backwards else INK
    upper = [(230, 434), (300, 434), (300, 285), (430, 285)]
    after = [(710, 285), (834, 285), (834, 410)]
    lower = [(300, 434), (300, 595), (834, 595), (834, 460)]
    right = [(862, 434), (1000, 434)]
    for points in (upper, after, right):
        b.arrow(list(reversed(points)) if backwards else points, color, 4)
    b.arrow(list(reversed(lower)) if backwards else lower, BLUE, 6)
    b.box((430, 231, 710, 340), outline=GREEN)
    b.text("F(x) = −0.1x + 0.3", 570, 249, 24, width=255, center=True)
    b.text("F′(x) = −0.1", 570, 293, 24, width=255, center=True, color=GREEN)
    b.d.ellipse((807, 408, 861, 462), fill="white", outline=INK, width=3)
    b.text("+", 834, 412, 36, width=46, center=True)


def resnet_forward(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "ResNet",
        2,
        "Forward: predict first, then measure the error.",
        "순전파: 먼저 예측하고, 정답과 얼마나 다른지 봅니다.",
    )
    n = block_numbers()
    block_layout(b)
    b.text("입력 x" if ko else "Input x", 132, 379, 23, width=215, center=True)
    b.text(f"{n['x']:.1f}", 132, 427, 35, width=210, center=True)
    b.text("수정분" if ko else "Correction", 570, 365, 22, width=260, center=True, color=GREEN)
    b.text(f"{n['f']:+.1f}", 570, 409, 32, width=260, center=True, color=GREEN)
    b.text("예측 y" if ko else "Prediction y", 1070, 378, 23, width=205, center=True)
    b.text(f"{n['y']:.1f}", 1070, 427, 35, width=205, center=True)
    b.text(
        "원본 2.0을 그대로 전달" if ko else "Carry the original 2.0 unchanged",
        562,
        552,
        25,
        width=480,
        center=True,
        color=BLUE,
    )
    note(
        b,
        "예측 2.1, 정답 2.2 → 아직 조금 부족합니다."
        if ko
        else "Prediction 2.1, target 2.2 → the prediction is still too small.",
        f"Loss = ½ × (2.1 − 2.2)² = {n['loss']:.3f}",
        "이 점에서는 ReLU가 켜져 있습니다. F는 두 층 가지를 단순화한 실제 식입니다."
        if ko
        else "ReLU is active here. F is the local expression of a declared two-layer branch.",
    )
    return b.image


def resnet_backward(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "ResNet",
        3,
        "Backward: the learning signal has two paths to earlier layers.",
        "역전파: 앞쪽 층으로 학습 신호가 두 길을 따라 돌아갑니다.",
    )
    n = block_numbers()
    b.text(
        "기울기 = 값을 조금 바꾸면 오차가 얼마나 달라지는지 알려주는 신호"
        if ko
        else "Gradient = how a small change in a value affects the loss",
        55,
        187,
        21,
        width=1090,
        color=GRAY,
    )
    block_layout(b, backwards=True)
    b.text("두 경로를 합침" if ko else "Sum both paths", 138, 368, 22, width=255, center=True)
    b.text(f"{n['total']:.2f}", 138, 414, 36, width=255, center=True, color=RED)
    b.text("오차에서 온 신호" if ko else "Signal from loss", 1050, 367, 22, width=265, center=True)
    b.text(f"{n['incoming']:.2f}", 1060, 414, 36, width=230, center=True, color=RED)
    b.text(
        "가지 경로" if ko else "Through the branch",
        565,
        365,
        21,
        width=375,
        center=True,
        color=GREEN,
    )
    b.text("−0.10 × (−0.1) = +0.01", 565, 407, 27, width=430, center=True, color=GREEN)
    b.text(
        "지름길: −0.10 × 1 = −0.10" if ko else "Shortcut: −0.10 × 1 = −0.10",
        566,
        549,
        26,
        width=520,
        center=True,
        color=BLUE,
    )
    note(
        b,
        "앞쪽 신호 = −0.10 + 0.01 = −0.09"
        if ko
        else "Signal to the earlier layer = −0.10 + 0.01 = −0.09",
        "지름길은 학습 신호를 직접 전달하고, 가지의 가중치도 계속 학습합니다."
        if ko
        else "The shortcut carries a direct signal; the branch weights still learn as well.",
        "신호는 기울기입니다. dL/dw₂ = −0.20. 더 큰 기울기가 항상 더 좋은 것은 아닙니다."
        if ko
        else "Signals are gradients. dL/dw₂ = −0.20. Larger gradients are not always better.",
    )
    return b.image


def depth_case(residual_path, x=1.0, n=8):
    slopes = []
    for _ in range(n):
        z = x + (-0.1 * x + 0.1) if residual_path else -0.1 * x + 1.1
        slopes.append((0.9 if residual_path else -0.1) * (z > 0))
        x = max(0.0, z)
    g = x  # loss = x_final^2 / 2, target 0
    gradients = [g]
    for s in reversed(slopes):
        g *= s
        gradients.append(g)
    return x, gradients


def resnet_depth(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "ResNet",
        4,
        "Why can this help when the network is deep?",
        "층이 깊어질 때, 이 지름길은 왜 도움이 될까요?",
    )
    b.text(
        "입력 특징까지 거슬러 전달되는 |기울기| · 설명용 8개 블록"
        if ko
        else "|Gradient| sent backward to earlier features · 8-block scalar illustration",
        55,
        191,
        22,
        width=1090,
    )
    # Log plot: each grid interval is a factor of 100; zero is never plotted.
    left, top, width, height = 117, 271, 790, 317
    for exponent in (0, -2, -4, -6, -8):
        y = top - exponent / 8 * height
        b.d.line((left, y, left + width, y), fill=LINE, width=1)
        b.text("1" if exponent == 0 else f"10^{exponent}", 37, y - 10, 17, width=77)
    for n in (0, 2, 4, 6, 8):
        x = left + n / 8 * width
        b.text(str(n), x, 605, 18, width=30, center=True)
    for is_residual, color in [(False, RED), (True, BLUE)]:
        _, gradients = depth_case(is_residual)
        pts = [
            (left + i / 8 * width, top - math.log10(abs(g)) / 8 * height)
            for i, g in enumerate(gradients)
        ]
        b.d.line(pts, fill=color, width=5)
        for x, y in pts:
            b.d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)
    b.text("지름길 있음" if ko else "With shortcut", 934, 284, 22, width=238, color=BLUE)
    b.text("0.9⁸ ≈ 0.430", 934, 328, 24, width=238, color=BLUE)
    b.text("직접 매핑" if ko else "Plain mapping", 934, 477, 22, width=238, color=RED)
    b.text("0.1⁸ = 10⁻⁸", 934, 521, 24, width=238, color=RED)
    b.text(
        "뒤로 통과한 블록 수 →" if ko else "Blocks traversed backward →",
        510,
        633,
        18,
        width=700,
        center=True,
    )
    note(
        b,
        "작은 가지 미분을 계속 곱하는 길 외에, 직접 전달되는 항이 생깁니다."
        if ko
        else "The shortcut adds a direct term instead of relying only on small branch derivatives.",
        "설정: 직접 매핑 미분 −0.1 / 잔차 가지 미분 −0.1 → 전체 미분 0.9"
        if ko
        else "Chosen slopes: plain −0.1; residual branch −0.1 → total block slope 0.9.",
        "수치 모형입니다. 정확도 비교가 아닙니다. F′=−1의 상쇄 또는 꺼진 ReLU에서는 신호가 0일 수 있습니다."
        if ko
        else "Numerical illustration, not accuracy evidence. Cancellation at F′=−1 or an inactive ReLU can still zero the signal.",
    )
    return b.image


def verify_explanations():
    proof = verify()
    n = block_numbers()
    for k, expected in dict(
        f=0.1,
        y=2.1,
        loss=0.005,
        incoming=-0.1,
        branch=0.01,
        shortcut=-0.1,
        total=-0.09,
        w2_grad=-0.2,
    ).items():
        assert math.isclose(n[k], expected, abs_tol=1e-13), k
    eps = 1e-5
    gx = (block_numbers(x=2 + eps)["loss"] - block_numbers(x=2 - eps)["loss"]) / (2 * eps)
    gw = (block_numbers(w2=-0.1 + eps)["loss"] - block_numbers(w2=-0.1 - eps)["loss"]) / (2 * eps)
    assert math.isclose(gx, n["total"], rel_tol=1e-8)
    assert math.isclose(gw, n["w2_grad"], rel_tol=1e-8)
    assert block_numbers(w2=-0.08)["loss"] < n["loss"]
    # The direct term is not a non-vanishing theorem.
    assert block_numbers(w2=-1, b2=3)["total"] == 0
    assert block_numbers(w2=-2, b2=0)["total"] == 0
    depth = {}
    for skip in (False, True):
        output, gs = depth_case(skip)
        expected = 0.9**8 if skip else (-0.1) ** 8
        assert output == 1
        assert math.isclose(gs[-1], expected, rel_tol=1e-13)
        h = 1e-3
        plus = depth_case(skip, x=1 + h)[0]
        minus = depth_case(skip, x=1 - h)[0]
        finite_difference = (0.5 * plus**2 - 0.5 * minus**2) / (2 * h)
        assert math.isclose(finite_difference, gs[-1], rel_tol=1e-4, abs_tol=2e-12)
        depth["residual" if skip else "plain"] = dict(
            output=output, gradients=gs, finite_difference=finite_difference
        )
    proof.update(
        single_block=n,
        depth=depth,
        gradient_checks="chain rule, central differences, cancellation and inactive-ReLU controls",
    )
    return proof


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--source", required=True)
    args = p.parse_args()
    proof = verify_explanations()
    args.output.mkdir(parents=True, exist_ok=True)
    proof.update(
        source=args.source,
        size=[1200, 840],
        frames=4,
        frame_duration_ms=[6500, 8000, 8000, 7500],
        files={},
    )
    makers = {
        "attention": [attention_roles, attention_scores, attention_values, attention_context],
        "resnet": [resnet_goal, resnet_forward, resnet_backward, resnet_depth],
    }
    for lang in ("en", "ko"):
        for method, scenes in makers.items():
            frames = [make(lang) for make in scenes]
            for i, frame in enumerate(frames, 1):
                frame.save(args.output / f"{method}.{lang}.{i}.png")
            frames[0].save(
                args.output / f"{method}.{lang}.gif",
                save_all=True,
                append_images=frames[1:],
                duration=proof["frame_duration_ms"],
                loop=0,
                disposal=2,
                optimize=False,
            )
    for path in sorted(args.output.iterdir()):
        if path.suffix not in (".png", ".gif"):
            continue
        with Image.open(path) as decoded:
            assert decoded.size == (1200, 840)
            assert getattr(decoded, "n_frames", 1) == (4 if path.suffix == ".gif" else 1)
            for i in range(getattr(decoded, "n_frames", 1)):
                decoded.seek(i)
                decoded.load()
                if path.suffix == ".gif":
                    assert decoded.info["duration"] == proof["frame_duration_ms"][i]
        raw = path.read_bytes()
        proof["files"][path.name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    (args.output / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
