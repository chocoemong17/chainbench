"""Approved teaching fixtures; authored inputs, not trained-model benchmarks."""

from __future__ import annotations

import math
import re

DURATION, FPS = 48, 24
NAMES = ("Ava", "Ben", "Mia")
PLACES = {"en": ("Library", "Garden", "Studio"), "ko": ("도서관", "정원", "작업실")}
KEYS = tuple(tuple(float(i == j) for j in range(3)) for i in range(3))
VALUES = KEYS
GRID = (
    "000000000",
    "000010000",
    "000111000",
    "001000100",
    "011111110",
    "010000010",
    "010010010",
    "010000010",
    "011111110",
)
INPUT = [[float(v) for v in row] for row in GRID]
DELTA = [[0.0] * 9 for _ in range(9)]
DELTA[6][4] = -1.0
DELTA[5][3] = DELTA[5][5] = 1.0


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


def query_case(selected=2, focus=4.0):
    """Assigned basis keys/values; focus is the selected scaled match score."""
    if selected not in (0, 1, 2) or not math.isfinite(focus) or not 0 <= focus <= 4:
        raise ValueError("Known name and focus in [0,4] required")
    query = [math.sqrt(3) * focus * (i == selected) for i in range(3)]
    return {"query": query, **attention(query, KEYS, VALUES)}


def residual_example(x=2.0, w2=-0.1, b2=0.3, target=2.2):
    """F=w2 ReLU(x)+b2, then ReLU(x+F). Derivatives away from kinks."""
    if not all(math.isfinite(v) for v in (x, w2, b2, target)):
        raise ValueError("Finite inputs required")
    hidden = max(0.0, x)
    delta = w2 * hidden + b2
    pre = x + delta
    y = max(0.0, pre)
    incoming = (y - target) * (pre > 0)
    slope = w2 * (x > 0)
    return dict(
        x=x,
        correction=delta,
        y=y,
        target=target,
        loss=0.5 * (y - target) ** 2,
        incoming=incoming,
        shortcut=incoming,
        branch=incoming * slope,
        dx=incoming * (1 + slope),
        dw2=incoming * hidden,
    )


def depth_case(depth, shortcut, slope=-0.1):
    """Chosen scalar maps at x=1, active ReLUs; distinct full mappings.

    Plain ReLU(slope*x+1-slope), residual ReLU(x+slope*x-slope).
    Terminal loss .5*y**2 has derivative1 at the shared forward point y=1.
    Returns SIGNED gradients. Displays explicitly show magnitudes.
    """
    if not isinstance(depth, int) or not 0 <= depth <= 16 or not math.isfinite(slope):
        raise ValueError("Depth in [0,16] and finite slope required")
    factor = slope + int(shortcut)
    return [factor**n for n in range(depth + 1)]


def grid_case(alpha):
    if not math.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError("Correction strength in [0,1] required")
    correction = [[alpha * d for d in row] for row in DELTA]
    output = [[max(0.0, x + d) for x, d in zip(xs, ds)] for xs, ds in zip(INPUT, correction)]
    return dict(correction=correction, output=output)


def smooth(t):
    u = max(0.0, min(1.0, t))
    return u * u * (3 - 2 * u)


def film_state(slug, frame):
    """Four twelve-second chapters with reading holds and continuous motion."""
    if (
        slug not in ("attention", "resnet")
        or not isinstance(frame, int)
        or not 0 <= frame < DURATION * FPS
    ):
        raise ValueError("Known film and valid frame required")
    scene, local = divmod(frame / FPS, 12)
    state = dict(scene=int(scene), local=local, phase=(local / 3) % 1)
    if slug == "attention":
        # The third scene moves the query continuously from Mia to Ava.
        blend = smooth((local - 3) / 4) if scene == 2 else 0
        focus = 4 * smooth((local - 1) / 5) if scene == 1 else 4
        query = [math.sqrt(3) * focus * blend, 0.0, math.sqrt(3) * focus * (1 - blend)]
        state.update(query=query, blend=blend, focus=focus, **attention(query, KEYS, VALUES))
    else:
        alpha = smooth((local - 2) / 5)
        depth = min(8, max(0, int((local - 1) * 8 / 7)))
        state.update(alpha=alpha, depth=depth, **grid_case(alpha))
    return state


def experiment(slug, source):
    if slug not in ("attention", "resnet") or not re.fullmatch("[a-f0-9]{40}", source):
        raise ValueError("Known lesson and full source commit required")
    record = dict(
        kind="chainbench.visual-paper.v2",
        slug=slug,
        source=source,
        duration=DURATION,
        fps=FPS,
        chapters=[0, 12, 24, 36],
    )
    if slug == "attention":
        record.update(
            keys=KEYS,
            values=VALUES,
            names=NAMES,
            places=PLACES,
            cases=[[query_case(i, k / 25) for k in range(101)] for i in range(3)],
            paper="https://arxiv.org/abs/1706.03762v7",
        )
    else:
        record.update(
            input=INPUT,
            delta=DELTA,
            block=residual_example(),
            grids=[grid_case(k / 100) for k in range(101)],
            blocks=[residual_example(w2=-0.1 * k / 100, b2=0.3 * k / 100) for k in range(101)],
            plain=depth_case(16, False),
            residual=depth_case(16, True),
            paper="https://arxiv.org/abs/1512.03385v1",
        )
    return record
