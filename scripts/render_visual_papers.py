"""Render the two paper films from computed records on GitHub Actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from chainbench.visual_papers import experiment

SIZE = (1280, 720)
BG, INK, MUTED, TEAL = "#172127", "#edf0e5", "#b7c8bf", "#68c7bb"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONTS = {s: ImageFont.truetype(FONT, s) for s in (19, 22, 26, 32, 40)}


def text(draw, xy, value, size=22, fill=INK, anchor=None):
    draw.text(xy, str(value), font=FONTS[size], fill=fill, anchor=anchor)


def arrow(draw, start, end, fill=TEAL, width=3):
    draw.line([start, end], fill=fill, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    pts = [
        end,
        (end[0] - 12 * math.cos(angle - 0.5), end[1] - 12 * math.sin(angle - 0.5)),
        (end[0] - 12 * math.cos(angle + 0.5), end[1] - 12 * math.sin(angle + 0.5)),
    ]
    draw.polygon(pts, fill=fill)


def rgb(values):
    return tuple(round(255 * min(1.0, max(0.0, v))) for v in values)


def base(record, k):
    img = Image.new("RGB", SIZE, BG)
    draw = ImageDraw.Draw(img)
    title = "ATTENTION / 02" if record["slug"] == "attention" else "RESNET / 03"
    text(draw, (42, 24), title, 22, MUTED)
    text(draw, (42, 55), "LOOK + MIX" if record["slug"] == "attention" else "KEEP + ADD", 32)
    text(draw, (1238, 42), "48 SEC", 22, MUTED, "ra")
    draw.line((42, 105, 1238, 105), fill="#354249")
    draw.line((42, 611, 1238, 611), fill="#354249")
    return img, draw


def attention_frame(record, k):
    img, d = base(record, k)
    row = record["rows"][k]
    text(d, (166, 145), "QUERY", 22, MUTED, "ma")
    text(d, (582, 145), "KEYS + VALUES", 22, MUTED, "ma")
    text(d, (1050, 145), "OUTPUT", 22, MUTED, "ma")
    cx, cy, radius = 166, 360, 96
    d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline="#48585b", width=2)
    d.line((cx - radius, cy, cx + radius, cy), fill="#354249")
    d.line((cx, cy - radius, cx, cy + radius), fill="#354249")
    for key, color in zip(record["keys"], record["colors"]):
        x, y = cx + radius * key[0], cy - radius * key[1]
        d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color)
    qx, qy = row["query"]
    arrow(d, (cx, cy), (cx + radius * qx / 4, cy - radius * qy / 4), width=5)
    text(d, (cx, 487), str(k) + "°", 40, TEAL, "ma")
    # Width and numbers both encode the same computed weights.
    for i, (name, weight, color) in enumerate(
        zip(record["names"], row["weights"], record["colors"])
    ):
        y = 207 + i * 99
        d.line((286, cy, 403, y + 30), fill="#465657", width=2)
        d.line((752, y + 30, 950, cy), fill=color, width=1 + round(15 * weight))
        d.rounded_rectangle(
            (403, y, 752, y + 68), radius=12, fill="#233137", outline=color, width=2
        )
        key = record["keys"][i]
        arrow(d, (435, y + 35), (435 + 20 * key[0], y + 35 - 20 * key[1]), color, 2)
        text(d, (473, y + 18), name, 26)
        text(d, (687, y + 20), f"{weight:.0%}", 22, MUTED, "ra")
        d.rounded_rectangle((709, y + 20, 735, y + 46), radius=4, fill=rgb(record["values"][i]))
    d.rounded_rectangle(
        (950, 270, 1150, 470), radius=20, fill=rgb(row["output"]), outline=INK, width=2
    )
    text(d, (1050, 491), "weighted mix", 22, MUTED, "ma")
    text(d, (42, 636), "Turn the query. Follow the weights.", 26)
    text(d, (42, 675), "Constructed color vectors · one attention head", 19, MUTED)
    return img


def pixel_image(values, signed=False):
    img = Image.new("RGB", (len(values[0]), len(values)))
    if signed:

        def color(v):
            strength = min(1.0, abs(v) / 0.2)
            target = (
                (104 / 255, 199 / 255, 187 / 255) if v >= 0 else (223 / 255, 120 / 255, 85 / 255)
            )
            return rgb([0.22 + (c - 0.22) * strength for c in target])
    else:

        def color(v):
            return rgb((v, v, v))

    img.putdata([color(v) for row in values for v in row])
    return img.resize((248, 248), Image.Resampling.NEAREST)


def resnet_frame(record, k):
    img, d = base(record, k)
    row = record["rows"][k]
    # The bypass carries x unchanged. A lower path feeds x to the residual branch.
    d.line([(212, 245), (212, 181), (1034, 181), (1034, 245)], fill=TEAL, width=4)
    arrow(d, (1034, 218), (1034, 245), TEAL, 4)
    text(d, (626, 139), "identity shortcut", 22, TEAL, "ma")
    d.line([(212, 532), (212, 567), (624, 567), (624, 532)], fill="#8da39b", width=3)
    arrow(d, (624, 567), (624, 532), "#8da39b", 3)
    for x, label, values, signed in [
        (88, "INPUT  x", record["input"], False),
        (500, "CHANGE  F(x)", row["delta"], True),
        (910, "OUTPUT  x + F(x)", row["output"], False),
    ]:
        text(d, (x + 124, 218), label, 22, MUTED, "ma")
        img.paste(pixel_image(values, signed), (x, 263))
        d.rounded_rectangle((x - 1, 262, x + 249, 512), radius=3, outline="#677875", width=2)
    text(d, (413, 363), "+", 40, TEAL, "ma")
    text(d, (828, 363), "=", 40, TEAL, "ma")
    text(d, (624, 583), "add brightness / subtract brightness", 19, MUTED, "ma")
    text(d, (42, 636), f"Correction strength  {row['strength']:.2f}", 26)
    text(d, (1238, 636), f"Target error  {row['rmse']:.3f}", 26, INK, "ra")
    text(d, (42, 675), "Chosen two-unit branch · final ReLU · no training benchmark", 19, MUTED)
    return img


def build(output, slug, source, review=None, preview_only=False):
    record = experiment(slug, source)
    output.mkdir(parents=True, exist_ok=True)
    paint = attention_frame if slug == "attention" else resnet_frame
    if review:
        review.mkdir(parents=True, exist_ok=True)
        for k in (0, record["steps"] // 2, record["steps"]):
            paint(record, k).save(review / f"{slug}-{k}.png")
    if preview_only:
        return
    paint(record, 0).save(output / "poster.jpg", quality=94)
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
        "24",
        "-i",
        "pipe:0",
        "-an",
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
        str(output / "film.mp4"),
        "-an",
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
        str(output / "film.webm"),
    ]
    process = subprocess.Popen(args, stdin=subprocess.PIPE)
    try:
        previous, pixels = None, None
        for k in record["frame_steps"]:
            if k != previous:
                pixels = paint(record, k).tobytes()
                previous = k
            process.stdin.write(pixels)
        process.stdin.close()
        if process.wait():
            raise RuntimeError("Film encoding failed")
    except BaseException:
        process.kill()
        process.wait()
        raise
    for filename in ("film.mp4", "film.webm"):
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
                    "stream=width,height,nb_read_frames:format=duration",
                    "-of",
                    "json",
                    str(output / filename),
                ]
            )
        )
        stream = probe["streams"][0]
        assert (stream["width"], stream["height"]) == SIZE
        assert int(stream["nb_read_frames"]) == 1152
        assert abs(float(probe["format"]["duration"]) - 48) < 0.1
    record["media"] = {
        name: {
            "bytes": (output / name).stat().st_size,
            "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest(),
        }
        for name in ("film.mp4", "film.webm", "poster.jpg")
    }
    (output / "experiment.json").write_text(
        json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n"
    )
    print(
        json.dumps(
            {"visual_paper": slug, "source": source, "frames": 1152, "media": record["media"]}
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
