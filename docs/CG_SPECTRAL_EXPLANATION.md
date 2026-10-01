# Source polynomials and actual CG errors

The development `reproduce shewchuk-1994` page now links its existing paths to
the polynomial argument in Shewchuk (1994), Sections 9.1–9.2. The published
2×2 matrix, both algorithms, all ten starts, budgets and stopping rules are
unchanged. This addition follows `feat/extended-tour`; remote PR/CI evidence is
pending authentication. It is newer than the review guide's pinned snapshot.

```sh
python -m chainbench reproduce shewchuk-1994 --lang ko --output paper.html
python -m chainbench reproduce shewchuk-1994 --format json --output paper.json
```

## Source and scope

[Primary PDF](https://www.cs.cmu.edu/~quake-papers/painless-conjugate-gradient.pdf),
edition 1¼, August 4, 1994; SHA-256
`368110e5592d0d3e0b62884bcfffae00eb4a1ca9f850961ca1b594c3a32313e0`.

| Source location (printed page; PDF page) | What is implemented |
| --- | --- |
| §9.1 (33; 39) | Expansion of actual error in orthonormal eigenvectors and its weighted squared energy |
| Eq. (50), Fig. 31(a–c) (34; 40) | Exact comparison polynomials of degrees 0, 1, 2 for eigenvalues {2,7} |
| §9.2, Fig. 33, Eq. (51) (36; 42) | Scaled Chebyshev comparisons over the whole interval [2,7] |
| Eq. (52) (36; 42) | Existing looser condition-number envelope; page locator corrected from 37 / 43 |

These are independently calculated redraws, not copied paper pixels. Figure
31(d)'s cluster positions are not fully specified; no cluster input is guessed.
The colored actual observations and nine extra starts are added explanations,
not additional original-paper figures. No preconditioner or new algorithm is run.

## The same computed error, two coordinates

For A=[[3,2],[2,6]], choose the explicit unit eigenvectors
v₂=(2,−1)/√5 and v₇=(1,2)/√5. Their signs and order are fixed. With
e=x−x* and cⱼ=vⱼᵀe:

    ||e||A² = 2 c₂² + 7 c₇² = 2 (f(x)−f*)

Every CG row retains both coefficients, both squared energy contributions and
their normalization by the **initial total squared energy**. Gray bars show the
initial contributions; blue bars show the selected iterate, on a common scale
across steps. Their sum is the squared norm ratio, not the norm ratio itself.

The observed cⱼ/cⱼ,₀ is plotted only at eigenvalue j. If cⱼ,₀=0 the ratio is null
and its marker is absent; any computed current coefficient and energy still
remain in the record. In particular, the existing start (3,0) has only the
λ=7 initial mode and CG stops after one update. The global player holds that
last computed state; it does not fabricate a second CG update.
The local CG-step selector stays synchronized with the page's trajectory player,
so a reader can change the displayed step beside the spectral figures. Selecting
a step also pauses playback and updates the other views of that same case.

## A bound polynomial is not automatically the actual polynomial

In exact arithmetic CG minimizes the weighted energy over its current Krylov
space. Equation (50) bounds that minimum by a polynomial's **largest magnitude
on the spectrum**. Minimizing that maximum is a different optimization problem.

| Degree | Finite-spectrum comparison P(t) | Envelope factor | Interval comparison Q(t) | Envelope factor |
| --- | --- | ---: | --- | ---: |
| 0 | 1 | 1 | 1 | 1 |
| 1 | 1−2t/9 | 5/9 | 1−2t/9 | 5/9 |
| 2 | (1−t/2)(1−t/7) | 0 | (137−72t+8t²)/137 | 25/137 |

All have value 1 at t=0. The degree-two finite-spectrum polynomial vanishes
at both eigenvalues but is −25/56 at the midpoint 4.5. The interval comparison
also controls every intermediate value; its midpoint is −25/137. The plot
shades [2,7] and samples 0≤t≤8 in increments of 0.05 to include normalization
at zero. Envelope factors apply to their stated spectrum/interval, not the
entire displayed domain. The two comparison curves coincide at degrees 0 and 1.

For the published start (−2,−2), the initial modal energies are 128/5 and 112/5.
Its first CG step uses α=13/75 and has component ratios 49/75 and −16/75.
The first ratio exceeds 5/9, but the total energy ratio is √(56/225)<5/9.
Thus the minimax comparison is an upper bound on the energy norm, not an upper
bound on each observed component ratio. No continuous curve is fitted to the
orange observations, and no internal CG polynomial coefficients are invented.

The two-step zero is an exact-arithmetic statement, not a floating-point test
threshold. Computed errors are retained rather than forced to zero. Independent
coordinate changes can differ by roundoff: validation uses relative 2e−11 and
absolute 2e−13 for spectral fields, with tighter rational first-step unit checks.

## Validation

The independent distribution validator uses scalar projections and expanded
polynomials, checks all samples/starts/rows, energy reconstruction, inactive
modes, exact factors and source locators. Corruption tests alter coefficients,
ratios, energy, initial weights, a polynomial sample, the interval factor,
an undefined ratio and a page locator. The existing fixed CG check is unchanged.

The browser check covers all stored states at 1440px and 390px, using independent
projections to verify markers and bars. It also checks every reference sample,
stopped states, missing ratios, controls, labels, downloads and native static
figures/tables with JavaScript disabled. Both tour variants reuse this report.
