# Visual reports

The development-source [Shewchuk reproduction](SHEWCHUK_REPRODUCTION.md) connects
equal-scale coordinates, projected 3D objective gaps, energy errors and full numerical
records. Original-paper setup and added controlled variations have separate labels.

For a guided entry point, use the [review guide](REVIEW_GUIDE.md) and
[offline tour](OFFLINE_TOUR.md). The tour connects sixteen local HTML pages,
including the full image protocol, both new geometries and all sampled cases.

The HTML report is the primary human-readable ChainBench output (tracked in issue #34). It is designed to
answer the question that raw tables do not: **what should I notice about this paper?**

## First command

```bash
chainbench report --format html --output report.html
```

The file is self-contained: plots are embedded as SVG and no browser-side network
request is needed.

## How to read a paper section

Every bundled check follows the same order:

1. **What the result says** — the mathematical idea in plain language.
2. **What ChainBench shows** — the finite synthetic evidence actually computed.
3. **What to notice** — the visual pattern the plot is meant to expose.
4. **Plot** — observed trajectory plus the relevant bound/reference when one exists.
5. **Limit** — what the experiment does not establish.
6. **Numerical details** — source, exact metric, threshold and implementation note.

For bound-based checks, dashed/reference curves are not fitted to the data: they are
the formulas used by the corresponding fixed numerical check. Heavy-ball instead
shows observed consecutive error ratios against its spectral prediction. The
ISTA/FISTA comparison is informational and has no pass/fail theorem threshold.

## One plot

```bash
chainbench plot hestenes-stiefel-1952 --output cg.svg
```

SVG is used so plots stay sharp, inspectable and dependency-free.

Development source after v0.5.0 adds a visible setup caption and full instance
metadata to standalone SVGs. Learning/report pages show the same setup in an
adjacent panel, with expandable inputs, method settings and input hash. See
[CANONICAL_CONTEXT.md](CANONICAL_CONTEXT.md) for fields and validation.

## Configurable experiments

```bash
chainbench experiment --preset quadratic --format html --output quadratic.html
```

A configurable experiment page shows objective-gap trajectories and the problem
family's named stationarity measure. Equal iteration counts do not imply equal work.

## Machine-readable data still matters

HTML is presentation. JSON and CSV remain the right formats for scripts, independent
comparison and archival evidence. The raw appendix exists so visual communication
never replaces the numerical record.

## No theorem-by-screenshot

A curve lying under a bound on a finite deterministic fixture is not a proof of the
theorem, an endorsement of the software, or evidence of broad external adoption.

## Release reading contract (v0.3.0)

The title of a paper is not a claim to reproduce its entire contribution or dataset.
Each story selects one public result and identifies the implementation specialization.
A faster-looking curve is not a fitted convergence-rate proof. Spectral radius need
not be the limit of every consecutive heavy-ball norm ratio.

Overview previews use the same samples as the detailed plots. `report` now defaults
to HTML; use `--format markdown` in scripts needing the old behavior. `experiment`
still defaults to JSON. Fixed reports and SVG use no JavaScript. New workflow
pages use optional local scripts for inspection, with a no-JavaScript reading path.
No generated report needs CDNs, remote fonts or telemetry.

The SVG metadata and HTML `chainbench-evidence` block retain the original floating
values. Fixed HTML checks that its supplied summaries agree with its plotted default
samples; nondefault/mismatched summaries are rejected rather than mixed with new
plots. Configurable HTML retains the whole run, including parameters and every row.

Positive log samples are plotted without clipping. Exact zeros interrupt a log line
and appear as triangles at the baseline; they are not positive points on that axis.
An all-zero plot switches to a labelled linear zero view. Series legends wrap, and
line patterns supplement color. Figure labels show whether the axis is log or linear.
The default log view is not an estimate of an asymptotic power-law exponent.

Installation checks independently parse the actual generated HTML and compare the
embedded records with CLI JSON results. These are maintainer-controlled validation,
not independent external use, endorsements or support-program qualification.


## v0.5.0: canonical plot, sampled breadth and geometry are separate

The learning/report pages now identify a one-fixture plot as a **canonical illustration**. Use `chainbench stress <topic>` for many seeded instances and `chainbench landscape` for contour/3D path geometry. These outputs answer different questions and should not be substituted for each other. See [EVIDENCE_LAYERS.md](EVIDENCE_LAYERS.md).

The development `geometry frank-wolfe` page places each recorded iterate and oracle
on a feasible triangle and projected objective surface. The selected step controls
both projections; the complete gap/certificate chart remains available below them.
All twelve cases, static paths and numeric tables work offline. See the [source and
visual contract](SIMPLEX_GEOMETRY.md), including why the 3D chord is not a surface curve.
Two linked certificate diagrams also show the affine model at each vertex and the
resulting optimal-value bracket. They use actual stored values and a fixed scale
within each case; the full table includes the final certificate. Affine vertex
values are distinguished from the objective surface heights.

The [proximal view](PROXIMAL_GEOMETRY.md) follows the same computed extrapolation,
gradient and shrinkage stages in two coordinate views, with every case available.
The [tight-GD view](GD_TIGHT_CASE.md) resolves the shrinking quadratic centre and
shows every constant-gradient update without changing the underlying construction.

The [FISTA image protocol](FISTA_DEBLURRING.md) embeds actual 64×64 grayscale PNGs,
all scalar observations and full-precision selected images. A shared selector changes
both methods to the same saved iteration. Fixed [0,1] display clipping never changes
the raw iterates, objective or image RMSE. These two error metrics remain separate.
Desktop/mobile browser checks compare every displayed pixel to the stored arrays.

The README preview is generated from the full JSON record by
`scripts/render_readme_image.py`; its metadata retains settings, hashes, endpoint
values and source permission. It is a static preview of the same computation, not
an image copied from the paper. Use the full HTML to inspect intermediate snapshots,
curves, source differences and numerical evidence.

The [heavy-ball counterexample](HEAVY_BALL_COUNTEREXAMPLE.md) keeps signed iterates,
the actual objective graph and the two-state `(x[k-1],x[k])` plane together. The
published rational cycle is a source reference; objective gap, gradient norm and
three-step difference remain distinct quantities. Its nine cases include every
declared added start, and the last selected point explicitly has no next update.
