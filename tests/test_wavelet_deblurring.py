import copy
import importlib.util
import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest

from chainbench.deblurring import blur_matrix
from chainbench.wavelet_deblurring import (
    WaveletLasso,
    array_hash,
    blur,
    haar,
    run_wavelet_deblurring,
)
from chainbench.wavelet_views import wavelet_html


@pytest.mark.parametrize("n", [8, 16, 256])
def test_three_stage_haar_inverse_norm_and_adjoint(n):
    rng = np.random.default_rng(5)
    x, y = rng.normal(size=(2, n, n))
    np.testing.assert_allclose(haar(haar(x), inverse=True), x, atol=4e-15)
    np.testing.assert_allclose(haar(haar(y, inverse=True)), y, atol=4e-15)
    assert np.sum(haar(x) ** 2) == pytest.approx(np.sum(x * x), rel=2e-15)
    assert np.sum(haar(x) * y) == pytest.approx(np.sum(x * haar(y, inverse=True)), abs=1e-12)
    # The deepest LL block is the normalized mean of each disjoint 8x8 block.
    expected = x.reshape(n // 8, 8, n // 8, 8).sum(axis=(1, 3)) / 8
    np.testing.assert_allclose(haar(x)[: n // 8, : n // 8], expected, atol=2e-15)


def test_haar_coefficients_against_direct_block_basis():
    image = np.arange(64).reshape(8, 8) / 64
    actual = haar(image)
    # Per-level 2D blocks, rather than separably recursing every 1D row/column.
    for level in (1, 2, 3):
        w, side = 2**level, 8 // 2**level
        for i in range(side):
            for j in range(side):
                block = image[i * w : (i + 1) * w, j * w : (j + 1) * w]
                xsign = np.r_[np.ones(w // 2), -np.ones(w // 2)]
                assert actual[i, side + j] == pytest.approx(np.sum(block * xsign) / w, abs=1e-15)
                assert actual[side + i, j] == pytest.approx(
                    np.sum(block * xsign[:, None]) / w, abs=1e-15
                )
                assert actual[side + i, side + j] == pytest.approx(
                    np.sum(block * xsign[:, None] * xsign) / w, abs=1e-15
                )
    assert actual[0, 0] == pytest.approx(image.sum() / 8)


def test_blur_matches_dense_operator_and_wavelet_gradient():
    rng = np.random.default_rng(2)
    matrix, kernel = blur_matrix(8)
    image, observed = rng.normal(size=(2, 8, 8))
    np.testing.assert_allclose(blur(image, kernel), matrix @ image @ matrix.T, atol=2e-16)
    assert np.sum(image * blur(observed, kernel)) == pytest.approx(
        np.sum(observed * blur(image, kernel)), abs=2e-14
    )
    np.testing.assert_allclose(blur(np.ones((8, 8)), kernel), 1.0, atol=2e-16)
    analysis = np.column_stack([haar(x.reshape(8, 8)).ravel() for x in np.eye(64)])
    operator = np.kron(matrix, matrix) @ analysis.T
    p = WaveletLasso(observed, kernel)
    c = rng.normal(size=64)
    expected = 2 * operator.T @ (operator @ c - observed.ravel())
    np.testing.assert_allclose(p.smooth_grad(c), expected, atol=2e-15)
    assert np.linalg.norm(operator, 2) == pytest.approx(1.0, abs=1e-15)
    direction = rng.normal(size=64)
    eps = 1e-6

    def smooth(x):
        return float(np.sum((matrix @ p.synthesize(x) @ matrix.T - observed) ** 2))

    assert (smooth(c + eps * direction) - smooth(c - eps * direction)) / (2 * eps) == pytest.approx(
        expected @ direction, rel=2e-8
    )


def test_penalty_is_in_coefficient_space_and_threshold_has_full_loss_scaling():
    _, kernel = blur_matrix(8)
    p = WaveletLasso(np.zeros((8, 8)), kernel)
    threshold = Fraction(1, 20000)
    z = np.array([-3, -1, -0.5, 0, 0.5, 1, 3]) * float(threshold)
    np.testing.assert_allclose(
        p.prox_l1(z, 0.5), np.array([-2, 0, 0, 0, 0, 0, 2]) * float(threshold), atol=1e-20
    )
    coeff = np.zeros(64)
    coeff[0] = 8.0
    assert p.lam * np.sum(np.abs(coeff)) != pytest.approx(
        p.lam * np.sum(np.abs(p.synthesize(coeff)))
    )
    assert p.value(coeff) == pytest.approx(64.0 + 0.0008)


@pytest.mark.parametrize("shape", [(7, 7), (8, 9), (10, 10), (8,), (2, 8, 8)])
def test_invalid_haar_shapes(shape):
    with pytest.raises(ValueError, match="Haar input"):
        haar(np.zeros(shape))


@pytest.mark.parametrize(
    "steps,seed", [(True, 0), (0, 0), (201, 0), (1, True), (1, -1), (1, 2**32)]
)
def test_invalid_protocol_parameters_rejected_before_image_allocation(steps, seed, monkeypatch):
    import chainbench.wavelet_deblurring as mod

    monkeypatch.setattr(mod._regutools_image, "simple_image", lambda *a: pytest.fail("allocated"))
    with pytest.raises(ValueError):
        run_wavelet_deblurring(steps, seed)


def test_actual_seeded_inputs_first_update_and_complete_snapshot_evidence():
    data = run_wavelet_deblurring(1, seed=0)
    params, problem = data["parameters"], data["problem"]
    truth, observed, noise = (
        np.array(problem[k]) for k in ("clean_image", "observed_image", "noise")
    )
    kernel = np.array(problem["kernel_1d"])
    dense, _ = blur_matrix(256)
    np.testing.assert_allclose(observed, dense @ truth @ dense.T + noise, atol=5e-16)
    np.testing.assert_array_equal(
        noise, np.random.Generator(np.random.PCG64(0)).normal(0, 0.001, (256, 256))
    )
    assert problem["f_star"] is None
    assert params["lam"] == 0.0001 and params["step_size"] == 0.5 and params["threshold"] == 0.00005
    p = WaveletLasso(observed, kernel)
    c0 = haar(observed).ravel()
    c1 = p.prox_l1(c0 - 0.5 * p.smooth_grad(c0), 0.5)
    for method, run in data["runs"].items():
        assert run["updates"] == 1 and run["termination"] == "fixed_budget"
        for k, snap in enumerate(run["snapshots"]):
            c, image = np.array(snap["coefficients"]), np.array(snap["image"])
            np.testing.assert_array_equal(c.ravel(), (c0, c1)[k])
            np.testing.assert_allclose(image, haar(c, inverse=True), atol=1e-15)
            assert snap["image_sha256"] == array_hash(image)
            assert snap["coefficients_sha256"] == array_hash(c)
            row = run["rows"][k]
            assert row["objective"] == pytest.approx(p.value(c.ravel()))
            assert row["objective"] == row["squared_residual"] + row["penalty"]
            assert row["zero_coefficients"] == np.count_nonzero(c == 0.0)
            assert row["image_rmse"] == pytest.approx(np.sqrt(np.mean((image - truth) ** 2)))
    assert data["runs"]["ista"] == data["runs"]["fista"]
    assert data["runs"]["ista"]["rows"][1]["zero_coefficients"] > 0
    assert data["source"]["image_permission_notice"].startswith("Image-generation subset")


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "wavelet_smoke", Path(__file__).resolve().parents[1] / "scripts/smoke_wavelet.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def wavelet_record():
    return run_wavelet_deblurring(3, seed=2)


def test_independent_block_basis_and_complete_recurrence(wavelet_record):
    validator = load_validator()
    rng = np.random.default_rng(11)
    image = rng.normal(size=(16, 16))
    np.testing.assert_allclose(validator.analysis(image), haar(image), atol=2e-15)
    np.testing.assert_allclose(validator.synthesis(image), haar(image, inverse=True), atol=2e-15)
    validator.validate_wavelet(wavelet_record)


@pytest.mark.parametrize(
    "fault", ["objective", "missing_row", "f_star", "coefficient", "noise_hash", "penalty"]
)
def test_corrupted_evidence_is_rejected(wavelet_record, fault):
    record = copy.deepcopy(wavelet_record)
    if fault == "objective":
        record["runs"]["ista"]["rows"][0]["objective"] += 0.1
    elif fault == "missing_row":
        record["runs"]["fista"]["rows"].pop()
    elif fault == "f_star":
        record["problem"]["f_star"] = 0
    elif fault == "coefficient":
        record["runs"]["ista"]["snapshots"][0]["coefficients"][0][0] += 0.01
    elif fault == "noise_hash":
        record["input_hashes"]["noise"] = "0" * 64
    else:
        record["parameters"]["lam"] = 0
    with pytest.raises(RuntimeError):
        load_validator().validate_wavelet(record)


def test_cli_seed_default_budget_and_scope_errors(wavelet_record, monkeypatch, tmp_path, capsys):
    import chainbench.cli as cli
    from chainbench.cli import main

    calls = []

    def compute(steps, seed=0):
        calls.append((steps, seed))
        return wavelet_record

    monkeypatch.setattr(cli, "run_wavelet_deblurring", compute)
    path = tmp_path / "wavelet.json"
    assert main(["reproduce", "fista-wavelet", "--format", "json", "--output", str(path)]) == 0
    assert calls == [(200, 0)]
    assert json.loads(path.read_text()) == wavelet_record
    assert (
        main(
            [
                "reproduce",
                "fista-wavelet",
                "--steps",
                "3",
                "--seed",
                "2",
                "--format",
                "json",
                "--output",
                str(path),
                "--force",
            ]
        )
        == 0
    )
    assert calls[-1] == (3, 2)
    for name in ("shewchuk-1994", "fista-deblurring", "lessard-2016"):
        with pytest.raises(SystemExit) as exc:
            main(["reproduce", name, "--seed", "0"])
        assert exc.value.code == 2
        assert "only supported for fista-wavelet" in capsys.readouterr().err


def test_view_retains_full_record_and_honest_unknown_optimum(wavelet_record):
    import html
    import re

    text = wavelet_html(wavelet_record, "ko")
    data = re.search(r'<pre id="chainbench-evidence">(.*?)</pre>', text, re.S)[1]
    assert json.loads(html.unescape(data)) == wavelet_record
    assert "F* = unknown" in text and "declared noise draw" in text
    assert "threshold=5×10⁻⁵" in text and "LL3" in text
    assert text.count("<img data-snapshot=") == 6
    assert text.count("<img data-coeff-snapshot=") == 6
    assert "image_permission_notice" in text and "Short preview budget" in text
