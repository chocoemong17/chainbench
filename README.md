# ChainBench

[![tests](https://github.com/chocoemong17/chainbench/actions/workflows/tests.yml/badge.svg)](https://github.com/chocoemong17/chainbench/actions/workflows/tests.yml)
![status](https://img.shields.io/badge/status-alpha-informational.svg)

**Read the idea. Follow the iterates. Recompute the evidence.**

ChainBench connects published optimization methods to their assumptions, update
rules and actual calculations. Explore 2D contours, 3D objective surfaces, image
reconstructions and reproducible instance families in local, bilingual reports.
Python 3.10+ and NumPy generate the pages; a browser is enough to read or share them.

**New here? [Start with the review guide](docs/REVIEW_GUIDE.md)** — it gives a runnable,
tested source checkout and specific questions to investigate. The development
features shown below are in a PR stack; the frozen **v0.5.0 release does not contain
the tour, paper reproductions or new geometry commands**.

## From a paper's experiment to actual pixels

![Clean input, blurred observation, and actual ISTA/FISTA reconstructions after 10,000 updates](docs/images/deblur-preview.svg)

A rerun of the **ISTA/FISTA subset of Beck–Teboulle (2009), Section 5.2 / Figure 5**:
64×64 public procedural image, 9×9 Gaussian blur with sigma=4 and edge-repeating
symmetric boundaries, no noise, lambda=0, L=2 and step=1/2. Both methods start at
the blurred observation and take 10,000 updates. All images share the [0,1] grayscale;
only display pixels are clipped.

| Actual observation at 10,000 updates | ISTA | FISTA |
| --- | ---: | ---: |
| Squared residual to the blurred observation, F | 1.247403e-4 | 1.109953e-8 |
| Pixel RMSE against the clean input | 4.576756e-2 | 2.017030e-2 |

A small residual does not imply exact image recovery. This is one published
synthetic protocol, with explicit source-version and coordinate differences;
it does not assert exact reproduction of the paper's reported endpoints.
[Inspect the source, inputs, permission and differences](docs/FISTA_DEBLURRING.md).
The [preview generator](scripts/render_readme_image.py) uses the same saved numerical
record as the full report, including hashes and attribution.

## Run the development tour

In a checkout containing these changes, with Python in your preferred environment:

```bash
python -m pip install .
python -m chainbench tour --lang ko --output tour
```

For a fresh checkout, follow the [pinned installation steps](docs/REVIEW_GUIDE.md#run-the-tested-development-snapshot).
Open `tour/index.html`. It connects **16 offline HTML pages**: the reading guide,
eight-topic atlas, three published-example workflows, two geometry views, eight
stress reports and one public tight case. Each report keeps its numerical evidence
and links back to the guide. The recipient needs no server, account or Python.

Use a new destination directory. The whole folder is about 45 MB uncompressed;
copy the folder to preserve its links. [Contents, settings and hashes](docs/OFFLINE_TOUR.md).

## Choose the question you want to answer

| Question | Open in the tour | What the evidence supports |
| --- | --- | --- |
| How do SD and CG move on a published example? | `shewchuk.html` | Exact stated 2D setup; nine additional starts labelled separately |
| Does fitting blurred data recover the clean image? | `deblur.html` | One declared image protocol; all 10,001 objective/RMSE observations per method |
| Can quadratic tuning fail on a smooth strongly convex function? | `heavy-ball.html` | Lessard–Recht–Packard's published counterexample; eight separately labelled added starts |
| How does an oracle respect a constraint? | `simplex.html` | Twelve controlled Frank–Wolfe target/start cases |
| What do momentum and soft thresholding do? | `proximal.html` | Nine controlled lambda/start cases with actual intermediate stages |
| Does a claim survive more sampled inputs? | `stress-<topic>.html` | All 32 seeds per topic, including unresolved ratios |
| Why can a bound be called tight? | `tight-gd.html` | A public upper bound and matching construction under stated assumptions |
| How are the ideas related? | `atlas.html` | Symbolic flows, assumptions, results, trade-offs and linked methods |

| A feasible Frank–Wolfe update | ISTA/FISTA at actual objective heights |
| --- | --- |
| ![Actual Frank–Wolfe simplex trajectory](docs/images/tour-simplex.svg) | ![Actual ISTA/FISTA trajectories on a composite objective](docs/images/tour-proximal.svg) |

These previews are controlled illustrations: simplex target (0.2,0.3,0.5), start e1,
C_f=2; diagonal LASSO a=(1,3), b=(1.4,-2.4), lambda=0.8, start (-1.8,1.2), L=9.
Both use 18 updates. The 3D chords join actual samples; they are not continuous
paths on the surface. [Simplex contract](docs/SIMPLEX_GEOMETRY.md) ·
[Proximal contract](docs/PROXIMAL_GEOMETRY.md).

Every plot identifies its problem, start, parameters, budget, metric and source.
Canonical illustrations, finite stress, published-example reruns and tight
constructions answer different questions. [Read the evidence distinctions](docs/EVIDENCE_LAYERS.md).

## Generate only the page you need

```bash
python -m chainbench reproduce shewchuk-1994 --lang ko --output paper.html
python -m chainbench reproduce fista-deblurring --lang ko --output deblur.html
python -m chainbench reproduce lessard-2016 --lang ko --output cycle.html
python -m chainbench geometry frank-wolfe --lang ko --output simplex.html
python -m chainbench geometry ista-fista --lang ko --output proximal.html
python -m chainbench learn --lang ko --output learn.html
python -m chainbench stress nesterov-1983 --trials 32 --seed 0 --lang ko --output stress.html
python -m chainbench case-study gd-tight --horizon 20 --lang ko --output tight.html
```

Reports support Korean and English, local controls, raw records and reading with
JavaScript disabled. Controls inspect stored computations; they do not run an
optimizer in the browser. Standalone SVGs retain setup captions and input metadata.
[Visual formats](docs/VISUAL_REPORTS.md) · [Learning workflows](docs/LEARNING_WORKFLOWS.md).

The [heavy-ball counterexample](docs/HEAVY_BALL_COUNTEREXAMPLE.md) connects the
actual function, signed iterates and `(previous, current)` state plane. Its published
three-cycle explains why a small repeat difference can coexist with a nonzero
gradient. The same method's successful quadratic fixture remains a separate story.

## Change a condition and replay a calculation

```bash
python -m chainbench sweep --preset quadratic --parameter condition_number --values 10 100 1000 --methods gd smooth-fista cg --lang ko --output conditioning.html
python -m chainbench experiment --preset quadratic --dimension 20 --condition-number 100 --steps 50 --methods gd cg --output saved.json
python -m chainbench replay saved.json --lang ko --output replay.html
```

A sweep changes one declared factor. A replay recomputes a schema-1 experiment and
compares inputs, trajectories and environments with stated tolerances. A `MATCH`
is numerical agreement, not author authentication or proof. Equal iteration counts
need not mean equal work. [Configuration and limits](docs/EXPERIMENTS.md).

## Use the frozen v0.5.0 release

If you want the released baseline, use Python 3.10+ in your preferred environment:

```bash
python -m pip install https://github.com/chocoemong17/chainbench/releases/download/v0.5.0/chainbench-0.5.0-py3-none-any.whl
python -m chainbench learn --lang ko --output learn-v050.html
```

The release supports `learn`, `report`, `plot`, `experiment`, `sweep`, `replay`,
`stress`, `landscape` and the original `case-study gd-tight`. New development
workflows and sampler v2 require the source snapshot above. Both currently report
package version 0.5.0: **record the commit as well as the version**.
[Release assets](https://github.com/chocoemong17/chainbench/releases/tag/v0.5.0)
remain unchanged. No PyPI publication is configured; do not assume a same-named
registry package is this project.

## Scope and validation

The fixed suite covers GD, smooth fixed-L FISTA under a historical Nesterov slug,
quadratic heavy-ball, CG, Frank–Wolfe, exact quadratic proximal point, FISTA and an
INFO-only ISTA comparison. Heavy-ball's tolerance is empirical. A finite sample
cannot prove a theorem or a universal ranking. ChainBench is an experimental alpha,
not a production solver or a reproduction of every experiment in each paper.
[Exact source-to-implementation mapping](docs/SOURCE_MAP.md) · [Public references](REFERENCES.md).

```bash
python -m pip install -e '.[dev]'
ruff check .
python -m pytest
python scripts/check_mutations.py
python -m build
python scripts/smoke_install.py
```

CI checks Ubuntu Python 3.10–3.12, Windows/macOS Python 3.12, minimum dependencies,
both clean distribution installs and offline Chromium at desktop/mobile widths.
Numerical records are checked against rendered curves, points and image pixels.
These are maintainer-controlled checks, not independent adoption evidence.

[Report a concrete success, failure or confusing explanation](https://github.com/chocoemong17/chainbench/issues/28).
The seven-person feedback there is maintainer-relayed. The [v0.2.0 reviewer kit](review/README.md)
is a frozen historical baseline. No stars or favorable reviews are requested.

[Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [Release process](RELEASING.md)

NumPy is the only runtime dependency. No API key, telemetry or paid service is
required. Installation may use the network; calculations and generated reports are
local afterward. Only public literature and licensed inputs belong here.
MIT license for ChainBench; the image-generator port retains its
[ReguTools permission notice](docs/licenses/REGUTOOLS.txt).
Public maintainer: **chocoemong17**.
