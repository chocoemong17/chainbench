"""An authored visual experiment for Kingma--Ba Algorithm 1, not paper data."""

from __future__ import annotations

import math

STEPS = 1200
START = (-3.0, 2.0)
TARGET = (0.0, 0.0)
SCALE = 10000
TIMING = ((0, 0), (4, 0), (22, 60), (24, 66), (27, 66), (31, 100), (42, 1200), (48, 1200))
METHODS = {
    "gd": {"label": "Gradient descent", "alpha": 3.9810717055349695e-5, "color": "#739ad4"},
    "momentum": {
        "label": "Momentum", "alpha": 2.2067340690845897e-5,
        "beta": 0.985935, "color": "#dfaa58",
    },
    "adam": {
        "label": "Adam",
        "alpha": 0.14,
        "beta1": 0.9,
        "beta2": 0.999,
        "epsilon": 1e-8,
        "color": "#eb7c68",
    },
}


def objective(point):
    x, y = point
    return x*x / 2 + x**4 / 4 + SCALE * (y*y / 2 + y**4 / 4)


def gradient(point):
    x, y = point
    return [x + x**3, SCALE * (y + y**3)]


def trajectory(method, *, steps=STEPS, alpha=None):
    if method not in METHODS or not isinstance(steps, int) or not 0 <= steps <= 10000:
        raise ValueError("Unknown method or invalid iteration budget")
    config = dict(METHODS[method])
    if alpha is not None:
        if not math.isfinite(alpha) or alpha <= 0:
            raise ValueError("alpha must be positive and finite")
        config["alpha"] = alpha
    x, target = list(START), TARGET
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
    """Slow early updates and a hold at Adam's observed target-entry step."""
    for (t0, k0), (t1, k1) in zip(TIMING, TIMING[1:]):
        if seconds <= t1:
            return max(k0, min(k1, k0 + int((seconds - t0) * (k1 - k0) / (t1 - t0) + 1e-8)))
    return STEPS


def time_at(k):
    k = min(STEPS, max(0, int(k)))
    for (t0, k0), (t1, k1) in zip(TIMING, TIMING[1:]):
        if k1 > k0 and k <= k1:
            return t0 + (k - k0) * (t1 - t0) / (k1 - k0)
    return 42.0


def settled_step(rows):
    """First point after which BOTH targets hold through the recorded budget."""
    f0, d0 = rows[0]["loss"], rows[0]["distance"]
    valid = [r["loss"] / f0 <= 1e-4 and r["distance"] / d0 <= 0.01 for r in rows]
    return 1 + max(i for i, okay in enumerate(valid) if not okay) if valid[-1] else None


def experiment(source):
    traces = {name: trajectory(name) for name in METHODS}
    return {
        "kind": "chainbench.adam-film",
        "source": source,
        "steps": STEPS,
        "duration": 48,
        "fps": 24,
        "fixture": "unequal-scale-quartic-v1",
        "function": "phi(x) + 10000*phi(y); phi(z) = z^2/2 + z^4/4",
        "start": list(START),
        "target": list(TARGET),
        "minimum": 0.0,
        "source_paper": "https://arxiv.org/abs/1412.6980v9",
        "traces": traces,
        "timing": TIMING,
        "target_test": {"relative_loss": 1e-4, "relative_distance": 0.01,
                        "maintained_through": STEPS,
                        "settled": {m: settled_step(t["rows"]) for m, t in traces.items()}},
    }
