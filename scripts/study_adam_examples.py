"""Cloud-only example selection; no film, website build, or performance theorem."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np

STEPS = 1200
DISTANCE_TARGET = 0.01
LOSS_TARGET = 0.0001
METHODS = ("gd", "momentum", "adam")


def evaluate(points, case):
    """Return authored objective and its analytic gradient, in optimizer coordinates."""
    angle = math.radians(case.get("angle", 0))
    c, s = math.cos(angle), math.sin(angle)
    x = c * points[..., 0] + s * points[..., 1]
    y = -s * points[..., 0] + c * points[..., 1]
    scale = case["scale"]
    if case["family"] == "quartic":
        loss = x**2 / 2 + x**4 / 4 + scale * (y**2 / 2 + y**4 / 4)
        gx, gy = x + x**3, scale * (y + y**3)
    elif case["family"] == "curved":
        bend = case["bend"]
        residual = y - bend * x**2
        loss = x**2 / 2 + x**4 / 4 + scale * residual**2 / 2
        gx, gy = x + x**3 - 2 * scale * bend * x * residual, scale * residual
    elif case["family"] == "rosenbrock":
        residual = y - x**2
        loss = (1 - x)**2 + scale * residual**2
        gx, gy = 2 * (x - 1) - 4 * scale * x * residual, 2 * scale * residual
    else:
        raise ValueError("unknown family")
    return loss, np.stack((c * gx - s * gy, s * gx + c * gy), axis=-1)


def rotate(point, angle):
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    x, y = point
    return [c*x-s*y, s*x+c*y]


def cases():
    result = []
    for scale in (1, 100, 10000):
        for angle in (0, 15, 45):
            result.append(dict(id=f"quartic-{scale}-{angle}", family="quartic",
                               scale=scale, angle=angle, start=rotate([-3, 2], angle),
                               target=[0, 0], rate_scale=1 / (28 * scale)))
    for scale in (100, 10000):
        for bend in (0.01, 0.1, 0.3):
            result.append(dict(id=f"curved-{scale}-{bend}", family="curved",
                               scale=scale, bend=bend, start=[-3, 2], target=[0, 0],
                               rate_scale=1 / (28 + scale * (1 + 36*bend**2))))
    for angle in (0, 30):
        result.append(dict(id=f"rosenbrock-{angle}", family="rosenbrock",
                           scale=100, angle=angle, start=rotate([-1.2, 1], angle),
                           target=rotate([1, 1], angle), rate_scale=0.001))
    for scale, angle in ((1000, 0), (100000, 0), (10000, 0.5), (10000, 1),
                         (10000, 2), (10000, 5)):
        result.append(dict(id=f"quartic-{scale}-{angle}", family="quartic",
                           scale=scale, angle=angle, start=rotate([-3, 2], angle),
                           target=[0, 0], rate_scale=1 / (28 * scale)))
    for start in ([-2.4, 1.6], [-3.6, 2.4], [-3, 1], [-2, 3]):
        result.append(dict(id=f"quartic-start-{start[0]}-{start[1]}", family="quartic",
                           scale=10000, angle=0, start=start, target=[0, 0],
                           rate_scale=1 / 280000))
    return result


def settings(case, method):
    if method == "adam":
        rates = sorted(set(np.geomspace(0.001, 1, 37)) | set(np.geomspace(0.001, 4, 65))
                       | {0.2, 0.25, 0.3})
        return [dict(alpha=float(a), beta=0.9) for a in rates]
    betas = (0,) if method == "gd" else (
        0, 0.5, 0.8, 0.9, 0.95, 0.975, 0.98, 0.985, 0.99, 0.9925,
        0.995, 0.9975, 0.999, 0.9995, 0.9999)
    rates = sorted(set(np.geomspace(0.0001, 8, 61)) | set(np.geomspace(0.0001, 64, 101)))
    return [dict(alpha=float(a * case["rate_scale"]), beta=b)
            for b in betas for a in rates]


def trajectories(case, method, configs, steps=STEPS):
    """Vectorized candidates; preserve divergence as missing observations, not zero."""
    x = np.tile(case["start"], (len(configs), 1)).astype(float)
    alpha = np.array([p["alpha"] for p in configs])[:, None]
    beta = np.array([p["beta"] for p in configs])[:, None]
    first, second = np.zeros_like(x), np.zeros_like(x)
    paths = np.full((steps + 1, len(configs), 2), np.nan)
    paths[0] = x
    alive = np.ones(len(configs), dtype=bool)
    with np.errstate(over="ignore", invalid="ignore"):
        for k in range(1, steps + 1):
            _, gradient = evaluate(x, case)
            if method == "gd":
                delta = alpha * gradient
            elif method == "momentum":
                first = beta * first + gradient
                delta = alpha * first
            elif method == "adam":
                first = 0.9 * first + 0.1 * gradient
                second = 0.999 * second + 0.001 * gradient**2
                delta = alpha * (first / (1 - 0.9**k)) / (
                    np.sqrt(second / (1 - 0.999**k)) + 1e-8)
            else:
                raise ValueError("unknown method")
            x = x - delta
            alive &= np.all(np.isfinite(x), axis=1) & (np.max(np.abs(x), axis=1) < 1e10)
            x[~alive] = np.nan
            paths[k] = x
        losses, _ = evaluate(paths, case)
    distances = np.linalg.norm(paths - case["target"], axis=-1)
    return paths, losses, distances


def summarize(paths, losses, distances, configs):
    records = []
    for i, config in enumerate(configs):
        p, f, d = paths[:, i], losses[:, i], distances[:, i]
        finite = bool(np.all(np.isfinite(f)) and np.all(np.isfinite(d)))
        valid = (f / f[0] <= LOSS_TARGET) & (d / d[0] <= DISTANCE_TARGET)
        # Must remain inside BOTH tolerances until the full budget ends.
        bad = np.flatnonzero(~valid)
        settled = int(bad[-1] + 1) if finite and valid[-1] else None
        record = dict(settings=config, finite=finite, settled=settled,
                      final_relative_loss=float(f[-1] / f[0]) if finite else None,
                      final_relative_distance=float(d[-1] / d[0]) if finite else None)
        if finite:
            delta = np.diff(p, axis=0)
            early = delta[:101]
            record["early_direction_reversals"] = int(np.sum(
                np.sum(early[1:] * early[:-1], axis=1) < 0))
            record["path_length"] = float(np.linalg.norm(delta, axis=1).sum())
        records.append(record)
    return records


def rank(record):
    return (record["settled"] if record["settled"] is not None else STEPS + 1,
            record["final_relative_distance"] if record["finite"] else math.inf,
            record["final_relative_loss"] if record["finite"] else math.inf)


def study(output, source):
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for case in cases():
        result = dict(case=case, methods={})
        for method in METHODS:
            configs = settings(case, method)
            paths, losses, distances = trajectories(case, method, configs)
            records = summarize(paths, losses, distances, configs)
            best = min(range(len(records)), key=lambda i: rank(records[i]))
            result["methods"][method] = dict(
                candidates=records, selected=best,
                path=paths[:, best].tolist() if records[best]["finite"] else None,
                loss=losses[:, best].tolist() if records[best]["finite"] else None,
                distance=distances[:, best].tolist() if records[best]["finite"] else None)
        results.append(result)
        print(json.dumps({"case": case["id"], "best": {
            method: data["candidates"][data["selected"]]
            for method, data in result["methods"].items()}}, allow_nan=False), flush=True)
    report = dict(source=source, steps=STEPS, relative_distance_target=DISTANCE_TARGET,
                  relative_loss_target=LOSS_TARGET, cases=results)
    (output / "study.json").write_text(json.dumps(report, allow_nan=False), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()
    study(args.output, args.source)
