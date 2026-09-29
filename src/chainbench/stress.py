"""Seeded multi-instance evidence: sampled stress tests are not theorem proofs."""
from __future__ import annotations

import hashlib
import json
import math
from html import escape

import numpy as np

from ._pages import bi, evidence, page
from .methods import (
    accelerated_gradient,
    conjugate_gradient,
    fista,
    frank_wolfe,
    gradient_descent,
    heavy_ball,
    ista,
    proximal_point,
)
from .problems import DiagonalLassoProblem, QuadraticProblem, SimplexQuadraticProblem
from .visuals import ChartSpec, LineSeries, render_line_chart

MAX_TRIALS = 64
TOPICS = (
    "gd-baseline",
    "nesterov-1983",
    "polyak-1964",
    "hestenes-stiefel-1952",
    "jaggi-2013",
    "rockafellar-1976",
    "beck-teboulle-2009",
    "ista-vs-fista",
)


def _rng(seed: int) -> np.random.Generator:
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    return np.random.Generator(np.random.PCG64(seed))


def _orthogonal_mix(rng: np.random.Generator, dim: int) -> np.ndarray:
    """Compose a few deterministic Householder reflections from the seeded RNG."""
    mix = np.eye(dim)
    for _ in range(3):
        v = rng.normal(size=dim)
        norm = float(np.hypot.reduce(v))
        if not math.isfinite(norm) or norm == 0:
            raise FloatingPointError("invalid sampled rotation vector")
        v = v / norm
        h = np.eye(dim) - 2.0 * np.outer(v, v)
        mix = h @ mix
    return mix


def _digest_problem(problem) -> str:
    h = hashlib.sha256()
    def add(name: str, value) -> None:
        arr = np.ascontiguousarray(np.asarray(value, dtype="<f8"))
        h.update(name.encode("ascii") + b"\0")
        h.update(json.dumps(arr.shape, separators=(",", ":")).encode("ascii") + b"\0")
        h.update(arr.tobytes(order="C"))
    if isinstance(problem, QuadraticProblem):
        add("Q", problem.Q); add("b", problem.b); add("x_star", problem.x_star)
    elif isinstance(problem, DiagonalLassoProblem):
        add("a", problem.a); add("b", problem.b); add("lam", [problem.lam])
    elif isinstance(problem, SimplexQuadraticProblem):
        add("target", problem.target)
    else:
        raise TypeError("unsupported stress problem")
    return h.hexdigest()


def _gaps(problem, trace) -> np.ndarray:
    values = np.asarray([problem.gap(x) for x in trace.iterates], dtype=float)
    if not np.all(np.isfinite(values)) or np.any(values < 0):
        raise FloatingPointError("invalid sampled objective gaps")
    return values


def _smooth_problem(rng: np.random.Generator, dim: int = 24) -> QuadraticProblem:
    L = float(10 ** rng.uniform(-0.35, 0.35))
    floor = L * 1e-5
    interior = np.sort(10 ** rng.uniform(math.log10(floor), math.log10(L), dim - 2))
    eig = np.r_[floor, interior, L]
    x_star = rng.uniform(-1.0, 1.0, dim)
    mix = _orthogonal_mix(rng, dim)
    q = mix.T @ np.diag(eig) @ mix
    q = 0.5 * q + 0.5 * q.T
    return QuadraticProblem.from_reference(q, x_star)


def _strong_problem(rng: np.random.Generator, dim: int = 24) -> QuadraticProblem:
    L = float(10 ** rng.uniform(-0.2, 0.3))
    kappa = float(10 ** rng.uniform(0.5, 3.0))
    mu = L / kappa
    interior = np.sort(10 ** rng.uniform(math.log10(mu), math.log10(L), dim - 2))
    eig = np.r_[mu, interior, L]
    x_star = rng.uniform(-1.0, 1.0, dim)
    mix = _orthogonal_mix(rng, dim)
    q = mix.T @ np.diag(eig) @ mix
    q = 0.5 * q + 0.5 * q.T
    return QuadraticProblem.from_reference(q, x_star)


def _lasso_problem(rng: np.random.Generator, dim: int = 28) -> DiagonalLassoProblem:
    a = rng.uniform(0.4, 2.0, dim)
    b = rng.uniform(-1.6, 1.6, dim)
    lam = float(10 ** rng.uniform(-2.0, -0.25))
    return DiagonalLassoProblem(a, b, lam)


def _simplex_problem(rng: np.random.Generator, dim: int = 28) -> SimplexQuadraticProblem:
    raw = rng.uniform(0.05, 1.0, dim)
    return SimplexQuadraticProblem(raw / raw.sum())


def _trial(topic: str, seed: int) -> dict:
    rng = _rng(seed)
    if topic in ("gd-baseline", "nesterov-1983"):
        p = _smooth_problem(rng)
        steps = 40
        trace = gradient_descent(p, steps) if topic == "gd-baseline" else accelerated_gradient(p, steps)
        k = np.arange(1, steps + 1, dtype=float)
        radius2 = float(p.x_star @ p.x_star)
        if topic == "gd-baseline":
            bound = p.L * radius2 / (2 * k)
        else:
            bound = 2 * p.L * radius2 / (k + 1) ** 2
        metric = float(np.max(_gaps(p, trace)[1:] / bound))
        return {"seed": seed, "metric": metric, "threshold": 1.0, "dim": p.dim,
                "L": p.L, "mu": p.mu, "steps": steps,
                "instance_sha256": _digest_problem(p), "orientation": "seeded-householder"}

    if topic == "polyak-1964":
        p = _strong_problem(rng)
        steps = 180
        trace, alpha, beta = heavy_ball(p, steps)
        errors = np.asarray([np.linalg.norm(x - p.x_star) for x in trace.iterates])
        valid = errors[:-1] > 1e-10
        ratios = errors[1:][valid] / errors[:-1][valid]
        if ratios.size == 0:
            raise FloatingPointError("sampled heavy-ball trial reached numerical floor too early")
        observed = float(np.median(ratios[-20:]))
        rho = float((np.sqrt(p.L) - np.sqrt(p.mu)) / (np.sqrt(p.L) + np.sqrt(p.mu)))
        metric = abs(observed - rho) / rho
        return {"seed": seed, "metric": metric, "threshold": 0.08, "dim": p.dim,
                "condition_number": p.L / p.mu, "steps": steps, "alpha": alpha,
                "beta": beta, "rho": rho, "evidence_kind": "empirical",
                "instance_sha256": _digest_problem(p), "orientation": "seeded-householder"}

    if topic == "hestenes-stiefel-1952":
        p = _strong_problem(rng)
        steps = min(20, p.dim)
        trace = conjugate_gradient(p, steps, rtol=0.0, atol=0.0)
        errors = np.sqrt(2 * _gaps(p, trace))
        rho = (np.sqrt(p.L / p.mu) - 1) / (np.sqrt(p.L / p.mu) + 1)
        k = np.arange(1, len(errors), dtype=float)
        metric = float(np.max(errors[1:] / (2 * rho ** k * errors[0]))) if k.size else 0.0
        return {"seed": seed, "metric": metric, "threshold": 1.0, "dim": p.dim,
                "condition_number": p.L / p.mu, "steps": steps,
                "instance_sha256": _digest_problem(p), "orientation": "seeded-householder"}

    if topic == "jaggi-2013":
        p = _simplex_problem(rng)
        steps = 40
        trace = frank_wolfe(p, steps)
        k = np.arange(1, steps + 1, dtype=float)
        bound = 2 * p.curvature_upper_bound / (k + 2)
        metric = float(np.max(_gaps(p, trace)[1:] / bound))
        return {"seed": seed, "metric": metric, "threshold": 1.0, "dim": p.dim,
                "steps": steps, "instance_sha256": _digest_problem(p)}

    if topic == "rockafellar-1976":
        p = _strong_problem(rng)
        c = float(10 ** rng.uniform(-0.6, 0.6))
        steps = 24
        trace = proximal_point(p, steps, c)
        errors = np.asarray([np.linalg.norm(x - p.x_star) for x in trace.iterates])
        q = 1 / (1 + c * p.mu)
        valid = errors[:-1] > 1e-12
        metric = float(np.max(errors[1:][valid] / (q * errors[:-1][valid])))
        return {"seed": seed, "metric": metric, "threshold": 1.0, "dim": p.dim,
                "condition_number": p.L / p.mu, "proximal_parameter": c, "steps": steps,
                "instance_sha256": _digest_problem(p), "orientation": "seeded-householder"}

    if topic in ("beck-teboulle-2009", "ista-vs-fista"):
        p = _lasso_problem(rng)
        steps = 50
        if topic == "beck-teboulle-2009":
            trace = fista(p, steps)
            radius2 = float(p.x_star @ p.x_star)
            if radius2 == 0:
                return _trial(topic, seed + 1000003)
            k = np.arange(1, steps + 1, dtype=float)
            bound = 2 * p.L * radius2 / (k + 1) ** 2
            metric = float(np.max(_gaps(p, trace)[1:] / bound))
            return {"seed": seed, "metric": metric, "threshold": 1.0, "dim": p.dim,
                    "lambda": p.lam, "steps": steps, "instance_sha256": _digest_problem(p)}
        gi = p.gap(ista(p, steps).iterates[-1])
        gf = p.gap(fista(p, steps).iterates[-1])
        metric = float(gf / gi) if gi > 1e-28 else 0.0
        return {"seed": seed, "metric": metric, "threshold": None, "dim": p.dim,
                "lambda": p.lam, "steps": steps, "evidence_kind": "informational",
                "instance_sha256": _digest_problem(p)}

    raise ValueError(f"unknown stress topic: {topic}")


def run_stress(topic: str, trials: int = 24, seed: int = 0) -> dict:
    if topic not in TOPICS:
        raise ValueError("unknown stress topic")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if isinstance(trials, bool) or not isinstance(trials, int) or not 2 <= trials <= MAX_TRIALS:
        raise ValueError(f"trials must be an integer between 2 and {MAX_TRIALS}")
    rows = [_trial(topic, seed + i) for i in range(trials)]
    metrics = np.asarray([row["metric"] for row in rows], dtype=float)
    if not np.all(np.isfinite(metrics)) or np.any(metrics < 0):
        raise FloatingPointError("invalid stress metric")
    threshold = rows[0]["threshold"]
    if any(row["threshold"] != threshold for row in rows):
        raise ValueError("stress trials disagree on threshold semantics")
    hashes = [row["instance_sha256"] for row in rows]
    summary = {
        "min": float(np.min(metrics)),
        "median": float(np.median(metrics)),
        "p90": float(np.quantile(metrics, .9)),
        "max": float(np.max(metrics)),
        "unique_instances": len(set(hashes)),
    }
    if threshold is not None:
        summary["within_threshold"] = int(np.count_nonzero(metrics <= threshold + 1e-10))
        summary["trials"] = trials
    return {
        "kind": "chainbench.stress",
        "schema_version": 1,
        "topic": topic,
        "seed": seed,
        "trials": trials,
        "threshold": threshold,
        "summary": summary,
        "rows": rows,
        "notice": (
            "Seeded sampled instances broaden finite evidence beyond one canonical fixture. "
            "They do not prove a class-wide theorem, certify worst-case behavior, or measure adoption."
        ),
    }


def _stress_chart(result: dict) -> ChartSpec:
    x = tuple(range(1, result["trials"] + 1))
    metrics = tuple(row["metric"] for row in result["rows"])
    series = [LineSeries("sampled metric", x, metrics, "samples")]
    if result["threshold"] is not None:
        series.append(LineSeries(
            "threshold", x, tuple(float(result["threshold"]) for _ in x), "bound"
        ))
    title = "Sampled evidence across reproducible instances"
    return ChartSpec(title, "trial", "normalized check metric", tuple(series), "linear")


def stress_html(result: dict, lang: str = "en") -> str:
    if result.get("kind") != "chainbench.stress":
        raise ValueError("not a stress report")
    topic = result["topic"]
    s = result["summary"]
    threshold = result["threshold"]
    if threshold is None:
        verdict = bi(
            "이 항목은 통과/실패 정리가 아니라 분포 자체를 보여줍니다.",
            "This topic is descriptive; the distribution has no theorem pass/fail threshold.",
        )
    else:
        label = "경험적 회귀 기준" if topic == "polyak-1964" else "선택한 이론 상계"
        label_en = "empirical regression threshold" if topic == "polyak-1964" else "selected theoretical envelope"
        verdict = bi(
            f'{result["trials"]}개 중 {s["within_threshold"]}개가 {label} 안에 있었습니다.',
            f'{s["within_threshold"]} of {result["trials"]} samples were within the {label_en}.',
        )
    cards = (
        '<div class="metric-grid">'
        f'<div class="metric"><span>median</span><strong>{s["median"]:.4g}</strong></div>'
        f'<div class="metric"><span>90%</span><strong>{s["p90"]:.4g}</strong></div>'
        f'<div class="metric"><span>max</span><strong>{s["max"]:.4g}</strong></div>'
        f'<div class="metric"><span>unique instances</span><strong>{s["unique_instances"]}</strong></div>'
        '</div>'
    )
    rows = []
    for index, row in enumerate(result["rows"], 1):
        details = ", ".join(
            f"{escape(str(k))}={escape(f'{v:.4g}' if isinstance(v, float) else str(v))}"
            for k, v in row.items()
            if k not in {"seed", "metric", "threshold", "evidence_kind", "instance_sha256"}
        )
        rows.append(
            f'<tr><td>{index}</td><td>{row["seed"]}</td><td>{row["metric"]:.6g}</td>'
            f'<td><code>{row["instance_sha256"][:12]}…</code></td><td>{details}</td></tr>'
        )
    protocol = bi(
        "한 개의 예시를 잘 골라 보여주는 대신, 연속된 seed로 여러 합성 문제를 생성해 같은 검사를 반복합니다. "
        "모든 seed와 파라미터를 아래 JSON에 보존합니다. 그래도 이것은 유한 표본이며 정리의 증명은 아닙니다.",
        "Instead of selecting one flattering example, ChainBench generates multiple synthetic instances from consecutive seeds and reruns the same measurement. Every seed and parameter is preserved below. This remains finite sampling, not proof.",
    )
    body = (
        '<div class="evidence-banner"><span class="evidence-tag">MULTI-INSTANCE STRESS</span>'
        + protocol + '</div>' + cards
        + '<section><h2>' + bi('표본 전체 보기', 'See the whole sample') + '</h2><p>' + verdict + '</p>'
        + '<div class="plot">' + render_line_chart(_stress_chart(result)) + '</div></section>'
        + '<section><h2>' + bi('어떤 상황들을 시험했나?', 'What situations were sampled?')
        + '</h2><p>' + bi(
            '각 행은 별도의 seed로 만든 문제입니다. 차원, 조건수, 정규화 계수처럼 결과 해석에 필요한 값도 함께 저장됩니다.',
            'Each row is a separate seeded problem. Dimensions, conditioning and regularization parameters needed for interpretation are stored with it.',
        ) + '</p><div class="scroll"><table><thead><tr><th>#</th><th>seed</th><th>metric</th><th>instance</th><th>parameters</th></tr></thead><tbody>'
        + ''.join(rows) + '</tbody></table></div></section>'
        + '<p class="callout caution">' + bi(
            '표본을 많이 통과했다고 해서 모든 허용 함수에서 성립함을 새로 증명한 것은 아닙니다. 반대로 정리 가정 밖의 문제를 섞어 실패를 만들지도 않습니다.',
            'Passing many samples does not newly prove a universal statement. The sampler also stays inside the assumptions instead of manufacturing failures outside the theorem class.',
        ) + '</p>' + evidence(result, f'stress-{topic}.json')
    )
    return page(
        'Many cases, not one cherry-picked curve',
        bi('한 개의 예시는 직관용, 여러 seed의 표본은 견고성 확인용, tight case는 별도의 수학적 주장입니다.',
           'One example is for intuition, seeded sampling probes robustness, and a tight case is a separate mathematical claim.'),
        body,
        lang=lang,
    )
