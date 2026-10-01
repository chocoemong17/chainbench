# Read saved experiments together

Development source adds `compare` for two to four complete schema-1 experiment
JSON reports. It reads their actual saved samples without running a solver.
Use `replay` separately when you want to recompute one saved configuration.

```bash
chainbench experiment --preset quadratic --dimension 4 --steps 8 --methods gd cg --output a.json
chainbench experiment --preset quadratic --dimension 4 --steps 12 --methods gd cg --output b.json
chainbench compare a.json b.json --lang ko --output comparison.html
chainbench compare a.json b.json --metric stationarity --format json --output comparison.json
```

Open the HTML in a browser. First read the pairwise differences: full normalized
configuration, declared input fingerprint, fixture/start, method parameters and
execution environment. Expand the fields to see their actual values. A changed
budget can share the same input; matching configurations can carry different
input fingerprints across floating-point environments. Neither is hidden.

For a deliberately different problem, generate a third record:

```bash
chainbench experiment --preset quadratic --dimension 4 --condition-number 100 --steps 8 --methods gd cg --output c.json
chainbench compare a.json b.json c.json --lang ko --output different-problems.html
```

An overlay is available only when **every record** agrees on the recorded problem
configuration and complete fixture, including its input digest, start, constants,
reference objective and stationarity definition. Each shared method has its own
overlay with at most four lines. Methods appearing in only one record remain in
their record's panel. Environment, budget, method options and termination can
still differ and remain visible. Different setups use separate panels with an
explicit warning about independent axis ranges and objective scales.

The selectable metric is `gap` (default), `stationarity`, or
`distance_to_reference`. Stationarity retains the family's actual definition:
gradient norm, proximal-gradient mapping norm, or Frank–Wolfe gap. Charts use only
the saved indices and values, end at each method's actual recorded update, and
never extrapolate or pad early termination. Zero values are marked at the log
baseline, not converted to small positive numbers. Iterations are not equal work.
`budget_complete` says the requested updates ran; it does not certify convergence.

## Provenance and limits

All original reports remain in `records[].experiment`. `record_sha256` hashes
their canonical JSON (sorted keys, compact separators, ASCII escaping), not the
original file bytes. Whitespace and key order do not change that hash. Duplicate
records are explicitly identified; importing a duplicate adds no evidence.

The existing schema-1 report contains an input fingerprint, not all input arrays.
Comparison can inspect whether the **declared** fingerprints agree; it cannot
authenticate those inputs, who ran the record or whether its numbers are truthful.
Its stricter metadata checks validate structure and finite data, not scientific
correctness. A coherent fabricated record can still pass those checks. There is
no authentication, theorem claim, tolerance-based rerun verdict or outside-review
claim. The generated example pair is a controlled illustration, not representative
sampling or a reproduction of an original paper figure.

Each input must be a regular local UTF-8 JSON file, at most 8,000,000 bytes. The
combined input limit is 16,000,000 bytes; exactly two to four files are required.
The comparison API also limits canonical record bytes. Config/work bounds,
trajectory indices/counts, finite samples, exact method fields and fixture
metadata are checked before presentation. Duplicate JSON keys, nonstandard or
nonfinite numbers, incompatible schemas and missing data fail. Source filenames
are not embedded; records use A/B/C/D in the supplied order.

Outputs cannot replace **any** input, including symlink/hardlink aliases, even
with `--force`. Other existing outputs require `--force`. Exit 0 means a valid
comparison was generated, including when records differ; exit 2 means invalid
input or an I/O error. No URL/code/array execution, telemetry or server is added.
NumPy remains the only runtime dependency.

## Validation and scope

Installed wheel and sdist smoke checks independently audit two-, three- and
four-record examples with all three metrics. They compare every retained report,
canonical hash, pair diagnostic, plotted sample and SVG metadata. Regression
cases corrupt hashes, diagnostics and curves and require rejection. Browser
checks inspect both matching and mixed problems at 1440px and 390px, keyboard
navigation, native details, language switching, exact JSON download, no-script
reading and absence of network requests. The browser job produces the actual
HTML files and a two-page static PDF review packet.

This implements the saved comparison item of issue #40. The broader local studio
and arbitrary-array replay requests remain separate. Existing replay APIs,
published release assets and the frozen historical review kit are unchanged.
