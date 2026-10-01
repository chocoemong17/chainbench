# The sharp cost of using few simplex atoms

`case-study fw-sparsity` computes the explicit support-constrained construction
in Jaggi (2013), Section 3, Lemmas 3–4 and supplementary Appendix C. It compares
that construction with actual iterations of the existing Frank–Wolfe method.
This is a public sharp lower bound, not a random search for difficult instances.

```sh
python -m chainbench case-study fw-sparsity --lang ko --output sparsity.html
python -m chainbench case-study fw-sparsity --format json --output sparsity.json
python -m chainbench case-study fw-sparsity --steps 128 --output longer.html
```

The default budget is 40; integer budgets 1–256 are supported. Every run includes
all four declared dimensions **3, 8, 32, 128**, starting from e₁. No seed is used
and no dimension is selected by its observed performance. These dimensions,
budgets, UI and comparisons are added examples, not original-paper experiments.
The existing `case-study gd-tight` defaults stay 20/1/1/1 for horizon/L/R/h.
GD-specific options are rejected for this case; `--steps` is rejected for GD.

This development addition follows the noisy-wavelet work and is newer than the
review guide's pinned snapshot. Remote PR/CI evidence is pending authentication;
the earlier published snapshot and v0.5.0 release are separate.
The subsequent [optional extended tour](OFFLINE_TOUR.md#optional-extended-path)
connects the default 40-update record to oracle geometry and the GD tight case.

## Source, scaling and the exact claims

Primary source: [Jaggi, *Revisiting Frank-Wolfe: Projection-Free Sparse Convex
Optimization*, PMLR 28(1):427–435 (2013)](https://proceedings.mlr.press/v28/jaggi13.html).
The [supplementary PDF](https://proceedings.mlr.press/v28/jaggi13-supp.pdf) gives
Algorithm 1 on PDF p.1, Theorem 1 on p.4, Lemmas 3–4 on p.5, and their proofs in
Appendix C on p.12. Its SHA-256 is
`26446809e3770656d1fea7a2105f203d058b299033043e30f31ba524d8875600`.
The normal nine-page paper states Theorem 1 on p.3; do not mix the two page maps.

The source problem is

    minimize f(x) = sum_i x_i^2
    subject to x_i >= 0, sum_i x_i = 1.

Its optimizer is uniform: x*=(1/n,…,1/n), f*=1/n. The Hessian is 2I and the
squared simplex diameter is 2, so its curvature is C_f=4. The curvature value
is attained between two distinct vertices. This **full squared norm** differs
from the half-squared-distance problem in the existing simplex geometry.

We reserve k for iteration and s for the number of positive coordinates. The
source uses k for sparsity in its lemmas. The claims being illustrated are:

- Lemma 3: among simplex vectors with at most s nonzero entries, the minimum
  objective is 1/s, for integer 1≤s≤n. The primal gap is at least 1/s−1/n.
- Attainment: any s coordinates with weight 1/s each attain this minimum.
- Lemma 4: the Frank–Wolfe dual gap is at least 2/s **only when s<n**.
- Theorem 1 with an exact oracle: the actual iteration gap is at most 8/(k+2)
  for k≥1. This upper bound and the support lower bound are different statements.

The page explains Lemma 3 by the elementary identity

    sum_active (x_i - 1/s)^2 = sum_i x_i^2 - 1/s >= 0.

This is an equivalent explanation of the published result; Appendix C itself
uses an induction. Equal weights make every term zero. The result is sharp
over vectors with a support constraint, regardless of which algorithm produced
the vector. It does **not** claim FW reaches the floor at each update or provide
an exact worst-case iteration constant for FW.

For the dual gap, g(x)=2(sum_i x_i²−min_i x_i). When s<n, a missing coordinate
implies min_i x_i=0, giving the lower bound. At full support this step is invalid:
the uniform optimum has g=0. Both the JSON field and plotted lower curve therefore
omit that bound at s=n; null is not converted into a replacement zero.

## Actual updates and comparison vectors

The existing `methods.frank_wolfe` runs unchanged. A private specialization of the
existing simplex problem supplies f=||x||² and gradient 2x, while reusing its
linear oracle. At each update, the first minimum gradient coordinate selects
a basis vector, then x_next=(1−γ_k)x+γ_k e_j with γ_k=2/(k+2).

The starting atom is replaced at γ₀=1: x₀=e₁, x₁=e₂. Both have support one.
Thereafter at most one new coordinate is added per update. An iteration count is
not a support count. No early stopping or tiny-coordinate truncation is used.

Every row includes the complete actual vector, gradient, oracle, support count,
step, objective, primal gap, dual gap, applicable bounds and equal weights on
the **same actual active coordinates**. The latter is an analytical comparison,
not another optimization algorithm. Its excess is computed stably as the sum of
squared deviations from those equal weights. A separate construction list retains
every s=1,…,n with uniform weights on the first s coordinates.

Primal gap uses ||x−x*||² to avoid subtracting nearly equal totals. Dual gap uses
2 sum_i x_i(x_i−min_j x_j), equivalent to the displayed formula on the unit simplex
and exactly zero at equal full-support weights. Neither quantity is clipped to
hide a negative calculation. Feasibility is checked before returning a report.
Inputs have canonical sorted-JSON SHA-256 fingerprints; Python, NumPy and package
versions are retained. The numerical and mathematical objects remain distinct.

## How to read the views

The common player chooses a dimension and actual iteration. Blue bars are actual
weights; green bars are equal weights on the same active coordinates. Within a
frame both panels have the same y scale, 1.15 times the largest actual weight.
The scale changes between frames and is labelled. All coordinates are included.

For n=3, the triangular feasible domain is drawn in an oblique objective surface.
With u=x₁+x₂/2 and v=√3 x₂/2 (zero-based array indices), the screen mapping is
(120+360u−70v, 360−120v−190f). Height is f itself, with minimum 1/3; it is not
a gap. Chords join computed iterates and need not lie on the surface between
endpoints. The green point is the comparison vector, with no invented trajectory.
Higher-dimensional cases show their complete weight vectors instead of a 3D
projection that would conceal most coordinates.

The objective/support scatter retains every iteration, including repeated support
counts and coincident observations. The 1/s curve includes all support budgets.
The iteration chart separates primal gap, its support floor and the source upper
bound. The dual chart ends its lower curve when support becomes full. Log plots
do not replace zeros by artificial positive values; native tables and JSON retain
the exact values. Without JavaScript all four cases, curves and tables remain
available, with the bars and geometry at k=min(2,budget).

## Verification

Tests compare all four 40-step trajectories against exact rational recurrences,
verify the curvature with a rational vertex-segment calculation, check every
attaining support vector, distinguish initial/replaced atoms, and reject invalid
budgets or incompatible CLI options. The independent standard-library validator
`scripts/smoke_fw_sparsity.py` also exercises the maximum 256-step budget and
checks every coordinate, metric, bound, input hash and construction with
rtol=2e−10 and atol=2e−12. Corruption tests cover invented bounds, missing
construction points, wrong scaling, vectors and hashes.

The installed-distribution workflow runs the full default and matches HTML to
JSON; release verification requires its evidence. The browser check verifies all
164 default states at each of two widths, every weight bar and 3D point, all
curve/scatter samples, the full-support boundary, keyboard/playback, language,
downloads and no-script reading. A configured check is not a remote CI result;
new commit CI and clean-install results must be verified after publication.
