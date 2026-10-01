# Randomized Kaczmarz: an attained expectation bound

Development source after v0.5.0:

```sh
chainbench case-study kaczmarz-expectation --lang ko --output kaczmarz.html
chainbench case-study kaczmarz-expectation --steps 160 --trials 128 --format json
```

This is a separate public construction, not a ninth fixed-suite check, a
performance ranking or a reproduction of a source-paper dataset.

## Source and indexing

Thomas Strohmer and Roman Vershynin, *A Randomized Kaczmarz Algorithm with
Exponential Convergence*, JFAA 15, 262–278 (2009),
[DOI](https://doi.org/10.1007/s00041-008-9030-4).
Exact locations below use the public
[arXiv:math/0702226v1](https://arxiv.org/pdf/math/0702226v1), dated 8 February 2007,
21 PDF pages. They are not journal page numbers. The publisher records online
publication in 2008 and the issue in 2009.

- Algorithm 1, Eq. (4), printed/PDF p.4: sample row i with probability
  `||a_i||²/||A||F²`, independently with replacement, then
  `x[k+1] = x[k] + (b_i-a_i·x[k])/||a_i||² * a_i`.
- Theorem 2, Eq. (5), same page: for a consistent full column rank system,
  `E||x[k]-x*||² <= (1-1/κ_scaled²)^k ||x[0]-x*||²`,
  where `κ_scaled=||A||F/σ_min(A)`. One iteration means one row projection.
- Section 3.2, printed/PDF p.9, gives equality constructions. Its final display
  prints `x_0` as the left-hand reference. At k=0 that cannot equal its right
  side for the stated nonzero start. We use error to the solution `x=0`, as
  specified by Theorem 2 and the construction immediately preceding the display.
  No assertion is made about whether the journal version corrected that typo.

The inspected preprint PDF SHA-256 is
`4ff4019ffa54f1d3571c95936c5375117c2036a92b67c66bfc8d0776d5a9a156`.
The repository contains independent code and citations, not the paper PDF or
copied figures/code.

## Six explicit members of the published family

Rows are unit coordinate vectors, ordered in contiguous blocks e1, e2, ….
Thus each *row* has probability 1/m, whereas the probability of a *direction*
is its multiplicity divided by m. All systems use b=0 and x*=0.

| ID | Direction multiplicities | Initial point | Exact E||x[k]||² |
|---|---|---|---|
| cube | [1,1,1] | (1,1,1) | 3(2/3)^k |
| half | [1,1] | e1 | (1/2)^k |
| one-in-eight | [1,7] | e1 | (7/8)^k |
| one-in-thirty-two | [1,31] | e1 | (31/32)^k |
| three-directions | [2,5,5] | e1 | (5/6)^k |
| eight-directions | [2,9,9,9,9,9,9,8] | e1 | (31/32)^k |

The cube uses §3.2's condition-number-one case: each coordinate survives until
first selected, with probability (2/3)^k. Linearity of expectation sums its
three squared coordinates; it does not assume coordinate survival events are
independent. The other cases use §3.2's repeated-basis construction with
r=min(multiplicities) rows e1 and at least r copies of every other direction.
The iterate stays at e1 until an e1 row is drawn, then remains at zero.
The survival probability is (1-r/m)^k, exactly the theorem upper bound because
`κ_scaled²=m/r`. The distinct spectral condition number has square
`max(multiplicities)/r`. The dimensions and seeds here are declared additions.

## Reproducible finite observations

Default: 40 updates, 64 trials, seeds 0…63. Allowed budgets: 1…160 updates and
1…128 trials. Each run uses `Generator(PCG64(seed)).choice(m, size=steps,
replace=True, p=row_probabilities)`. The same seeds are reused across cases;
results from different cases must not be pooled as independent trials.
The record includes Python/NumPy/package versions. Mathematical independence
in the theorem is modeled by this declared pseudorandom stream.

Every row index and every full iterate is retained, including repeated points
and all steps after zero. Unit basis rows and these starting points make the
coordinates exactly representable 0/1 values. `first_zero=null` means the trial
has not reached zero within the budget; it is not failure or missing evidence.
The batch mean includes all declared seeds, including unresolved trials.
No trial is filtered or retried, and no empirical mean is required to lie below
the expectation curve. Even a single valid trial can stay strictly above it.

## What the visuals mean

The cube is an orthographic projection of actual x1, x2, x3 coordinates, not an
objective-height plot. The initial yaw is 35 degrees and elevation is 25 degrees;
the yaw control rotates the camera only. Each cube edge has coordinate length 1.
The colored plane is the selected constraint x_j=0. Gray/orange points are the
previous/current iterate; orange segments join actual updates. At k=0 no row
or plane is selected. The other five cases use their exact two-state diagram;
their complete vectors remain in the readout, native tables and JSON.

Every seed appears in the linear-axis squared-error chart; exact zero stays zero.
Gray lines show all trials, orange the selected trial, blue the finite batch
mean and green dashed the exact expectation. The expectation equals the theorem
upper bound on these inputs; the selected run and sample mean need not.
Displayed lines connect integer iteration samples, not intermediate iterations.
Without JavaScript, all six initial diagrams, curves and full seed tables remain
available. The embedded JSON and download retain unrounded inputs and numbers.

## Validation and limits

Tests enumerate complete small probability trees, verify the singular-value
constants, reproduce the declared random stream via an independent inverse CDF,
check every point with the finite-state recurrence and preserve trial/budget
prefixes. The installed-artifact validator imports no package computation: it
reconstructs the coordinate hits and exact rational survival probabilities,
checks hashes/means/histograms, and rejects deliberately corrupted records.
Expectation comparisons allow relative error 3e-14 and absolute error 1e-30;
row indices and 0/1 coordinates are exact comparisons. These tolerances cover
floating exponentiation, not deviations of the finite sample mean.

The browser check exercises all cases/seeds/iterations at desktop and mobile
widths, camera rotation, native tables, language, playback, offline download and
JavaScript-disabled access. New CI steps and both installation checks are wired;
remote results are pending authenticated PR publication. Executing built wheel
and sdist code in an existing runtime is not a clean-install claim.

## Development: the conditional step in the proof

The same runs now expose Theorem 2's proof on preprint pp.5–6: Eqs. (8)–(9)
and the orthogonal-projection/Pythagorean argument. For a fixed previous point,
let `d=previous-next` and `e=next-x*`. Consistency puts the solution in the
selected hyperplane, so `e·d=0` and

```text
||previous-x*||² = ||e||² + ||d||²
E(||d||² | previous) = ||A previous-b||² / ||A||F²
E(||next-x*||² | previous)
  <= (1-σ_min(A)²/||A||F²) ||previous-x*||².
```

This connects projection geometry to the weighted sampling rule. The source
then takes full expectations and iterates the inequality. The conditional mean
averages over every possible next row with the previous point fixed; it is not
the finite-trial mean at a given time. On these six source constructions the
conditional upper bound is also attained in exact arithmetic.

`conditional_projection` adds a finite candidate table for each distinct actual
recorded point. It retains every individual row probability, candidate next point,
remaining/removed error vector, squared norm, inner product and identity residual.
The direction grouping is only a display aggregation of repeated basis rows;
the raw row-level outcomes remain in native tables and JSON. Candidate points are
hypothetical choices and are never inserted into any sampled history. Existing
inputs, seeds, draws, iterates, error curves and summaries are unchanged.

At completed update k>=1, the panel fixes `x[k-1]`, highlights the row actually
used in that update, and connects the triangle to `x[k]`. At k=0 it enumerates
initial possibilities with no selected row and no completed triangle. At the
last recorded update it explains that update; it invents no subsequent draw.

The triangle uses orthogonal error coordinates: horizontal removed-error length,
vertical remaining-error length, and equal pixel units in both directions.
It is a rotated error-vector representation, not the original x1/x2/x3 coordinate
picture (which remains above). Pixel scale is fixed within each case at
`215/sqrt(initial_squared_error)`. If either leg is zero, the triangle degenerates
and no right-angle mark is drawn. If input error is zero, the conditional ratio
is null rather than a fabricated 0/0 value. Computed identity residuals are
retained, including any floating summation roundoff.

The independent validator reconstructs each candidate by its coordinate hit and
uses exact rational probabilities for conditional means and constants. It checks
every stored vector, grouping and null denominator. The browser additionally
checks candidate heights, selected directions, triangle lengths and degenerate
states for every seed and iteration. Older schema-1 records without the optional
explanation remain readable; current installed exports are required to include it.
