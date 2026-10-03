# Review a calculation, then its scope

Start with a question you can inspect in the output. The tour connects published
examples, controlled geometry, finite breadth and a tight construction, while
keeping their claims separate. The v0.7.0 reading ZIP packages the complete tour.

## Download the versioned tour

Follow the [download guide](OFFLINE_DOWNLOAD.md) for the 25-page HTML ZIP, standalone
PDF, source records and publication status. Extract the whole archive and open
`index.html`, then follow the reading route below. Python is needed only to
recompute reports. The release assets become available after the main gate passes.

The following archived previews and computation snapshot retain earlier review
history. Their recorded source and CI outcomes are separate from the versioned release.

## Change conditions, then preserve the actual input

After reading a report, choose a question from the [studio guide](STUDIO.md#three-questions-to-explore).
Keep the seed and methods fixed while changing one parameter; use several seeds
before drawing a broader conclusion. Each press of **Run a new experiment**
performs a new Python calculation. Report controls inspect its already computed
rows. Save all three downloads and use [instance replay](STORED_INPUTS.md) when
you want to rerun the saved arrays and start rather than generate a new problem.

The studio and exact-input CLI require v0.7.0 source/package; the historical
snapshot below and frozen v0.6.0 package do not contain them. Their downloaded
reports remain readable offline after Python stops. The original 25-page tour
is still a precomputed reading route and does not require the studio.

## Historical previews and pinned development snapshot

For a preview without installation or GitHub sign-in, open the archived
[two-page Korean FISTA PDF](https://github.com/chocoemong17/chainbench/blob/archive/local-reviews-20261001/cloud/33b6243/ChainBench_FISTA_review.pdf)
and [five geometry views with reading notes](https://github.com/chocoemong17/chainbench/tree/archive/local-reviews-20261001/cloud/33b6243/browser-gallery).
The PDF and gallery record their tested source commit, actual cloud output and
hashes. They remain available beyond the Actions artifact lifetime. The gallery
contains selected display examples; the full reports retain every declared case.

The [consolidated development PR](https://github.com/chocoemong17/chainbench/pull/73)
is merged into `main` and links its actual checks. Open a successful
[tests run](https://github.com/chocoemong17/chainbench/actions/workflows/tests.yml)
and download `chainbench-reading-bundle-<commit>` from **Artifacts**. Extract the
whole archive and open `index.html`; generation takes place on GitHub.
GitHub requires sign-in to download Actions artifacts. After download, the tour
needs no account, server or network. Artifacts expire after seven days.

Runs with the PDF workflow also provide `chainbench-review-packet-<commit>`:
a two-page Korean FISTA reading guide, rendered-page previews and `evidence.json`.
Its actual figure, symbolic flows and comparison table come from the audited tour.
The evidence records the source revision, manifest hash and PDF checks. This short
guide covers step selection; the full bundle contains all the other reports.
Packet generation is not a claim that the remaining CI jobs passed.

To inspect the earlier 9f797d5 computation snapshot, use Git and Python 3.10+.
These commands intentionally select that historical implementation; use the
[versioned download](OFFLINE_DOWNLOAD.md) for the current reading bundle:

```bash
git clone https://github.com/chocoemong17/chainbench.git chainbench-review
cd chainbench-review
git checkout --detach 9f797d5e2f7a2f3db2e3051ffa09a95e4c57ebf6
python -m pip install .
git rev-parse HEAD
python -m chainbench tour --extended --lang ko --output tour
```

Open `tour/index.html`. This immutable computation snapshot includes the earlier paper-reading commands,
including the five-method landscape comparison, CG metric view,
heavy-ball counterexample and earlier stacked features.
The [snapshot's tests](https://github.com/chocoemong17/chainbench/actions/runs/36875447704)
and [reading-bundle generation](https://github.com/chocoemong17/chainbench/actions/runs/36875447467)
record the actual outcomes. The suite contains 1,288 tests; read the run status
rather than treating a test count as a passing result. The
[preceding run](https://github.com/chocoemong17/chainbench/actions/runs/36873275915)
exposed 12 Windows fixture-decoding failures, fixed by explicit UTF-8 reads in
this snapshot. The failed run remains available. Documentation and PDF tooling
can follow this immutable computation snapshot.
Pipeline checks are maintainer validation, not independent review or a guarantee
over arbitrary inputs.

The checkout is intentionally detached for an identifiable review. The commands
do not merge PRs or publish a release. The package version still says 0.5.0, so
record the commit too. New README edits may postdate this implementation snapshot.

The extended tour generates twenty-five HTML files and a manifest. The index
reports the actual uncompressed size; each file's bytes and SHA-256 are recorded.
Use a new output directory; existing directories are refused. After generation,
share the whole folder. It needs no server, account or network to read. The original
papers' links require a connection; all report content and controls are local.
Use `--lang en` to start in English, or switch language within a page.

## A short reading route

### 1. Separate data fitting from image recovery

Open **Image experiment** (`deblur.html`). Change the common snapshot from k=0 to
k=100, then k=10,000. Both methods start with the same observed image. Compare
the squared residual to the blurred observation against the pixel RMSE to the clean
input: a small objective does not mean an exact reconstruction.

The known optimal objective is zero because the data are noiseless. This does not
mean that the zero image is optimal. The run has lambda=0; use **proximal geometry**
for positive-penalty soft thresholding. The image page states the source-version
difference, the equivalent image-coordinate calculation and omitted MTWIST method.
It does not fit the inputs to the paper's approximate endpoint values.
[Full source contract](FISTA_DEBLURRING.md).

### 2. Follow an actual update in space

Open **Published setup** (`shewchuk.html`) and select the original start (-2,-2).
SD and CG take the same first exact line-search step. CG reaches (2,-2) on its
second update to floating-point tolerance; it is not padded with invented later
iterations. At k=2, open the metric view: the same steps become paths on circular
level sets. Compare SD's Euclidean right angle to CG's A-metric right angle using
their actual normalized directions and inner products. This changes the drawing,
not the solver. Before two steps there is no pair to compare, including the
one-update (3,0) case. Compare contours, objective heights and energy error, then inspect
the nine added starts. They use the same matrix and are labelled separately from
the original example. [Source and recurrence](SHEWCHUK_REPRODUCTION.md).

Next, open **Simplex geometry** or **Proximal geometry**. Inspect one oracle vertex
or one extrapolate → gradient → shrinkage sequence. Try another declared case.
The 3D chords join computed samples; their interiors are not trajectories on the
objective surface. These cases explain movement but are not representative samples.

Open **Five methods on the same quadratic** (`landscape.html`) to compare fixed
steps, momentum, CG and exact quadratic PPA. Read the method settings and actual
iteration indices above the linked plots. Early-stopped CG holds its last computed
point; PPA solves a linear system at each update. Equal iteration counts do not
mean equal work or time. [Input and projection contract](LANDSCAPE_CONTEXT.md).

### 3. Look at a published failure of quadratic tuning

Open **Heavy-ball counterexample** (`heavy-ball.html`). At the published start 3.3,
inspect the signed history and the state plane `(x[k-1],x[k])`. The method approaches
the source's three-cycle on a smooth strongly convex function that is not quadratic.
The gradient stays nonzero even while the three-step difference gets small.

Then inspect every added grid start. Some approach the cycle and others approach
zero. GD is a separately labelled comparison. Neither the cycle nor the convergent
variations are hidden, and a small three-step difference alone is not called a
convergence certificate. [Exact source and omitted IQC scope](HEAVY_BALL_COUNTEREXAMPLE.md).

### 4. Inspect an inconvenient sampled result

Open the **ISTA vs FISTA stress** report, then seed 24. Its ratio is unresolved
because the denominator is below the comparison floor. The row remains present;
the program neither calls it a zero ratio nor replaces the seed. Open other rows
and inspect exact arrays, starts, budgets and curves. The tour includes all seeds
0–31 for all eight topics, not just favorable cases.

Dimension, start and orientation follow a declared stratified design. Quantile
statistics and nearest-rank example cards are different objects. All of this is
finite synthetic breadth, not a universal method ranking.
[Sampler contract and migration from v0.5.0](STRESS_SAMPLING.md).

### 5. Find out where a tight claim comes from

Open **Tight GD** (`tight-gd.html`). Follow the iterates and the constant gradient
on the affine part; inspect the normalized quadratic centre. The public upper
bound and matching construction establish the tight result under its stated
assumptions. The numerical equality only checks this implementation. Changing the
horizon changes the function. [Theorems, scope and algebra](GD_TIGHT_CASE.md).

### 6. Continue into the extended reports

| Question | Open in the bundle | What to distinguish |
| --- | --- | --- |
| What does shrinkage do to noisy image coefficients? | `wavelet.html` | Actual three-stage Haar coefficients; new noise draw; unknown optimum |
| When is an accuracy floor caused by sparse support? | `fw-sparsity.html` | Sharp support minimum versus an iteration bound |
| How does a randomized projection relate to its expectation? | `kaczmarz.html` | All 64 trials per case, conditional row outcomes and exact expectation |
| Why change the row-selection probabilities? | `sampling.html` | Three declared Fourier inputs; actual complex updates; finite paths |
| Does the condition number explain every CG path? | `cg-spectrum.html` | 18 inputs with the same interval; actual mode energy and comparison polynomials |
| What changes when the loss changes each round? | `adam.html` | Source analysis variants, online regret and the retained slow AMSGrad case |
| What do the copies and dual memory do in ADMM? | `admm.html` | 36 cases; original objective versus infeasible split values and residual tests |
| Why is a proposed FISTA step rejected? | `backtracking.html` | Every trial in 36 runs; local candidate test, carried L and accepted path |

The index connects fixed-L FISTA, backtracking and ADMM with explicit flows and
notation comparisons. The same shrinkage operation appears in different
subproblems; variables, thresholds and iteration costs must be read in context.
[Settings, source contracts and evidence levels](OFFLINE_TOUR.md#optional-extended-path).

The **atlas** connects the eight topics through assumptions, symbolic update flows,
operation/state comparisons, selected bounds and limitations. A historical link is
not a claim that every recurrence is transcribed from the oldest cited paper.

## Recompute or inspect the underlying record

The reports expose their numerical evidence; JSON exports preserve it for scripts.
For example, from the pinned source checkout:

```bash
python -m chainbench reproduce fista-deblurring --format json --output deblur.json
python -m chainbench reproduce lessard-2016 --format json --output cycle.json
python -m chainbench stress-case ista-vs-fista --seed 24 --format json --output sample-24.json
python -m chainbench check all --json
```

The image record includes the clean/observed arrays, blur matrix and boundary rule,
float-array hashes, every scalar observation, declared snapshots and environment.
Its display clips to [0,1]; its stored iterates and measurements do not. The stress
record keeps the unresolved reason and actual run. The fixed check command reports
seven quantitative checks and one INFO-only comparison; INFO is not a theorem pass.

To regenerate the checked-in README image from a full record in the pinned checkout:

```bash
python scripts/render_readme_image.py deblur.json --output deblur-preview.svg
```

The script independently validates inputs, snapshot metrics and first updates using
the installed-smoke validator before encoding the preview. Its SVG metadata keeps
the input/final-image hashes, final observations, environment, settings and source
permission notice. Small floating-point differences across environments can alter
the final hashes; compare numerical values with the documented tolerances.

`replay` applies to saved schema-1 `experiment` records. It does not accept every
workflow's JSON. To recompute a reproduction or stress sample, run its documented
command with the same settings. A SHA-256 fingerprint is an identity check, not an
author signature or a proof.

## What remains limited

The project covers selected results from public optimization literature. The two
image workflows use declared synthetic protocols. The noisy Haar experiment uses
a new noise draw and an unknown optimum; original-paper noise/endpoints and MTWIST
are not reproduced. The geometric cases are controlled illustrations. Stress covers a
declared family rather than arbitrary datasets. The tight construction applies
only within its cited assumptions. There is no production-solver claim or universal
speed ranking; iteration counts do not normalize per-step computational cost.
The heavy-ball workflow reproduces the selected counterexample, not the paper's
IQC programs or a claim that all momentum choices fail.

For the versioned toolkit, follow [the v0.7.0 installation](../README.md#install-v070).
The [v0.5.0 baseline](https://github.com/chocoemong17/chainbench/releases/tag/v0.5.0)
remains unchanged for historical comparisons.
It has the earlier workflows and sampler, without the new reproduction, geometry
or tour commands. Prior releases and the v0.2.0 kit are preserved.

If you review the project, report a concrete input, output or confusing explanation
in [issue #28](https://github.com/chocoemong17/chainbench/issues/28), along with your
commit, environment and command. Existing seven-person feedback is
maintainer-relayed, not seven independently archived reports.
