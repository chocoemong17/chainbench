# Shewchuk's two paths: a published numerical example

Available from the development source checkout; the frozen v0.5.0 release predates
this command. NumPy remains the only runtime dependency.

```bash
python -m chainbench reproduce shewchuk-1994 --lang ko --output paper.html
python -m chainbench reproduce shewchuk-1994 --format json --output paper.json
```

This independently recomputes the setup behind **Figures 8 and 30** in Jonathan
Richard Shewchuk, *An Introduction to the Conjugate Gradient Method Without the
Agonizing Pain*, edition 1 1/4, August 4, 1994.
[Original author-hosted source](https://www.cs.cmu.edu/~quake-papers/painless-conjugate-gradient.pdf).
It is a pedagogical numerical example, not a dataset benchmark. The report redraws
computed paths; it neither copies pixels nor digitizes the source curves.

## Exact source mapping

| Item | Source location (printed page; PDF page) | Implementation |
| --- | --- | --- |
| Quadratic and system | Section 3, Eq. (4) (2; 8) | `A=[[3,2],[2,6]]`, `b=[2,-8]`, `c=0` |
| Steepest descent | Section 4, Eqs. (10)–(12), Figure 8 (8; 14) | Recomputed residual, exact quadratic line search |
| Conjugate gradient | Section 8, Eqs. (45)–(49), Figure 30 (32; 38) | Existing ChainBench scaled-correction CG |
| Energy-norm envelope | Section 9.2, Eq. (52) (37; 43) | `2 rho^k ||e0||_A`, `rho=(sqrt(kappa)-1)/(sqrt(kappa)+1)` |

For both paths, `x0=[-2,-2]`, `x*=[2,-2]`, `f*=−10`, eigenvalues are 2 and 7,
and condition number is 3.5. The objective is `f(x)=0.5*x^T*A*x-b^T*x`.
The chosen source bytes have SHA-256
`368110e5592d0d3e0b62884bcfffae00eb4a1ca9f850961ca1b594c3a32313e0`.
Locations and hash are embedded in the report. No source PDF, third-party code or
external image dataset is distributed. The small mathematical inputs are specified
above and implemented independently; no image/data license is required to rerun them.

## What is checked

Independent rational arithmetic verifies the first five steepest-descent updates.
Both methods first reach `(2/25, -46/75)`; CG next reaches `(2,-2)` within floating
precision. Its two displacements are A-conjugate. Tests independently recompute the
gap, residual and energy norm from every coordinate, validate every input hash and
compare projected SVG coordinates with the same numerical trace.

`--steps` is a bounded integer from 2 to 40 (default 12). Both methods stop if the
recomputed residual satisfies `||b-Ax||₂ <= 1e-12 ||b-Ax0||₂`. `max_steps` means the
budget was exhausted, not that convergence was established. CG stops after one or
two updates on these cases; the report never extends its trajectory with invented
iterations. The player holds the last computed point and explicitly labels it.

The envelope is an exact-arithmetic result. Finite agreement is not a proof, a
worst-case certificate or a general floating-point convergence guarantee. The
envelope uses positive iterations; computed initial values remain visible. Zero
errors are shown as labelled baseline triangles on the log chart, not fabricated
positive numbers.

## Same setup, explicit differences

The contour ranges match the source figures: `x1 ∈ [-4,6]`, `x2 ∈ [-6,4]`. Equal
coordinate scales preserve angles. ChainBench chooses the contour levels (listed
under the plot), budget, tolerance, colors and line styles. The projected 3D view
plots `z=f−f*`, not `f`; its wireframe is transparent, not a depth-occluded rendering.
The energy plot and 3D view are added explanations, not original-paper figures.

The existing CG implementation rescales a correction system and recomputes true
residuals, preserving exact-arithmetic iterates while changing floating-point
evaluation. No identical-byte match to the author's original numerical run is
claimed. Original raw iterate data are not supplied with the source; the independent
reference is the published recurrence and rational arithmetic, not extracted pixels.

## More than one start, with a narrow claim

The report includes **all nine** starts in `{-3,0,3} × {-4,0,3}`, with no performance
filter. Each opens a contour, energy chart, iteration player and full value table.
These are controlled ChainBench additions on the same matrix, not paper figures,
random samples or evidence across dimensions and spectra. Starting at `(3,0)` makes
the initial error an eigenvector, and both methods finish in one update. This is a
useful counterpoint to a universal interpretation of the original two-step CG path.

JSON contains every input, coordinate, metric, termination status, source mapping,
environment and fingerprint. Input hashes use little-endian float64 bytes in order
`A` (row-major), `b`, `c`, `x0`. Rerun the displayed command to recompute all cases;
the existing `replay` command accepts schema-1 experiments, not this reproduction
envelope. No saved-file import or automatic source download is added here.

## Browser and installation checks

The page uses inline SVG and local controls, with Korean/English text and no CDN,
remote fonts, requests or telemetry. Without JavaScript, paths and native details
remain usable. Chart overflow is contained in a horizontally scrollable plot area.

```bash
python scripts/check_reproduction_browser.py --html paper.html --output browser-check
```

This optional development check uses Playwright and records Chromium screenshots
and JSON evidence at 1440px and 390px, tests offline keyboard/playback/language/JSON
download behavior and every variation, and checks the no-JavaScript fallback.
It is not a runtime dependency. The existing wheel and sdist smoke workflow also
executes the new installed command, compares HTML to JSON, and independently checks
the published setup and metrics. Publication requires that evidence for both builds.
