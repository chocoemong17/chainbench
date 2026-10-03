"""Static review boards, drawn from computed rows. Never renders a movie."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import runpy
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

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
    bx.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value*100:g}%"))
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
    # A durable, compact ledger keeps EVERY tried setting, including failed ones.
    # Selected full paths are in proposal.json; the complete study JSON is in Actions.
    ledger = io.StringIO(newline="")
    writer = csv.writer(ledger)
    writer.writerow(["phase", "case", "method", "candidate", "alpha", "beta", "finite",
                     "settled", "relative_loss", "relative_distance", "path_length", "early_reversals"])
    count = 0
    for phase, cases in (("broad", report["cases"]),
                         ("refinement", [dict(case=report["proposal"]["case"],
                                              methods=report["proposal"]["refinement"])])):
        for case in cases:
            for method, data in case["methods"].items():
                for i, r in enumerate(data["candidates"]):
                    writer.writerow([phase, case["case"]["id"], method, i,
                                     r["settings"]["alpha"], r["settings"]["beta"], r["finite"],
                                     r["settled"], r["final_relative_loss"], r["final_relative_distance"],
                                     r.get("path_length"), r.get("early_direction_reversals")])
                    count += 1
    (output / "candidate-ledger.csv.gz").write_bytes(gzip.compress(ledger.getvalue().encode(), mtime=0))
    lines = ["# Adam example review", "", "English · [한국어](README.ko.md)", "",
             "A nonlinear valley with very different scales in its two directions.",
             "Adam adjusts each direction's step size: less wall-to-wall motion, more progress toward the minimum.",
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
              "<details><summary>Starting points, tuning and exact evidence</summary>", "",
              "### Nearby starts with the same settings", "",
              "| Start | GD | Momentum | Adam |", "|---|---:|---:|---:|"]
    for row in report["proposal"]["frozen_starts"]:
        values = []
        for r in row["frozen"].values():
            values.append(str(r["settled"]) if r["settled"] is not None else
                          ("> 1,200" if r["finite"] else "diverged"))
        lines.append(f"| {row['case']['start']} | {' | '.join(values)} |")
    lines += ["", "The aggressive baseline settings selected on the central start can fail elsewhere.",
              "Retuning each nearby start in the broad grid gives the following results:", "",
              "| Start | GD | Momentum | Adam |", "|---|---:|---:|---:|"]
    for row in report["proposal"]["frozen_starts"]:
        values = [str(r["settled"]) if r["settled"] is not None else "> 1,200"
                  for r in row["retuned"].values()]
        lines.append(f"| {row['case']['start']} | {' | '.join(values)} |")
    lines += ["", "These are declared sensitivity checks, not independent training benchmarks.",
              f"[Full candidate ledger](candidate-ledger.csv.gz): {count:,} tried settings, including failures.",
              "The broad-grid table precedes central refinement; it is not a claim of globally optimal tuning.",
              "The quartic coefficients differ by 10,000; this is not a constant global condition number.",
              "Adam beta1=0.9, beta2=0.999, epsilon=1e-8; both bias corrections; zero initial moments.",
              "Momentum: b ← beta·b + gradient; x ← x − alpha·b; b starts at zero.",
              "The original paper: [Kingma & Ba, Algorithm 1 and §2.1](https://arxiv.org/abs/1412.6980v9).", "",
              f"Computed from source `{report['source']}`. [Machine-readable paths and settings](proposal.json).", "",
              "</details>", ""]
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")
    percentages = {m: 100*d["distance"][100]/d["distance"][0]
                   for m, d in report["proposal"]["methods"].items()}
    ko = ["# Adam — 새 예시 검토", "", "[English](README.md) · 한국어", "",
          "**한 방향은 완만하고 다른 방향은 매우 가파른 4차 함수**입니다.",
          "Adam이 방향마다 보폭을 조절해서 왕복 운동을 줄이고 목표로 이동하는 모습을 보여줍니다.", "",
          "![같은 출발점에서 실제 100회 이동한 경로](paths.svg)", "",
          f"같은 100회 계산 후 남은 거리는 GD 약 {percentages['gd']:.1f}%, "
          f"Momentum 약 {percentages['momentum']:.1f}%, Adam 약 {percentages['adam']:.1f}%입니다.", "",
          "![첫 60회 왕복 운동 확대와 목표까지의 거리](progress.svg)", "",
          "| 방법 | 목표 구간에 들어가 유지한 업데이트 횟수 |", "|---|---:|"]
    for method, data in report["proposal"]["methods"].items():
        settled = data["summary"]["settled"]
        ko.append(f"| {LABELS[method]} | {settled if settled is not None else '1,200회 안에 미도달'} |")
    ko += ["", "목표는 시작 거리의 1% 이하이면서 함수값이 시작값의 0.01% 이하인 구간이며,",
           "1,200회까지 계속 유지했는지 확인했습니다. 실행 시간이 아닌 **같은 기울기 계산 횟수**의 비교입니다.", "",
           "다른 방법도 학습률을 탐색했고, Momentum은 관성 계수도 조정했습니다.",
           "Adam이 항상 가장 빠르다는 뜻은 아닙니다. 이 예시는 방향별 경사 차이를 다루는 장점을 설명합니다.",
           "함수의 방향을 크게 회전시키거나 경사 차이를 없애면 순위가 달라지는 결과도 함께 남겼습니다.", "",
           "[조건·주변 시작점·전체 비교 기록](README.md) · "
           "[원 논문](https://arxiv.org/abs/1412.6980v9)", "",
           "이번 검토본은 경로와 그래프입니다. 기존 홈페이지 구성은 유지하며, 새 영상은 아직 만들지 않았습니다.", ""]
    (output / "README.ko.md").write_text("\n".join(ko), encoding="utf-8")
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
