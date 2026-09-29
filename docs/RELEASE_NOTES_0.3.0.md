# ChainBench v0.3.0 — see the selected result, not a wall of numbers

This experimental alpha release completes the visual-report and supported-instance
controls developed in PRs #35 and #37, with a final presentation/evidence audit.

## Start here

```bash
python -m chainbench report --output report.html
python -m chainbench plot beck-teboulle-2009 --output fista.svg
python -m chainbench experiment --preset quadratic --dimension 20 --condition-number 100 --steps 50 --methods gd smooth-fista cg --format html --output custom.html
```

Open the HTML file locally: previews lead to each selected paper message, actual
trajectory/reference plot, measured outcome and limitation. Fixed HTML defaults to
HTML now; scripts wanting the former Markdown output must add `--format markdown`.
The configurable `experiment` command still defaults to JSON.

## Numerical honesty in the visual layer

Legends wrap without hiding the fifth method. Zero observations are not silently
replaced by positive values on log axes; all-zero experiments have a labelled linear
view. Exact samples and environment records are embedded and preserved. Fixed-suite
verdicts must agree with plotted samples, and clean-install checks parse the exported
HTML evidence rather than accepting only the presence of an SVG tag.

Each paper section demonstrates a selected published result or an explicitly named
specialization, not the paper's complete experiments. Historical Nesterov naming,
empirical heavy-ball tolerance, quadratic proximal-point scope and INFO-only
ISTA/FISTA comparison remain explicit. A visible curve is not a proof or universal
method ranking; different methods have different work per iteration.

## Instance controls and boundaries

`preset` and `experiment --preset` accept supported dimensions, methods, budgets
and family-specific parameters. `--random-seed` samples those configuration knobs;
save the resolved JSON. It is not arbitrary dataset generation or a certified worst
case. Existing JSON/CSV/Markdown and Python method APIs remain available.

The NumPy-only runtime, pseudonymous maintainer and public-literature-only scope
remain unchanged. No API integration, paid service, telemetry or PyPI publication.
The frozen v0.2.0 review helper remains historical and is not silently retargeted.
Prior tags/assets are preserved. See the attached checksums, install verification
and build environment for this release's actual validation evidence.
