# Inspect every stress sample

The development source after v0.5.0 adds full case inspection to all eight stress
topics. It also corrects two misleading edge cases: an ISTA/FISTA denominator at
the comparison floor is no longer exported as a zero ratio, and a zero-radius
FISTA sample is no longer silently replaced with a different seed.

```bash
python -m chainbench stress nesterov-1983 --trials 16 --seed 0 --lang ko --output stress.html
python -m chainbench stress ista-vs-fista --trials 16 --seed 16 --lang ko --output paired.html
python -m chainbench stress-case ista-vs-fista --seed 24 --lang ko --output case.html
python -m chainbench stress-case ista-vs-fista --seed 24 --format json --output case.json
```

Ranked cards and every table row link to a real sample: its convergence curve,
method parameters, complete iterate table, actual generated inputs, measurement
rule and input hash. The standalone `stress-case` command reruns exactly that seed
under the same versioned sampler. It does not rerun the entire distribution.
Both commands default to HTML, support JSON, and protect existing output with `--force`.
The eight fixed literature checks are unchanged.

## Declared sampler v2

The sampler is `stratified-pcg64-v2`. Seeds must be integers in [0, 2^63−1]; a batch
uses consecutive seeds and rejects a range overflowing that limit. Batch size is
2–64 (default 24). Each seed initializes NumPy PCG64 independently.

| Choice | Declared rule |
| --- | --- |
| Dimension | `(6,12,24,40)[seed % 4]` |
| Quadratic orientation | `(seed // 4) % 2`: diagonal or three seeded Householder reflections |
| Initial point | `(seed // 8) % 2`: zero or uniform [-1,1] coordinates; simplex uses e1 or a normalized positive draw |
| Smooth quadratic spectra | L is log-uniform over [10^−0.35,10^0.35]; kappa=10^5; sorted log-uniform interior eigenvalues |
| Strong quadratic spectra | Same L range; kappa log-uniform over [10^0.5,10^3]; sorted log-uniform interior eigenvalues |
| Quadratic reference | Coordinates uniform in [-1,1]; b=Q x* |
| Diagonal LASSO | a uniform [0.4,2], b uniform [-1.6,1.6], lambda log-uniform [10^−2,10^−0.25] |
| Simplex target | Uniform positive coordinates [0.05,1], then normalize |
| Proximal parameter | c log-uniform [10^−0.6,10^0.6] |

Any 16 consecutive seeds cover the 4×2×2 dimension/orientation/start strata for
quadratics. Smaller batches may cover only a subset; the table always shows what
was actually run. LASSO deliberately stays diagonal, and the simplex has no rotation
stratum. Smooth-convex topics retain one condition number while varying their
interior spectra, scales, orientations and starting points. This is a declared
synthetic design, not a claim to cover every dimension or condition number.

## Measurement contracts

The recurrence and source locations are unchanged from [SOURCE_MAP.md](SOURCE_MAP.md).
In particular, `nesterov-1983` is the historical CLI name for **smooth fixed-L FISTA**,
and proximal point uses the exact quadratic specialization.

| Topic | Actual measurement | Budget / qualifications |
| --- | --- | --- |
| gd-baseline | max gap / [L R²/(2k)], k≥1 | 40 updates; R=||x0−x*|| |
| nesterov-1983 | max gap / [2L R²/(k+1)²], k≥1 | 40 updates; same actual initial radius |
| beck-teboulle-2009 | max composite gap / [2L R²/(k+1)²], k≥1 | 50 updates; known diagonal-LASSO optimum |
| jaggi-2013 | max primal gap / [2 C_f/(k+2)], k≥1 | 40 updates; C_f=2, feasible start, exact oracle |
| hestenes-stiefel-1952 | max energy error / [2 rho^k initial energy], computed k≥1 | min(20,n) budget; true-residual rtol=10^−12, atol=0; no padded iterates |
| polyak-1964 | relative difference between rho and median of up to last 20 valid consecutive error ratios | 180 updates; previous error>10^−10; 8% is an empirical tolerance |
| rockafellar-1976 | max consecutive error ratio / [1/(1+c mu)] | 24 updates; previous error>10^−12 |
| ista-vs-fista | final FISTA gap / final ISTA gap | 50 updates each; INFO-only, no threshold |

The plot under each sample displays the quantities used by that measurement. Gaps
are tied to actual iterates and known reference solutions. The ratio index lists and
excluded floor indices are retained. Curves do not fit or prove an asymptotic rate.
For theorem-linked topics the project uses normalized threshold 1 plus 10^−10
tolerance; heavy-ball retains its explicitly empirical 0.08 tolerance.

## Unresolved means unresolved

- If the ISTA final gap is at or below 10^−28, the ratio is `null`, even if the FISTA
  gap is also zero. The record retains both gaps, all iterates, the floor and a reason.
- If the initial radius yields a zero theoretical envelope, or no eligible error
  ratios remain, the corresponding normalized metric is also `null`.
- Such a row has `status: "unresolved"`. It is retained under its original seed.
  It is never counted as within-threshold or resampled until it looks measurable.
- Nonfinite or negative measurements are errors. They are not recoded as unresolved
  samples to make an invalid run appear usable.

Under the local tested environment, ISTA/FISTA seed 24 exercises the denominator
floor. Seed 20 in the displayed 16–31 batch has a final FISTA gap larger than ISTA's;
both absolute convergence curves are available. Equal iteration counts do not imply
equal work, and a ratio near numerical precision is not a runtime ranking.

## Quantiles and selected actual cases

All aggregates explicitly report total, measured and unresolved counts. Threshold
topics additionally report within- and above-threshold counts. Numerical summaries
use measured samples only; an entirely unresolved batch has `null` min/median/p90/max
and no ranked cards, rather than a vacuous successful result.

The median and p90 summary values use NumPy's linearly interpolated quantiles. The
cards choose **actual observations** at nearest ranks `ceil(q*n)` for q=0.5,0.9,1
among measured rows sorted by metric then seed. Therefore a card's observed value
may differ from the interpolated summary. Every unselected sample is still visible.
“Maximum observed” means the largest sampled measurement, not a certified worst case.

## Schema and reproducibility

Stress JSON is now `schema_version: 2`, and includes sampler/version/environment,
source assumptions, complete inputs and trajectories. `stress-case` returns a
`chainbench.stress-case` wrapper with the same case object as the matching batch row.
The same seed **does not preserve the old v0.5.0 input** after changing the sampler.
To reproduce a historical schema-1 run, use its historical release/environment;
do not compare seed numbers alone across sampler versions.

`instance_sha256` covers sorted named numeric arrays: matrix/reference or diagonal
LASSO/simplex inputs, x0, update budget, and c where applicable. Each array encodes
ASCII name+NUL, compact JSON shape+NUL, then little-endian float64 bytes in C order.
Method identity is stored separately in topic/runs. The actual stored arrays are
the provenance record; BLAS/eigensolver rounding can change bytes across platforms.
The ordinary schema-1 `experiment`/`replay` interface is separate and unchanged;
`replay` is not a loader for these stress reports.

## Checks and scope

Tests independently reconstruct gaps, certificates, normalization, input hashes,
stratum coverage, rank selection and single-case identity. Explicit degenerate
fixtures prevent silent resampling and fabricated zero ratios. Clean wheel and sdist
checks execute the new command and validate ordinary and unresolved output.
Offline browser checks open every sample and ranked link, save exact JSON, exercise
Korean/English switching and inspect 1440px/390px and no-JavaScript layouts.

This broadens finite evidence within three synthetic families. It is not an
original-paper dataset benchmark, a representative real-world sample, a proof,
an arbitrary worst-case search or an adoption measure.
