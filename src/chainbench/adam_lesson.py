"""An authored visual experiment for Kingma--Ba Algorithm 1, not paper data."""

from __future__ import annotations

import math

STEPS = 2400
ANGLE = math.radians(30)
START = (-1.2, 1.0)
METHODS = {
    "gd": {"label": "Gradient descent", "alpha": 0.001, "color": "#739ad4"},
    "momentum": {"label": "Momentum", "alpha": 0.001, "beta": 0.9, "color": "#dfaa58"},
    "adam": {
        "label": "Adam",
        "alpha": 0.02,
        "beta1": 0.9,
        "beta2": 0.999,
        "epsilon": 1e-8,
        "color": "#eb7c68",
    },
}


def rotate(point, angle=ANGLE):
    c, s = math.cos(angle), math.sin(angle)
    x, y = point
    return [c * x - s * y, s * x + c * y]


def objective(point):
    x, y = rotate(point, -ANGLE)
    return (1 - x) ** 2 + 100 * (y - x * x) ** 2


def gradient(point):
    x, y = rotate(point, -ANGLE)
    return rotate([2 * (x - 1) - 400 * x * (y - x * x), 200 * (y - x * x)])


def trajectory(method, *, steps=STEPS, alpha=None):
    if method not in METHODS or not isinstance(steps, int) or not 0 <= steps <= 10000:
        raise ValueError("Unknown method or invalid iteration budget")
    config = dict(METHODS[method])
    if alpha is not None:
        if not math.isfinite(alpha) or alpha <= 0:
            raise ValueError("alpha must be positive and finite")
        config["alpha"] = alpha
    x, target = rotate(START), rotate([1.0, 1.0])
    m, v = [0.0, 0.0], [0.0, 0.0]
    rows = [
        {
            "k": 0,
            "point": x[:],
            "loss": objective(x),
            "distance": math.dist(x, target),
            "step": [0.0, 0.0],
        }
    ]
    for k in range(1, steps + 1):
        g = gradient(x)
        if method == "gd":
            delta = [-config["alpha"] * q for q in g]
        elif method == "momentum":
            m = [config["beta"] * a + b for a, b in zip(m, g)]
            delta = [-config["alpha"] * a for a in m]
        else:
            b1, b2 = config["beta1"], config["beta2"]
            m = [b1 * a + (1 - b1) * b for a, b in zip(m, g)]
            v = [b2 * a + (1 - b2) * b * b for a, b in zip(v, g)]
            delta = [
                -config["alpha"]
                * (a / (1 - b1**k))
                / (math.sqrt(b / (1 - b2**k)) + config["epsilon"])
                for a, b in zip(m, v)
            ]
        next_x = [a + b for a, b in zip(x, delta)]
        if not all(math.isfinite(a) for a in next_x) or max(map(abs, next_x)) > 1e10:
            raise ValueError("Diverged trajectory; never replace with a successful trace")
        x = next_x
        loss, distance = objective(x), math.dist(x, target)
        if not math.isfinite(loss):
            raise ValueError("Non-finite objective")
        rows.append({"k": k, "point": x[:], "loss": loss, "distance": distance, "step": delta})
    return {"settings": config, "rows": rows}


def iteration_at(seconds):
    """Video clock: introduction, slow early steps, later steps, final hold."""
    if seconds <= 6:
        return 0
    if seconds <= 16:
        return min(60, int((seconds - 6) * 6))
    if seconds < 40:
        return min(STEPS, 60 + int((seconds - 16) * (STEPS - 60) / 24))
    return STEPS


def time_at(k):
    k = min(STEPS, max(0, int(k)))
    return 6 + k / 6 if k <= 60 else 16 + (k - 60) * 24 / (STEPS - 60)


def experiment(source):
    return {
        "kind": "chainbench.adam-film",
        "source": source,
        "steps": STEPS,
        "duration": 48,
        "fps": 24,
        "rotation_degrees": 30,
        "function": "(1-u)^2 + 100(v-u^2)^2; [x,y] = R(30deg)[u,v]",
        "start": rotate(START),
        "target": rotate([1.0, 1.0]),
        "minimum": 0.0,
        "source_paper": "https://arxiv.org/abs/1412.6980v9",
        "traces": {name: trajectory(name) for name in METHODS},
    }
