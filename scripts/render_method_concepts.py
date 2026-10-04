"""Render deliberately rough, review-only scenes in GitHub Actions.

No trained model, production lesson or timing benchmark is created here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

INK = "#25313b"
GRAY = "#64717d"
LINE = "#d5dce2"
BLUE = "#2261ba"
GREEN = "#16805d"
RED = "#bb5139"
PALE = "#f1f4f7"
NAMES = ["Ava", "Ben", "Mia"]
PLACES = {"en": ["Library", "Garden", "Studio"], "ko": ["도서관", "정원", "작업실"]}
KEYS = [[float(i == j) for j in range(3)] for i in range(3)]
VALUES = [row[:] for row in KEYS]
GRID = [
    "000000000",
    "000010000",
    "000111000",
    "001000100",
    "011111110",
    "010000010",
    "010010010",
    "010000010",
    "011111110",
]
INPUT = [[float(v) for v in row] for row in GRID]
DELTA = [[0.0] * 9 for _ in range(9)]
DELTA[6][4] = -1.0
DELTA[5][3] = DELTA[5][5] = 1.0


def attention(selected, order=(0, 1, 2)):
    query = [4 * math.sqrt(3) * (i == selected) for i in range(3)]
    scores = [sum(q * k for q, k in zip(query, KEYS[i])) / math.sqrt(3) for i in order]
    exp = [math.exp(s - max(scores)) for s in scores]
    weights = [v / sum(exp) for v in exp]
    value = [sum(w * VALUES[i][j] for w, i in zip(weights, order)) for j in range(3)]
    return weights, value


def residual(alpha):
    correction = [[alpha * d for d in row] for row in DELTA]
    output = [[max(0.0, x + d) for x, d in zip(xs, ds)] for xs, ds in zip(INPUT, correction)]
    return correction, output


class Board:
    def __init__(self, lang, title, takeaway):
        self.lang = lang
        self.image = Image.new("RGB", (1200, 840), "white")
        self.d = ImageDraw.Draw(self.image)
        self.text("ROUGH SCENE / 검토용 시안", 36, 22, 17, color=GRAY)
        self.text(title, 36, 57, 40, width=1128)
        self.text(takeaway, 36, 117, 25, width=1128)
        self.d.line((36, 166, 1164, 166), fill=LINE, width=2)

    def text(self, value, x, y, size=22, width=1120, color=INK, center=False):
        path = (
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
            if self.lang == "ko" or any(ord(c) > 0x3000 for c in value)
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        )
        for actual in range(size, 13, -1):
            font = ImageFont.truetype(path, actual)
            if self.d.textlength(value, font=font) <= width:
                break
        else:
            raise ValueError(f"Text does not fit: {value}")
        anchor = "mt" if center else "lt"
        bounds = self.d.textbbox((x, y), value, font=font, anchor=anchor)
        assert bounds[0] >= 0 and bounds[1] >= 0 and bounds[2] <= 1200 and bounds[3] <= 840
        self.d.text((x, y), value, fill=color, font=font, anchor=anchor)

    def box(self, bounds, fill="white", outline=LINE, width=2):
        self.d.rounded_rectangle(bounds, radius=8, fill=fill, outline=outline, width=width)

    def arrow(self, points, color=GRAY, width=3):
        self.d.line(points, fill=color, width=width, joint="curve")
        (x0, y0), (x, y) = points[-2:]
        angle = math.atan2(y - y0, x - x0)
        size = max(10, width + 5)
        back = [
            (x - size * math.cos(angle + sign * 0.45), y - size * math.sin(angle + sign * 0.45))
            for sign in (-1, 1)
        ]
        self.d.polygon([(x, y), *back], fill=color)

    def grid(self, data, x, y, cell=16, signed=False):
        for i, row in enumerate(data):
            for j, v in enumerate(row):
                color = (GREEN if v > 0 else RED) if signed else INK
                rgb = tuple(int(color[k : k + 2], 16) for k in (1, 3, 5))
                fill = tuple(round(255 + abs(v) * (c - 255)) for c in rgb)
                self.d.rectangle(
                    (x + j * cell, y + i * cell, x + (j + 1) * cell - 1, y + (i + 1) * cell - 1),
                    fill=fill,
                    outline=LINE,
                )


def attention_board(lang, selected):
    ko = lang == "ko"
    b = Board(
        lang,
        "Attention",
        "질문이 바뀌면, 참고하는 정보가 바뀝니다."
        if ko
        else "Change the question. Change the information retrieved.",
    )
    weights, value = attention(selected)
    match = max(range(3), key=value.__getitem__)
    b.text(
        "같은 정보 3개 · 내용은 그대로" if ko else "Same three records. Nothing is edited.",
        633,
        188,
        20,
        center=True,
        width=590,
        color=GRAY,
    )
    # All links exist; thickness represents the computed weight.
    for i, w in enumerate(weights):
        y = 280 + i * 133
        color = BLUE if i == selected else LINE
        b.arrow([(307, 417), (395, y), (479, y)], color, max(2, round(w * 11)))
        b.arrow([(767, y), (879, y), (920, 417)], color, max(2, round(w * 11)))
        b.box(
            (480, y - 48, 766, y + 48),
            fill="#eef4fd" if i == selected else "white",
            outline=BLUE if i == selected else LINE,
        )
        b.text(NAMES[i], 500, y - 30, 23, width=240)
        b.text(PLACES[lang][i], 500, y + 6, 24, width=240, color=BLUE if i == selected else GRAY)
        b.text(
            f"{w:.1%}",
            819,
            y - 32,
            20,
            width=94,
            center=True,
            color=BLUE if i == selected else GRAY,
        )
    b.box((36, 365, 307, 469), fill=PALE, outline=INK)
    b.text("질문" if ko else "QUERY", 55, 381, 17, width=225, color=GRAY)
    b.text(
        f"{NAMES[selected]}의 위치는?" if ko else f"Where is {NAMES[selected]}?",
        55,
        414,
        26,
        width=230,
    )
    b.box((920, 365, 1164, 469), fill="#eef4fd", outline=BLUE)
    b.text("가장 큰 위치 성분" if ko else "LARGEST COMPONENT", 940, 381, 16, width=200, color=GRAY)
    b.text(PLACES[lang][match], 940, 414, 29, width=200, color=BLUE)
    b.text(
        "굵은 길 = 높은 주의 가중치" if ko else "Thicker route = greater attention weight",
        600,
        619,
        22,
        width=1080,
        center=True,
    )
    b.box((36, 669, 1164, 767), fill=PALE)
    b.text(
        "비교 · 항상 똑같이 평균 내면?" if ko else "Reference: always take the same average",
        57,
        686,
        22,
        width=1080,
    )
    b.text(
        "어떤 질문에도 도서관 33.3% · 정원 33.3% · 작업실 33.3%"
        if ko
        else "Every query: Library 33.3%  /  Garden 33.3%  /  Studio 33.3%",
        57,
        727,
        20,
        width=1080,
        color=GRAY,
    )
    b.text(
        "설명용 벡터 · 실제 가중합 계산 · 백분율은 정답 확률이 아닙니다."
        if ko
        else "Assigned vectors; computed weighted sum. Percentages are weights, not confidence.",
        36,
        803,
        17,
        width=1128,
        color=GRAY,
    )
    return b.image


def residual_board(lang, alpha):
    ko = lang == "ko"
    b = Board(
        lang,
        "ResNet",
        "원래 정보는 그대로 보내고, 수정분을 따로 더합니다."
        if ko
        else "Carry the input forward. Add the change separately.",
    )
    correction, output = residual(alpha)
    b.arrow([(215, 422), (270, 422), (270, 284), (476, 284)], GRAY)
    b.arrow([(630, 284), (830, 284), (830, 401)], GREEN)
    b.arrow([(270, 422), (270, 599), (830, 599), (830, 445)], BLUE, 7)
    b.arrow([(855, 422), (969, 422)], INK, 4)
    b.grid(INPUT, 70, 350)
    b.text("입력 특징 x" if ko else "Input features x", 142, 307, 23, width=240, center=True)
    b.grid(correction, 480, 219)
    b.text(
        "수정분 F(x)" if ko else "Residual F(x)", 552, 179, 24, width=300, center=True, color=GREEN
    )
    b.text(
        f"수정 강도 {alpha:.0%}" if ko else f"Correction {alpha:.0%}",
        552,
        384,
        24,
        width=340,
        center=True,
    )
    b.text(
        "초록 + / 주황 −" if ko else "Green + / orange −",
        552,
        423,
        19,
        width=330,
        center=True,
        color=GRAY,
    )
    b.d.ellipse((805, 397, 855, 447), fill="white", outline=INK, width=3)
    b.text("+", 830, 402, 35, width=46, center=True)
    b.grid(output, 975, 350)
    b.text("출력 x + F(x)" if ko else "Output x + F(x)", 1047, 307, 23, width=285, center=True)
    b.text(
        "같은 원본을 보내는 지름길" if ko else "Shortcut carries the original",
        550,
        553,
        24,
        width=510,
        center=True,
        color=BLUE,
    )
    # Every block below has zero residual, not the correction shown above.
    b.box((36, 649, 1164, 785), fill=PALE)
    b.text("모든 수정분이 0이면" if ko else "Set every residual to zero", 54, 667, 22, width=325)
    b.text(
        "이 입력은 그대로 남습니다." if ko else "This input stays unchanged.",
        54,
        711,
        19,
        width=325,
        color=GRAY,
    )
    for x, label in [
        (400, "입력" if ko else "Input"),
        (690, "1개 블록 후" if ko else "After 1 block"),
        (980, "8개 블록 후" if ko else "After 8 blocks"),
    ]:
        b.grid(INPUT, x, 698, cell=7)
        b.text(label, x + 31, 666, 18, width=210, center=True)
    b.arrow([(489, 730), (661, 730)], BLUE, 4)
    b.arrow([(779, 730), (951, 730)], BLUE, 4)
    b.text(
        "특징 격자 모형 · 지정한 수정분 · 학습 결과가 아닙니다. 같은 차원, 음수 없는 입력."
        if ko
        else "Feature-grid schematic, prescribed corrections; not training. Same dimensions; input ≥ 0.",
        36,
        803,
        16,
        width=1128,
        color=GRAY,
    )
    return b.image


def verify():
    expected = math.exp(4) / (math.exp(4) + 2)
    for selected in range(3):
        weights, value = attention(selected)
        assert math.isclose(weights[selected], expected, rel_tol=1e-14)
        assert math.isclose(sum(weights), 1.0, abs_tol=1e-14)
        assert value == weights
        assert max(range(3), key=value.__getitem__) == selected
        for i in range(3):
            if i != selected:
                assert math.isclose(weights[i], 1 / (math.exp(4) + 2), rel_tol=1e-14)
        _, shuffled = attention(selected, order=(2, 0, 1))
        assert all(math.isclose(a, b, abs_tol=1e-14) for a, b in zip(value, shuffled))
    for alpha in (0.0, 0.5, 1.0):
        correction, output = residual(alpha)
        for i in range(9):
            for j in range(9):
                assert 0 <= output[i][j] <= 1
                assert output[i][j] - INPUT[i][j] == correction[i][j]
        assert sum(c != 0 for row in correction for c in row) == (3 if alpha else 0)
    assert residual(1)[1][6][4] == 0
    assert residual(1)[1][5][3] == residual(1)[1][5][5] == 1
    propagated = [row[:] for row in INPUT]
    for _ in range(8):
        propagated = [[max(0.0, v + 0.0) for v in row] for row in propagated]
        assert propagated == INPUT
    return {
        "attention_matching_weight": expected,
        "fixed_mean": [1 / 3] * 3,
        "residual_changed_cells": 3,
        "zero_residual_identity_blocks": 8,
        "scope": "assigned vectors and prescribed corrections; no training benchmark",
        "checks": "attention normalization, closed form, lookup and permutation; residual addition, "
        "signed changes, range and eight-block zero-residual preservation",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    proof = verify()
    args.output.mkdir(parents=True, exist_ok=True)
    proof.update(source=args.source, size=[1200, 840], duration_ms=2400, files={})
    for lang in ("en", "ko"):
        for method, frames in [
            ("attention", [attention_board(lang, s) for s in (0, 2, 1)]),
            ("resnet", [residual_board(lang, a) for a in (0.0, 0.5, 1.0)]),
        ]:
            stem = f"{method}.{lang}"
            frames[1 if method == "attention" else 2].save(args.output / f"{stem}.png")
            frames[0].save(
                args.output / f"{stem}.gif",
                save_all=True,
                append_images=frames[1:],
                duration=2400,
                loop=0,
                disposal=2,
                optimize=False,
            )
            for ext in ("png", "gif"):
                path = args.output / f"{stem}.{ext}"
                with Image.open(path) as decoded:
                    assert decoded.size == (1200, 840)
                    assert getattr(decoded, "n_frames", 1) == (3 if ext == "gif" else 1)
                    for i in range(getattr(decoded, "n_frames", 1)):
                        decoded.seek(i)
                        decoded.load()
                raw = path.read_bytes()
                proof["files"][path.name] = {
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
    (args.output / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
