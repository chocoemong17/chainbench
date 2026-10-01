# Nonuniform sampling: a declared-input protocol rerun

```bash
python -m chainbench reproduce kaczmarz-sampling --lang ko --output sampling.html
python -m chainbench reproduce kaczmarz-sampling --format json --output sampling.json
python -m chainbench reproduce kaczmarz-sampling --steps 100 --output preview.html
```

This development workflow follows Strohmer–Vershynin, *A randomized Kaczmarz
algorithm with exponential convergence*, [arXiv:math/0702226v1](https://arxiv.org/pdf/math/0702226v1),
Section 4.1: Eq. (18), p.10; experimental setup and Theorem 4, p.11;
Figure 1, p.12. The preprint is from 2007; the journal publication is from
2009, [DOI 10.1007/s00041-008-9030-4](https://doi.org/10.1007/s00041-008-9030-4).
The source PDF used to check those locations has SHA-256
`4ff4019ffa54f1d3571c95936c5375117c2036a92b67c66bfc8d0776d5a9a156`.

The source uses a degree-50 trigonometric polynomial, 700 uniformly distributed
sample nodes and three choices of row order. Its plotted budget reaches 15,000
projections. It does not provide the exact nodes, signal coefficients, initial
point or random stream. This command therefore reruns the published protocol
with fully declared new inputs; it does not recover the original figure's pixels
or numerical endpoints. It is separate from the finite-state
[expected-error construction](KACZMARZ_EXPECTATION.md).

## Inputs and recurrence

For sorted nodes `t_j` in `[0,1)`, extend the neighboring nodes periodically
across the endpoints and set `w_j=(t_next-t_previous)/2`. For frequencies
`k=-50,...,50`, the weighted matrix and data are

    A[j,k] = sqrt(w_j) exp(2π i k t_j)
    b[j]   = sqrt(w_j) f(t_j).

With `v_j` the unweighted Fourier row, the complex orthogonal projection is

    x_next = x + (f(t_j) - v_j x) conj(v_j) / ||v_j||².

The denominator is recomputed from the row (mathematically 101). The positive
weight cancels from this projection, so all three methods use the same update:
cyclic ascending row order, uniformly random rows, or probabilities
`p_j=w_j/sum(w)`. The paragraph in §4.1 says row norm; Algorithm 1 and Eq. (18)
resolve the intended rule as **squared** weighted-row norm `101*w_j`.

All methods start from zero. All three seeds 0, 1 and 2 remain in the report.
NumPy `Generator(PCG64(SeedSequence([seed, stream])))` uses separate streams:

- Stream 0: 700 uniform nodes, sorted in ascending order.
- Stream 1: a standard normal DC coefficient, 50 positive-frequency complex
  coefficients `(normal + i*normal)/sqrt(2)`, and conjugate-reflected negative
  coefficients. The coefficient vector is normalized to unit L2 norm.
- Stream 2: uniform draws shared by the two random methods within this case.
  Uniform sampling uses `floor(700*u)`, and weighted sampling uses inverse CDF
  with `side='right'` and the last CDF endpoint set to 1.

The signals are real in exact arithmetic. Both real and imaginary values remain
in the export. Sharing the uniform draws is an explicit coupling choice, not an
expectation estimator. All 15,000 updates run even after reaching roundoff.
`--steps` accepts 1 through 15,000; reduced budgets are labelled previews.

## What the pictures measure

The curve is **coefficient L2 error**, as in Figure 1, rather than squared error
or weighted data residual. It retains every completed projection, including zero.
No smoothing, resampling, endpoint matching or noise floor substitution is used.
Each curve is a single run. Three chosen instances do not establish a general
ranking; tiny differences near roundoff have no speed interpretation.

Waveforms connect 513 actual display samples of the reference and reconstructed
signal. They show real parts, with one vertical scale shared by all methods and
snapshots within a case. The highlighted observation is the row just projected
onto; it is absent at k=0. A separate plot shows all 700 selection probabilities
at their actual node positions. The native gallery and complete node/count table
remain readable without JavaScript. Counts cover the full budget rather than
the selected snapshot. These high-dimensional signals are displayed as functions;
no arbitrary 3D projection is presented as the coefficient geometry.

## A sufficient condition is not a necessary one

Theorem 4 assumes maximum periodic gap `δ < 1/(2r)=0.01` and gives the spectral
condition bound `(1+2rδ)/(1-2rδ)`. This is checked separately from the actual SVD.
The first declared seed fails this sufficient condition, so its theoretical
upper bound stays `null`; the case remains visible and still runs normally.
Seeds 1 and 2 satisfy it. None meets the stronger `δ<=1/(4r)=0.005` condition
that would give an upper bound of 3. An actual condition number below 3 does
not make that sufficient hypothesis true.

The record also stores scaled condition squared `||A||_F²/σ_min²`; this differs
from the spectral condition number `σ_max/σ_min` used in Theorem 4.

## Numerical evidence

### One observation changes the whole bandlimited waveform

An optional projection explanation retains the actual coefficient vector just
before each noninitial snapshot, its rounded difference from the next vector,
and the corresponding waveforms. It does not reconstruct the prior state by
reversing a rounded update. The initial point has no completed projection.

For `n=2r+1=101`, the source's finite Fourier basis and row projection imply

    K_r(u) = (1/n) sum[q=-r..r] exp(2π i q u)
    ideal Δf(t) = (f(t_j) - v_j x) n/||v_j||² K_r(t-t_j).

This is a derived explanation, not another figure or experiment reported in the
paper. `K_r` is the normalized Dirichlet kernel; for periodic distance
`u=((t-t_j+0.5) mod 1)-0.5` it is evaluated stably as
`sinc(n*u)/sinc(u)`, where NumPy's sinc is `sin(πu)/(πu)`. At the selected node
the removable limit is exactly 1. The response grid adds that actual node to the
513 display samples, so the center is explicitly represented.

The three linked panels show the actual previous/next waveforms, the unit kernel,
and the actual real signal correction versus the exact-arithmetic prediction.
Previous/next waveforms share the main plot's case-wide scale, including every
retained prior state. The unit kernel always uses `[-0.3,1.1]`. The correction
axis rescales for each selection and prints its absolute range; its apparent
height cannot compare step sizes. An exactly zero real correction uses an
explicit zero label and a display range of ±1 rather than dividing by zero.
Real and imaginary values both remain in JSON.

The actual correction is `E*(x_next-x_previous)`, where `E` evaluates the
Fourier series on the retained grid. It need not equal either the ideal kernel
prediction or `E*x_next-E*x_previous` bit for bit. Both raw maximum differences
are shown, especially near the floating-point floor. Blue is an analytical
comparison, not another solver's trajectory. A first-projection shortcut helps
inspect the mechanism before the updates become tiny. Every stage is a native
expandable block without JavaScript; older records lacking the explanation still
render and validate. Installed evidence requires the new extension.

### Replaying and validating the retained data

Inputs, RNG draws, every selected row, all norm and squared-norm errors, and
snapshots at `0,1,10,100,1000,5000,10000,15000` (within the budget, plus its endpoint)
are retained. Snapshots include all 101 complex coefficients, 513 complex signal
values, weighted residual and the last projection's before/after values. Hashes
use row-major little-endian float64 or complex128, with real/imaginary values
interleaved for complex arrays. Python and NumPy versions are recorded.

`scripts/smoke_nonuniform.py` imports no ChainBench implementation. It constructs
the operator using separate sine/cosine arrays and replays each projection using
real/imaginary scalar-vector formulas. It checks periodic weights, random inputs,
all row choices, errors, snapshots, feasibility of the last projected observation,
conditioning and hashes. Comparisons use `rtol=2e-9, atol=2e-12` for independent
trigonometric evaluation and accumulated floating-point arithmetic. This tolerance
does not turn sub-tolerance endpoints into matching historical paper results.
Hand-calculated complex projection and periodic-boundary tests, deliberately
corrupted records, CLI exports and SVG-to-record checks cover different failure
modes. Both package formats exercise budgets 1, 13 and the default 15,000.

For the projection extension, the validator compares prior states to its own
recurrence and evaluates the response with independent sine/cosine arrays and
a finite cosine sum rather than the producer's sinc quotient. It verifies that
the retained coefficient correction is the actual subtraction, that the selected
node is included, and that the raw floating-point diagnostics follow the stored
arrays. Diagnostic recomputation uses absolute tolerance `3e-30` with the same
relative tolerance, rather than flooring small differences to zero. Tests cover
the three-frequency hand formula, integer periodicity, the removable center,
zero residual, legacy evidence, deliberate corruption and all SVG curve points.

The eight fixed checks, existing outputs and pinned public review evidence are
unchanged. This development addition requires its own remote PR/CI and isolated
package-install evidence before being treated as a published verified snapshot.
