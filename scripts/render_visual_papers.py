"""Animate the approved four-scene lessons; render only on GitHub Actions."""

from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from chainbench.visual_papers import DURATION, FPS, INPUT, NAMES, PLACES, experiment, film_state

SIZE = (1280, 720)
BG, INK, MUTED, BLUE, GREEN, RED = (
    "#172127",
    "#edf0e5",
    "#b7c8bf",
    "#8bb9ff",
    "#68c7bb",
    "#eea083",
)
TRACK, PANEL = "#3a494e", "#223138"


@functools.lru_cache(maxsize=64)
def font(size, ko=False):
    path = (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        if ko
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    return ImageFont.truetype(path, size)


class Frame:
    def __init__(self, slug, lang, number, title):
        self.ko = lang == "ko"
        self.image = Image.new("RGB", SIZE, BG)
        self.d = ImageDraw.Draw(self.image)
        self.text((42, 24), slug.upper(), 21, MUTED)
        self.text((1238, 24), f"0{number + 1} / 04", 21, MUTED, "ra")
        # Native captions use the otherwise empty top band, not the diagram.
        self.d.line((42, 106, 1238, 106), fill=TRACK)
        self.text((42, 128), title, 32, width=1196)
        for i in range(4):
            self.d.rounded_rectangle(
                (42 + i * 303, 696, 326 + i * 303, 700), 2, fill=BLUE if i == number else TRACK
            )

    def tr(self, en, ko):
        return ko if self.ko else en

    def text(self, xy, value, size=25, color=INK, anchor=None, width=None):
        f = font(size, any(ord(c) > 0x3000 for c in str(value)))
        bounds = self.d.textbbox(xy, str(value), font=f, anchor=anchor)
        if width is not None and bounds[2] - bounds[0] > width:
            raise ValueError(f"Text too wide: {value}")
        if not (0 <= bounds[0] <= bounds[2] <= SIZE[0] and 0 <= bounds[1] <= bounds[3] <= SIZE[1]):
            raise ValueError(f"Text outside frame: {value}")
        self.d.text(xy, str(value), font=f, fill=color, anchor=anchor)

    def box(self, bounds, color=TRACK):
        self.d.rounded_rectangle(bounds, 14, fill=PANEL, outline=color, width=2)

    def path(self, points, color, phase, width=3, reverse=False):
        if reverse:
            points = list(reversed(points))
        self.d.line(points, fill=color, width=width, joint="curve")
        a, b = points[-2:]
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        self.d.polygon(
            [
                b,
                *[
                    (b[0] - 12 * math.cos(angle + s * 0.5), b[1] - 12 * math.sin(angle + s * 0.5))
                    for s in (-1, 1)
                ],
            ],
            fill=color,
        )
        lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
        distance = phase * sum(lengths)
        for a, b, length in zip(points, points[1:], lengths):
            if distance <= length:
                u = distance / length
                x, y = a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])
                self.d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=INK)
                break
            distance -= length

    def note(self, en, ko, scope_en, scope_ko):
        self.d.line((42, 587, 1238, 587), fill=TRACK)
        self.text((42, 608), self.tr(en, ko), 25, width=1196)
        self.text((42, 652), self.tr(scope_en, scope_ko), 18, MUTED, width=1196)

    def grid(self, values, x, y, signed=False):
        for r, row in enumerate(values):
            for c, v in enumerate(row):
                color = (GREEN if v >= 0 else RED) if signed else INK
                base = tuple(int(PANEL[j : j + 2], 16) for j in (1, 3, 5))
                target = tuple(int(color[j : j + 2], 16) for j in (1, 3, 5))
                rgb = tuple(round(a + abs(v) * (b - a)) for a, b in zip(base, target))
                self.d.rectangle(
                    (x + c * 24, y + r * 24, x + c * 24 + 21, y + r * 24 + 21), fill=rgb
                )


def attention_frame(record, frame, lang="en"):
    s = film_state("attention", frame)
    scene, phase = s["scene"], s["phase"]
    titles = [
        ("A question. A name tag. Information to collect.", "질문, 맞춰 볼 이름표, 가져올 내용."),
        ("Better matches receive larger shares.", "더 잘 맞는 정보에 더 큰 비중을 줍니다."),
        ("Change the question. Change what you gather.", "질문이 바뀌면 모이는 정보도 바뀝니다."),
        ("Words gather context from one another.", "단어들이 서로 참고해 문맥을 만듭니다."),
    ]
    f = Frame("Attention", lang, scene, titles[scene][lang == "ko"])
    places = PLACES[lang]
    if scene == 0:
        f.box((42, 260, 352, 454), BLUE)
        f.text((64, 282), "Q · Query", 28, BLUE)
        f.text((64, 335), f.tr("What I am looking for", "찾으려는 것"), 22)
        f.text((64, 389), f.tr("Where is Mia?", "Mia의 위치는?"), 28)
        for x, heading, sub in [
            (604, "K · Key", f.tr("Name to match", "맞춰 볼 이름표")),
            (1050, "V · Value", f.tr("Content to collect", "가져올 내용")),
        ]:
            f.text((x, 199), heading, 27, BLUE if x == 604 else GREEN, "ma")
            f.text((x, 242), sub, 21, MUTED, "ma")
        for i, name in enumerate(NAMES):
            y = 312 + i * 91
            w = s["weights"][i]
            color = BLUE if i == 2 else TRACK
            f.path([(352, 362), (440, y), (486, y)], color, phase, 2 + round(4 * w))
            f.box((490, y - 28, 718, y + 28), color)
            f.text((604, y - 17), name, 27, INK, "ma")
            f.path([(722, y), (890, y)], GREEN if i == 2 else TRACK, phase, 2 + round(4 * w))
            f.box((902, y - 28, 1236, y + 28), GREEN if i == 2 else TRACK)
            f.text((1069, y - 17), places[i], 27, INK, "ma")
        f.note(
            "Compare Q with K; the shares decide how much V to collect.",
            "Q와 K를 비교한 비중으로 V의 내용을 모읍니다.",
            "Assigned name/location vectors. Keys and values have different jobs.",
            "이름과 위치 벡터를 지정한 예시입니다. 이름표 K와 내용 V의 역할은 다릅니다.",
        )
    elif scene in (1, 2):
        label = "Mia" if s["blend"] < 0.01 else "Ava" if s["blend"] > 0.99 else "Mia → Ava"
        f.text(
            (42, 202), f.tr(f"Question: Where is {label}?", f"질문: {label}의 위치는?"), 28, BLUE
        )
        f.text((390, 261), f.tr("Softmax → shares", "Softmax → 참고 비중"), 23, MUTED)
        f.text((1000, 261), f.tr("Information collected", "모인 정보"), 23, GREEN, "ma")
        for i, (name, w) in enumerate(zip(NAMES, s["weights"])):
            y = 322 + i * 80
            f.text((42, y), name, 27)
            f.d.rounded_rectangle((175, y, 688, y + 29), 6, fill=TRACK)
            f.d.rounded_rectangle((175, y, 175 + 513 * w, y + 29), min(6, 513 * w / 2), fill=BLUE)
            f.text((776, y - 2), f"{100 * w:.0f}%", 27, BLUE, "ra")
            f.path([(793, y + 16), (841, y + 16), (884, 401)], GREEN, phase, 2 + round(7 * w))
            f.text((919, y), places[i], 25)
            f.text((1228, y), f"{100 * s['output'][i]:.0f}%", 27, GREEN, "ra")
        f.note(
            *(
                (
                    "Softmax turns scores into shares that add to 100%.",
                    "Softmax는 비교 점수를 합이 100%인 비중으로 바꿉니다.",
                    "Rounded display. Attention shares are not answer confidence.",
                    "표시는 반올림한 값입니다. 비중은 정답 확률이 아닙니다.",
                )
                if scene == 1
                else (
                    "A weighted sum collects each value in proportion to its share.",
                    "각 내용을 비중만큼 모으는 것이 가중합입니다.",
                    "Same keys and values. Only the query changes; all values still contribute.",
                    "이름표와 내용은 그대로입니다. 질문만 바뀌며, 다른 정보도 조금씩 담깁니다.",
                )
            )
        )
    else:
        words = f.tr(["The cat", "on the sofa", "sleeps"], ["고양이가", "소파에서", "잔다"])
        for x, word in zip((42, 475, 908), words):
            f.box((x, 222, x + 328, 292), BLUE if x == 908 else TRACK)
            f.text((x + 164, 239), word, 29, INK, "ma")
        for left, question, answer in [
            (75, f.tr("Who?", "누가?"), words[0]),
            (733, f.tr("Where?", "어디서?"), words[1]),
        ]:
            f.path([(1072, 295), (1072, 334), (left + 222, 334), (left + 222, 387)], BLUE, phase)
            f.box((left, 390, left + 445, 539), GREEN)
            f.text((left + 222, 410), "Head · " + question, 29, BLUE, "ma")
            f.text((left + 222, 477), answer, 28, INK, "ma")
        f.note(
            "Self-attention gathers context; heads can explore different relations.",
            "Self-attention은 문맥을 모으고, 여러 head는 다른 관계를 살필 수 있습니다.",
            "Illustrative relationships. Learned head roles are not fixed to “who” or “where”.",
            "관계 설명용 그림입니다. 실제 head는 학습되며 ‘누가/어디’로 고정되지 않습니다.",
        )
    return f.image


def resnet_frame(record, frame, lang="en"):
    s = film_state("resnet", frame)
    scene, phase = s["scene"], s["phase"]
    titles = [
        (
            "Keep useful features. Learn the correction.",
            "쓸 만한 정보는 유지하고, 바꿀 부분을 배웁니다.",
        ),
        (
            "Forward: carry the input and add a correction.",
            "순전파: 원래 정보에 수정분을 더합니다.",
        ),
        (
            "Backward: a second route for the learning signal.",
            "역전파: 학습 신호가 돌아가는 길이 하나 더 있습니다.",
        ),
        ("Help the signal reach earlier layers.", "앞쪽 층까지 학습 신호가 닿도록 돕습니다."),
    ]
    f = Frame("ResNet", lang, scene, titles[scene][lang == "ko"])
    if scene == 0:
        for x, values, label, signed in [
            (82, INPUT, f.tr("Original features", "원래 정보"), False),
            (530, s["correction"], f.tr("Correction", "수정분"), True),
            (977, s["output"], f.tr("Next features", "다음 정보"), False),
        ]:
            f.text((x + 108, 211), label, 27, INK, "ma")
            f.grid(values, x, 275, signed)
        f.text((408, 363), "+", 48, BLUE, "ma")
        f.text((855, 363), "=", 48, BLUE, "ma")
        f.text((640, 533), f.tr("Add 2 cells · remove 1", "2칸 추가 · 1칸 삭제"), 25, GREEN, "ma")
        f.note(
            "The correction is the residual. No change needed? It can be zero.",
            "이 수정분이 잔차입니다. 바꿀 필요가 없다면 0이면 됩니다.",
            "Feature-grid illustration of a learning target, not image-restoration training.",
            "학습 목표를 설명하는 격자 모형입니다. 이미지 복원 학습 실험은 아닙니다.",
        )
    elif scene in (1, 2):
        backward = scene == 2
        color = RED if backward else GREEN
        f.box((431, 224, 740, 330), GREEN)
        f.text((585, 238), f.tr("Learned branch", "학습하는 가지"), 27, GREEN, "ma")
        f.text(
            (585, 286),
            f.tr(
                "Find how to adjust" if backward else "Correction +0.1",
                "가중치의 수정 방향" if backward else "수정분 +0.1",
            ),
            23,
            INK,
            "ma",
        )
        for path in [
            [(217, 399), (299, 399), (299, 278), (426, 278)],
            [(743, 278), (899, 278), (899, 372)],
            [(927, 399), (1066, 399)],
        ]:
            f.path(path, color, phase, 4, backward)
        f.path([(299, 399), (299, 527), (899, 527), (899, 426)], BLUE, phase, 5, backward)
        f.d.ellipse((873, 373, 925, 425), fill=BG, outline=INK, width=3)
        f.text((899, 373), "+", 36, INK, "ma")
        f.text(
            (122, 333),
            f.tr("Earlier layers" if backward else "Input", "앞쪽 층" if backward else "입력"),
            25,
            INK,
            "ma",
        )
        f.text(
            (1170, 333),
            f.tr("From error" if backward else "Prediction", "오차에서 온" if backward else "예측"),
            24,
            INK,
            "ma",
        )
        if not backward:
            f.text((122, 383), "2.0", 40, INK, "ma")
            f.text((1170, 383), "2.1", 40, INK, "ma")
            f.text((1170, 457), f.tr("Target 2.2", "정답 2.2"), 22, MUTED, "ma")
        else:
            f.text((122, 442), f.tr("Both paths", "두 길의 신호"), 23, BLUE, "ma")
            f.text((1170, 442), f.tr("Learning signal", "학습 신호"), 22, RED, "ma")
            f.text(
                (585, 389),
                f.tr("The branch still learns.", "가지에서도 학습합니다."),
                24,
                GREEN,
                "ma",
            )
        f.text(
            (588, 485),
            f.tr(
                "Shortcut: a direct route back"
                if backward
                else "Shortcut carries the original 2.0",
                "지름길: 신호를 직접 돌려보냄" if backward else "지름길: 원래 값 2.0을 전달",
            ),
            24,
            BLUE,
            "ma",
        )
        f.note(
            *(
                (
                    "The error tells us how far the prediction is from the target.",
                    "정답과 예측의 차이를 줄이려면, 고칠 방향을 알아야 합니다.",
                    "Chosen two-layer branch with active ReLUs. Exact calculation in the details.",
                    "ReLU가 활성화된 두 층 가지의 예시입니다. 계산식은 상세설명에 있습니다.",
                )
                if not backward
                else (
                    "Backprop computes gradients: how changes would affect the error.",
                    "역전파는 기울기, 즉 값의 변화가 오차에 미치는 영향을 계산합니다.",
                    "Both contributions add. An optimizer then uses gradients to update weights.",
                    "두 경로의 신호가 합쳐집니다. 이후 최적화 알고리즘이 기울기로 가중치를 바꿉니다.",
                )
            )
        )
    else:
        depth = s["depth"]
        f.text(
            (42, 203),
            f.tr(
                f"Start at 100 · travel back through {depth} blocks",
                f"100에서 출발 · {depth}개 블록을 거슬러 이동",
            ),
            28,
        )
        for i, (key, color, label) in enumerate(
            [
                ("plain", RED, f.tr("Plain mappings only", "직접 매핑만")),
                ("residual", BLUE, f.tr("With shortcuts", "지름길 있음")),
            ]
        ):
            y = 300 + i * 137
            mag = abs(record[key][depth])
            number = 100 * mag
            f.text((42, y - 30), label, 26, color)
            f.d.rounded_rectangle((42, y + 15, 1052, y + 57), 6, fill=TRACK)
            if mag > 0:
                f.d.rectangle((42, y + 15, 42 + 1010 * mag, y + 57), fill=color)
            value = f.tr("< 1", "1 미만") if number < 1 else f"{number:.0f}"
            f.text((1228, y + 13), value, 32, color, "ra")
        f.text(
            (42, 542),
            f.tr(
                "Full track = starting 100 · color = arriving signal magnitude",
                "막대 전체 = 출발 100 · 색 = 도착한 신호의 크기",
            ),
            20,
            MUTED,
        )
        f.note(
            "A direct route can help earlier layers receive a learning signal.",
            "직접 전달 경로는 앞쪽 층까지 학습 신호가 닿도록 도울 수 있습니다.",
            "Chosen scalar model, not a performance test. Signal preservation is not guaranteed.",
            "지정한 숫자 모형의 예시입니다. 성능 실험이나 신호 보존의 보장은 아닙니다.",
        )
    return f.image


def encode(output, record, paint, lang):
    suffix = "" if lang == "en" else ".ko"
    paint(record, 0, lang).save(output / f"poster{suffix}.jpg", quality=94)
    args = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        "1280x720",
        "-framerate",
        str(FPS),
        "-i",
        "pipe:0",
    ]
    color = [
        "-vf",
        "scale=out_color_matrix=bt709:out_range=tv",
        "-colorspace",
        "bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-color_range",
        "tv",
        "-an",
    ]
    args += color + [
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "22",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output / f"film{suffix}.mp4"),
    ]
    args += color + [
        "-c:v",
        "libvpx-vp9",
        "-b:v",
        "0",
        "-crf",
        "34",
        "-cpu-used",
        "4",
        "-row-mt",
        "1",
        "-pix_fmt",
        "yuv420p",
        str(output / f"film{suffix}.webm"),
    ]
    process = subprocess.Popen(args, stdin=subprocess.PIPE)
    try:
        for frame in range(DURATION * FPS):
            process.stdin.write(paint(record, frame, lang).tobytes())
        process.stdin.close()
        if process.wait():
            raise RuntimeError("Film encoding failed")
    except BaseException:
        process.kill()
        process.wait()
        raise
    for ext in ("mp4", "webm"):
        probe = json.loads(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-count_frames",
                    "-show_entries",
                    "stream=width,height,nb_read_frames,color_space,color_transfer,color_primaries,color_range:format=duration",
                    "-of",
                    "json",
                    str(output / f"film{suffix}.{ext}"),
                ]
            )
        )
        stream = probe["streams"][0]
        assert (stream["width"], stream["height"]) == SIZE
        assert int(stream["nb_read_frames"]) == DURATION * FPS
        assert (
            stream["color_space"]
            == stream["color_transfer"]
            == stream["color_primaries"]
            == "bt709"
        )
        assert stream["color_range"] == "tv"
        assert abs(float(probe["format"]["duration"]) - DURATION) < 0.1


def build(output, slug, source, review=None, preview_only=False):
    record = experiment(slug, source)
    output.mkdir(parents=True, exist_ok=True)
    paint = attention_frame if slug == "attention" else resnet_frame
    if review:
        review.mkdir(parents=True, exist_ok=True)
        for lang in ("en", "ko"):
            for scene in range(4):
                paint(record, (scene * 12 + 9) * FPS, lang).save(
                    review / f"{slug}-{lang}-{scene + 1}.png"
                )
    if preview_only:
        return
    for lang in ("en", "ko"):
        encode(output, record, paint, lang)
    record["media"] = {
        name: {
            "bytes": (output / name).stat().st_size,
            "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest(),
        }
        for name in (
            "film.mp4",
            "film.webm",
            "poster.jpg",
            "film.ko.mp4",
            "film.ko.webm",
            "poster.ko.jpg",
        )
    }
    (output / "experiment.json").write_text(
        json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n"
    )
    print(
        json.dumps(
            dict(visual_paper=slug, source=source, frames=DURATION * FPS, media=record["media"])
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args()
    for slug in ("attention", "resnet"):
        build(args.output / slug, slug, args.source, args.review, args.preview_only)
