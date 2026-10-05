"""Revision 3: staged branches, moving convolutions, volumes and multilayer masks."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

from PIL import Image
from render_learning_concepts import BLUE, GRAY, GREEN, INK, LINE, ORANGE, SIZE, Board

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("foundations_v3", ROOT / "review/learning_foundations_v3.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class Scene(Board):
    def __init__(self, lang, title, chapter, total, caption):
        super().__init__(lang, title, 0, caption)
        self.d.rectangle((0, 0, 1200, 48), fill="white")
        self.text(f"CONCEPT V3 / 시안 3차    ·    {chapter} / {total}", 36, 20, 18, color=GRAY)

    def say(self, en, ko, *args, **kwargs):
        self.text(ko if self.ko else en, *args, **kwargs)

    def grid(self, data, x, y, cell=36, max_value=1, numbers=False):
        super().grid(data, x, y, cell, max_value, False)
        # Readable maps carry their values. Tiny matrix/volume schematics stay schematic.
        if cell < 30:
            return
        for r, row in enumerate(data):
            for c, value in enumerate(row):
                if value == 0:
                    continue
                label = f"{value:g}" if float(value).is_integer() else f"{value:.1f}"
                strength = min(1, abs(value)/max_value)
                self.text(label, x+(c+.5)*cell, y+r*cell+8, 22, width=cell-2,
                          color="white" if strength > .5 else INK, center=True)


BP_CAPTIONS = [
    ("Five variables, two branches: y = AB + CDE.", "다섯 변수에서 출발해 두 갈래가 합쳐집니다: y = AB + CDE."),
    ("First compute AB and CD in their separate branches.", "먼저 두 갈래에서 AB와 CD를 계산합니다."),
    ("Multiply CD by E, then add the branches. Target: 4.", "CD에 E를 곱한 뒤 두 갈래를 더합니다. 목표는 4입니다."),
    ("Start backward: prediction 2 minus target 4 gives a signal of −2.", "뒤로 계산 시작: 예측 2에서 목표 4를 빼면 변화 신호는 −2입니다."),
    ("At addition, the incoming signal goes to BOTH branches.", "더하기에서는 들어온 변화 신호가 양쪽 갈래로 각각 전달됩니다."),
    ("At AB, multiply the signal by the OTHER factor.", "AB에서는 들어온 신호에 상대편 값을 곱합니다."),
    ("At (CD)E, send a signal to CD and another to E.", "(CD)E에서도 CD 쪽과 E 쪽의 변화 신호를 각각 구합니다."),
    ("Continue through CD to reach C and D.", "CD를 한 번 더 거슬러 올라가 C와 D까지 도착합니다."),
    ("Now we have the gradients of ALL five variables.", "이제 다섯 변수 모두의 기울기를 얻었습니다."),
    ("An optimizer uses those gradients to update all five values.", "최적화 방법이 이 기울기들을 받아 다섯 값을 갱신합니다."),
]


def backprop(lang, stage):
    if stage >= 10:
        return backprop_repeat(lang, stage)
    b = Scene(lang, "Backpropagation · AB + CDE", stage+1, 12, BP_CAPTIONS[stage][lang == "ko"])
    values = m.updated() if stage == 9 else m.VALUES
    result = m.branched(values)
    points = {"A": (94, 225), "B": (94, 305), "C": (94, 405), "D": (94, 485),
              "E": (94, 565), "AB": (355, 270), "CD": (355, 455),
              "CDE": (625, 485), "y": (875, 350), "L": (1090, 350)}
    edges = [("A", "AB"), ("B", "AB"), ("C", "CD"), ("D", "CD"),
             ("CD", "CDE"), ("E", "CDE"), ("AB", "y"), ("CDE", "y"), ("y", "L")]
    reverse = ({("y", "L")} if stage == 3 else
               {("AB", "y"), ("CDE", "y")} if stage == 4 else
               {("A", "AB"), ("B", "AB")} if stage == 5 else
               {("CD", "CDE"), ("E", "CDE")} if stage == 6 else
               {("C", "CD"), ("D", "CD")} if stage == 7 else set())
    for a, z in edges:
        x, y = points[a]
        u, v = points[z]
        start, end = (x+65, y), (u-66, v)
        if (a, z) in reverse:
            b.arrow([end, start], ORANGE, 6)
        else:
            b.arrow([start, end], BLUE if stage < 3 or stage == 9 else LINE, 3)
    for key, (x, y) in points.items():
        if key in "ABCDE" and len(key) == 1:
            value = values["ABCDE".index(key)]
        else:
            value = result["loss" if key == "L" else key]
        known = key in tuple("ABCDE") or stage >= 2 or (stage == 1 and key in ("AB", "CD"))
        label = f"{key} = {value:.3g}" if known else key + " = ?"
        if key == "L":
            label = f"L ≈ {value:.3f}" if stage == 9 else (f"L = {value:g}" if known else "L = ?")
        b.box((x-64, y-27, x+64, y+27), outline=GREEN if stage == 9 else BLUE)
        b.text(label, x, y-12, 23, width=118, center=True)
    b.say("Target 4", "목표 4", 1088, 276, 22, width=180, center=True, color=GREEN)
    if stage >= 3 and stage != 9:
        for key, gradient, appears in [("y", -2, 3), ("AB", -2, 4), ("CDE", -2, 4), ("CD", -4, 6)]:
            if stage >= appears:
                x, y = points[key]
                b.text(f"g = {gradient:g}", x, y+37, 21, width=160, center=True, color=ORANGE)
        for key, gradient, appears in [("A", -6, 5), ("B", -4, 5), ("C", 4, 7), ("D", -8, 7), ("E", 4, 6)]:
            if stage >= appears:
                x, y = points[key]
                b.box((x+66, y+7, x+186, y+43), fill="white", outline="white")
                b.text(f"g = {gradient:+g}", x+126, y+14, 22, width=116, center=True, color=ORANGE)
    messages = [
        ("Two products join at +. The right branch has an extra multiplication.", "왼쪽 곱과 오른쪽 곱이 +에서 만납니다. 오른쪽은 곱셈을 한 번 더 합니다."),
        ("AB = 2×3 = 6      CD = 2×(−1) = −2", "AB = 2×3 = 6      CD = 2×(−1) = −2"),
        ("CDE = −2×2 = −4      y = 6−4 = 2      L = (2−4)²/2 = 2", "CDE = −2×2 = −4      y = 6−4 = 2      L = (2−4)²/2 = 2"),
        ("g means: how the loss changes when this value increases a tiny amount.", "g는 이 값을 아주 조금 키울 때 오차 지표가 얼마나 변하는지를 나타냅니다."),
        ("g(AB) = −2×1 = −2      g(CDE) = −2×1 = −2", "더하기의 양쪽 변화율은 각각 1:  g(AB) = −2,  g(CDE) = −2"),
        ("g(A) = −2×B = −6      g(B) = −2×A = −4", "g(A) = −2×B = −6      g(B) = −2×A = −4"),
        ("g(CD) = −2×E = −4      g(E) = −2×CD = +4", "g(CD) = −2×E = −4      g(E) = −2×CD = +4"),
        ("g(C) = −4×D = +4      g(D) = −4×C = −8", "g(C) = −4×D = +4      g(D) = −4×C = −8"),
        ("Gradients A…E:  [−6, −4, +4, −8, +4]. Reuse values; reverse each operation.", "A…E의 기울기: [−6, −4, +4, −8, +4]. 앞의 값을 재사용해 연산마다 거슬러 갑니다."),
        ("One step, rate 0.02: y 2 → 3.433; loss 2 → 0.161 (rounded).", "보폭 계수 0.02로 한 번 갱신: y 2 → 3.433, 오차 2 → 0.161 (반올림)."),
    ]
    if stage == 9:
        progress(b, m.training_trace()[:2])
    b.banner(*messages[stage], y=616)
    b.note("Constructed expression; L=(y−4)²/2. Backprop computes gradients; an optimizer updates values.",
           "직접 정한 식과 L=(y−4)²/2. 역전파는 기울기를 계산하고, 최적화 방법이 값을 바꿉니다.")
    return b.image


def progress(b, rows):
    """A small output scale in the empty right side of the computation graph."""
    b.say("Output approaches target 4", "출력이 목표 4에 가까워집니다", 735, 469, 21, width=425)
    b.d.line((750, 524, 1135, 524), fill=LINE, width=4)
    b.d.line((1135, 508, 1135, 540), fill=GREEN, width=3)
    for row in rows:
        x = 750+(row["y"]-2)/2*385
        b.d.ellipse((x-5, 519, x+5, 529), fill=BLUE)
    b.text("2", 750, 548, 19, width=40, center=True)
    b.text("4", 1135, 548, 19, width=40, center=True, color=GREEN)
    b.text(f"y = {rows[-1]['y']:.4f}", 950, 554, 23, width=230, center=True, color=BLUE)


def backprop_repeat(lang, chapter, iteration=2, phase="update"):
    trace = m.training_trace()
    if chapter == 11:
        b = Scene(lang, "Backpropagation · AB + CDE", 12, 12,
                  "Repeated updates bring the prediction closer to 4." if lang == "en" else
                  "반복해서 갱신하니 예측이 목표 4에 점점 가까워집니다.")
        b.say("Target 4", "목표 4", 1055, 209, 25, width=125, color=GREEN)
        b.d.line((100, 253, 1110, 253), fill=GREEN, width=3)
        points = [(110+row["step"]*163, 520-(row["y"]-2)/2*267) for row in trace]
        b.d.line(points, fill=BLUE, width=5)
        for row, (x, y) in zip(trace, points):
            b.d.ellipse((x-7, y-7, x+7, y+7), fill=BLUE)
            b.text(f"{row['y']:.4f}", x, y+19 if row["y"] > 3.6 else y-35,
                   24, width=146, center=True, color=BLUE)
            b.text(str(row["step"]), x, 562, 23, width=80, center=True)
        b.say("Number of updates", "갱신 횟수", 95, 600, 20, width=250)
        b.banner(f"Same rate 0.02: loss {trace[0]['loss']:g} → {trace[-1]['loss']:.6f}. Gradients are recomputed each time.",
                 f"보폭 계수 0.02 유지: 오차 {trace[0]['loss']:g} → {trace[-1]['loss']:.6f}. 기울기는 매번 다시 계산합니다.", y=630)
        b.note("This chosen example improves at every shown step. Backprop supplies gradients; the optimizer updates values.",
               "이 예시의 표시된 단계에서는 매번 가까워집니다. 역전파는 기울기를 구하고 최적화 방법이 갱신합니다.")
        return b.image
    row = trace[iteration if phase == "update" else iteration-1]
    labels = {"forward": ("Forward: calculate the current prediction", "순방향: 현재 값으로 다시 예측"),
              "backward": ("Backward: recompute the five gradients", "역전파: 다섯 기울기를 다시 계산"),
              "update": ("Update: move all five variables once", "갱신: 다섯 변수를 한 번 이동")}
    caption = labels[phase][lang == "ko"]
    b = Scene(lang, "Backpropagation · AB + CDE", 11, 12,
              (f"Step {iteration}/6 · " if lang == "en" else f"{iteration}/6번째 갱신 · ")+caption)
    points = {"A": (94, 225), "B": (94, 305), "C": (94, 405), "D": (94, 485),
              "E": (94, 565), "AB": (355, 270), "CD": (355, 455),
              "CDE": (625, 485), "y": (875, 350), "L": (1090, 350)}
    edges = [("A", "AB"), ("B", "AB"), ("C", "CD"), ("D", "CD"),
             ("CD", "CDE"), ("E", "CDE"), ("AB", "y"), ("CDE", "y"), ("y", "L")]
    color = {"forward": BLUE, "backward": ORANGE, "update": GREEN}[phase]
    for a, z in edges:
        x, y = points[a]
        u, v = points[z]
        ends = [(x+65, y), (u-(81 if z == "L" else 66), v)]
        b.arrow(ends[::-1] if phase == "backward" else ends, color, 4)
    for key, (x, y) in points.items():
        value = row["values"]["ABCDE".index(key)] if key in tuple("ABCDE") else row["loss" if key == "L" else key]
        label = f"L≈{value:.6f}" if key == "L" else f"{key}={value:.4g}"
        half_width = 80 if key == "L" else 64
        b.box((x-half_width, y-27, x+half_width, y+27), outline=color)
        b.text(label, x, y-12, 23, width=2*half_width-9, center=True)
    b.say("Target 4", "목표 4", 1088, 276, 22, width=180, center=True, color=GREEN)
    if phase == "backward":
        b.say("Fresh gradients", "현재의 기울기", 735, 398, 21, width=425, color=ORANGE)
    progress(b, trace[:row["step"]+1])
    before, after = trace[iteration-1], trace[iteration]
    if phase == "update":
        b.banner(f"Prediction {before['y']:.4f} → {after['y']:.4f}; distance to 4: {before['distance_to_target']:.4f} → {after['distance_to_target']:.4f}.",
                 f"예측 {before['y']:.4f} → {after['y']:.4f}; 목표와 거리 {before['distance_to_target']:.4f} → {after['distance_to_target']:.4f}.", y=616)
    else:
        b.banner("Forward → backward → update. Repeat with the NEW current values.",
                 "순방향 → 역전파 → 갱신. 바뀐 현재 값에서 같은 과정을 반복합니다.", y=616)
    b.note("Rate 0.02, the same target 4. Gradients are recalculated at every step, not reused from step 1.",
           "목표 4와 보폭 계수 0.02는 유지합니다. 첫 기울기를 계속 쓰지 않고 매번 다시 계산합니다.")
    return b.image


def volume(b, maps, x, y, cell=16):
    h, w, depth = len(maps[0]), len(maps[0][0]), len(maps)
    high = max(1., max(abs(v) for ch in maps for row in ch for v in row))
    for z in reversed(range(depth)):
        left, top = x+z*26, y-z*22
        b.grid(maps[z], left, top, cell, high)
        b.d.rectangle((left, top, left+w*cell, top+h*cell), outline=INK, width=2)
    if depth > 1:
        for dx, dy in ((0, 0), (w*cell, 0), (w*cell, h*cell)):
            b.d.line((x+dx, y+dy, x+dx+26*(depth-1), y+dy-22*(depth-1)), fill=GRAY, width=2)


CNN_CAPTIONS = [
    ("A 3×3 patch and a 3×3 filter produce ONE output value.", "3×3 창과 필터를 곱해 더하면 출력 값 하나가 만들어집니다."),
    ("Stride 1: move one cell, compute one value, fill the next cell.", "스트라이드 1: 한 칸 이동하고 계산해서, 다음 출력 칸을 채웁니다."),
    ("A second filter scans the SAME input and builds another map.", "다른 필터도 같은 입력을 훑어 별도의 반응 지도를 만듭니다."),
    ("Stride 2 moves two input cells per step, giving a smaller output.", "스트라이드 2는 두 칸씩 이동하므로 출력 지도가 더 작아집니다."),
    ("Feature maps become the channels of the NEXT layer.", "여러 반응 지도가 다음 층에 들어가는 채널이 됩니다."),
    ("A deeper filter spans ALL incoming channels, then adds their contributions.", "다음 층의 필터는 입력 채널 전체를 보고, 채널별 계산을 더합니다."),
    ("Combine the deeper features to obtain two output scores.", "다음 층에서 모은 특징을 합쳐 마지막 출력 점수 두 개를 만듭니다."),
    ("The first CNN layer can be written as a large matrix product.", "첫 CNN 층의 계산을 큰 행렬 곱으로 펼쳐 볼 수 있습니다."),
    ("Shared filter values versus freely learned matrix entries.", "위치마다 공유하는 필터 값과, 각 칸을 따로 학습하는 행렬을 비교합니다."),
]


def scan(b, kernel, step, stride, focus=False):
    data = m.v1.picture()
    coords = [(r, c) for r in range(0, 5, stride) for c in range(0, 7, stride)]
    r, c = coords[step]
    patch = [row[c:c+3] for row in data[r:r+3]]
    output = m.conv(data, kernel, stride)
    raw = sum(patch[i][j]*kernel[i][j] for i in range(3) for j in range(3))
    value = max(0., raw)
    b.say("Input 7×9", "입력 7×9", 50, 197, 24)
    b.grid(data, 50, 250, 33)
    b.d.rectangle((50+c*33, 250+r*33, 50+(c+3)*33, 250+(r+3)*33), outline=ORANGE, width=5)
    b.say("Selected patch", "선택한 창", 388, 225, 21, width=170)
    b.grid(patch, 386, 277, 38, 1, True)
    b.text("×", 522, 311, 30, width=40)
    b.say("Filter", "필터", 565, 225, 21, width=140)
    b.grid(kernel, 565, 277, 38, 2, True)
    b.arrow([(701, 337), (787, 337)], BLUE)
    b.say("Output map", "출력 지도", 817, 197, 24)
    for i, row in enumerate(output):
        for j, v in enumerate(row):
            left, top = 817+j*39, 250+i*39
            visited = i*len(row)+j <= step if not focus else (i, j) == (r, c)
            if visited:
                b.grid([[v]], left, top, 39, 6)
            else:
                b.d.rectangle((left, top, left+38, top+38), fill="#e4e8eb", outline="white")
    rr, cc = r//stride, c//stride
    b.d.rectangle((817+cc*39, 250+rr*39, 817+(cc+1)*39, 250+(rr+1)*39), outline=ORANGE, width=4)
    sums = [sum(a*z for a, z in zip(row, krow)) for row, krow in zip(patch, kernel)]
    b.say("Multiply matching cells, then add:", "같은 위치끼리 곱한 뒤 더하기:", 386, 430, 22, width=370)
    b.text(" + ".join(f"({v:g})" for v in sums) + f" = {raw:g}", 386, 473, 25, width=400)
    b.say(f"Negative → 0. This cell: {value:g}", f"음수는 0으로. 이번 칸: {value:g}", 386, 522, 24, width=440)
    b.banner(f"Stride {stride}   ·   position {step+1}/{len(coords)}   ·   output {len(output)}×{len(output[0])}",
             f"스트라이드 {stride}   ·   위치 {step+1}/{len(coords)}   ·   출력 {len(output)}×{len(output[0])}")


def cnn(lang, chapter, step=None):
    b = Scene(lang, "CNN · scan → channels → layers" if lang == "en" else "CNN · 이동 → 채널 → 여러 층",
              chapter+1, 9, CNN_CAPTIONS[chapter][lang == "ko"])
    c = m.cnn_values()
    if chapter < 4:
        kernel = m.v1.HORIZONTAL if chapter == 2 else m.v1.VERTICAL
        stride = 2 if chapter == 3 else 1
        if step is None:
            step = 8 if chapter == 0 else 11 if stride == 2 else 34
        scan(b, kernel, step, stride, focus=chapter == 0)
    elif chapter == 4:
        for maps, x, y, size, name, dims in [([m.v1.picture()], 65, 310, 18, "Input", "7×9×1"),
                                            (c["one"], 365, 325, 19, "Layer 1", "5×7×2"),
                                            (c["two"], 725, 332, 25, "Layer 2", "3×5×2")]:
            volume(b, maps, x, y, size)
            b.text({"Input": "입력", "Layer 1": "첫 층", "Layer 2": "다음 층"}.get(name, name)
                   if b.ko else name, x, 211, 28, width=250)
            b.text(dims, x, 489, 30, width=220)
        b.arrow([(249, 364), (339, 364)])
        b.arrow([(552, 364), (697, 364)])
        b.say("2 filters", "필터 2개", 262, 282, 21, width=145)
        b.say("2 filters, each 3×3×2", "필터 2개, 각각 3×3×2", 567, 252, 20, width=250)
        b.banner("Height × width × channels. Each next-layer filter spans the incoming channel depth.",
                 "높이 × 너비 × 채널입니다. 면은 반응 지도, 깊이는 채널 수이며 다음 필터는 그 깊이도 봅니다.")
    elif chapter == 5:
        terms = []
        for ch, x in ((0, 65), (1, 395)):
            volume(b, [c["one"][ch]], x, 282, 34)
            b.d.rectangle((x, 282, x+102, 384), outline=ORANGE, width=5)
            subtotal = sum(c["one"][ch][r][col] for r in range(3) for col in range(3)) / (9 if ch == 0 else 18)
            terms.append(subtotal)
            b.say(f"Channel {ch+1}", f"채널 {ch+1}", x, 209, 28)
            factor = "1/9" if ch == 0 else "1/18"
            b.say("Patch sum × " + factor, "창의 합 × " + factor, x, 486, 25, width=285)
            b.text(f"≈ {subtotal:.3f}", x, 532, 27, color=BLUE)
        b.text("+", 336, 356, 35, width=50)
        b.arrow([(669, 365), (813, 365)])
        b.box((835, 301, 1137, 425), outline=BLUE)
        b.text(f"≈ {sum(terms):.3f}", 986, 341, 38, width=280, center=True, color=BLUE)
        b.say("One next-layer cell", "다음 층의 한 칸", 820, 245, 23, width=330)
        b.banner("One 3×3×2 filter combines BOTH maps. A second filter makes a second output map.",
                 "3×3×2 필터 하나가 두 지도를 함께 계산합니다. 다른 필터는 또 다른 출력 지도를 만듭니다.")
    elif chapter == 6:
        volume(b, c["two"], 82, 290, 42)
        b.text("3×5×2", 96, 501, 31)
        b.arrow([(363, 362), (493, 362)])
        b.say("Mean of each map", "지도마다 평균 내기", 503, 223, 25, width=380)
        for i, mean in enumerate(c["pooled"]):
            b.box((512, 295+i*110, 724, 370+i*110))
            b.text(f"{mean:.3f}", 618, 316+i*110, 32, width=190, center=True)
            for j in range(2):
                b.arrow([(737, 332+i*110), (904, 332+j*110)], BLUE if i == j else ORANGE, 3)
            b.text(f"{'점수' if b.ko else 'Score'} {i+1}: {c['scores'][i]:.3f}",
                   929, 318+i*110, 24, width=256)
        b.banner("The final small matrix mixes these features into scores. These are not probabilities.",
                 "마지막 작은 행렬이 모은 특징을 섞어 점수를 만듭니다. 이 숫자는 정답 확률이 아닙니다.")
    else:
        b.say("First CNN layer", "첫 번째 CNN 층", 60, 194, 27)
        volume(b, [m.v1.picture()], 55, 283, 16)
        volume(b, c["one"], 349, 308, 18)
        b.arrow([(215, 345), (322, 345)])
        b.say("Two shared 3×3 filters", "공유하는 3×3 필터 2개", 63, 457, 24, width=490)
        b.text("18", 271, 509, 54, width=200, center=True, color=BLUE)
        b.d.line((585, 187, 585, 585), fill=LINE, width=2)
        if chapter == 7:
            b.say("Unroll the SAME convolution", "같은 CNN 계산을 펼치기", 620, 193, 24, width=525)
            b.grid(m.matrix(), 620, 246, 4.6, 2)
            b.text("70 × 63", 708, 218, 20, width=180)
            flat = [[v] for row in m.v1.picture() for v in row]
            b.grid(flat, 977, 262, 4.6, 1)
            b.text("×", 943, 366, 28, width=30)
            b.arrow([(1003, 401), (1063, 401)])
            b.grid([[v] for ch in c["one"] for row in ch for v in row], 1098, 246, 4.6, 6)
            b.text("ReLU", 1011, 440, 19, width=90)
            b.say("63 inputs → 70 outputs", "63개 입력 → 70개 출력", 750, 574, 20, width=410)
            b.banner("Repeated entries in this matrix are TIED to the same 18 filter coefficients.",
                     "펼친 행렬의 반복되는 칸들은 같은 필터 값에 묶입니다. 이 CNN의 독립적인 값은 18개입니다.")
        else:
            b.say("Dense: learn each entry freely", "Dense: 모든 칸을 독립 학습", 620, 193, 24, width=525)
            # Uniform empty slots depict parameter positions, not invented weights or predictions.
            for r in range(70):
                for col in range(63):
                    left, top = 666+col*3.2, 255+r*3.2
                    b.d.rectangle((left, top, left+2.3, top+2.3), fill="#91a9c8")
            b.text("70 × 63", 712, 220, 22, width=190)
            b.text("×", 900, 352, 28, width=40)
            for n, x in ((63, 971), (70, 1122)):
                for i in range(n):
                    b.d.rectangle((x, 255+i*3.2, x+11, 257+i*3.2), fill=LINE)
            b.arrow([(1003, 368), (1090, 368)])
            b.text("63", 963, 220, 20, width=64)
            b.text("70", 1113, 220, 20, width=64)
            b.text("4,410", 873, 509, 54, width=360, center=True, color=ORANGE)
            b.banner("Same input/output sizes: CNN 18, Dense 4,410 trainable weights. Biases excluded.",
                     "같은 입력·출력 크기에서 학습할 값: CNN 18개, Dense 4,410개. 편향은 제외합니다.")
    b.note("Chosen filters; labels rounded, zeros blank. First-layer counts only; no accuracy comparison.",
           "직접 정한 필터. 소수는 반올림, 0은 빈칸. 파라미터는 첫 층만 비교하며 정확도 비교는 아닙니다.")
    return b.image


DO_CAPTIONS = [
    ("A network with 3 → 5 → 5 → 2 units.", "3 → 5 → 5 → 2개 노드로 이루어진 여러 층의 신경망입니다."),
    ("Temporarily switch off some units in the first hidden layer.", "첫 번째 중간층에서 일부 노드를 이번 계산 동안 쉬게 합니다."),
    ("Also switch off units in the next hidden layer.", "다음 중간층에서도 일부 노드를 쉬게 합니다."),
    ("Values travel only through the participating paths.", "값은 이번에 참여하는 노드와 연결을 통해서만 전달됩니다."),
    ("The next training mask opens some paths and closes others.", "다음 참여 조합에서는 닫혀 있던 길이 열리고 다른 길이 쉬게 됩니다."),
    ("Repeat with different combinations across BOTH hidden layers.", "두 중간층 모두에서 조합을 바꾸며 반복합니다."),
    ("Prediction: restore every unit and scale the hidden outgoing weights.", "예측할 때는 모두 복귀시키고 중간층에서 나가는 연결의 크기를 조절합니다."),
    ("The goal is less reliance on one fixed team of units.", "목표는 늘 같은 노드 조합에만 지나치게 의존하는 것을 줄이는 것입니다."),
]


def dropout(lang, chapter, variant=None, pulse=None):
    b = Scene(lang, "Dropout · 3 → 5 → 5 → 2", chapter+1, 8, DO_CAPTIONS[chapter][lang == "ko"])
    if variant is None:
        variant = 2 if chapter == 4 else 4 if chapter == 5 else 0
    selected = m.masks()[min(4, variant if chapter >= 4 else 0)]
    mask1 = selected[0] if 1 <= chapter <= 5 else [1]*5
    mask2 = selected[1] if 2 <= chapter <= 5 else [1]*5
    prediction = chapter >= 6
    values = m.dropout(mask1, mask2, prediction)["layers"]
    masks = [[1]*3, mask1, mask2, [1]*2]
    positions = [[(x, 230 + i*340/(n-1)) for i in range(n)]
                 for x, n in zip((86, 388, 744, 1092), m.WIDTHS)]
    positions[-1] = [(1092, 300), (1092, 480)]
    for layer in range(3):
        for i, (x, y) in enumerate(positions[layer]):
            for j, (u, v) in enumerate(positions[layer+1]):
                active = masks[layer][i] and masks[layer+1][j]
                color = BLUE if active and (pulse is None or layer == int(pulse)) else LINE
                b.d.line((x+17, y, u-17, v), fill=color, width=1 if color == LINE else 2)
                if active and pulse is not None and layer == int(pulse):
                    t = pulse-layer
                    xx, yy = x+17+t*(u-x-34), y+t*(v-y)
                    b.d.ellipse((xx-3, yy-3, xx+3, yy+3), fill=ORANGE)
    names = [("Input", "입력"), ("Hidden 1", "중간층 1"), ("Hidden 2", "중간층 2"), ("Scores", "점수")]
    for layer, points in enumerate(positions):
        center = points[0][0]
        b.say(*names[layer], center, 184, 23, width=192, center=True)
        for i, (x, y) in enumerate(points):
            active = masks[layer][i]
            b.d.ellipse((x-18, y-18, x+18, y+18), fill="white", outline=BLUE if active else GRAY, width=3)
            if not active:
                b.d.line((x-18, y-18, x+18, y+18), fill=ORANGE, width=4)
                b.d.line((x-18, y+18, x+18, y-18), fill=ORANGE, width=4)
            else:
                b.text(str(i+1), x, y-11, 19, width=33, center=True, color=BLUE)
            if layer == 3:
                b.text(f"{values[-1][i]:.3f}", 1092, y+32, 24, width=185, center=True)
    if chapter == 0:
        b.banner("The two hidden layers extract and combine features before producing two scores.",
                 "두 중간층이 특징을 만들고 조합한 뒤 점수 두 개로 보냅니다. 노드 안 숫자는 번호입니다.")
    elif chapter <= 5 and sum(mask2) == 0:
        b.banner("This draw omits ALL of hidden 2: both scores are zero. The next draw can reopen paths.",
                 "이번 조합은 중간층 2가 전부 빠져 점수가 모두 0입니다. 다음 조합에서는 길이 다시 열립니다.")
    elif chapter <= 5:
        b.banner(f"Participating: hidden 1 {sum(mask1)}/5, hidden 2 {sum(mask2)}/5. × = temporarily omitted.",
                 f"이번 참여: 중간층 1 {sum(mask1)}/5개, 중간층 2 {sum(mask2)}/5개. ×는 잠시 제외한 노드입니다.")
    else:
        b.banner("All units return. Scale outgoing weights of BOTH hidden layers by 0.5 (paper convention).",
                 "모두 복귀합니다. 두 중간층에서 나가는 연결을 각각 0.5배 합니다. 입력 연결은 그대로입니다.")
    b.note("Fixed weights, seeded masks, p=0.5 per hidden unit. Scores are computed; no training gain measured.",
           "고정 가중치·노드별 참여 확률 0.5의 예시. 점수는 계산값이며 학습 효과를 측정한 결과는 아닙니다.")
    return b.image


def build(args):
    proof = m.verify()
    proof.update(source=args.source, revision=3, status="concept-pending-owner-review", size=SIZE,
                 files={}, animations={}, chapter_counts={"backprop": 12, "cnn": 9, "dropout": 8})
    args.output.mkdir(parents=True, exist_ok=False)
    frame_hashes = {}
    # A shared palette keeps colors stable and lets GIF store only changed regions.
    colors = [(r, g, b) for r in range(0, 256, 51) for g in range(0, 256, 51)
              for b in range(0, 256, 51)]
    colors += [(round(i*255/31),)*3 for i in range(32)]
    colors += [tuple(int(color[k:k+2], 16) for k in (1, 3, 5))
               for color in (INK, GRAY, LINE, BLUE, GREEN, ORANGE)]
    colors += [(255, 255, 255)]*(256-len(colors))
    palette = Image.new("P", (1, 1))
    palette.putpalette([v for color in colors for v in color])
    for lang in ("en", "ko"):
        for topic, count, renderer in (("backprop", 12, backprop), ("cnn", 9, cnn), ("dropout", 8, dropout)):
            frames, times, stills = [], [], []
            for chapter in range(count):
                still = renderer(lang, chapter)
                still.save(args.output / f"{topic}.{lang}.{chapter+1}.png", optimize=True)
                stills.append(still)
                if topic == "backprop" and chapter == 10:
                    for iteration in range(2, 7):
                        for phase, duration in (("forward", 550), ("backward", 550), ("update", 900)):
                            frames.append(backprop_repeat(lang, chapter, iteration, phase))
                            times.append(duration)
                elif topic == "cnn" and chapter in (1, 2, 3):
                    steps = 12 if chapter == 3 else 35
                    for step in range(steps):
                        frames.append(cnn(lang, chapter, step))
                        times.append(180 if chapter != 3 else 280)
                    times[-1] = 1800
                elif topic == "dropout" and chapter == 3:
                    for pulse in range(15):
                        frames.append(dropout(lang, chapter, pulse=pulse/5))
                        times.append(160)
                    frames.append(still)
                    times.append(1600)
                elif topic == "dropout" and chapter in (4, 5):
                    for variant in ((1, 2) if chapter == 4 else (3, 4)):
                        frames.append(dropout(lang, chapter, variant))
                        times.append(1500)
                else:
                    frames.append(still)
                    times.append(4000)
            name = f"{topic}.{lang}.gif"
            frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
            frame_hashes[name] = [hashlib.sha256(frame.convert("RGB").tobytes()).hexdigest()
                                  for frame in frames]
            frames[0].save(args.output / name, save_all=True, append_images=frames[1:],
                           duration=times, loop=0, disposal=1, optimize=True)
            proof["animations"][name] = {"authored_frames": len(frames), "duration_ms": sum(times)}
            for start in range(0, count, 4):
                contact = Image.new("RGB", SIZE, "white")
                for j, still in enumerate(stills[start:start+4]):
                    contact.paste(still.resize((600, 380)), ((j % 2)*600, (j//2)*380))
                contact.save(args.output / f"{topic}.{lang}.contact{start//4+1}.png", optimize=True)
    for path in sorted(args.output.iterdir()):
        with Image.open(path) as decoded:
            assert decoded.size == SIZE
            duration = 0
            frames = getattr(decoded, "n_frames", 1)
            for i in range(frames):
                decoded.seek(i)
                decoded.load()
                duration += decoded.info.get("duration", 0)
                if path.suffix == ".gif":
                    actual = hashlib.sha256(decoded.convert("RGB").tobytes()).hexdigest()
                    assert actual == frame_hashes[path.name][i], f"GIF pixels differ: {path.name}, {i}"
            if path.suffix == ".gif":
                assert duration == proof["animations"][path.name]["duration_ms"]
                assert frames == proof["animations"][path.name]["authored_frames"]
                proof["animations"][path.name]["decoded_frames"] = frames
                proof["animations"][path.name]["all_frame_pixels_verified"] = True
        raw = path.read_bytes()
        proof["files"][path.name] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    assert len(proof["files"]) == 80
    total_bytes = sum(row["bytes"] for row in proof["files"].values())
    assert total_bytes < 12_000_000, f"Bundle is {total_bytes} bytes"
    proof["total_bytes"] = total_bytes
    (args.output / "verification.json").write_text(json.dumps(proof, indent=2)+"\n", encoding="utf8")
    print(json.dumps({"files": len(proof["files"]), "source": args.source,
                      "animations": proof["animations"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-f0-9]{40}", args.source):
        raise ValueError("Full source SHA required")
    build(args)
