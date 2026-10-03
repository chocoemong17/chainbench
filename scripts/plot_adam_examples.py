"""Static review boards, drawn from computed rows. Never renders a movie."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import runpy
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter

MODEL = runpy.run_path(str(Path(__file__).with_name("study_adam_examples.py")))
COLORS = {"gd": "#507eb6", "momentum": "#b47a24", "adam": "#d55e4d"}
LABELS = {"gd": "Gradient descent", "momentum": "Momentum", "adam": "Adam"}
INK, MUTED, PAPER = "#242c2c", "#677271", "#faf8f2"


def style():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "text.color": INK, "axes.labelcolor": MUTED,
                         "xtick.color": MUTED, "ytick.color": MUTED,
                         "axes.edgecolor": "#d6d8d1", "axes.facecolor": PAPER,
                         "figure.facecolor": PAPER, "savefig.facecolor": PAPER,
                         "svg.fonttype": "none", "svg.hashsalt": "adam-example-v1"})


def clean(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=0, pad=7)
    ax.grid(axis="y", color="#dde0d9", linewidth=0.6, zorder=0)


def save(fig, output, name):
    for suffix in ("svg", "png"):
        fig.savefig(output / f"{name}.{suffix}", dpi=150, metadata={"Date": None}
                    if suffix == "svg" else None)
    plt.close(fig)


def paths_board(report, output):
    proposal = report["proposal"]
    fig = plt.figure(figsize=(12, 7.5))
    fig.text(.06, .935, "ADAM  /  EXAMPLE STUDY", fontsize=10, color=MUTED)
    fig.text(.06, .875, "Same valley. Different progress.", fontsize=27, fontfamily="DejaVu Serif")
    fig.text(.06, .827, "The first 100 gradient updates — equal axes, equal starting point.", color=MUTED)
    grid = fig.add_gridspec(1, 3, left=.065, right=.965, bottom=.205, top=.73, wspace=.26)
    xs, ys = np.meshgrid(np.linspace(-3.5, .9, 400), np.linspace(-2.7, 2.7, 400))
    heights, _ = MODEL["evaluate"](np.stack((xs, ys), axis=-1), proposal["case"])
    for col, (method, data) in enumerate(proposal["methods"].items()):
        ax = fig.add_subplot(grid[0, col])
        color = COLORS[method]
        ax.contour(xs, ys, heights, levels=np.geomspace(.1, 150000, 12),
                   colors="#e2e3db", linewidths=.75)
        p = np.array(data["path"])[:101]
        ax.plot(p[:, 0], p[:, 1], color=color, lw=1.8, alpha=.86)
        ax.scatter(p[:21, 0], p[:21, 1], color=color, s=10, zorder=4)
        ax.scatter(*p[0], marker="s", facecolor=PAPER, edgecolor=INK, s=45, zorder=6)
        ax.scatter(*p[-1], color=color, edgecolor=PAPER, linewidth=1, s=70, zorder=7)
        ax.scatter(0, 0, marker="+", color=INK, s=100, linewidth=1.5, zorder=8)
        ax.set(xlim=(-3.5, .9), ylim=(-2.7, 2.7), xticks=[-3, -2, -1, 0], yticks=[-2, 0, 2])
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(LABELS[method], color=color, fontsize=14, loc="left", pad=20)
        ax.set_xlabel("x")
        if col == 0:
            ax.set_ylabel("y  ·  steep direction")
        clean(ax)
        fraction = data["distance"][100] / data["distance"][0]
        ax.text(0, -.18, f"{100*fraction:.1f}% distance left", transform=ax.transAxes,
                color=color, fontsize=13, weight="bold")
    fig.text(.065, .1, "□ start       + minimum       ● update 100       small dots: first 20 updates",
             color=MUTED, fontsize=10)
    fig.text(.065, .055, "Unequal-scale quartic: f = φ(x) + 10,000 φ(y),   φ(z) = z²/2 + z⁴/4.",
             color=MUTED, fontsize=10)
    save(fig, output, "paths")


def progress_board(report, output):
    fig = plt.figure(figsize=(12, 6.8))
    fig.text(.065, .925, "SEE THE STRUGGLE", fontsize=10, color=MUTED)
    fig.text(.065, .86, "Make the early oscillation visible.", fontsize=25, fontfamily="DejaVu Serif")
    grid = fig.add_gridspec(1, 2, left=.08, right=.96, bottom=.22, top=.7, wspace=.27)
    ax, bx = fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1])
    for method, data in report["proposal"]["methods"].items():
        color = COLORS[method]
        p = np.array(data["path"])
        ax.plot(np.arange(61), p[:61, 1], color=color, label=LABELS[method], lw=1.5,
                marker="o", ms=2)
        d = np.array(data["distance"]) / data["distance"][0]
        bx.plot(np.arange(len(d)), d, color=color, lw=2, label=LABELS[method])
    ax.axhline(0, color=INK, lw=.7, alpha=.4)
    ax.set(xlabel="Gradient updates", ylabel="y position", xlim=(0, 60), ylim=(-2.7, 2.7))
    ax.set_title("Wall-to-wall movement · first 60 updates", loc="left", fontsize=12, pad=18)
    bx.set(yscale="log", xlim=(0, 1200), ylim=(.001, 1.5),
           xlabel="Gradient updates", ylabel="Distance / starting distance")
    bx.yaxis.set_major_formatter(PercentFormatter(xmax=1))
    bx.axhline(.01, color=INK, lw=1, ls=(0, (3, 3)))
    bx.text(1175, .012, "1% distance", ha="right", fontsize=9, color=MUTED)
    bx.set_title("Getting close — and staying close", loc="left", fontsize=12, pad=18)
    clean(ax)
    clean(bx)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower left", bbox_to_anchor=(.065, .09),
               ncol=3, frameon=False, fontsize=11)
    fig.text(.065, .045, "Target also requires objective ≤ 0.01% of its initial value; checked through update 1,200.",
             fontsize=10, color=MUTED)
    save(fig, output, "progress")


def write_review(report, output):
    rows = []
    for case in report["cases"]:
        for method, data in case["methods"].items():
            best = data["candidates"][data["selected"]]
            rows.append(dict(case=case["case"]["id"], method=method,
                             alpha=best["settings"]["alpha"], beta=best["settings"]["beta"],
                             settled=best["settled"], candidates=len(data["candidates"]),
                             divergent=sum(not c["finite"] for c in data["candidates"])))
    with (output / "case-summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    compact = {k: v for k, v in report.items() if k not in ("cases", "proposal")}
    compact["proposal"] = {k: v for k, v in report["proposal"].items() if k != "refinement"}
    compact["all_cases"] = rows
    compact["refinement"] = {
        m: dict(tried=len(d["candidates"]), divergent=sum(not c["finite"] for c in d["candidates"]),
                best=d["candidates"][d["best"]]) for m, d in report["proposal"]["refinement"].items()}
    (output / "proposal.json").write_text(json.dumps(compact, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    lines = ["# Adam example review", "", "A nonlinear valley with very different scales in its two directions.",
             "", "![Actual first 100 updates](paths.svg)", "", "![Early oscillation and progress](progress.svg)",
             "", "| Method | Updates to the target | Learning rate | Momentum |", "|---|---:|---:|---:|"]
    for method, data in report["proposal"]["methods"].items():
        r = data["summary"]
        k = r["settled"] if r["settled"] is not None else "> 1,200"
        lines.append(f"| {LABELS[method]} | {k} | {r['settings']['alpha']:.8g} | {r['settings']['beta']:.6g} |")
    lines += ["", "The target requires **both** distance ≤ 1% of its starting value and objective ≤ 0.01% of its starting value,",
              "remaining there through update 1,200. Equal full-gradient counts, not wall-clock speed.", "",
              "Adam uses a round learning rate of 0.14; each baseline uses its best found central setting.",
              "This constructed example shows why coordinate-wise normalization can help.",
              "Rotation or a well-scaled function can change the ranking; all 27 cases are in [the table](case-summary.csv).", "",
              "## Nearby starts with the same settings", "",
              "| Start | GD | Momentum | Adam |", "|---|---:|---:|---:|"]
    for row in report["proposal"]["frozen_starts"]:
        values = []
        for r in row["frozen"].values():
            values.append(str(r["settled"]) if r["settled"] is not None else
                          ("> 1,200" if r["finite"] else "diverged"))
        lines.append(f"| {row['case']['start']} | {' | '.join(values)} |")
    lines += ["", "These are declared sensitivity checks, not independent training benchmarks.",
              "The original paper: [Kingma & Ba, Algorithm 1 and §2.1](https://arxiv.org/abs/1412.6980v9).", "",
              f"Computed from source `{report['source']}`. [Machine-readable paths and settings](proposal.json).", ""]
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")
    manifest = {p.name: dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                for p in output.iterdir() if p.is_file() and p.name != "manifest.json"}
    (output / "manifest.json").write_text(json.dumps(dict(source=report["source"], files=manifest), indent=2), encoding="utf-8")
    print(json.dumps(dict(source=report["source"], files=manifest)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    style()
    paths_board(data, args.output)
    progress_board(data, args.output)
    write_review(data, args.output)
