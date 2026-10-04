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

from chainbench.adam_lesson import SCALE, experiment, iteration_at, objective

SIZE = (1280, 720)
BG = "#172127"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def background(record):
    """An open near wall and a tall fixed camera make the valley floor visible."""
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor=BG)
    ax = fig.add_axes([-0.07, -0.06, 1.0, .95], projection="3d", facecolor=BG)
    xs = np.linspace(-3.6, 0.8, 100)
    # Resolve the bottom of the narrow valley explicitly, rather than bridging it
    # with a coarse uniform mesh. The optimizer coordinates are never rescaled.
    ys = np.unique(np.r_[0, np.geomspace(.001, .2, 45), np.linspace(.2, 2.7, 70)])
    cmap = LinearSegmentedColormap.from_list(
        "depth", ["#247f86", "#5c9e9b", "#a8bbb0", "#e0d5ac"])

    def height(x, y):
        return np.log1p(x*x/2 + x**4/4 + SCALE*(y*y/2 + y**4/4))

    def filled_side(y):
        x, y = np.meshgrid(xs, y)
        z = height(x, y)
        ax.plot_surface(x, y, z, rcount=len(y), ccount=len(xs), cmap=cmap,
                        vmin=0, vmax=12, linewidth=0, edgecolor="none", antialiased=False)

    filled_side(ys)
    filled_side(np.linspace(-.045, 0, 24))
    # The entire near wall is retained geometrically but shown only as a mesh.
    near = -np.unique(np.r_[0, .025, .05, .1, .2, .35, .55, .8, 1.1, 1.5, 2, 2.7])[::-1]
    near_dense = -ys[::-1]
    # A sparse base grid and vertical drop lines give an unambiguous depth cue.
    for xx in (-3, -2, -1, 0):
        ax.plot([xx, xx], [-2.7, 2.7], [-.12, -.12], color="#405159", lw=.65)
    for yy in (-2, -1, 0, 1, 2):
        ax.plot([-3.6, .8], [yy, yy], [-.12, -.12], color="#405159", lw=.65)
    ax.set(xlim=(-3.6, 1.0), ylim=(-2.7, 2.7), zlim=(-.15, 12.2))
    ax.set_box_aspect((4.6, 5.4, 3.8))
    ax.view_init(elev=27, azim=-56)
    ax.set_axis_off()
    fig.canvas.draw()
    img = Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy())
    projection = ax.get_proj()

    def project(point, level=None):
        px, py = point
        z = math.log1p(objective(point)) if level is None else level
        sx, sy, _ = proj3d.proj_transform(px, py, z, projection)
        a, b = ax.transData.transform((sx, sy))
        return (float(a), float(SIZE[1] - b))

    view = {
        "paths": {m: [project(r["point"]) for r in t["rows"]] for m, t in record["traces"].items()},
        "footprints": {m: [project(r["point"], 0) for r in t["rows"]] for m, t in record["traces"].items()},
        "target": project(record["target"]), "start": project(record["start"]),
        "height_ticks": [(f, project((.95, 2.7), math.log1p(f))) for f in (0, 100, 10000, 100000)],
    }
    # Matplotlib sorts entire line artists behind surfaces. Draw the transparent
    # cutaway mesh in projected screen space so the intended near wall stays visible.
    wire = ImageDraw.Draw(img)
    for xx in np.linspace(-3.6, .8, 7):
        wire.line([project((xx, yy)) for yy in ys], fill="#648887", width=1)
        wire.line([project((xx, yy)) for yy in near_dense], fill="#546c70", width=1)
    for yy in near:
        wire.line([project((xx, yy)) for xx in xs], fill="#435c62", width=1)
    wire.line([project((xx, 0)) for xx in xs], fill="#b3efdb", width=2)
    wire.line([project((.8, yy)) for yy in np.r_[near_dense, ys[1:]]], fill="#96b3b0", width=2)
    plt.close(fig)
    return img, view


def dashed(draw, a, b, color):
    length = math.dist(a, b)
    for distance in range(0, int(length), 10):
        lo, hi = distance / length, min(distance + 4, length) / length
        draw.line((a[0]+(b[0]-a[0])*lo, a[1]+(b[1]-a[1])*lo,
                   a[0]+(b[0]-a[0])*hi, a[1]+(b[1]-a[1])*hi), fill=color, width=1)


def paint(base, view, record, index):
    img = base.copy()
    draw = ImageDraw.Draw(img)
    small = ImageFont.truetype(FONT, 22)
    medium = ImageFont.truetype(FONT, 29)
    large = ImageFont.truetype(FONT, 42)
    draw.text((42, 24), "ADAM  /  01", font=small, fill="#c4ccc1")
    draw.text((42, 48), f"k = {index:,}", font=large, fill="#f1f3e9")
    draw.text((1110, 34), f"{record['steps']:,}", font=medium, fill="#bac8bd")
    draw.line((42, 104, 1238, 104), fill="#36444a", width=1)
    for method, trace in record["traces"].items():
        color = trace["settings"]["color"]
        pts = view["paths"][method][:index+1]
        foot = view["footprints"][method][index]
        dashed(draw, pts[-1], foot, "#728788")
        draw.ellipse((foot[0]-3, foot[1]-3, foot[0]+3, foot[1]+3), outline="#849793", width=1)
        if len(pts) > 1:
            faded = tuple(round(int(color[i:i+2], 16)*.38 + int(BG[i:i+2], 16)*.62)
                          for i in (1, 3, 5))
            draw.line(pts, fill=faded, width=2, joint="curve")
            draw.line(pts[-61:], fill="#13262f", width=7, joint="curve")
            draw.line(pts[-61:], fill=color, width=3, joint="curve")
        px, py = pts[-1]
        draw.ellipse((px-8, py-8, px+8, py+8), fill=color, outline="#eef4df", width=2)
    tx, ty = view["target"]
    draw.line((tx-11, ty, tx+11, ty), fill="#fff5d3", width=2)
    draw.line((tx, ty-11, tx, ty+11), fill="#fff5d3", width=2)
    sx, sy = view["start"]
    draw.ellipse((sx-8, sy-8, sx+8, sy+8), outline="#d2d8c9", width=1)
    ticks = view["height_ticks"]
    draw.line((ticks[0][1], ticks[-1][1]), fill="#9aaea4", width=1)
    for value, (x, y) in ticks:
        draw.line((x-4, y, x+4, y), fill="#c4d3c4", width=1)
        draw.text((x+8, y-11), {0:"0", 100:"10²", 10000:"10⁴", 100000:"10⁵"}[value],
                  font=small, fill="#c4d3c4")
    draw.text((994, 222), "Distance left", font=small, fill="#b8c8bf")
    for j, (method, trace) in enumerate(record["traces"].items()):
        y = 263 + j * 100
        color = trace["settings"]["color"]
        label = "GD" if method == "gd" else trace["settings"]["label"]
        draw.text((994, y), label, font=medium, fill=color)
        percentage = 100 * trace["rows"][index]["distance"] / trace["rows"][0]["distance"]
        draw.text((994, y+36), f"{percentage:.1f}%", font=small, fill="#e1e7d7")
        settled = record["target_test"]["settled"][method]
        if settled is not None and index >= settled:
            draw.text((1090, y+36), f"k {settled}", font=small, fill=color)
    draw.text((42, 635), "Height = log(1 + f)  ·  near wall: wireframe", font=small, fill="#bdcdc2")
    draw.text((42, 665), "+ minimum   ·   dashed lines show depth", font=small, fill="#bdcdc2")
    return img


def review_frames(output, source, record, base, view):
    output.mkdir(parents=True, exist_ok=True)
    for k in (0, 10, 30, 66, 100, 611, 1200):
        paint(base, view, record, k).save(output / f"depth-k{k}.png")
    proof = {"source": source, "camera": {"elevation": 27, "azimuth": -56},
             "height": "log1p(objective)", "near_wall": "wireframe; no optimizer coordinates changed",
             "path_bounds": {m: [min(x for x, y in pts), max(x for x, y in pts),
                                  min(y for x, y in pts), max(y for x, y in pts)]
                             for m, pts in view["paths"].items()},
             "height_ticks": view["height_ticks"], "target": view["target"],
             "settled": record["target_test"]["settled"]}
    (output / "depth-verification.json").write_text(json.dumps(proof, indent=2)+"\n")
    print(json.dumps({"depth_review": proof}))


def build_film(output: Path, source: str, review=None, preview_only=False):
    if not re.fullmatch("[0-9a-f]{40}", source):
        raise ValueError("A complete source commit is required")
    output.mkdir(parents=True, exist_ok=True)
    record = experiment(source)
    frames = [iteration_at(n / record["fps"]) for n in range(record["duration"] * record["fps"])]
    record["frame_iterations"] = frames
    record["render"] = {
        "size": list(SIZE),
        "height": "log1p(objective)",
        "camera": {"elevation": 27, "azimuth": -56},
        "near_wall": "wireframe cutaway",
        "depth_cues": "height colors, floor grid, height ticks, vertical current-point projections",
        "paths": "projected actual iterates",
        "trails": "entire history faint; latest 60 updates bright",
        "frame_mapping": "each video frame selects one computed iterate; no interpolation",
    }
    base, view = background(record)
    if review is not None:
        review_frames(review, source, record, base, view)
    # Fail on clipped numerical paths, rather than hiding out-of-frame behavior.
    for points in view["paths"].values():
        assert all(20 < x < 980 and 180 < y < 628 for x, y in points), (
            "Path leaves film view",
            min(x for x, y in points),
            max(x for x, y in points),
            min(y for x, y in points),
            max(y for x, y in points),
        )
    assert math.dist(view["height_ticks"][0][1], view["height_ticks"][-1][1]) > 140
    if preview_only:
        return
    paint(base, view, record, 0).save(output / "poster.jpg", quality=93)
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
            process.stdin.write(paint(base, view, record, index).tobytes())
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
    parser.add_argument("--review", type=Path)
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args()
    build_film(args.output, args.source, args.review, args.preview_only)
