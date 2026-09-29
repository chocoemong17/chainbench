# ChainBench

[![tests](https://github.com/chocoemong17/chainbench/actions/workflows/tests.yml/badge.svg)](https://github.com/chocoemong17/chainbench/actions/workflows/tests.yml)
![status](https://img.shields.io/badge/status-alpha-informational.svg)

**Understand a selected optimization result, change one condition, and replay the evidence.**

ChainBench is a small local learning and numerical-reproduction toolkit. It connects
published methods to assumptions, actual recurrences, reference formulas and plots
on synthetic problems with independently known solutions. It is not a production
solver, a theorem prover, or a reproduction of every experiment in the cited papers.

## 1. Start with a question, not a table

```bash
python -m chainbench learn --lang ko --output learn.html
```

Open `learn.html` in a browser. Eight topic cards explain **question → mechanism →
assumptions → recurrence → guarantee → observed curve → limitation**. Switch between
Korean and English, search a topic, expand bound-ratio plots, and save exact samples.
The page is self-contained. Browser controls do not run a new optimizer or upload data.

Prefer a compact fixed-suite dashboard or one figure?

```bash
python -m chainbench report --output report.html
python -m chainbench plot beck-teboulle-2009 --output fista.svg
```

![A FISTA observation and its public upper envelope](docs/images/fista.svg)

This example is generated from the plotting implementation, not a fabricated result
or an external review. Source mapping and the scope of each result are explicit in
[docs/SOURCE_MAP.md](docs/SOURCE_MAP.md).

## Install v0.4.0

Use Python 3.10+ in a new virtual environment. NumPy is the only runtime dependency;
no API key, telemetry or paid service is required. Pip may need network access during
installation; calculations and HTML viewing are local afterward.

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows: use .venv\Scripts\python.exe in place of python below
python -m pip install https://github.com/chocoemong17/chainbench/releases/download/v0.4.0/chainbench-0.4.0-py3-none-any.whl
python -m chainbench --version
python -m chainbench learn --lang ko --output learn.html
```

Alternatively install the local wheel from [GitHub Releases](https://github.com/chocoemong17/chainbench/releases).
Do not assume a same-named registry package is this project; no PyPI publication is
configured. From a source checkout, run `python -m pip install .` in its root.

## 2. Change one condition

```bash
python -m chainbench sweep --preset quadratic --parameter condition_number --values 10 100 1000 --methods gd smooth-fista cg --lang ko --output conditioning.html
```

Compare actual trajectories at 2–8 values, with every resolved config and observation
preserved. All inputs and the **combined** work budget are validated first. Different
panels may have different y-axis ranges and objective scales; this is not a speed
leaderboard or universal method ranking.

Single runs still accept direct settings or reusable JSON:

```bash
python -m chainbench experiment --preset quadratic --dimension 20 --condition-number 100 --steps 50 --methods gd cg --format html --output custom.html
python -m chainbench preset quadratic --random-seed 17 --output config.json
python -m chainbench experiment --config config.json --output saved.json
```

The seed samples existing synthetic configuration knobs, not arbitrary data or
certified worst cases. See [configuration reference](docs/EXPERIMENTS.md).

## 3. Replay, rather than trusting a saved number

```bash
python -m chainbench replay saved.json --lang ko --output replay.html
```

This **recomputes** a complete schema-1 saved experiment and compares trajectories,
parameters, inputs and environments. `MATCH` means observed agreement within the
specified tolerances and identical input-byte fingerprints. `INPUT_DIFFERENCE` and
`MISMATCH` remain visible. A match is not authentication of the author or proof that
an independent person ran the original. Missing/non-finite evidence is an error.

## 4. Inspect one public tight example

```bash
python -m chainbench case-study gd-tight --horizon 20 --lang ko --output tight.html
```

The separate Drori–Teboulle case constructs a one-dimensional Huber objective that
attains a specific published bound for constant-step GD with `0<h<=1`. Changing the
horizon changes the function. The mathematical worst-case assertion comes from the
public upper bound and matching construction, not a numerical search or a graph.
See [exact source, formula and limits](docs/GD_TIGHT_CASE.md).

## Scope and evidence

The original suite is unchanged: GD, Nesterov-style smooth FISTA, quadratic heavy-ball,
CG, Frank–Wolfe, exact quadratic proximal point, FISTA and an INFO-only ISTA comparison.
There are seven quantitative conditions plus one informational comparison. Historical
Nesterov naming, empirical heavy-ball tolerance and the small synthetic fixtures are
explicitly distinguished from entire-paper reproduction.

Existing Python method APIs and JSON/CSV/Markdown exports remain available. `report`
defaults to HTML; `experiment` defaults to JSON. New workflow pages have optional local
JavaScript controls; the old fixed reports remain script-free. Existing files require
`--force` to overwrite; input files cannot be replaced by their own outputs.

[Learning/sweep/replay guide](docs/LEARNING_WORKFLOWS.md) ·
[Public references](REFERENCES.md) · [Roadmap](ROADMAP.md) ·
[Contributing](CONTRIBUTING.md) · [Release process](RELEASING.md)

## Validation and feedback

```bash
python -m pip install -e '.[dev]'
ruff check .
python -m pytest
python scripts/check_mutations.py
python -m build
python scripts/smoke_install.py
```

CI covers Ubuntu Python 3.10–3.12, Windows/macOS Python 3.12 and a minimum-dependency
environment. Wheel and sdist are installed in separate clean environments outside the
checkout; old and new CLI outputs are exercised before release. Tests are evidence
about implemented cases, not an exhaustive correctness proof or independent adoption.

[Report actual success, failure or confusion in issue #28](https://github.com/chocoemong17/chainbench/issues/28).
The seven-person feedback there is maintainer-relayed. No star or favorable review is
requested. The [v0.2.0 review helper](review/README.md) remains a frozen historical
baseline, not the latest package. Prior releases are preserved.

Only public literature and independent code belong here. No private research,
unpublished derivations, private datasets or real-name maintainer metadata are needed.
MIT license. Public maintainer: **chocoemong17**.
