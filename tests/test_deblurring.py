import base64
import hashlib
import struct
import zlib
from types import SimpleNamespace

import numpy as np
import pytest

from chainbench._regutools_image import simple_image
from chainbench.deblur_views import image_uri
from chainbench.deblurring import DeblurLeastSquares, blur_matrix, run_deblurring
from chainbench.methods import _proximal_iterates, fista, ista
from chainbench.problems import diagonal_lasso


def test_source_image_against_scalar_one_based_reference():
    # Deliberately use the source's 1-based indexing and scalar writes as an oracle.
    n = 64
    image = np.zeros((n + 1, n + 1))
    n2, n3, n6, n12 = 32, 21, 11, 5
    for row_offset, threshold, weight in ((2, 1.0, 1), (n6, 0.6, 2)):
        for i in range(1, 2 * n6 + 1):
            for j in range(1, 2 * n3 + 1):
                qi = n6 - i + 1 if i <= n6 else i - n6
                qj = n3 - j + 1 if j <= n3 else j - n3
                radius = (qi / n6) ** 2 + (qj / n3) ** 2
                if radius < threshold:
                    image[row_offset + i, n3 - 1 + j] += weight
    image[image == 3] = 2
    for i in range(1, n3 + 1):
        for j in range(1, n3 + 1):
            image[n3 + n12 + i, 1 + j] = 3 * int(j >= i)
    for i in range(1, 2 * n6 + 2):
        for j in range(1, 2 * n6 + 2):
            image[n2 + n12 + i, n2 + j] = 4 * int(i == n6 + 1 or j == n6 + 1)
    np.testing.assert_array_equal(simple_image(), image[1:, 1:] / 4)
    assert set(np.unique(simple_image())) == {0.0, 0.25, 0.5, 0.75, 1.0}


def direct_blur(image, kernel):
    # Independent stencil using an explicitly extended image, not B @ x @ B.T.
    n = len(image)
    padded = np.pad(image, 4, mode="symmetric")
    out = np.zeros_like(image)
    for i in range(9):
        for j in range(9):
            out += kernel[i] * kernel[j] * padded[i : i + n, j : j + n]
    return out


def test_blur_adjoint_lipschitz_and_gradient_against_independent_stencil():
    B, kernel = blur_matrix(8)
    rng = np.random.default_rng(12)
    u, v = rng.normal(size=(2, 8, 8))
    np.testing.assert_allclose(B, B.T, atol=2e-16)
    np.testing.assert_allclose(B.sum(axis=1), 1, atol=2e-16)
    assert np.linalg.norm(B, 2) == pytest.approx(1, abs=2e-15)
    A = np.kron(B, B)
    np.testing.assert_allclose(A @ u.ravel(), direct_blur(u, kernel).ravel(), atol=1e-15)
    assert np.sum(u * direct_blur(v, kernel)) == pytest.approx(
        np.sum(v * direct_blur(u, kernel)), abs=1e-14
    )
    p = DeblurLeastSquares(v, B)
    np.testing.assert_allclose(
        p.smooth_grad(u.ravel()), 2 * A.T @ (A @ u.ravel() - v.ravel()), atol=2e-15
    )
    epsilon = 1e-6
    difference = (p.value((u + epsilon * v).ravel()) - p.value((u - epsilon * v).ravel())) / (
        2 * epsilon
    )
    assert difference == pytest.approx(p.smooth_grad(u.ravel()) @ v.ravel(), rel=1e-8)
    np.testing.assert_allclose(direct_blur(np.ones((8, 8)), kernel), 1.0, atol=1e-15)


def haar2(image):
    out = image.copy()
    n = len(image)
    for _ in range(3):
        block = out[:n, :n]
        horizontal = np.concatenate(
            (
                (block[:, ::2] + block[:, 1::2]) / np.sqrt(2),
                (block[:, ::2] - block[:, 1::2]) / np.sqrt(2),
            ),
            axis=1,
        )
        out[:n, :n] = np.concatenate(
            (
                (horizontal[::2] + horizontal[1::2]) / np.sqrt(2),
                (horizontal[::2] - horizontal[1::2]) / np.sqrt(2),
            ),
            axis=0,
        )
        n //= 2
    return out


def test_zero_penalty_wavelet_and_image_updates_are_equivalent():
    B, _ = blur_matrix(8)
    A = np.kron(B, B)
    Wt = np.column_stack([haar2(e.reshape(8, 8)).ravel() for e in np.eye(64)])
    np.testing.assert_allclose(Wt @ Wt.T, np.eye(64), atol=1e-15)
    W = Wt.T
    truth = np.arange(64, dtype=float) / 64
    b = A @ truth
    p = DeblurLeastSquares(b.reshape(8, 8), B)
    coeff = SimpleNamespace(
        dim=64,
        L=2.0,
        smooth_grad=lambda x: 2 * Wt @ A.T @ (A @ W @ x - b),
        prox_l1=lambda x, step: x.copy(),
        value=lambda x: float(np.sum((A @ W @ x - b) ** 2)),
    )
    for method in (ista, fista):
        pixel = method(p, 12, b)
        wavelet = method(coeff, 12, Wt @ b)
        np.testing.assert_allclose(
            pixel.iterates, np.array(wavelet.iterates) @ W.T, rtol=2e-13, atol=2e-15
        )
        np.testing.assert_allclose(pixel.values, wavelet.values, rtol=5e-12, atol=1e-15)


@pytest.mark.parametrize("accelerated", [False, True])
def test_streamed_updates_preserve_public_trace_and_isolate_yielded_arrays(accelerated):
    p = diagonal_lasso()
    public = (fista if accelerated else ista)(p, 6)
    stream = _proximal_iterates(p, 6, accelerated=accelerated)
    first = next(stream)
    first[:] = 1e9
    np.testing.assert_array_equal(list(stream), public.iterates[1:])
    # Independent indexed recurrence including the first nonzero momentum.
    x = np.zeros(p.dim)
    y = x.copy()
    t = 1.0
    reference = [x.copy()]
    for _ in range(6):
        z = (y if accelerated else x) - p.smooth_grad(y if accelerated else x) / p.L
        xn = np.sign(z) * np.maximum(np.abs(z) - p.lam / p.L, 0)
        tn = (1 + np.sqrt(1 + 4 * t * t)) / 2
        y = xn + (t - 1) / tn * (xn - x)
        x, t = xn, tn
        reference.append(x.copy())
    np.testing.assert_array_equal(public.iterates, reference)


def test_noiseless_record_first_updates_metrics_hashes_and_snapshots():
    result = run_deblurring(10)
    p = result["problem"]
    truth = np.array(p["clean_image"])
    b = np.array(p["observed_image"])
    kernel = np.array(p["kernel_1d"])
    np.testing.assert_allclose(b, direct_blur(truth, kernel), atol=1e-15)
    assert p["f_star"] == 0 and not np.all(truth == 0)
    for name, run in result["runs"].items():
        assert len(run["rows"]) == 11
        assert [s["iteration"] for s in run["snapshots"]] == [0, 1, 10]
        for snapshot in run["snapshots"]:
            u = np.array(snapshot["image"])
            assert snapshot["sha256"] == hashlib.sha256(u.astype("<f8").tobytes()).hexdigest()
            row = run["rows"][snapshot["iteration"]]
            assert row["objective"] == pytest.approx(
                np.sum((direct_blur(u, kernel) - b) ** 2), rel=1e-12
            )
            assert row["image_rmse"] == pytest.approx(np.sqrt(np.mean((u - truth) ** 2)), rel=1e-14)
        expected = b - direct_blur(direct_blur(b, kernel) - b, kernel)
        np.testing.assert_allclose(run["snapshots"][1]["image"], expected, atol=2e-16)
    assert (
        result["runs"]["ista"]["rows"][2]["objective"]
        == result["runs"]["fista"]["rows"][2]["objective"]
    )
    assert (
        result["runs"]["ista"]["rows"][3]["objective"]
        != result["runs"]["fista"]["rows"][3]["objective"]
    )
    assert not result["parameters"]["full_paper_budget"]


@pytest.mark.parametrize("steps", [True, 0, -1, 10001, 1.5, None])
def test_invalid_work_budget_is_rejected(steps):
    with pytest.raises(ValueError):
        run_deblurring(steps)


def test_display_encoding_uses_fixed_scale_without_mutating_numbers():
    values = np.array([[-1, 0, 0.5, 1, 2]])
    data = base64.b64decode(image_uri(values).split(",")[1])
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    length = struct.unpack("!I", data[8:12])[0]
    pos = 8 + 12 + length
    assert data[pos + 4 : pos + 8] == b"IDAT"
    length = struct.unpack("!I", data[pos : pos + 4])[0]
    assert zlib.decompress(data[pos + 8 : pos + 8 + length]) == bytes([0, 0, 0, 128, 255, 255])
    np.testing.assert_array_equal(values, [[-1, 0, 0.5, 1, 2]])


def load_validator():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('deblur_smoke', Path(__file__).resolve().parents[1]/'scripts/smoke_deblurring.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_deblurring


def test_independent_installed_validator_and_corruptions():
    import copy
    record=run_deblurring(3)
    validate=load_validator()
    validate(record)
    for field in ('notice','kernel','hash','rows','objective','first'):
        data=copy.deepcopy(record)
        if field=='notice':
            data['source']['image_permission_notice']=''
        elif field=='kernel':
            data['problem']['kernel_1d'][0]*=2
        elif field=='hash':
            data['problem']['clean_sha256']='0'*64
        elif field=='rows':
            data['runs']['fista']['rows'].pop(1)
        elif field=='objective':
            data['runs']['fista']['rows'][1]['objective']*=2
        else:
            snap=data['runs']['fista']['snapshots'][1]
            snap['image'][0][0]+=.1
            raw=np.array(snap['image'],dtype='<f8').tobytes()
            snap['sha256']=hashlib.sha256(raw).hexdigest()
        with pytest.raises(RuntimeError):
            validate(data)


def test_full_published_budget_cli_and_existing_default(tmp_path):
    import json

    from chainbench.cli import main
    path=tmp_path/'full.json'
    assert main(['reproduce','fista-deblurring','--format','json','--output',str(path)])==0
    record=json.loads(path.read_text())
    assert record['parameters']['steps']==10000
    assert record['parameters']['full_paper_budget']
    assert all(len(run['rows'])==10001 for run in record['runs'].values())
    load_validator()(record)
    old=tmp_path/'old.json'
    assert main(['reproduce','shewchuk-1994','--format','json','--output',str(old)])==0
    data=json.loads(old.read_text())
    assert data['parameters']['steps']==12
