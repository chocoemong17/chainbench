"""Render the Adam paper lesson on GitHub Actions from real numerical traces."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from mpl_toolkits.mplot3d import proj3d
from PIL import Image, ImageDraw, ImageFont

from chainbench.adam_lesson import ANGLE, experiment, iteration_at

SIZE = (1280, 720)
BG = "#172127"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def background(record):
    """One fixed camera keeps paths comparable throughout the film."""
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=BG)
    ax = fig.add_axes([-0.08, -0.1, 1.00, 1.11], projection="3d", facecolor=BG)
    x, y = np.meshgrid(np.linspace(-1.85, 0.9, 135), np.linspace(-0.45, 1.9, 135))
    c, s = math.cos(ANGLE), math.sin(ANGLE)
    u, v = c * x + s * y, -s * x + c * y
    f = (1 - u) ** 2 + 100 * (v - u * u) ** 2
    z = np.log1p(f)
    cmap = LinearSegmentedColormap.from_list("valley", ["#274544", "#55726b", "#8a9a87", "#c4c9af"])
    ax.plot_surface(
        x,
        y,
        z,
        rcount=100,
        ccount=100,
        cmap=cmap,
        alpha=0.90,
        edgecolor="none",
        antialiased=True,
        shade=True,
    )
    ax.contour(
        x,
        y,
        z,
        levels=[0.02, 0.1, 0.3, 0.7, 1.3, 2.3, 3.5, 5.0, 6.5],
        zdir="z",
        offset=-0.12,
        colors="#60746d",
        linewidths=0.7,
        alpha=0.7,
    )
    ax.set(xlim=(-1.85, 0.9), ylim=(-0.45, 1.9), zlim=(-0.12, 7.8))
    ax.set_box_aspect((2.75, 2.35, 1.55))
    ax.view_init(elev=43, azim=-72)
    ax.set_axis_off()
    fig.canvas.draw()
    img = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())
    projection = ax.get_proj()

    def project(point):
        px, py = point
        uu, vv = c * px + s * py, -s * px + c * py
        height = math.log1p((1 - uu) ** 2 + 100 * (vv - uu * uu) ** 2)
        sx, sy, _ = proj3d.proj_transform(px, py, height, projection)
        a, b = ax.transData.transform((sx, sy))
        return (float(a), float(SIZE[1] - b))

    projected = {
        m: [project(r["point"]) for r in trace["rows"]] for m, trace in record["traces"].items()
    }
    target, start = project(record["target"]), project(record["start"])
    plt.close(fig)
    return img, projected, target, start


def paint(base, projected, target, start, record, index):
    img = base.copy()
    draw = ImageDraw.Draw(img)
    small = ImageFont.truetype(FONT, 24)
    medium = ImageFont.truetype(FONT, 32)
    large = ImageFont.truetype(FONT, 44)
    # The film itself contains only numerical labels and method names; the
    # language-specific explanation is in selectable caption tracks.
    draw.text((42, 28), "ADAM  /  01", font=small, fill="#c4ccc1")
    draw.text((42, 52), f"k = {index:,}", font=large, fill="#f1f3e9")
    draw.text((1110, 35), "2,400", font=medium, fill="#bac8bd")
    draw.line((42, 111, 1238, 111), fill="#36444a", width=1)
    for method, trace in record["traces"].items():
        color = trace["settings"]["color"]
        pts = projected[method][: index + 1]
        if len(pts) > 1:
            draw.line(pts, fill=color, width=3, joint="curve")
        px, py = pts[-1]
        draw.ellipse((px - 8, py - 8, px + 8, py + 8), fill=color, outline="#162027", width=2)
    tx, ty = target
    draw.ellipse((tx - 8, ty - 8, tx + 8, ty + 8), outline="#fff5d3", width=2)
    draw.line((tx - 13, ty, tx + 13, ty), fill="#fff5d3", width=1)
    draw.line((tx, ty - 13, tx, ty + 13), fill="#fff5d3", width=1)
    sx, sy = start
    draw.ellipse((sx - 8, sy - 8, sx + 8, sy + 8), outline="#d2d8c9", width=1)
    # A compact numerical ledger leaves the terrain as the main visual.
    for j, (method, trace) in enumerate(record["traces"].items()):
        y = 208 + j * 101
        color = trace["settings"]["color"]
        draw.line((1001, y + 10, 1021, y + 10), fill=color, width=3)
        label = "GD" if method == "gd" else trace["settings"]["label"]
        draw.text((1032, y), label, font=medium, fill=color)
        draw.text(
            (1001, y + 35), f"f = {trace['rows'][index]['loss']:.2e}", font=small, fill="#d6dcd0"
        )
    draw.text((42, 634), "z = log(1 + f)", font=small, fill="#bcc9bf")
    draw.text((42, 658), "f* = 0", font=small, fill="#bcc9bf")
    return img


def build_film(output: Path, source: str):
    if not re.fullmatch("[0-9a-f]{40}", source):
        raise ValueError("A complete source commit is required")
    output.mkdir(parents=True, exist_ok=True)
    record = experiment(source)
    frames = [iteration_at(n / record["fps"]) for n in range(record["duration"] * record["fps"])]
    record["frame_iterations"] = frames
    record["render"] = {
        "size": list(SIZE),
        "height": "log1p(objective)",
        "camera": {"elevation": 43, "azimuth": -72},
        "paths": "projected actual iterates",
        "frame_mapping": "each video frame selects one computed iterate; no interpolation",
    }
    base, projected, target, start = background(record)
    # Fail on clipped numerical paths, rather than hiding out-of-frame behavior.
    for points in projected.values():
        assert all(20 < x < 990 and 115 < y < 632 for x, y in points), (
            "Path leaves film view",
            min(x for x, y in points),
            max(x for x, y in points),
            min(y for x, y in points),
            max(y for x, y in points),
        )
    paint(base, projected, target, start, record, 0).save(output / "poster.jpg", quality=93)
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
        str(record["fps"]),
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
        str(output / "adam.mp4"),
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
        str(output / "adam.webm"),
    ]
    process = subprocess.Popen(args, stdin=subprocess.PIPE)
    try:
        for index in frames:
            process.stdin.write(paint(base, projected, target, start, record, index).tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("Film encoding failed")
    except BaseException:
        process.kill()
        process.wait()
        raise
    record["media"] = {}
    for name in ["adam.mp4", "adam.webm", "poster.jpg"]:
        data = (output / name).read_bytes()
        record["media"][name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    # ffprobe verifies that the delivery files really contain the declared frames.
    for name in ["adam.mp4", "adam.webm"]:
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
                    str(output / name),
                ]
            )
        )
        stream = probe["streams"][0]
        assert [stream["width"], stream["height"]] == list(SIZE)
        assert int(stream["nb_read_frames"]) == len(frames)
        assert abs(float(probe["format"]["duration"]) - record["duration"]) < 0.1
    (output / "experiment.json").write_text(
        json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n",
        encoding="utf8",
    )
    print(
        json.dumps(
            {
                "adam_film": record["media"],
                "source": source,
                "frames": len(frames),
                "final_loss": {m: t["rows"][-1]["loss"] for m, t in record["traces"].items()},
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    build_film(args.output, args.source)
