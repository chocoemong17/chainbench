"""Independent block-basis/reference-recurrence validation of noisy-image exports.

Uses the declared NumPy runtime, but never imports ChainBench implementation code.
"""

from __future__ import annotations

import hashlib

import numpy as np


def analysis(image):
    n = len(image)
    out = np.empty_like(image)
    for width in (2, 4, 8):
        side = n // width
        blocks = image.reshape(side, width, side, width)
        signs = np.r_[np.ones(width // 2), -np.ones(width // 2)]
        out[:side, side : 2 * side] = (blocks * signs[None, None, None, :]).sum(axis=(1, 3)) / width
        out[side : 2 * side, :side] = (blocks * signs[None, :, None, None]).sum(axis=(1, 3)) / width
        out[side : 2 * side, side : 2 * side] = (
            blocks * signs[None, :, None, None] * signs[None, None, None, :]
        ).sum(axis=(1, 3)) / width
    out[: n // 8, : n // 8] = image.reshape(n // 8, 8, n // 8, 8).sum(axis=(1, 3)) / 8
    return out


def synthesis(coeff):
    n = len(coeff)
    out = np.repeat(np.repeat(coeff[: n // 8, : n // 8] / 8, 8, 0), 8, 1)
    for width in (2, 4, 8):
        side = n // width
        signs = np.tile(np.r_[np.ones(width // 2), -np.ones(width // 2)], side)
        for values, pattern in [
            (coeff[:side, side : 2 * side], signs[None, :]),
            (coeff[side : 2 * side, :side], signs[:, None]),
            (coeff[side : 2 * side, side : 2 * side], signs[:, None] * signs[None, :]),
        ]:
            out += np.repeat(np.repeat(values / width, width, 0), width, 1) * pattern
    return out


def reflected_blur(image, kernel):
    n = len(image)
    indices = np.arange(n)
    temp, out = np.zeros_like(image), np.zeros_like(image)
    for j, weight in enumerate(kernel):
        idx = indices + j - 4
        idx = np.where(idx < 0, -idx - 1, np.where(idx >= n, 2 * n - 1 - idx, idx))
        temp += weight * image[:, idx]
    for j, weight in enumerate(kernel):
        idx = indices + j - 4
        idx = np.where(idx < 0, -idx - 1, np.where(idx >= n, 2 * n - 1 - idx, idx))
        out += weight * temp[idx, :]
    return out


def validate_wavelet(result, *, require_duality=False):
    def require(condition, message):
        if not condition:
            raise RuntimeError("wavelet evidence: " + message)

    def close(a, b, *, atol=2e-11):
        a, b = np.asarray(a), np.asarray(b)
        require(
            a.shape == b.shape
            and np.isfinite(a).all()
            and np.isfinite(b).all()
            and np.allclose(a, b, rtol=2e-9, atol=atol),
            "numerical observation differs; max absolute difference=" + str(np.max(np.abs(a - b))),
        )

    def digest(a):
        return hashlib.sha256(np.asarray(a, dtype="<f8").tobytes()).hexdigest()

    require(
        result["kind"] == "chainbench.wavelet-deblurring" and result["schema_version"] == 1,
        "schema differs",
    )
    par, problem = result["parameters"], result["problem"]
    steps, seed = par["steps"], par["seed"]
    require(
        type(steps) is int and 1 <= steps <= 200 and type(seed) is int and 0 <= seed < 2**32,
        "invalid protocol",
    )
    require(
        par["L"] == 2
        and par["lam"] == 1e-4
        and par["threshold"] == 5e-5
        and par["step_size"] == 0.5
        and par["noise_std"] == 0.001
        and par["haar_levels"] == 3
        and par["paper_budget"] == 200
        and par["full_paper_budget"] == (steps == 200),
        "parameters differ",
    )
    require(
        problem["f_star"] is None
        and problem["shape"] == [256, 256]
        and problem["dimension"] == 65536,
        "problem differs",
    )
    require(
        result["evidence_level"] == "published-protocol-rerun-with-declared-noise", "scope differs"
    )
    require("Copyright" in result["source"]["image_permission_notice"], "permission notice absent")
    expected_snapshots = sorted({0, 1, steps} | {k for k in (10, 100, 200) if k <= steps})
    has_duality = "duality" in result
    require(has_duality or not require_duality, "current export lacks duality")
    if has_duality:
        require(
            result["duality"]["safety_factor"] == 1 - 1e-12
            and result["duality"]["doi"] == "10.1109/JSTSP.2007.910971",
            "dual scaling/source differs",
        )
    require(
        par["snapshot_iterations"] == expected_snapshots
        and set(result["runs"]) == {"ista", "fista"},
        "snapshot or method selection differs",
    )
    truth, observed, noise = (
        np.asarray(problem[k]) for k in ("clean_image", "observed_image", "noise")
    )
    kernel = np.exp(-(np.arange(-4, 5, dtype=float) ** 2) / 32)
    kernel /= kernel.sum()
    for name, value in [
        ("clean", truth),
        ("observed", observed),
        ("noise", noise),
        ("kernel", np.asarray(problem["kernel_1d"])),
    ]:
        require(
            value.shape == ((9,) if name == "kernel" else (256, 256)) and np.isfinite(value).all(),
            "input shape/finite differs",
        )
        require(result["input_hashes"][name] == digest(value), "input hash differs")
    close(kernel, problem["kernel_1d"])
    close(noise, np.random.Generator(np.random.PCG64(seed)).normal(0, 0.001, (256, 256)))
    close(observed, reflected_blur(truth, kernel) + noise)

    def gradient(c):
        return 2 * analysis(reflected_blur(reflected_blur(synthesis(c), kernel) - observed, kernel))

    def soft(c):
        return np.sign(c) * np.maximum(np.abs(c) - 0.00005, 0)

    c0 = analysis(observed)
    z0 = c0 - gradient(c0) / 2
    selected = [
        int(np.argmin(np.abs(z0))),
        int(np.argmax(np.abs(z0))),
        int(np.argmin(np.abs(np.abs(z0) - 0.00005))),
    ]
    require([r["index"] for r in result["first_step"]] == selected, "coefficient selection differs")
    for item in result["first_step"]:
        i = item["index"]
        for key, value in [
            ("coefficient", c0),
            ("gradient", gradient(c0)),
            ("before_threshold", z0),
            ("after_threshold", soft(z0)),
        ]:
            close(item[key], value.ravel()[i])
    for method, run in result["runs"].items():
        require(
            len(run["rows"]) == steps + 1
            and run["updates"] == steps
            and run["termination"] == "fixed_budget",
            "trace incomplete",
        )
        require(
            [s["iteration"] for s in run["snapshots"]] == expected_snapshots, "snapshots incomplete"
        )
        saved = {s["iteration"]: s for s in run["snapshots"]}
        c, y, t = c0.copy(), c0.copy(), 1.0
        for k, row in enumerate(run["rows"]):
            require(row["iteration"] == k, "row index differs")
            image = synthesis(c)
            fit = np.sum((reflected_blur(image, kernel) - observed) ** 2)
            penalty = 0.0001 * np.sum(np.abs(c))
            for key, value in [
                ("objective", fit + penalty),
                ("squared_residual", fit),
                ("penalty", penalty),
                ("image_rmse", np.sqrt(np.mean((image - truth) ** 2))),
            ]:
                close(row[key], value)
            require(row["zero_coefficients"] == np.count_nonzero(c == 0), "zero count differs")
            if k in saved:
                s = saved[k]
                close(s["image"], image, atol=1e-9)
                try:
                    # The block-basis reference changes floating summation order.
                    # After 200 accelerated steps, near-zero coefficients differ
                    # by up to 4.9e-10 over declared seeds 0, 1, 2. This floor is
                    # 50,000 times smaller than the actual shrinkage threshold.
                    close(s["coefficients"], c, atol=1e-9)
                except RuntimeError as exc:
                    raise RuntimeError(f"{method} k={k} coefficients: {exc}") from exc
                require(
                    s["image_sha256"] == digest(s["image"])
                    and s["coefficients_sha256"] == digest(s["coefficients"]),
                    "snapshot hash differs",
                )
                close(s["image_range"], [np.min(image), np.max(image)])
                close(
                    s["proximal_gradient_norm"], np.linalg.norm(2 * (c - soft(c - gradient(c) / 2)))
                )
                require(("dual_bound" in s) == has_duality, "incomplete duality record")
                if has_duality:
                    # Use the saved actual point, avoiding accumulated reference
                    # iteration roundoff in this separate diagnostic.
                    actual_c, actual_image = np.asarray(s["coefficients"]), np.asarray(s["image"])
                    r = reflected_blur(actual_image, kernel) - observed
                    raw_norm = np.max(np.abs(2 * analysis(reflected_blur(r, kernel))))
                    scale = (1 - 1e-12) * (min(1, 1e-4 / raw_norm) if raw_norm else 1)
                    nu = 2 * r * scale
                    adjoint = analysis(reflected_blur(nu, kernel))
                    feasible_norm = np.max(np.abs(adjoint))
                    require(feasible_norm <= 1e-4, "independent dual candidate infeasible")
                    d = s["dual_bound"]
                    require(d["dual_adjoint_inf"] <= 1e-4, "reported dual infeasible")
                    require(d["suboptimality_upper_bound"] >= 0, "negative dual gap")
                    quadratic, linear = np.sum(nu * nu) / 4, np.sum(observed * nu)
                    primal = np.sum(r * r) + 1e-4 * np.sum(np.abs(actual_c))
                    lower = -quadratic - linear
                    square = np.sum((r - nu / 2) ** 2)
                    slack = 1e-4 * np.sum(np.abs(actual_c)) + np.sum(adjoint * actual_c)
                    for key, value in dict(
                        raw_adjoint_inf=raw_norm,
                        scale=scale,
                        dual_adjoint_inf=feasible_norm,
                        feasibility_margin=1e-4 - feasible_norm,
                        dual_quadratic=quadratic,
                        dual_linear=linear,
                        lower_bound=lower,
                        primal_objective=primal,
                        suboptimality_upper_bound=primal - lower,
                        square_slack=square,
                        l1_slack=slack,
                        identity_residual=primal - lower - square - slack,
                    ).items():
                        close(
                            d[key],
                            value,
                            atol=2e-13
                            if key in ("dual_adjoint_inf", "feasibility_margin")
                            else 2e-11,
                        )
                    close(d["primal_objective"], row["objective"])
            if k < steps:
                point = y if method == "fista" else c
                nxt = soft(point - gradient(point) / 2)
                tn = (1 + np.sqrt(1 + 4 * t * t)) / 2
                y = nxt + (t - 1) / tn * (nxt - c)
                c, t = nxt, tn
