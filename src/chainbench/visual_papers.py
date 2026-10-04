"""Small, explicit illustrations of Attention Eq. (1) and ResNet Eq. (1).

Authored inputs and weights, not trained models or source-paper benchmarks.
See docs/VISUAL_PAPERS.md for the scope of each display.
"""

from __future__ import annotations

import math
import re

COLORS = ("#df5545", "#398c68", "#4979bf", "#b88b2d")
NAMES = ("Red", "Green", "Blue", "Gold")
KEYS = ((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0))
VALUES = ((0.88, 0.25, 0.20), (0.22, 0.68, 0.47), (0.23, 0.45, 0.85), (0.89, 0.65, 0.22))
DURATION, FPS = 48, 24


def attention(query, keys, values):
    """A single query in softmax(Q K^T / sqrt(d_k)) V; no learned projections."""
    if not query or not keys or len(keys) != len(values) or not values[0]:
        raise ValueError("Nonempty matching keys and values required")
    if any(len(k) != len(query) for k in keys) or any(len(v) != len(values[0]) for v in values):
        raise ValueError("Mismatched dimensions")
    if not all(math.isfinite(x) for row in [query, *keys, *values] for x in row):
        raise ValueError("Finite inputs required")
    scores = [math.fsum(q * k for q, k in zip(query, key)) / math.sqrt(len(query)) for key in keys]
    if not all(math.isfinite(s) for s in scores):
        raise ValueError("Nonfinite scores")
    exps = [math.exp(s - max(scores)) for s in scores]
    weights = [e / math.fsum(exps) for e in exps]
    output = [math.fsum(w * v[c] for w, v in zip(weights, values)) for c in range(len(values[0]))]
    return {"scores": scores, "weights": weights, "output": output}


def residual_block(x, strength):
    """Two ReLU hidden units [ReLU(x), ReLU(1)], then add x and ReLU.

    W1=[[1],[0]], b1=[0,1], W2=strength*[.8,-.4], b2=0.
    Zero branch preserves nonnegative x; final ReLU still clips negative x.
    """
    if not math.isfinite(x) or not math.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError("Finite x and strength in [0,1] required")
    correction = strength * (0.8 * max(0.0, x) - 0.4)
    return correction, max(0.0, x + correction)


def pattern(size=32):
    """An original binary ring and diagonal, no image downloads."""
    return [
        [
            float(
                0.18 < math.hypot((c + 0.5) / size - 0.5, (r + 0.5) / size - 0.5) < 0.35
                or abs(r - c) < 2
            )
            for c in range(size)
        ]
        for r in range(size)
    ]


def timing(steps):
    return [(0, 0), (4, 0), (22, steps // 2), (25, steps // 2), (41, steps), (48, steps)]


def frame_steps(steps):
    knots = timing(steps)
    result = []
    for frame in range(DURATION * FPS):
        t = frame / FPS
        for (a, ka), (b, kb) in zip(knots, knots[1:]):
            if t <= b:
                result.append(ka + math.floor((kb - ka) * (t - a) / (b - a) + 1e-8))
                break
    return result


def experiment(slug, source):
    if slug not in ("attention", "resnet") or not re.fullmatch("[a-f0-9]{40}", source):
        raise ValueError("Known lesson and full source commit required")
    steps = 180 if slug == "attention" else 100
    record = {
        "kind": "chainbench.visual-paper.v1",
        "slug": slug,
        "source": source,
        "steps": steps,
        "duration": DURATION,
        "fps": FPS,
        "timing": timing(steps),
        "frame_steps": frame_steps(steps),
        "rows": [],
    }
    if slug == "attention":
        record.update(
            keys=KEYS,
            values=VALUES,
            names=NAMES,
            colors=COLORS,
            paper="https://arxiv.org/abs/1706.03762v7",
            query_norm=4.0,
        )
        for k in range(steps + 1):
            query = [4 * math.cos(math.radians(k)), 4 * math.sin(math.radians(k))]
            record["rows"].append({"k": k, "query": query, **attention(query, KEYS, VALUES)})
    else:
        mask = pattern()
        pixels = [[0.25 + 0.5 * v for v in row] for row in mask]
        target = [[0.05 + 0.9 * v for v in row] for row in mask]
        record.update(
            input=pixels, target=target, row_index=16, paper="https://arxiv.org/abs/1512.03385v1"
        )
        for k in range(steps + 1):
            pairs = [[residual_block(x, k / steps) for x in row] for row in pixels]
            delta = [[p[0] for p in row] for row in pairs]
            output = [[p[1] for p in row] for row in pairs]
            error = math.sqrt(
                math.fsum((y - z) ** 2 for ys, zs in zip(output, target) for y, z in zip(ys, zs))
                / 1024
            )
            record["rows"].append(
                {"k": k, "strength": k / steps, "delta": delta, "output": output, "rmse": error}
            )
    return record
