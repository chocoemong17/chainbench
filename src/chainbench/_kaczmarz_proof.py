"""Finite conditional projections in the published coordinate constructions."""

from __future__ import annotations

import numpy as np


def conditional_projections(inputs, runs):
    a = np.array(inputs["A"])
    b = np.array(inputs["b"])
    solution = np.array(inputs["solution"])
    probabilities = np.array(inputs["row_probabilities"])
    norm2 = np.einsum("ij,ij->i", a, a)
    frobenius2 = float(norm2.sum())
    minimum_singular2 = float(min(inputs["direction_counts"]))
    states = []
    # Each input state is a real recorded point. Candidate outcomes enumerate
    # possible row choices; they are not additional sampled iterates.
    for point in sorted({tuple(x) for run in runs for x in run["iterates"]}):
        x = np.array(point)
        error = x-solution
        error2 = float(error@error)
        outcomes = []
        for index, row in enumerate(a):
            nxt = x+(b[index]-row@x)/norm2[index]*row
            remaining, removed = nxt-solution, x-nxt
            remaining2, removed2 = float(remaining@remaining), float(removed@removed)
            outcomes.append(dict(row_index=index, probability=float(probabilities[index]),
                                 next=nxt.tolist(), remaining_error=remaining.tolist(),
                                 removed_error=removed.tolist(), squared_error=remaining2,
                                 squared_step=removed2, inner_product=float(remaining@removed),
                                 pythagorean_residual=error2-remaining2-removed2))
        groups = []
        offset = 0
        for axis,count in enumerate(inputs["direction_counts"]):
            indices = list(range(offset,offset+count))
            groups.append(dict(direction=axis, row_indices=indices,
                               probability=float(probabilities[indices].sum()),
                               next=outcomes[offset]["next"],
                               squared_error=outcomes[offset]["squared_error"],
                               squared_step=outcomes[offset]["squared_step"]))
            offset += count
        mean = float(probabilities@np.array([r["squared_error"] for r in outcomes]))
        removed_mean = float(probabilities@np.array([r["squared_step"] for r in outcomes]))
        residual = a@x-b
        residual_ratio = float(residual@residual)/frobenius2
        upper = (1-minimum_singular2/frobenius2)*error2
        states.append(dict(
            key=','.join(str(int(v)) for v in point), x=list(point), squared_error=error2,
            outcomes=outcomes, directions=groups,
            conditional_squared_error=mean, conditional_squared_step=removed_mean,
            residual_energy_over_frobenius=residual_ratio,
            conditional_identity_residual=error2-mean-removed_mean,
            theorem_conditional_upper=upper,
            conditional_ratio=mean/error2 if error2 else None,
        ))
    return dict(
        kind="chainbench.kaczmarz-conditional-projections", states=states,
        source="Theorem 2 proof, Eqs. (8)–(9) and conditional Pythagorean argument; arXiv:math/0702226v1 printed/PDF pp.5–6",
        interpretation="Fix the previous point; average over possible next row choices, not over finite sampled trials. At k>=1 explain the completed update k; at k=0 show initial possibilities without a selected row.",
        frobenius_squared=frobenius2, minimum_singular_squared=minimum_singular2,
    )
