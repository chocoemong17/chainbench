# Visual reports

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
still defaults to JSON. HTML and SVG use no JavaScript, CDNs, web fonts or telemetry.

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
