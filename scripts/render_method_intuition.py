"""Intermediate-difficulty review scenes using the previously checked examples."""

from __future__ import annotations

import argparse
import hashlib
import json
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
    attention,
    residual,
)
from render_method_explanations import (
    attention_roles,
    block_numbers,
    depth_case,
    note,
    stage,
    verify_explanations,
)


def attention_shares(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "Attention",
        2,
        "How much should each piece of information count?",
        "각 정보를 얼마나 참고하면 될까요?",
    )
    b.text(
        "질문: Mia의 위치는?" if ko else "Question: Where is Mia?",
        55,
        202,
        30,
        width=1090,
        color=BLUE,
    )
    weights, _ = attention(2)
    for i, w in enumerate(weights):
        y = 300 + i * 107
        b.box((55, y - 15, 1155, y + 68), fill="#edf4ff" if i == 2 else PALE)
        b.text(NAMES[i], 79, y + 10, 27, width=190)
        b.text(
            ("관련 높음" if i == 2 else "관련 낮음")
            if ko
            else ("High match" if i == 2 else "Low match"),
            279,
            y + 13,
            23,
            width=225,
            color=BLUE if i == 2 else GRAY,
        )
        b.d.rectangle((570, y + 15, 968, y + 43), fill=LINE)
        b.d.rectangle((570, y + 15, 570 + 398 * w, y + 43), fill=BLUE)
        b.text(f"{w:.0%}", 1050, y + 6, 31, width=150, center=True, color=BLUE)
    b.text(
        "비교 점수 → Softmax → 합이 100%인 비중"
        if ko
        else "Match scores → Softmax → shares adding to 100%",
        600,
        619,
        25,
        width=1080,
        center=True,
    )
    note(
        b,
        "질문과 더 잘 맞는 이름표에 더 큰 비중을 줍니다."
        if ko
        else "A closer match to the query gets a larger share.",
        "Softmax는 점수를 이런 비중으로 바꾸는 계산입니다."
        if ko
        else "Softmax is the calculation that turns scores into these shares.",
        "이 예시의 비중을 정수로 반올림했습니다. 정답 확률은 아닙니다."
        if ko
        else "Rounded shares for this example; they are not confidence in the answer.",
    )
    return b.image


def attention_collect(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "Attention",
        3,
        "A new question changes the information we gather.",
        "질문이 달라지면, 모이는 정보도 달라집니다.",
    )
    for left, selected in ((40, 2), (617, 0)):
        b.box((left, 215, left + 540, 625), fill=PALE)
        b.text(
            f"{NAMES[selected]}의 위치는?" if ko else f"Where is {NAMES[selected]}?",
            left + 270,
            239,
            30,
            width=495,
            center=True,
            color=BLUE,
        )
        weights, _ = attention(selected)
        for i, w in enumerate(weights):
            y = 328 + i * 67
            b.text(PLACES[lang][i], left + 23, y, 23, width=147)
            b.d.rectangle((left + 188, y + 4, left + 422, y + 30), fill=LINE)
            b.d.rectangle((left + 188, y + 4, left + 188 + 234 * w, y + 30), fill=BLUE)
            b.text(f"{w:.0%}", left + 471, y - 1, 24, width=90, center=True)
        b.text(
            (PLACES[lang][selected] + " 정보가 주로 담김")
            if ko
            else ("Mostly " + PLACES[lang][selected] + " information"),
            left + 270,
            558,
            24,
            width=495,
            center=True,
            color=GREEN,
        )
    note(
        b,
        "각 내용(V)을 비중만큼 모으는 것이 “가중합”입니다."
        if ko
        else "Collecting each value in proportion to its share is a “weighted sum”.",
        "관련 정보는 많이, 다른 정보는 조금 담아서 다음 층에 보냅니다."
        if ko
        else "Pass mostly relevant information, plus smaller contributions, to the next layer.",
        "같은 정보, 다른 질문. 벡터 계산은 아래 “자세히 보기”에 있습니다."
        if ko
        else "Same records, different queries. The vector calculation is in the optional details.",
    )
    return b.image


def attention_language(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "Attention",
        4,
        "In a sentence, words gather context from one another.",
        "문장에서는 단어들이 서로 참고해 문맥을 만듭니다.",
    )
    words = ["고양이가", "소파에서", "잔다"] if ko else ["The cat", "on the sofa", "sleeps"]
    for x, word in zip((55, 452, 849), words):
        b.box((x, 224, x + 295, 305), outline=BLUE if x == 849 else LINE)
        b.text(word, x + 147, 248, 29, width=265, center=True)
    b.text(
        "“잔다”를 이해할 때 참고할 수 있는 관계"
        if ko
        else "Possible relations for understanding “sleeps”",
        600,
        351,
        25,
        width=1090,
        center=True,
    )
    for left, question, answer in [
        (55, "누가?" if ko else "Who?", words[0]),
        (647, "어디에서?" if ko else "Where?", words[1]),
    ]:
        b.box((left, 421, left + 497, 614), fill="#edf4ff", outline=BLUE)
        b.text("Head · " + question, left + 249, 444, 29, width=460, center=True, color=BLUE)
        b.arrow([(left + 249, 489), (left + 249, 521)], BLUE, 3)
        b.text(answer, left + 249, 548, 28, width=450, center=True)
    note(
        b,
        "Self-attention: 같은 문장 안에서 각 단어가 다른 단어를 참고합니다."
        if ko
        else "Self-attention lets each word use information from the same sentence.",
        "여러 head는 서로 다른 관점으로 관계를 살필 수 있습니다."
        if ko
        else "Multiple heads can look at relationships from different perspectives.",
        "관계 설명용 그림입니다. 실제 head의 역할은 학습되며, “누가/어디”로 고정되지 않습니다."
        if ko
        else "Illustrative relationships. Actual head roles are learned, not fixed to “who” or “where”.",
    )
    return b.image


def resnet_correction(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "ResNet",
        1,
        "Keep what is useful. Learn what needs changing.",
        "쓸 만한 정보는 유지하고, 바꿀 부분을 배웁니다.",
    )
    _, target = residual(1)
    panels = [
        (65, INPUT, "현재 정보" if ko else "Current features"),
        (518, target, "원하는 정보" if ko else "Desired features"),
        (942, DELTA, "배울 수정분" if ko else "Correction to learn"),
    ]
    for x, data, label in panels:
        b.grid(data, x, 257, cell=19, signed=data is DELTA)
        b.text(label, x + 85, 203, 24, width=300, center=True)
    b.arrow([(247, 341), (500, 341)], GRAY, 3)
    b.text(
        "추가 2칸 · 삭제 1칸" if ko else "Add 2 cells · remove 1",
        1022,
        461,
        21,
        width=320,
        center=True,
        color=GREEN,
    )
    b.box((55, 529, 1145, 625), fill="#ecf6f1", outline=GREEN)
    b.text(
        "원래 정보 + 배운 수정분 = 다음 정보"
        if ko
        else "Original features + learned correction = next features",
        600,
        560,
        29,
        width=1045,
        center=True,
        color=GREEN,
    )
    note(
        b,
        "이 수정분을 “잔차(residual)”라고 부릅니다."
        if ko
        else "This correction is called the residual.",
        "더 바꿀 필요가 없다면 수정분은 0이면 됩니다."
        if ko
        else "When no change is needed, the residual can be zero.",
        "학습 목표를 설명하는 격자 모형입니다. 이미지 복원 실험은 아닙니다."
        if ko
        else "Feature-grid illustration of the learning target, not an image-restoration experiment.",
    )
    return b.image


def friendly_block(b, backwards=False):
    ko = b.lang == "ko"
    upper = [(239, 429), (297, 429), (297, 282), (430, 282)]
    after = [(710, 282), (833, 282), (833, 404)]
    lower = [(297, 429), (297, 593), (833, 593), (833, 458)]
    right = [(861, 429), (1010, 429)]
    for route in (upper, after, right):
        b.arrow(list(reversed(route)) if backwards else route, RED if backwards else INK, 4)
    b.arrow(list(reversed(lower)) if backwards else lower, BLUE, 6)
    b.box((430, 227, 710, 342), outline=GREEN)
    b.text(
        "학습하는 가지" if ko else "Learned branch",
        570,
        243,
        26,
        width=250,
        center=True,
        color=GREEN,
    )
    b.text(
        ("가중치를 조정" if ko else "Adjust weights")
        if backwards
        else ("수정분 +0.1" if ko else "Correction +0.1"),
        570,
        291,
        24,
        width=250,
        center=True,
    )
    b.d.ellipse((806, 403, 860, 457), fill="white", outline=INK, width=3)
    b.text("+", 833, 409, 33, width=46, center=True)


def resnet_predict(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "ResNet",
        2,
        "First make a prediction, then compare it with the target.",
        "먼저 예측하고, 정답과 비교합니다.",
    )
    friendly_block(b)
    b.text("입력" if ko else "Input", 135, 365, 26, width=220, center=True)
    b.text("2.0", 135, 416, 37, width=220, center=True)
    b.text("예측" if ko else "Prediction", 1070, 365, 26, width=210, center=True)
    b.text(f"{block_numbers()['y']:.1f}", 1070, 416, 37, width=210, center=True)
    b.text(
        "지름길: 원래 값 2.0을 전달" if ko else "Shortcut: carry the original 2.0",
        565,
        548,
        25,
        width=510,
        center=True,
        color=BLUE,
    )
    note(
        b,
        "2.0에 0.1을 보태면 2.1입니다. 정답 2.2보다 조금 작습니다."
        if ko
        else "Adding 0.1 to 2.0 gives 2.1, a little below the target 2.2.",
        "이 차이를 줄이려면, 각 층이 무엇을 고쳐야 하는지 알아야 합니다."
        if ko
        else "To reduce the error, the layers need to know how their weights should change.",
        "숫자는 같은 검산된 예시를 사용합니다. 계산식은 “자세히 보기”에 있습니다."
        if ko
        else "Same checked numerical example; equations are in the optional details.",
    )
    return b.image


def resnet_feedback(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "ResNet",
        3,
        "Backpropagation sends a learning signal toward earlier layers.",
        "역전파는 고칠 방향을 알려주는 신호를 뒤로 보냅니다.",
    )
    b.text(
        "오차가 각 층의 값에 얼마나 민감한지 계산하며 돌아갑니다."
        if ko
        else "Working backward, it measures how changes at each layer affect the error.",
        55,
        188,
        21,
        width=1090,
        color=GRAY,
    )
    friendly_block(b, backwards=True)
    b.text("앞쪽 층" if ko else "Earlier layers", 132, 365, 26, width=223, center=True)
    b.text(
        "두 길의 신호를 받음" if ko else "Receive both paths", 133, 469, 20, width=232, center=True
    )
    b.text("오차에서 온" if ko else "From the error", 1068, 364, 22, width=220, center=True)
    b.text(
        "학습 신호" if ko else "Learning signal", 1068, 468, 24, width=226, center=True, color=RED
    )
    b.text(
        "가지에서도 학습이 진행됩니다." if ko else "The branch keeps learning.",
        567,
        391,
        24,
        width=457,
        center=True,
        color=GREEN,
    )
    b.text(
        "지름길: 신호를 직접 돌려보내는 길" if ko else "Shortcut: a direct route back",
        565,
        548,
        25,
        width=540,
        center=True,
        color=BLUE,
    )
    note(
        b,
        "학습 신호는 “기울기”입니다. 이 신호로 가중치의 수정 방향을 구합니다."
        if ko
        else "The learning signal is a gradient; it determines how weights should change.",
        "지름길이 있어서 앞쪽 층으로 돌아가는 경로가 하나 더 생깁니다."
        if ko
        else "The shortcut adds another route for that signal to reach earlier layers.",
        "두 경로의 신호는 합쳐집니다. 가지를 학습하지 않고 건너뛰는 뜻은 아닙니다."
        if ko
        else "The contributions add together. The shortcut does not mean skipping branch learning.",
    )
    return b.image


def resnet_reach(lang):
    ko = lang == "ko"
    b = stage(
        lang,
        "ResNet",
        4,
        "A shortcut helps the learning signal reach farther back.",
        "깊은 곳의 앞쪽 층까지, 학습 신호가 닿도록 돕습니다.",
    )
    b.text(
        "신호를 100으로 시작해, 8개 블록을 거슬러 올라가는 숫자 예시"
        if ko
        else "A numerical example: start with signal 100, then go backward through 8 blocks",
        55,
        197,
        22,
        width=1090,
    )
    for row, skip in enumerate((False, True)):
        y = 290 + 184 * row
        magnitude = abs(depth_case(skip)[1][-1])
        color = BLUE if skip else GRAY
        b.box((55, y - 10, 1145, y + 134), fill=PALE)
        b.text(
            ("지름길 있는 경우" if skip else "직접 매핑만 있는 경우")
            if ko
            else ("With shortcuts" if skip else "Plain mappings only"),
            78,
            y + 8,
            25,
            width=480,
            color=color,
        )
        # Full bar width represents the starting magnitude; tiny values are not enlarged.
        b.d.rectangle((80, y + 71, 935, y + 107), fill=LINE)
        b.d.rectangle((80, y + 71, 80 + 855 * magnitude, y + 107), fill=color)
        label = (
            (f"약 {100 * magnitude:.0f}" if ko else f"About {100 * magnitude:.0f}")
            if skip
            else ("1 미만" if ko else "Less than 1")
        )
        b.text(label, 1034, y + 68, 29, width=194, center=True, color=color)
    note(
        b,
        "여러 층을 지나며 약해질 수 있는 신호에, 직접 전달 경로를 보탭니다."
        if ko
        else "A direct route helps when the signal would weaken through successive layers.",
        "그래서 깊은 신경망의 앞쪽 층도 학습하기 쉬워질 수 있습니다."
        if ko
        else "This can make it easier for earlier layers in a deep network to learn.",
        "지정한 숫자 모형의 신호 크기입니다. 성능 비교가 아니며, 신호 보존이 항상 보장되지는 않습니다."
        if ko
        else "Signal magnitudes in a chosen numerical model, not a performance benchmark or a preservation guarantee.",
    )
    return b.image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    proof = verify_explanations()
    weights, _ = attention(2)
    rounded = [round(100 * w) for w in weights]
    assert rounded == [2, 2, 96] and sum(rounded) == 100
    assert abs(depth_case(False)[1][-1]) * 100 < 1
    assert round(abs(depth_case(True)[1][-1]) * 100) == 43
    proof.update(
        source=args.source,
        size=[1200, 840],
        frames=4,
        duration_ms=7500,
        attention_display_shares=rounded,
        depth_display_scale=100,
        intended_difficulty="about 6 on the owner scale; not a measured readability score",
        files={},
    )
    args.output.mkdir(parents=True, exist_ok=True)
    makers = {
        "attention": [attention_roles, attention_shares, attention_collect, attention_language],
        "resnet": [resnet_correction, resnet_predict, resnet_feedback, resnet_reach],
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
                duration=7500,
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
                    assert decoded.info["duration"] == 7500
        raw = path.read_bytes()
        proof["files"][path.name] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    (args.output / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    main()
