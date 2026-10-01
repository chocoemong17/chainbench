# CG arithmetic and repeated calculations

The development CG implementation retains its scaled correction recurrence,
initial-residual stopping rule and NumPy matrix-vector products. Its three scalar
inner-product sites (initial residual square, search-direction curvature and
updated residual square) accumulate the float64 products with
[`math.fsum`](https://docs.python.org/3/library/math.html#math.fsum).
This improves summation accuracy and removes the observed dependence of these
reductions on the native BLAS path. It does not use arbitrary precision or change
the literature envelope. Products are still rounded float64 multiplications.

## Observed failure and controlled diagnosis

The [Intel macOS job](https://github.com/chocoemong17/chainbench/actions/runs/36891895555/job/110469887536)
passed 1,315 tests and failed three independent CG rerun comparisons at the strict
relative 1e-12 / absolute 1e-14 comparison tolerance. Those first mismatches were
small, but a complete audit revealed larger later discrepancies. Increasing the
comparison tolerance would have hidden them.

The [baseline audit](https://github.com/chocoemong17/chainbench/actions/runs/36896154426)
used Intel macOS 26, Python 3.12.10 and NumPy 2.5.3 linked to Accelerate.
For each of eight stress topics it compared every stored floating value in
seeds 0–31 across three repeated batches and individual-case reruns. It also
compared each canonical/normalized chart across ten reruns. Exact input/config,
hash, type, count and status fields were checked separately.

- Native CG seed 7 differed by about 3.22e-4 at update 20, coordinate 39.
- The single-thread trial still differed by about 4.32e-4 for seed 19 at that
  coordinate/update. Thread limits did not resolve the problem.
- Neither environment changed exact input/provenance fields or produced nonfinite
  values. Other topics stayed within the existing strict comparison tolerance.

The [controlled replacement audit](https://github.com/chocoemong17/chainbench/actions/runs/36896839745)
compared compensated scalar products alone with compensated scalar and
matrix-vector products. Both preserved the original true-residual calculation.
Both had zero discrepancies beyond the unchanged comparison tolerance across the
same declared grid, and their focused CG/recurrence/scaling regressions passed.
This implicates scalar accumulation in the observed drift; it does not establish
a general defect in Accelerate or a bound for arbitrary inputs.

The production change adopts only the scalar-product replacement. Matrix-vector
multiplication remains on the original path. The
[diagnostic source](https://github.com/chocoemong17/chainbench/tree/332a9c8b8f1b8be26e7adb02e5dcb4932a87f8df)
is a separate investigation branch, not an additional runtime dependency or a
replacement for the full PR validation matrix.

## Preserved contracts and limits

- The recurrence, normalization, budgets, initial points and theorem thresholds
  stay the same. Recomputed true residuals still control stopping.
- An initial point with `b - Q @ x0 == 0` still returns immediately. Substituting
  a differently accumulated residual there would change that API contract.
- Nonfinite products or sums raise `FloatingPointError`.
- Tests retain the strict independent-rerun comparison and exact provenance.
  New checks retain a unit between cancelling large terms at multiple allocation
  offsets, reject nonfinite arithmetic, repeat the observed seeds, and preserve a
  cancellation-sensitive exact start.
- Finite CG trajectories can change from earlier development/release builds.
  Archive/source commits identify which arithmetic generated each result.
  Cross-platform bitwise equality, exact n-step termination and a production
  performance guarantee are not claimed.

The compensated reduction adds work to the small dense educational solver.
No iteration count is presented as an equal-cost comparison with other methods.
The public [source mapping](SOURCE_MAP.md#conjugate-gradient) and existing
independent numerical validators remain authoritative for the checked result.
