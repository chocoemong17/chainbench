"""Standard-library verification of installed deblurring data, independent of NumPy."""

from __future__ import annotations

import hashlib
import math
import struct


def validate_deblurring(result):
    if result.get("kind") != "chainbench.fista-deblurring":
        raise RuntimeError("missing deblurring protocol record")
    p, options = result["problem"], result["parameters"]
    steps = options["steps"]
    if (
        p["shape"] != [64, 64]
        or p["dimension"] != 4096
        or p["L"] != 2
        or p["f_star"] != 0
        or options["lambda"] != 0
        or options["noise_std"] != 0
        or options["seed"] is not None
        or options["step_size"] != 0.5
        or not 1 <= steps <= 10000
        or options["full_paper_budget"] != (steps == 10000)
    ):
        raise RuntimeError("deblurring source conditions differ")
    notice = result["source"].get("image_permission_notice", "")
    if "Permission  to use, copy, modify" not in notice or "Per Christian Hansen" not in notice:
        raise RuntimeError("image-generator attribution or permission notice missing")

    def close(a, b):
        if (
            not math.isfinite(a)
            or not math.isfinite(b)
            or not math.isclose(a, b, rel_tol=2e-10, abs_tol=1e-13)
        ):
            raise RuntimeError("deblurring sample disagrees with independent operator")

    def fingerprint(image):
        if len(image) != 64 or any(len(row) != 64 for row in image):
            raise RuntimeError("incorrect image shape")
        flat = [x for row in image for x in row]
        if any(not math.isfinite(x) for x in flat):
            raise RuntimeError("non-finite image data")
        return hashlib.sha256(struct.pack("<4096d", *flat)).hexdigest()

    for key, prefix in [
        ("clean_image", "clean"),
        ("observed_image", "observed"),
        ("blur_matrix_1d", "matrix"),
    ]:
        if fingerprint(p[key]) != p[prefix + "_sha256"]:
            raise RuntimeError("deblurring input fingerprint differs")
    truth, b = p["clean_image"], p["observed_image"]
    if p["clean_sha256"] != "1f8f4514e4179f4ea31023abc1291d3f0bb15cbfae40f7d0a7d0df94d3587694":
        raise RuntimeError("declared source image differs")
    weights = [math.exp(-i * i / 32) for i in range(-4, 5)]
    total = sum(weights)
    weights = [x / total for x in weights]
    for a, v in zip(p["kernel_1d"], weights):
        close(a, v)

    def mirror(i):
        return -i - 1 if i < 0 else 127 - i if i >= 64 else i

    for i, row in enumerate(p["blur_matrix_1d"]):
        expected = [0.0] * 64
        for d, w in zip(range(-4, 5), weights):
            expected[mirror(i + d)] += w
        for a, v in zip(row, expected):
            close(a, v)

    def blur(image):
        first = [
            [sum(weights[d + 4] * image[mirror(i + d)][j] for d in range(-4, 5)) for j in range(64)]
            for i in range(64)
        ]
        return [
            [sum(weights[d + 4] * first[i][mirror(j + d)] for d in range(-4, 5)) for j in range(64)]
            for i in range(64)
        ]

    for a, row in zip(blur(truth), b):
        for x, y in zip(a, row):
            close(x, y)
    start_residual = [[x - y for x, y in zip(row, obs)] for row, obs in zip(blur(b), b)]
    correction = blur(start_residual)
    first = [[x - y for x, y in zip(row, corr)] for row, corr in zip(b, correction)]
    expected_points = sorted(
        {0, 1, steps} | {k for k in (10, 100, 200, 1000, 5000, 10000) if k <= steps}
    )
    if options["snapshot_iterations"] != expected_points or set(result["runs"]) != {
        "ista",
        "fista",
    }:
        raise RuntimeError("deblurring run design differs")
    for run in result["runs"].values():
        rows = run["rows"]
        if (
            len(rows) != steps + 1
            or [r["iteration"] for r in rows] != list(range(steps + 1))
            or run["updates"] != steps
            or run["termination"] != "fixed_budget"
            or [s["iteration"] for s in run["snapshots"]] != expected_points
        ):
            raise RuntimeError("deblurring trajectory incomplete")
        for row in rows:
            if any(
                not math.isfinite(row[key]) or row[key] < 0 for key in ("objective", "image_rmse")
            ):
                raise RuntimeError("invalid deblurring metric")
        for snap in run["snapshots"]:
            u = snap["image"]
            if fingerprint(u) != snap["sha256"]:
                raise RuntimeError("snapshot fingerprint differs")
            row = rows[snap["iteration"]]
            residual = blur(u)
            close(
                row["objective"],
                sum((x - y) ** 2 for a, o in zip(residual, b) for x, y in zip(a, o)),
            )
            close(
                row["image_rmse"],
                math.sqrt(sum((x - y) ** 2 for a, t in zip(u, truth) for x, y in zip(a, t)) / 4096),
            )
            close(snap["range"][0], min(min(a) for a in u))
            close(snap["range"][1], max(max(a) for a in u))
            expected = b if snap["iteration"] == 0 else first if snap["iteration"] == 1 else None
            if expected is not None:
                for a, c in zip(u, expected):
                    for x, y in zip(a, c):
                        close(x, y)
