# Learn, sample many cases, inspect geometry, vary one thing, and replay (v0.5.0)

For the new development-source `reproduce shewchuk-1994` workflow (not bundled in the
v0.5.0 release), see [the published-example guide](SHEWCHUK_REPRODUCTION.md).

This release adds four bounded workflows to the existing engine. None requires a
server, API key, telemetry, a new solver or a new runtime dependency. HTML outputs
contain calculated observations; browser controls change their presentation, not
run optimization in JavaScript. Exact numbers remain in the expandable record.

## 1. Begin with a question

```bash
python -m chainbench learn --lang ko --output learn.html
python -m chainbench learn --focus beck-teboulle-2009 --output fista.html
```

Open the saved HTML locally. Use the language button (Korean/English), keyword
filter, topic cards, explanatory panels and expandable normalized-ratio plots.
A topic explains motivation, assumptions, the implemented recurrence, a selected
published guarantee, the actual observation and what it does not establish.
Source links are optional links; no remote resource is loaded by the report.

The six inequality topics include a normalized ratio plot with threshold 1.
Heavy-ball is instead an empirical tail comparison, and ISTA/FISTA is INFO only;
neither gets a misleading pointwise bound plot. Underlying samples and verdicts
are checked with the same audit as `report`. A JSON export button saves the
embedded evidence locally. No upload is performed. Without JavaScript the text,
figures, native details sections and initial chosen language remain usable.

## 2. Change one field, not everything

```bash
python -m chainbench sweep --preset quadratic --parameter condition_number --values 10 100 1000 --methods gd smooth-fista cg --lang ko --output conditioning.html
python -m chainbench sweep --preset diagonal-lasso --parameter lam --values 0.01 0.12 1 --format json --output sweep.json
```

Supported parameters: `condition_number` and `L` (quadratic), `lam` (diagonal LASSO),
`dimension` and `steps` (all three families). You may fix dimension, steps and
methods with their existing flag names, except the swept field cannot also have
a fixed override. All 2–8 distinct values are validated and normalized before any
run. The **sum** of work proxies is limited by the existing 100-million work cap;
this is an allocation safeguard, not an exact operation or runtime count.

Each panel stores its own full experiment envelope, input/configuration digests,
method parameters and termination status. A point is exactly rerunnable using
its `experiments[i].config` as a config file. Sweeping changes one requested field;
derived matrices, spectral constants and optimizer may change too. Panels have
independent y ranges; compare tick values, not apparent slope alone. Varying L,
regularization or dimension can change the objective scale. These are controlled
observations, not a speed leaderboard or universal solver ranking.

## 3. Replay a saved experiment

```bash
python -m chainbench experiment --preset quadratic --dimension 6 --steps 8 --output original.json
python -m chainbench replay original.json --lang ko --output replay.html
python -m chainbench replay original.json --format json --output replay.json
```

Input must be a complete schema-1 **experiment report**, not merely a config, a
learning report, or a sweep envelope. The loader rejects duplicate keys,
non-standard JSON numbers, incomplete trajectories, inconsistent configs/digests
and files larger than 8 MB. Configuration limits apply before recomputation.

Results are compared field by field, including parameters, trajectories and
termination. Discrete indices and update counts compare exactly. Floating values
use `rtol=1e-7, atol=1e-12` by default; both tolerances must be finite within [0,1].
The formula is Python's symmetric `math.isclose` comparison. At most the first
20 mismatch descriptions are retained, but the full mismatch count is recorded.

- `MATCH`: observations agree at the stated tolerances and input-byte digests match.
- `INPUT_DIFFERENCE`: observations agree but the input-byte fingerprint differs.
- `MISMATCH`: observations, structure or discrete values differ.

Environment changes are recorded separately. A different environment does not by
itself refute reproducibility; a changed input fingerprint is never silently
converted into MATCH. Exit 0 means MATCH, exit 1 requires review, exit 2 means
invalid input or an execution/output error. Existing files are protected by
`--force`; the replay input can never be overwritten by its output.

A matching rerun is not authentication of a report's author or proof of a theorem.
Someone can fabricate a matching saved record. Preserve the actual origin of any
external feedback rather than turning a matching JSON into an independent user.

## 4. A public tight GD example

```bash
python -m chainbench case-study gd-tight --horizon 20 --h 1 --L 1 --R 1 --lang ko --output tight.html
```

This is deliberately **not** a general worst-case search engine. It implements the
one-dimensional Huber-type function from Drori and Teboulle's public construction,
with a matching upper bound for a specific method, class and horizon. See
[GD_TIGHT_CASE.md](GD_TIGHT_CASE.md) for theorem locations, assumptions and formulas.
The basic eight-item check registry is unchanged; this is a separate case study.

## Privacy and compatibility

The new pages have local language/filter/download controls, not external scripts.
All embedded data are HTML-escaped; no user expressions, URLs or data-loading hooks
are evaluated. Existing APIs, fixed checks, report exports and the frozen v0.2.0
review kit remain intact. `report` defaults to HTML as in v0.3.0; `experiment` still
defaults to JSON. New `sweep`, `replay` and `case-study` commands default to HTML and
also support JSON. Generated pages use only system fonts and embedded SVGs.


## Many cases and geometry (v0.5.0)

A learning page now labels its first plot as a canonical illustration. To reduce cherry-picking concerns, run the same paper-linked measurement over seeded instances with `chainbench stress <topic>`. To understand *why* trajectories differ on an ill-conditioned quadratic, use `chainbench landscape`, which renders the same run as contour, 3D surface and loss views. See [EVIDENCE_LAYERS.md](EVIDENCE_LAYERS.md).
