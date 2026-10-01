# One offline reading path

Available in development source after v0.5.0:

```bash
python -m chainbench tour --lang ko --output tour
```

Open `tour/index.html` in a browser. The recipient needs no Python installation,
server, account, API key or network after someone generates the folder. Copy or
archive the **whole folder**, so relative page links remain intact. Public source
links are optional; embedded images, scripts and numerical records load locally.

## What is included

The command generates seventeen HTML files and one manifest, currently about 45 MB
uncompressed. It reuses existing computations with fixed, declared settings:

| Page | Settings | Evidence level |
| --- | --- | --- |
| `index.html` | Generated navigation and previews from the actual reports | Reading guide |
| `atlas.html` | All eight fixed topics and their existing canonical fixtures | Symbolic explanations + canonical observations |
| `shewchuk.html` | 12-update budget; published start and all nine added starts | Exact published setup + separate controlled variations |
| `deblur.html` | 64×64 noiseless image; both methods at 10,000 updates | Published experiment protocol rerun with declared differences |
| `heavy-ball.html` | Published start 3.3 plus eight grid starts; 50 updates | Published counterexample + controlled variations and GD comparison |
| `simplex.html` | 18 updates; all 12 target/start combinations | Controlled geometry |
| `proximal.html` | 18 updates; both methods for all nine lambda/start combinations | Controlled geometry |
| `landscape.html` | Condition number 20, angle 32°, at most 18 updates; all five methods | One controlled quadratic illustration; unequal work per step |
| `stress-<topic>.html` | Every topic; every seed 0–31; sampler v2 | Finite synthetic breadth |
| `tight-gd.html` | Horizon 20; h=L=R=1 | Public tight construction within its stated scope |

The index asks what to read next and distinguishes these evidence levels. The
previews are extracted from the actual generated SVGs and the final FISTA reconstruction PNG. They are static: full
interactive controls, raw samples and limitations remain in the linked reports.
Every report has a return-to-tour link. The image experiment and proximal geometry
have reciprocal links, labelled with their distinct lambda=0 versus positive-lambda
settings; the atlas also links to the image experiment. Both Korean and English and native
no-JavaScript reading are supported.

The newer atlas report cards link each topic to the computations included in the
bundle: 22 links in the base tour and 25 in the extended tour. Report pages also
link to the relevant lesson or method-comparison panel. Cards for reports absent
from the base bundle offer commands without broken local links. Their commands
are checked against the linked artifacts' manifest settings. See the
[reading-path contract](LEARNING_WORKFLOWS.md#follow-a-topic-into-its-actual-reports).

## Optional extended path

```bash
python -m chainbench tour --extended --lang ko --output tour-extended
```

This produces twenty-five HTML files and a manifest. The generated index reports
the actual uncompressed report size, and the manifest records every file's bytes.
It keeps all sixteen base report records and adds:

| Page | Settings | Evidence level |
| --- | --- | --- |
| `wavelet.html` | 256×256; three-stage Haar; noise σ=0.001, PCG64 seed 0; λ=0.0001; 200 updates | Published Figure 4 protocol with a declared new noise draw; unknown optimum |
| `fw-sparsity.html` | 40 updates in each dimension 3, 8, 32, 128 | Public sharp support minimum compared with actual FW iterates |
| `kaczmarz.html` | Six public-family systems; every seed 0–63; 40 row projections | Published expectation-bound attainment; every finite trial retained |
| `sampling.html` | 700 nodes, 101 Fourier coefficients; seeds 0, 1, 2; three row-selection methods, 15,000 projections each | Published nonuniform sampling protocol with fully declared new inputs |
| `cg-spectrum.html` | n=16, interval [2,7]; all 3 spectra × 2 bases × 3 initial-error profiles; budget 32, true-residual rtol=10⁻¹² | Controlled spectral illustrations, not Figure 31(d)'s unspecified original inputs |
| `adam.html` | C=3,10,100 × alpha fractions 0.1,0.5,0.9; both source variants, all 3,000 rounds | Published Theorem 1 counterexample family with declared finite inputs; online regret, not a fixed-objective gap |
| `admm.html` | All 2 matrices × 3 regularization fractions × 2 starts × 3 fixed penalties; 60 updates, no early stop | Controlled 2D splitting geometry, not the source's dense experiment; original-primal gap versus infeasible split value |
| `backtracking.html` | 3 λ values × 4 starts × 3 initial L guesses; 18 accepted updates, all trials | Controlled FISTA candidate tests; original gap and signed model difference |

The step-selection section follows the proximal geometry and connects fixed-L
FISTA to backtracking. Its two symbolic flows and seven comparison rows distinguish
inputs, curvature, shrinkage threshold, acceptance test, carried L, source envelope
and candidate work. The preview is the actual first rejected model SVG at
λ=0.8, x₀=(0,0), L₀=1, k=1, j=0. It retains negative model heights and identifies
q=(0.6,−6.4), F(q)−Q₁(q,y)=163.84>0. The axis s is position along this candidate's
line, not an iteration. All 36 runs and every trial remain in the linked report.
The manifest binds their source, hashes, stable gate, eta=2 carried-L variant,
fixed budget and exact preview. Reciprocal proximal/backtracking links and the
atlas reach the report and guide. No new canonical topic or question card is added.
[Equations and scope](FISTA_BACKTRACKING.md).

The variable-splitting section follows this comparison. It places
the same soft-threshold operator inside two different symbolic update flows.
The proximal report's z is the gradient-step proposal, called v in the bridge;
ADMM's z is the sparse copy. FISTA's y is an extrapolated gradient-evaluation
point; ADMM's y=ρu is feature-coordinate dual memory. The thresholds λ/L and λ/ρ
come from different subproblems. The reports use different lambda grids and
budgets, and a linear solve is not the same work as a gradient evaluation.
This connection explains mechanisms rather than ranking the displayed curves.

Reciprocal proximal/ADMM links and an atlas link reach the report and the index's
notation guide. Existing atlas topics and all 25 workflow cards stay unchanged.
The preview is the exact k=1 original-primal surface SVG for the coupled matrix,
λ/λ_max=0.1, zero start and ρ=1, with full x/z paths and selected markers.
Its XML-valid attributes let that same plot load as an independent SVG image;
coordinates, texts and numerical records are retained. The manifest binds all
36 case identities and input hashes, source, fixed budget, initial null x,
unrelaxed fixed-penalty variant, metric and preview selection. The report's
36-cell overview retains every matrix/start/regularization/penalty combination,
showing final residual status, both norm/tolerance ratios, first pass or absence,
and original gap. Each cell reaches its final geometric state, or the matching
native final row when scripts are disabled.
[Equations, interpretation and source scope](ADMM_GEOMETRY.md).

The Adam section follows the heavy-ball counterexample and asks what changes
when the loss changes each round. Its comparison table keeps a fixed function's
iterates/objective gap separate from average online regret against a single fixed
comparator. Reciprocal links connect the two reports; the atlas also links to
Adam without inventing a ninth canonical check or altering its 25 workflow cards.
The index preview is the exact generated average-regret SVG for C=3, alpha
fraction 0.1, with every actual round for both methods. It keeps the slow AMSGrad
case and scopes the orange lower reference to Adam's complete three-round blocks.
The manifest binds the source, nine cases, budget, variant (no debiasing, beta1=0,
epsilon=0, period three), metric and preview. It does not identify this with the
different period-101 Figure 1 experiment or modern Adam defaults.
[Numerical and display contract](ADAM_COUNTEREXAMPLE.md).

The new cards show the actual FISTA reconstruction at k=200 and the n=3, k=2
simplex objective geometry. Links connect noiseless and noisy image problems,
coordinate shrinkage and actual image coefficients, and oracle geometry and
support-constrained accuracy. The GD tight case links to the sparsity construction
with an explicit distinction between iteration-bound and support-bound attainment.

The CG section connects the published 2×2 example to 18 new declared inputs at
the same condition number. Its preview comes directly from the report's Hadamard,
equal-initial-energy overview, including all actual updates for all three spectra.
The relative A-norm metric differs from squared error; the source interval
comparison is not a fitted CG polynomial or a floating-point certificate.
Reciprocal links connect both CG reports, and the CG study also returns to its
atlas lesson. The atlas and CG stress page link to the study. No new canonical
topic is introduced; all 25 existing extended-atlas workflow cards remain intact.
The manifest binds all 18 cases, source, budget, stopping tolerance, metric and
exact preview selection. [Numerical and display contract](CG_SPECTRUM.md).

The randomized section adds the initial actual-coordinate cube for A=I₃ and
x0=(1,1,1); the three axes are coordinates, not objective height. Its reading
question and comparison table distinguish three mathematical statements:
attaining GD's deterministic iteration bound, attaining the best objective with
limited support, and attaining an expected squared-error bound over random row
selections. GD and sparsity pages link to the randomized report; that report
links back to the deterministic construction. No new fixed-suite check or
canonical atlas topic is implied. All earlier numeric records are unchanged.

The nonuniform sampling section then asks how the same row projection works on
irregular signal observations. Its preview is the actual seed-0 weighted-method
waveform at k=100, extracted from the generated report's native gallery. Reciprocal
links connect it to the expectation construction. Their inputs and metrics are
different: expected squared error on a finite-state construction versus individual
coefficient L2 error paths on declared Fourier systems. No cross-report timing
ranking or expectation estimate is implied. The first input remains visible when
Theorem 4's sufficient gap condition fails. All three inputs and full budgets are
bound to the manifest; see the [sampling contract](NONUNIFORM_SAMPLING.md).

The [image contract](FISTA_WAVELET.md) records source differences, full arrays,
residual/penalty and RMSE; objective F is not called a gap to an unknown optimum.
The [sparsity contract](FW_SPARSITY.md) keeps every dimension and ends the dual
floor at full support. Equal weights on the current support are a comparison
point, not another algorithm trajectory.
The [Kaczmarz contract](KACZMARZ_EXPECTATION.md) retains every draw and coordinate,
including unresolved runs and draws after zero. Its finite sample mean is never
required to lie below the exact expectation curve. Seeds are reused across cases;
cases must not be pooled as independent trials.

This optional path and all eight extensions are included in the
[review guide's pinned snapshot](REVIEW_GUIDE.md). GitHub Actions generates and
audits the full bundle; [PR #73](https://github.com/chocoemong17/chainbench/pull/73)
links current tests, browser checks and independent clean installations.
The default command continues to generate the base seventeen pages.

## Reading across evidence levels

The heavy-ball counterexample links to the atlas's quadratic heavy-ball explanation;
the corresponding quadratic stress report links to the counterexample. These links
connect different function classes without implying that their guarantees transfer.

The stress interval is fixed in advance, not selected by performance. Across
quadratics it contains two full cycles of the declared dimension/orientation/start
strata. All 256 sampled rows remain available, including unresolved ratios; seed
24 of ISTA/FISTA is one such unresolved row. This is finite synthetic coverage,
not representative real-world data, a performance ranking or a theorem proof.

## Files, settings and hashes

`manifest.json` records the package/NumPy/Python/OS environment, language, entry
page, each artifact's evidence level and reproduction command, applicable source
and case settings, exact UTF-8 byte length and SHA-256. Commands omit `--output`;
append it with a new filename to generate a separate standalone report. The tour
adds navigation, so its file hash intentionally differs from a standalone export.
The numeric record remains the same.

Schema 1's `extensions` field is `[]` for the base bundle or
`["fista-wavelet", "fw-sparsity", "kaczmarz-expectation", "kaczmarz-sampling", "cg-spectrum", "reddi-2018", "admm-lasso", "fista-backtracking"]`
for the current extended bundle. Earlier nineteen-page bundles with just
`["fista-wavelet", "fw-sparsity"]` and twenty-page bundles also containing
`"kaczmarz-expectation"`, and twenty-one-page bundles also containing
`"kaczmarz-sampling"`, and twenty-two-page bundles also containing
`"cg-spectrum"`, and twenty-three-page bundles also containing `"reddi-2018"`
and twenty-four-page bundles also containing `"admm-lasso"`
remain valid. Older base manifests without the field
are accepted as base bundles.
Unknown selections, unadvertised
extra files and changes to extension budgets, seed or source metadata are rejected
by the validator.

Hashes cover the listed HTML files. The manifest does not hash itself and is not
an author signature, independent review or proof. Generated timestamps and absolute
paths are omitted; environment or numerical-library changes can still alter bytes.

The parent directory must exist. The command stages calculations in a temporary
sibling folder, then creates a **new** destination exclusively. It has no overwrite
flag. Existing files, directories and symlinks are refused before computation.
If calculation fails, no destination is created; if destination writing fails,
files created by that attempt are removed. The manifest is written last.

## Validation

Tests and installed wheel/sdist smoke inspect every file hash, local path/anchor,
return link, all eight topics and all 32 seeds. Numerical validators check the
published example, both geometries, tight case and image experiment; installed standalone commands must reproduce
selected tour records exactly, including the unresolved case. Missing or changed
artifacts and injected calculation/write failures are exercised.

The folder audit reads links, fragment targets and embedded evidence in one HTML
traversal per document. Escaped record text is decoded as HTML text, so apparent
tags inside a JSON string, comment or script do not become navigation links.
Once decoded, the raw JSON text is discarded while the link/target inventory is
retained. The reader requires exactly one evidence block, including when a
duplicate is empty or fragments would otherwise concatenate into valid JSON.
The evidence id must also be unique and unambiguous, rather than shared with
another element or hidden by a repeated id attribute. Missing or malformed
evidence also fails extraction.

All extension metadata, fixed budgets and the retained unresolved-case contract
are checked before numerical and presentation audits. This lets a mislabeled
bundle fail without first recomputing unrelated experiments. Every valid bundle
still runs all the independent audits with their existing tolerances; there is
no cache of successful validations. Regression checks also rehash an incorrect
ADMM update and require its numerical rejection, so a matching file hash alone
cannot replace the scientific checks. Generated reports and records are unchanged.

Table headings preserve their authored letter case and spacing: `x`, `gₜ`,
`ηₜ` and `Δx` must keep the same notation as the equations and stored values.
The browser audit checks computed text transforms on every table heading and
its descendants, including inactive cases and collapsed iteration tables, on
the index and every report at both viewport widths.

The configured browser CI opens all sixteen or twenty-four reports from the index and returns from each at
1440px and 390px, verifies loaded previews, the full image budget, reciprocal geometry links and the
preserved unresolved row, and
checks language, overflow, offline operation and a no-JavaScript reading path.
The extended check also exercises the 100-update image snapshot, full-support
dual-floor omission, retained randomized trials, all three sampling inputs and
reciprocal expectation/signal links. It also opens the CG spectral study, selects
a single-mode start, verifies its unpadded trace, follows both CG links and opens
the related lesson. The no-JavaScript path opens its native overview.
The Adam path follows both counterexample links, verifies six selected actual
rounds for both methods and the retained slow AMSGrad case, exercises keyboard
navigation, and opens the native table with scripts disabled. Earlier extended
bundles with two through seven extensions remain readable.
The ADMM path follows reciprocal comparison links and the notation-guide link,
checks original-primal and dual geometry plus readouts at k=0/1/2/30/60 in both
the preview case and a zero-gap yet infeasible split state, and tests keyboard
controls and native first-step figures/tables. The comparison table also scrolls
with the keyboard on mobile. A separate presentation audit rejects a missing
flow, notation row, required navigation or a rehashed preview which differs from
the named report SVG; it also requires that SVG to parse as standalone XML.
The same ADMM DOM audit also checks the selected quadratic subproblem contours,
their translated center and previous-z marker, the separate full-range shrinkage
axes, threshold bands, previous-memory readouts, arrows and native input table.
These views derive from the existing record; the original surface preview and
all numerical results remain unchanged. The tour also checks all overview cells
against the recorded values and follows the two inspected cases through their
overview links, requiring the selector and iteration to reach the stated final
state before checking other iterations.
The backtracking path opens every one of its 36 cases and checks all 790 trial
states at each width against the actual rendered coordinates, model curves and
readouts. It checks keyboard controls, reciprocal links, the source lesson,
Korean/English guide layouts, mobile table scrolling and native first-trial access.
Metadata faults are rejected before expensive audits; independent presentation
checks reject changed flow, envelope, caption, preview or required navigation,
even when the modified files have matching manifest hashes.
The release gate requires
both `offline_tour: matched` and `extended_tour: matched` for both distribution
formats; installed standalone image/sparsity/Kaczmarz/sampling/CG/Adam/ADMM/backtracking records must match the extended tour.
The separate `kaczmarz_expectation: matched`, `nonuniform_sampling: matched`, `cg_spectrum: matched`, `adam_counterexample: matched` and `admm_geometry: matched`
results are also required. A contract
test binds the smoke producer's actual summary keys to the release gate so adding
a workflow cannot silently leave those components inconsistent.

No tour or release is hosted or published by this command. Generated results should
be reviewed before sharing; prior releases and the frozen v0.2.0 kit are unchanged.
