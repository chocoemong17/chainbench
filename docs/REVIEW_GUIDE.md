# Review a calculation, then its scope

Start with a question you can inspect in the output. The tour connects published
examples, controlled geometry, finite breadth and a tight construction, while
keeping their claims separate. It is a development snapshot, not a new release.

## Run the tested development snapshot

Use Git and Python 3.10+ in your preferred Python environment. These commands use
a new checkout and pin the implementation behind the previews:

```bash
git clone https://github.com/chocoemong17/chainbench.git chainbench-review
cd chainbench-review
git checkout --detach 9b54b09465388604dbd2bcd5183c60650173489c
python -m pip install .
git rev-parse HEAD
python -m chainbench tour --lang ko --output tour
```

Open `tour/index.html`. This immutable computation snapshot includes every command
on this page, including the heavy-ball counterexample and earlier stacked features.
The [development issue](https://github.com/chocoemong17/chainbench/issues/67) links
its PR and CI evidence, where the exact tested PR-head commit is recorded. The
implementation snapshot has 700 tests; documentation-only updates can follow it.
Pipeline checks are maintainer validation, not independent review or a guarantee
over arbitrary inputs.

The checkout is intentionally detached for an identifiable review. The commands
do not merge PRs or publish a release. The package version still says 0.5.0, so
record the commit too. New README edits may postdate this implementation snapshot.

The tour generates sixteen HTML files and a manifest, about 45 MB uncompressed.
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
iterations. Compare contours, objective heights and energy error, then inspect
the nine added starts. They use the same matrix and are labelled separately from
the original example. [Source and recurrence](SHEWCHUK_REPRODUCTION.md).

Next, open **Simplex geometry** or **Proximal geometry**. Inspect one oracle vertex
or one extrapolate → gradient → shrinkage sequence. Try another declared case.
The 3D chords join computed samples; their interiors are not trajectories on the
objective surface. These cases explain movement but are not representative samples.

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

The project covers selected results from public optimization literature. The image
run is one synthetic noiseless protocol; the noisy experiment and MTWIST are not
implemented. The geometric cases are controlled illustrations. Stress covers a
declared family rather than arbitrary datasets. The tight construction applies
only within its cited assumptions. There is no production-solver claim or universal
speed ranking; iteration counts do not normalize per-step computational cost.
The heavy-ball workflow reproduces the selected counterexample, not the paper's
IQC programs or a claim that all momentum choices fail.

For the released baseline instead, follow [the v0.5.0 installation](../README.md#use-the-frozen-v050-release).
It has the earlier workflows and sampler, without the new reproduction, geometry
or tour commands. Prior releases and the v0.2.0 kit are preserved.

If you review the project, report a concrete input, output or confusing explanation
in [issue #28](https://github.com/chocoemong17/chainbench/issues/28), along with your
commit, environment and command. Existing seven-person feedback is
maintainer-relayed, not seven independently archived reports.
