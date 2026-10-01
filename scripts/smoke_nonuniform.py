"""Independent real/imaginary recurrence for the nonuniform sampling export."""

from __future__ import annotations

import hashlib

import numpy as np


def validate_nonuniform(result, *, require_projection=False):
    def require(condition, message):
        if not condition:
            raise RuntimeError("nonuniform sampling: " + message)

    def close(actual, expected, atol=2e-12):
        a, b = np.asarray(actual), np.asarray(expected)
        require(
            a.shape == b.shape
            and np.isfinite(a).all()
            and np.isfinite(b).all()
            and np.allclose(a, b, rtol=2e-9, atol=atol),
            "numeric evidence differs",
        )

    def complex_array(record, shape):
        real, imag = np.asarray(record["real"]), np.asarray(record["imag"])
        require(
            real.shape == imag.shape == shape
            and np.isfinite(real).all()
            and np.isfinite(imag).all(),
            "invalid complex record",
        )
        value = np.empty(shape, dtype=complex)
        value.real, value.imag = real, imag
        return value

    def digest(array):
        kind = "<c16" if np.iscomplexobj(array) else "<f8"
        return hashlib.sha256(np.asarray(array, dtype=kind).tobytes()).hexdigest()

    require(
        result["kind"] == "chainbench.nonuniform-sampling" and result["schema_version"] == 1,
        "schema differs",
    )
    extension = result.get("projection_geometry")
    require(not require_projection or extension is not None, "projection explanation missing")
    if extension is not None:
        require(
            extension.get("kind") == "chainbench.fourier-projection-response"
            and extension.get("schema_version") == 1,
            "projection explanation schema differs",
        )
    par = result["parameters"]
    steps = par["steps"]
    require(type(steps) is int and 1 <= steps <= 15000, "invalid budget")
    require(
        par["bandlimit"] == 50
        and par["sample_count"] == 700
        and par["dimension"] == 101
        and par["paper_plot_budget"] == 15000
        and par["full_paper_plot_budget"] == (steps == 15000)
        and par["seeds"] == [0, 1, 2],
        "protocol differs",
    )
    expected_snapshots = sorted(
        {0, 1, steps} | {k for k in (10, 100, 1000, 5000, 10000, 15000) if k <= steps}
    )
    require(par["snapshot_iterations"] == expected_snapshots, "snapshot selection differs")
    require([c["seed"] for c in result["cases"]] == [0, 1, 2], "case omitted or reordered")
    grid = np.linspace(0, 1, 513)
    close(result["display_grid"], grid, atol=0)
    f = np.arange(-50, 51)
    grid_phase = (2 * np.pi * grid[:, None]) * f
    gr, gi = np.cos(grid_phase), np.sin(grid_phase)
    for case in result["cases"]:
        seed = case["seed"]
        require(case["id"] == f"seed-{seed}", "case identity differs")
        t, w, u = (np.asarray(case[key]) for key in ("nodes", "weights", "sampling_uniforms"))
        require(t.shape == w.shape == (700,) and u.shape == (steps,), "input dimensions differ")
        require(
            np.isfinite(t).all()
            and np.isfinite(w).all()
            and np.isfinite(u).all()
            and t[0] >= 0
            and t[-1] < 1
            and np.all(np.diff(t) > 0)
            and np.all(w > 0)
            and np.all((u >= 0) & (u < 1)),
            "invalid nodes, weights or draws",
        )
        close(case["frequencies"], f, atol=0)
        expected_weights = np.array(
            [
                (
                    (t[(j + 1) % 700] + (1 if j == 699 else 0))
                    - (t[(j - 1) % 700] - (1 if j == 0 else 0))
                )
                / 2
                for j in range(700)
            ]
        )
        close(w, expected_weights, atol=0)
        p = w / w.sum()
        close(case["probabilities"], p, atol=0)
        truth = complex_array(case["truth_coefficients"], (101,))
        samples = complex_array(case["observed_samples"], (700,))
        for name, value in (
            ("nodes", t),
            ("weights", w),
            ("truth_coefficients", truth),
            ("observed_samples", samples),
            ("sampling_uniforms", u),
        ):
            require(case["input_hashes"][name] == digest(value), "input hash differs")
        generators = [
            np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, j])))
            for j in range(3)
        ]
        close(t, np.sort(generators[0].uniform(size=700)), atol=0)
        generated = np.zeros(101, dtype=complex)
        generated[50] = generators[1].normal()
        generated[51:] = (
            generators[1].normal(size=50) + 1j * generators[1].normal(size=50)
        ) / np.sqrt(2)
        generated[:50] = generated[51:][::-1].conjugate()
        generated /= np.linalg.norm(generated)
        close(truth, generated, atol=0)
        close(u, generators[2].uniform(size=steps), atol=0)
        phase = (2 * np.pi * t[:, None]) * f
        ar, ai = np.cos(phase), np.sin(phase)
        close(samples.real, ar @ truth.real - ai @ truth.imag)
        close(samples.imag, ar @ truth.imag + ai @ truth.real)
        truth_signal = complex_array(case["truth_signal"], (513,))
        close(truth_signal.real, gr @ truth.real - gi @ truth.imag)
        close(truth_signal.imag, gr @ truth.imag + gi @ truth.real)
        gaps = np.diff(np.r_[t, t[0] + 1])
        close(case["periodic_gaps"], gaps, atol=0)
        condition = case["conditioning"]
        delta = float(max(gaps))
        applicable = 100 * delta < 1
        require(
            condition["theorem4_applicable"] is applicable
            and condition["theorem4_bound_three_applicable"] is (delta <= 0.005),
            "theorem hypothesis differs",
        )
        close(condition["max_periodic_gap"], delta, atol=0)
        if applicable:
            close(condition["theorem4_condition_upper"], (1 + 100 * delta) / (1 - 100 * delta))
        else:
            require(
                condition["theorem4_condition_upper"] is None,
                "inapplicable theorem has numeric bound",
            )
        singular = np.linalg.svd(np.sqrt(w)[:, None] * (ar + 1j * ai), compute_uv=False)
        close(condition["singular_values"], singular)
        close(condition["spectral_condition"], singular[0] / singular[-1])
        close(condition["scaled_condition_squared"], 101 * w.sum() / singular[-1] ** 2)
        require(set(case["runs"]) == {"cyclic", "uniform", "weighted"}, "method missing")
        cdf = np.cumsum(p)
        cdf[-1] = 1
        for method, run in case["runs"].items():
            expected_rows = (
                np.arange(steps) % 700
                if method == "cyclic"
                else np.floor(700 * u).astype(int)
                if method == "uniform"
                else np.searchsorted(cdf, u, side="right")
            )
            require(
                run["rows"] == expected_rows.tolist()
                and run["updates"] == steps
                and run["termination"] == "fixed_budget",
                "row choices or budget differ",
            )
            require(
                len(run["error_l2"]) == len(run["error_squared"]) == steps + 1, "incomplete curve"
            )
            require(
                [s["iteration"] for s in run["snapshots"]] == expected_snapshots,
                "incomplete snapshots",
            )
            saved = {s["iteration"]: s for s in run["snapshots"]}
            xr, xi = np.zeros(101), np.zeros(101)
            previous = None
            for k in range(steps + 1):
                error2 = float(np.sum((xr - truth.real) ** 2 + (xi - truth.imag) ** 2))
                close(run["error_squared"][k], error2)
                close(run["error_l2"][k], np.sqrt(error2))
                if k in saved:
                    s = saved[k]
                    c = complex_array(s["coefficients"], (101,))
                    close(c.real, xr)
                    close(c.imag, xi)
                    require(s["coefficients_sha256"] == digest(c), "coefficient hash differs")
                    signal = complex_array(s["signal"], (513,))
                    # Stored-point checks isolate display evidence from accumulated recurrence roundoff.
                    close(signal.real, gr @ c.real - gi @ c.imag)
                    close(signal.imag, gr @ c.imag + gi @ c.real)
                    residual_r = ar @ c.real - ai @ c.imag - samples.real
                    residual_i = ar @ c.imag + ai @ c.real - samples.imag
                    close(
                        s["weighted_residual_l2"],
                        np.sqrt(np.sum(w * (residual_r**2 + residual_i**2))),
                    )
                    projection = s["last_projection"]
                    if k == 0:
                        require(projection is None, "initial point has fictitious projection")
                    else:
                        i, br, bi, old_error, correction, prior_r, prior_i = previous
                        require(projection["row"] == i, "last row differs")
                        close(projection["node"], t[i], atol=0)
                        if method == "cyclic":
                            require(
                                projection["probability"] is None,
                                "cyclic order labelled probabilistic",
                            )
                        else:
                            close(
                                projection["probability"], 1 / 700 if method == "uniform" else p[i]
                            )
                        for field, expected in (
                            ("prediction_before", complex(br, bi)),
                            (
                                "prediction_after",
                                complex(ar[i] @ xr - ai[i] @ xi, ar[i] @ xi + ai[i] @ xr),
                            ),
                            ("observed", samples[i]),
                        ):
                            close(complex_array(projection[field], ()), expected)
                        for field, expected in (
                            ("previous_error_squared", old_error),
                            ("next_error_squared", error2),
                            ("correction_squared", correction),
                            ("pythagorean_residual", old_error - error2 - correction),
                        ):
                            close(projection[field], expected)
                        require(
                            ("signal_update" in projection) == (extension is not None),
                            "partial projection explanation",
                        )
                        if extension is not None:
                            validate_signal_update(
                                projection, c, prior_r, prior_i, grid, complex_array, close, require
                            )
                if k == steps:
                    break
                i = int(expected_rows[k])
                br, bi = ar[i] @ xr - ai[i] @ xi, ar[i] @ xi + ai[i] @ xr
                er, ei = samples.real[i] - br, samples.imag[i] - bi
                denominator = np.sum(ar[i] ** 2 + ai[i] ** 2)
                dr = (er * ar[i] + ei * ai[i]) / denominator
                di = (ei * ar[i] - er * ai[i]) / denominator
                previous = (
                    i,
                    br,
                    bi,
                    error2,
                    float(np.sum(dr * dr + di * di)),
                    xr.copy(),
                    xi.copy(),
                )
                xr, xi = xr + dr, xi + di


def validate_signal_update(
    projection, following, prior_r, prior_i, original_grid, complex_array, close, require
):
    """Independent cosine/sine operator and finite cosine sum, with actual prior state."""
    record = projection["signal_update"]
    previous = complex_array(record["previous_coefficients"], (101,))
    close(previous.real, prior_r)
    close(previous.imag, prior_i)
    correction = complex_array(record["coefficient_correction"], (101,))
    require(
        np.array_equal(correction, following - previous), "correction is not actual subtraction"
    )
    grid = np.unique(np.r_[original_grid, projection["node"]])
    require(np.array_equal(record["grid"], grid), "projection grid differs")
    center = int(np.flatnonzero(grid == projection["node"])[0])
    require(
        type(record["node_index"]) is int and record["node_index"] == center,
        "kernel center differs",
    )
    frequencies = np.arange(-50, 51)
    phase = (2 * np.pi * grid[:, None]) * frequencies
    cosine, sine = np.cos(phase), np.sin(phase)
    arrays = {}
    for field, coefficients in [
        ("previous_signal", previous),
        ("next_signal", following),
        ("correction_signal", correction),
    ]:
        values = complex_array(record[field], grid.shape)
        close(values.real, cosine @ coefficients.real - sine @ coefficients.imag)
        close(values.imag, cosine @ coefficients.imag + sine @ coefficients.real)
        arrays[field] = values
    offsets = grid - projection["node"]
    # Real finite Fourier sum instead of the producer's wrapped sinc quotient.
    kernel = (1 + 2 * np.sum(np.cos(2 * np.pi * offsets[:, None] * np.arange(1, 51)), axis=1)) / 101
    close(record["normalized_kernel"], kernel)
    require(record["normalized_kernel"][center] == 1.0, "kernel center is not one")
    observed = complex_array(projection["observed"], ())
    predicted = complex_array(projection["prediction_before"], ())
    residual = observed - predicted
    close(complex_array(record["projection_residual"], ()), residual)
    row_phase = (2 * np.pi * projection["node"]) * frequencies
    denominator = np.sum(np.cos(row_phase) ** 2 + np.sin(row_phase) ** 2)
    close(record["row_norm_squared"], denominator)
    ideal = complex_array(record["ideal_signal_correction"], grid.shape)
    close(ideal, residual * 101 / denominator * kernel)
    close(arrays["previous_signal"][center], predicted)
    close(arrays["next_signal"][center], observed)
    close(arrays["correction_signal"][center], residual)
    # Check the raw diagnostics from the retained floating-point arrays, without flooring.
    row = np.exp(2j * np.pi * projection["node"] * frequencies)
    ideal_coefficients = residual / float(np.vdot(row, row).real) * row.conjugate()
    for field, value in [
        ("coefficient_roundoff_inf", np.max(np.abs(correction - ideal_coefficients))),
        ("kernel_comparison_error_inf", np.max(np.abs(arrays["correction_signal"] - ideal))),
        (
            "linearity_residual_inf",
            np.max(
                np.abs(
                    arrays["next_signal"] - arrays["previous_signal"] - arrays["correction_signal"]
                )
            ),
        ),
    ]:
        close(record[field], value, atol=3e-30)


def exercise_nonuniform(cli, work, env, run, extract_record):
    import json

    for steps in (1, 13, 15000):
        command = [cli, "reproduce", "kaczmarz-sampling"]
        if steps != 15000:
            command += ["--steps", str(steps)]
        data = json.loads(run(command + ["--format", "json"], work, env))
        validate_nonuniform(data, require_projection=True)
        html = run(command + ["--lang", "ko"], work, env)
        if data["parameters"]["steps"] != steps or extract_record(html) != data:
            raise RuntimeError("installed nonuniform sampling HTML/JSON or default budget differs")
        if html.count('class="sampling-case"') != 3:
            raise RuntimeError("declared sampling cases missing from installed report")
