# Same condition number, different CG spectra

```bash
python -m chainbench case-study cg-spectrum --lang ko --output cg-spectrum.html
python -m chainbench case-study cg-spectrum --format json --output cg-spectrum.json
```

This standalone development study extends the two-dimensional published-example
[spectral explanation](CG_SPECTRAL_EXPLANATION.md) to 18 declared inputs. It is
included in the [pinned review snapshot](REVIEW_GUIDE.md);
[PR #73](https://github.com/chocoemong17/chainbench/pull/73) links actual remote CI. It is
also available through `tour --extended`, which links it to the published 2×2
example and the CG lesson. The base 17-page tour keeps its existing scope.

## Source and exact scope

[Shewchuk (1994)](https://www.cs.cmu.edu/~quake-papers/painless-conjugate-gradient.pdf)
§9.1, printed pp.33–35 / PDF pages 39–41, Eq. (50) and Figure 31 explain
CG through error polynomials. Section 9.2, printed p.36 / PDF page 42,
Eqs. (51)–(52) and Figure 33 give the Chebyshev interval comparison.
Figure 31(d) does not specify its clustered input values. These newly declared
matrices illustrate that reasoning; they do not reproduce the figure's data.
No paper PDF or third-party implementation is distributed.

## All 18 inputs

Each problem is `f(x)=xᵀAx/2`, with `b=0`, `x*=0`, dimension 16 and
`||x0||₂=1`. All cases use the declared interval `[2,7]` and condition number 3.5.
The full Cartesian product is retained, without outcome filtering:

| Choice | Values |
| --- | --- |
| Spectrum | Eight copies each of 2 and 7; eight equally spaced values in each of `[2,2.1]` and `[6.9,7]`; sixteen equally spaced values in `[2,7]` |
| Basis U | Identity; normalized Sylvester Hadamard matrix of order 16, entries ±1/4 |
| Initial coefficients | Normalized all-ones; normalized `1/sqrt(λ_i)`; first coordinate vector |

Construct `A=U diag(λ) Uᵀ` and `x0=Uc`. Equal coefficients give more initial
energy to large eigenvalues; equal-energy coefficients equalize `λ_i c_i²`.
A single-mode start has only eigenvalue 2 initially active. The Hadamard basis
changes the coordinates without changing the exact spectral problem.

The stored `A` is the actual rounded matrix accepted by the quadratic problem.
Its measured extreme eigenvalues, `AU−Udiag(λ)` residual and `UᵀU−I` residual
are retained. Construction modes need not be perfect eigenvectors of the rounded
matrix. SHA-256 covers little-endian float64 row-major `A`, then `b`, then `x0`.
No random inputs or hidden seeds are used.

## Recurrence, stop and measured quantities

The existing scaled correction-equation `conjugate_gradient` implementation runs
with `rtol=1e-12`, `atol=0`. The criterion uses the recomputed **true** residual
relative to the initial residual, not `||b||` (which is zero here). The default
budget is 32, with integer budgets 1–64 supported. A stopped run is not padded.
Exact-arithmetic termination at the number of distinct active eigenvalues does
not certify a floating-point stopping count.

Every actual iterate stores `x`, `c=Uᵀx`, the true residual, direct energy `xᵀAx`,
spectral energy `sum λ_i c_i²`, their raw difference and both normalized energy
norms. The overview metric is `sqrt(xᵀAx/(x0ᵀAx0))`; it is not the objective gap
or its square. Small nonzero errors and exact zeros are retained as calculated.

For the declared inputs, the default run reaches the residual tolerance in
2 / 12 / 16 updates for two values / two clusters / spread with both full-mode
profiles and both bases. The single-mode starts finish in one update. These
finite observations are neither representative performance estimates nor a
universal ordering of spectra.

## Reading the mode panels

The signed dots are actual `c_i(k)/c_i(0)` values at the declared eigenvalues.
Repeated modes can overlap. If `c_i(0)=0` the ratio is `null`, rather than a
division by an arbitrary floor. All sixteen energy bars remain present:

    bar_i(k) = λ_i c_i(k)² / sum_j λ_j c_j(0)²

Their sum's square root equals the reconstructed spectral energy ratio.
Axes stay fixed across the recorded stages of each case; near-roundoff values
remain available in tables even when too small to see. Direct matrix energy and
mode reconstruction are displayed separately, including their raw difference.

The grey continuous curve is the source comparison polynomial

    P_k(λ) = T_k((9−2λ)/5) / T_k(9/5).

It is not a fitted actual CG polynomial, nor a pointwise bound on each signed
mode ratio. Its maximum magnitude on `[2,7]` is `1/T_k(9/5)`. In exact arithmetic,
the optimal CG energy norm is at most this interval envelope. The looser
`2*((sqrt(3.5)−1)/(sqrt(3.5)+1))^k` envelope is also retained in JSON.
Neither envelope is presented as a rigorous certificate of the rounded run.

## A separate degree-2 witness

Choose roots `a,b` at the means of the first eight and last eight sorted
eigenvalues, independently of outcomes. The displayed polynomial is
`p(λ)=(1−λ/a)(1−λ/b)`. Its energy-weighted factor is

    sqrt(sum_i λ_i c_i(0)² p(λ_i)² / sum_i λ_i c_i(0)²).

In exact arithmetic the relative CG A-error at **k=2** is no larger than this
factor. The report also gives the maximum over all declared modes and over
initially active modes. It does not claim the witness is optimal or equals the
CG polynomial. This panel has fixed degree 2 and stays separate from the stage
selector. If the run stopped at k=1 or the budget was one, no k=2 observation
is invented.

## Validation and offline behavior

`scripts/smoke_cg_spectrum.py` imports neither ChainBench nor NumPy. It rebuilds
the inputs with scalar sums and closed-form Walsh entries, audits every iterate
with 60-digit Decimal **unscaled** CG, recomputes the mode/energy/residual
identities and checks stopping. Comparison polynomials use independent cosine
and hyperbolic-cosine formulas. Absolute tolerance `1e-14` covers cancellation
in coordinates; positive magnitudes use relative `2e-12` and absolute `1e-300`.
Stored exact identities, hashes, coverage and metadata are checked separately.
Missing evidence, fabricated zeros, non-finite values and changed polynomials
are covered by failure-injection tests.

The browser checker triggers real controls and independently checks every
displayed ratio point, energy bar and reference curve at desktop/mobile widths.
It also checks keyboard navigation, JSON downloads, offline operation and
native HTML without JavaScript. Each case and every actual stage remains in
the HTML. No browser-side optimizer or external resource is required.

Installed-wheel and installed-sdist workflows execute budgets 1, 32 and 64 and
compare the HTML record with independently validated JSON. The release consumer
requires their `cg_spectrum: matched` result. A locally built archive or execution
with an existing environment is not evidence of a clean installation.
