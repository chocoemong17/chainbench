"""Render low-cost review storyboards in Actions, never production films."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("foundations", ROOT / "review/learning_foundations.py")
model = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model)

INK, GRAY, LINE = "#26333d", "#596974", "#d8dfe3"
BLUE, GREEN, ORANGE = "#225daf", "#117257", "#b24729"
PALE = "#eff3f5"
SIZE = (1200, 760)


class Board:
    def __init__(self, lang, title, scene, caption):
        self.ko = lang == "ko"
        self.image = Image.new("RGB", SIZE, "white")
        self.d = ImageDraw.Draw(self.image)
        self.text("CONCEPT / 시안   ·   " + str(scene + 1) + " / 4", 36, 20, 18, color=GRAY)
        self.text(title, 36, 58, 38)
        self.text(caption, 36, 117, 25)
        self.d.line((36, 165, 1164, 165), fill=LINE, width=2)

    def text(self, value, x, y, size=24, width=1128, color=INK, center=False):
        path = ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
                if any(ord(c) > 0x3000 for c in value)
                else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        for actual in range(size, 17, -1):
            font = ImageFont.truetype(path, actual)
            if self.d.textlength(value, font=font) <= width:
                break
        else:
            raise ValueError(f"Text does not fit at readable size: {value}")
        missing = font.getmask(chr(0x10FFFF))
        for char in set(value):
            if ord(char) > 127 and not char.isspace():
                glyph = font.getmask(char)
                if glyph.size == missing.size and bytes(glyph) == bytes(missing):
                    raise ValueError(f"Missing glyph: {char!r}")
        anchor = "mt" if center else "lt"
        bounds = self.d.textbbox((x, y), value, font=font, anchor=anchor)
        if not (0 <= bounds[0] <= bounds[2] <= SIZE[0]
                and 0 <= bounds[1] <= bounds[3] <= SIZE[1]):
            raise ValueError(f"Text outside canvas: {value}")
        self.d.text((x, y), value, fill=color, font=font, anchor=anchor)

    def box(self, bounds, fill=PALE, outline=LINE):
        self.d.rounded_rectangle(bounds, radius=8, fill=fill, outline=outline, width=2)

    def arrow(self, points, color=BLUE, width=4):
        self.d.line(points, fill=color, width=width, joint="curve")
        (x0, y0), (x, y) = points[-2:]
        angle = math.atan2(y - y0, x - x0)
        back = [(x - 14 * math.cos(angle + sign * .45),
                 y - 14 * math.sin(angle + sign * .45)) for sign in (-1, 1)]
        self.d.polygon([(x, y), *back], fill=color)

    def grid(self, data, x, y, cell=36, max_value=1, numbers=False):
        for r, row in enumerate(data):
            for c, value in enumerate(row):
                strength = min(1, abs(value) / max_value)
                color = ORANGE if value < 0 else BLUE
                rgb = [int(color[k:k+2], 16) for k in (1, 3, 5)]
                fill = tuple(round(255 + strength * (v - 255)) for v in rgb)
                left, top = x + c * cell, y + r * cell
                self.d.rectangle((left, top, left+cell-1, top+cell-1), fill=fill, outline=LINE)
                if numbers:
                    self.text(str(value), left + cell/2, top + 8, 22,
                              width=cell-2, color="white" if strength > .5 else INK, center=True)

    def note(self, en, ko):
        self.text(ko if self.ko else en, 36, 706, 19, color=GRAY)

    def banner(self, en, ko, y=600):
        self.box((36, y, 1164, y+76))
        self.text(ko if self.ko else en, 58, y+25, 24, width=1084)


def backprop(lang, scene):
    ko = lang == "ko"
    captions = [
        ("A prediction misses the target. Which weights should change?", "예측이 목표와 다릅니다. 어느 연결을 얼마나 고쳐야 할까요?"),
        ("Send a change signal backward, using the values already computed.", "앞에서 계산한 값을 재사용해, 변화 신호를 뒤로 보냅니다."),
        ("An optimizer uses those signals to take one small step.", "최적화 방법이 그 신호를 받아 연결의 값을 조금 바꿉니다."),
        ("Backprop computes the signals. Adam can choose the steps.", "역전파는 변화 신호를 구하고, Adam은 이동할 보폭을 정할 수 있습니다."),
    ]
    b = Board(lang, "Backpropagation / 역전파" if ko else "Backpropagation", scene, captions[scene][ko])
    w1, w2 = model.update() if scene == 2 else (1.0, .5)
    hidden, output, loss = model.forward(w1, w2)
    for x, value, label in [(130, 2, "입력" if ko else "Input"),
                             (475, hidden, "중간 값" if ko else "Hidden value"),
                             (820, output, "예측" if ko else "Prediction")]:
        b.text(label, x, 218, 23, width=240, center=True)
        b.box((x-79, 270, x+79, 370), outline=BLUE)
        b.text(f"{value:g}", x, 294, 40, width=150, center=True, color=BLUE)
    for x, w in ((303, w1), (648, w2)):
        b.arrow([(x-90, 320), (x+85, 320)])
        b.text(f"× {w:g}", x, 261, 29, width=160, center=True)
    b.text("목표" if ko else "Target", 1080, 218, 23, width=150, center=True)
    b.box((1010, 270, 1150, 370), fill="#f2f7f3", outline=GREEN)
    b.text("2", 1080, 294, 40, width=110, center=True, color=GREEN)
    if scene == 1:
        b.arrow([(1080, 405), (820, 405), (475, 405), (130, 405)], ORANGE, 5)
        b.text("출력의 변화 신호 −1" if ko else "Output change signal −1", 1075, 452,
               22, width=230, center=True, color=ORANGE)
        for x, value in ((303, "−1"), (648, "−2")):
            b.text("연결의 기울기" if ko else "Weight gradient", x, 450, 23, width=260, center=True)
            b.text(value, x, 495, 40, width=140, center=True, color=ORANGE)
        b.banner("Negative here: increasing either weight slightly lowers the loss.",
                 "이 예시의 음수 신호: 해당 연결 값을 조금 키우면 오차가 줄어듭니다.")
    elif scene == 2:
        b.text("연결 값  1 → 1.1     /     0.5 → 0.7" if ko else "Weights  1 → 1.1     /     0.5 → 0.7",
               70, 435, 30)
        b.text(f"Loss  0.5000 → {loss:.4f}", 70, 500, 36, color=GREEN)
        b.banner("One gradient-descent step, rate 0.1. A step that is too large can fail.",
                 "경사하강 한 번, 보폭 계수 0.1. 너무 크게 움직이면 오차가 커질 수 있습니다.")
    elif scene == 3:
        for x, title, detail in [(60, "역전파" if ko else "Backprop",
                                  "어디를 바꾸면 오차가 변할까?" if ko else "How does each weight affect the loss?"),
                                 (645, "최적화 방법" if ko else "Optimizer",
                                  "어느 방향으로 얼마나 움직일까?" if ko else "Which direction and how far to move?")]:
            b.box((x, 445, x+490, 566))
            b.text(title, x+24, 463, 28, width=450)
            b.text(detail, x+24, 514, 22, width=446)
        b.banner("Reuse intermediate results to compute gradients through the whole chain.",
                 "중간 계산을 재사용하면서, 여러 연결의 변화 신호를 함께 구합니다.")
    else:
        b.text("예측과 목표의 차이  −1" if ko else "Prediction minus target  −1", 80, 445, 29)
        b.text("Loss  0.5", 80, 510, 37, color=ORANGE)
        b.banner("Changing every weight blindly gives no useful direction.",
                 "연결마다 오차에 미치는 영향을 알면, 고칠 방향을 계산할 수 있습니다.")
    b.note("Chosen two-weight linear chain; squared loss. Not the paper's sigmoid experiment.",
           "직접 정한 두 연결의 선형 모형·제곱 오차. 원문의 sigmoid 실험 재현은 아닙니다.")
    return b.image


def cnn(lang, scene):
    ko = lang == "ko"
    captions = [
        ("Slide the same small detector over the image.", "작은 무늬 탐지기를 그림의 여러 위치에서 똑같이 사용합니다."),
        ("Move the pattern: the strong response moves with it.", "무늬를 옮기면, 크게 반응하는 위치도 함께 옮겨집니다."),
        ("Different filters notice different patterns.", "다른 탐지기는 다른 무늬에 반응합니다."),
        ("Reuse weights across positions instead of relearning each location.", "위치마다 새로 배우지 않고, 같은 연결 값을 여러 위치에서 공유합니다."),
    ]
    b = Board(lang, "CNN / 합성곱 신경망" if ko else "CNN / convolution", scene, captions[scene][ko])
    data = model.picture()
    if scene == 0:
        b.text("입력 그림" if ko else "Image", 70, 200, 25)
        b.grid(data, 70, 253)
        b.d.rectangle((108, 329, 222, 443), outline=ORANGE, width=5)
        b.text("같은 3×3 탐지기" if ko else "One 3×3 filter", 505, 200, 23, width=260)
        b.grid(model.VERTICAL, 512, 290, 48, 2, True)
        b.arrow([(432, 386), (490, 386)])
        b.text("반응 지도" if ko else "Response map", 797, 200, 25)
        b.grid(model.correlate(data, model.VERTICAL), 798, 290, 42, 6)
        b.text("6", 861, 382, 24, width=40, color="white", center=True)
        b.arrow([(677, 386), (778, 386)])
        b.banner("Three central pixels × 2 = 6; side pixels here contribute zero.",
                 "선택한 창: 가운데 세 칸 × 2 = 6. 양옆의 빈 칸은 0을 더합니다.")
    elif scene == 1:
        for x, shift in ((70, 0), (690, 1)):
            b.text(("옮기기 전" if shift == 0 else "오른쪽 한 칸") if ko
                   else ("Before" if shift == 0 else "One cell to the right"), x, 198, 25)
            b.grid(model.picture(shift), x, 247, 32)
            b.text("반응 지도" if ko else "Response map", x, 483, 21)
            b.grid(model.correlate(model.picture(shift), model.VERTICAL), x+172, 486, 19, 6)
        b.arrow([(411, 350), (649, 350)])
        b.banner("The response follows position; this is not complete position invariance.",
                 "반응하는 위치가 따라 움직입니다. 위치 정보가 사라지는 것은 아닙니다.")
    elif scene == 2:
        for x, kernel, label in [(65, model.VERTICAL, "세로" if ko else "Vertical"),
                                  (660, model.HORIZONTAL, "가로" if ko else "Horizontal")]:
            b.text(label, x, 210, 30)
            b.grid(kernel, x, 296, 40, 2, True)
            b.arrow([(x+130, 356), (x+171, 356)])
            b.grid(model.correlate(data, kernel), x+184, 287, 40, 6)
        b.banner("A CNN learns filters from examples. We chose these two to show the mechanism.",
                 "실제 CNN은 탐지기를 학습합니다. 여기서는 원리가 보이도록 두 개를 정했습니다.")
    else:
        for x, title, number, detail in [
            (65, "공유하는 경우" if ko else "Shared filters", "18", "2 × 3 × 3"),
            (650, "위치마다 별도인 경우" if ko else "Separate at every position", "630", "2 × 35 × 3 × 3")]:
            b.box((x, 225, x+484, 530))
            b.text(title, x+25, 250, 25, width=434)
            b.text(number, x+242, 320, 82, width=420, center=True, color=BLUE)
            b.text(detail, x+242, 449, 28, width=434, center=True)
        b.banner("For this grid: two filters, 35 positions, no bias. Sharing saves parameters.",
                 "이 격자에서 탐지기 2개·위치 35개·편향 제외. 공유하면 배울 값이 줄어듭니다.")
    b.note("Hand-set filters; stride 1, valid cross-correlation + ReLU. Not a trained LeNet.",
           "직접 정한 필터·보폭 1·패딩 없는 상관 연산과 ReLU. LeNet 학습 결과는 아닙니다.")
    return b.image


def dropout(lang, scene):
    ko = lang == "ko"
    captions = [
        ("If a few units always work together, the network can rely on that team.",
         "늘 같은 특징들만 함께 쓰면, 그 조합에 지나치게 의존할 수 있습니다."),
        ("During training, temporarily leave some units out.",
         "학습할 때 일부 특징을 잠깐 쉬게 합니다."),
        ("A new training case can use a different combination.",
         "다음 학습에서는 다른 조합이 일하도록 바꿉니다."),
        ("At prediction time, use all units with the paper's scaled weights.",
         "예측할 때는 모두 사용하고, 원문의 방식대로 연결의 크기를 조절합니다."),
    ]
    b = Board(lang, "Dropout", scene, captions[scene][ko])
    masks = ((1, 1, 1, 1), (1, 1, 0, 0), (0, 0, 1, 1), (1, 1, 1, 1))
    mask = masks[scene]
    scale = .5 if scene == 3 else 1
    b.text("특징값" if ko else "Feature values", 260, 193, 23)
    b.text("합한 값" if ko else "Sum", 940, 255, 24, width=220, center=True)
    for i, (value, keep) in enumerate(zip(model.FEATURES, mask)):
        y = 270 + 88*i
        color = BLUE if keep else LINE
        b.arrow([(354, y), (845, 415)], color, 4 if keep else 2)
        b.d.ellipse((268, y-30, 328, y+30), fill=PALE if keep else "white", outline=color, width=3)
        b.text(f"{value:g}", 298, y-16, 28, width=50, center=True, color=BLUE if keep else GRAY)
        if not keep:
            b.d.line((269, y-29, 327, y+29), fill=ORANGE, width=4)
            b.text("쉼" if ko else "off", 180, y-15, 22, width=85, center=True, color=ORANGE)
    b.box((865, 350, 1065, 465), outline=BLUE)
    b.text(f"{scale * model.dropout(mask):g}", 965, 380, 47, width=180, center=True, color=BLUE)
    if scene == 3:
        b.text("각 연결 × 0.5" if ko else "Each weight × 0.5", 525, 233, 27, width=450)
        b.banner("All 16 masks average to 5 in this linear sum. Everyone participates at test time.",
                 "이 선형 합에서 16개 조합의 평균은 5. 예측할 때는 모든 특징이 참여합니다.")
    elif scene in (1, 2):
        b.text("특징마다 참여 확률 50%" if ko else "Each unit: 50% chance to stay", 500, 228, 26, width=650)
        b.text("여기서는 두 조합을 골라 보여줍니다." if ko else "Two selected masks are shown here.",
               500, 280, 22, width=650, color=GRAY)
        b.banner("A unit can return next time. It is not permanently deleted.",
                 "다음에는 다시 참여할 수 있습니다. 연결을 영구히 없애는 방법은 아닙니다.")
    else:
        b.banner("The aim: reduce reliance on a fixed team, to help with unseen examples.",
                 "목표: 고정된 조합에만 의존하는 것을 줄여, 처음 보는 예에도 잘 대응하게 하기.")
    b.note("Fixed features, chosen masks; no training or measured accuracy gain. Linear mean only.",
           "고정 특징·선택한 조합의 시안. 학습·정확도 향상 실험이 아니며 평균의 일치는 선형 합에 한합니다.")
    return b.image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{40}", args.source):
        raise ValueError("A full source SHA is required")
    proof = model.verification()
    proof.update(source=args.source, status="concept-pending-owner-review", size=SIZE,
                 frame_ms=5000, files={})
    args.output.mkdir(parents=True, exist_ok=False)
    contacts = []
    for lang in ("en", "ko"):
        for name, renderer in (("backprop", backprop), ("cnn", cnn), ("dropout", dropout)):
            frames = [renderer(lang, scene) for scene in range(4)]
            for i, frame in enumerate(frames):
                frame.save(args.output / f"{name}.{lang}.{i+1}.png")
            frames[0].save(args.output / f"{name}.{lang}.gif", save_all=True,
                           append_images=frames[1:], duration=5000, loop=0, disposal=2)
            contact = Image.new("RGB", (1200, 760))
            for i, frame in enumerate(frames):
                contact.paste(frame.resize((600, 380)), ((i % 2)*600, (i // 2)*380))
            contact.save(args.output / f"{name}.{lang}.contact.png")
            contacts.append(contact)
    for path in sorted(args.output.glob("*")):
        with Image.open(path) as decoded:
            count = getattr(decoded, "n_frames", 1)
            assert count == (4 if path.suffix == ".gif" else 1)
            assert decoded.size == SIZE
            for i in range(count):
                decoded.seek(i)
                decoded.load()
                if path.suffix == ".gif":
                    assert decoded.info["duration"] == 5000
        raw = path.read_bytes()
        proof["files"][path.name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    assert sum(f["bytes"] for f in proof["files"].values()) < 5_000_000
    (args.output / "verification.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf8")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
