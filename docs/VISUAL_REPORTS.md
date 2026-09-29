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
