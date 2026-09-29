"""Export trajectories on a deterministic rotated quadratic (not a theorem proof)."""
from __future__ import annotations

import argparse
import csv
import sys

import numpy as np

from chainbench import (
    QuadraticProblem,
    accelerated_gradient,
    conjugate_gradient,
    gradient_descent,
    heavy_ball,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dim", type=int, default=12)
    parser.add_argument("--condition", type=float, default=10.)
    parser.add_argument("--steps", type=int, default=20)
    args = parser.parse_args(argv)
    if args.dim < 2 or args.steps < 0 or not np.isfinite(args.condition) or args.condition <= 1:
        parser.error("require dim>=2, steps>=0, and a finite condition number>1")
    u = np.arange(1, args.dim + 1, dtype=float)
    u /= np.linalg.norm(u)
    rotation = np.eye(args.dim) - 2 * np.outer(u, u)
    q = rotation @ np.diag(np.geomspace(1 / args.condition, 1, args.dim)) @ rotation.T
    q = .5 * q + .5 * q.T
    optimum = np.linspace(-1, 1, args.dim)
    try:
        problem = QuadraticProblem(q, q @ optimum, optimum)
        traces = {
            "gd": gradient_descent(problem, args.steps),
            "smooth-fista": accelerated_gradient(problem, args.steps),
            "cg": conjugate_gradient(problem, args.steps),
            "heavy-ball": heavy_ball(problem, args.steps)[0],
        }
    except (ValueError, FloatingPointError) as exc:
        parser.error(str(exc))
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["method", "iteration", "gap", "residual_norm", "cg_termination", "dim", "condition"])
    for method, trace in traces.items():
        for k, x in enumerate(trace.iterates):
            writer.writerow([
                method, k, problem.gap(x), float(np.hypot.reduce(problem.grad(x))),
                (trace.termination or "") if k == len(trace.iterates) - 1 else "",
                args.dim, args.condition,
            ])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
