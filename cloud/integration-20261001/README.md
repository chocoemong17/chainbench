# Integrated learning toolkit: source and verification

[Open the two-page FISTA PDF](../e385810/ChainBench_FISTA_review.pdf) ·
[Read five actual geometry views](../33b6243/browser-gallery) ·
[Open the source](https://github.com/chocoemong17/chainbench/tree/e3858108ea492df04121c14d5306ac2bab1454fa)

The consolidated development toolkit was integrated through
[PR #73](https://github.com/chocoemong17/chainbench/pull/73).
The original integration commit was `69a16c5dd00241011250ea560501de451514e0d3`.
Its tree `6cc7fcf4a5cdf4912ee3f399991e892e9cf87ceb` is identical to the
fully passing PR head `f8971a1f7da8ff53564369d553203c9fc0ea6543`.

The [final PR tests](https://github.com/chocoemong17/chainbench/actions/runs/36880865578)
passed all eight jobs. All six OS/Python/dependency configurations passed 1,288 tests
each. Separate jobs verified clean wheel/sdist installations and the offline
desktop/mobile/no-script browser behavior. Numerical and browser fault injections
remained enabled. [Final PR cloud generation](https://github.com/chocoemong17/chainbench/actions/runs/36880865655)
independently audited 24 records and generated 25 HTML pages plus the two-page PDF.

The original [main tests](https://github.com/chocoemong17/chainbench/actions/runs/36882942713)
passed seven jobs. GitHub cancelled the eighth, macOS ARM64, before assigning a
runner and explicitly reported capacity constraints. This is not an all-green
main result. Its [cloud generation](https://github.com/chocoemong17/chainbench/actions/runs/36882942845)
passed separately.

[PR #76](https://github.com/chocoemong17/chainbench/pull/76) uses the standard
macOS 26 Intel pool and preserves all six compatibility configurations. Its first
Intel run reported 12 exact-equality failures between independent
numerical reruns (1,276 tests passed). The repair allows only recomputed floats
to use the existing 1e-12 relative / 1e-14 absolute trajectory tolerance. Inputs,
configuration, hashes, structure, counts, statuses and missing values remain exact;
serialization and multiple views of the same stored record retain exact equality.
Nonfinite values remain errors. Thirty focused cases exercise the distinction,
including decoded floats versus NumPy float64.

That comparison repair exposed three remaining Intel failures (1,315 passed).
A complete diagnostic found larger late CG drift, up to 4.32e-4; thread limits
did not remove it. Controlled experiments isolated CG's scalar inner products.
The final repair uses compensated summation for those three quantities, preserving
matrix-vector products, true-residual stopping and the original comparison and
theorem thresholds. Fifteen further regressions cover cancellation, nonfinite
arithmetic, repeated problematic seeds and the exact-start contract.
[Diagnosis and numerical migration](https://github.com/chocoemong17/chainbench/blob/b857694bbdd4f314bbe2bf2d05629af02d829023/docs/CG_ARITHMETIC.md).
Rendering, package version and release assets remain unchanged, while finite CG
trajectories can differ from earlier builds.

The CG repair's [full run](https://github.com/chocoemong17/chainbench/actions/runs/36897340879)
passed seven jobs. Intel macOS passed 1,332 tests, including all CG regressions,
and failed one HTML retention test. That test compared a separately recomputed
GD chart with exact equality. The follow-up captures all charts actually passed
to the renderer and compares the full embedded records exactly. Remaining
vector-based independent rerun checks use the unchanged strict comparator.
Runtime arithmetic and comparison tolerances are unchanged by this follow-up.

The next [minimum-dependency run](https://github.com/chocoemong17/chainbench/actions/runs/36901800433/job/110502506552)
failed 17 tests and passed 1,316 because a Frank–Wolfe segment independently
reevaluated the actual next objective. Five jobs passed; the browser and macOS
jobs were cancelled when the repair superseded this head. The native dedicated
audit did not reproduce the failure. A controlled Prescott-kernel run did:
0.38999999999999996 versus stored 0.39, with no coordinate difference.
The segment now validates and retains the actual stored next objective. It keeps
the scheduled path, exact identity checks and independent 60-digit Decimal audit.
Seven regressions cover value retention, integration and invalid data. The
[controlled repair run](https://github.com/chocoemong17/chainbench/actions/runs/36904276640)
passed all twelve cases, budgets 1/18/60 with three repeats, the Decimal audit,
and 60 focused tests per kernel on Prescott, Sandybridge and Haswell.
The initial probe's two incorrect new fixtures and their correction remain in
[issue #78](https://github.com/chocoemong17/chainbench/issues/78). Kernel forcing is
confined to the diagnostic branch.

PR #76's final tested head was `77d29114c2f0281e7387c1c7bf52308f7bd164ce`.
Its [full PR CI](https://github.com/chocoemong17/chainbench/actions/runs/36904513888)
passed all eight jobs, including 1,340 tests in each of six compatibility
configurations. It was merged as main `e3858108ea492df04121c14d5306ac2bab1454fa`.
The merged tree `260bcb2433eb518b039130353c922494fe424126` is identical to the tested
candidate's tree. The separate [main push CI](https://github.com/chocoemong17/chainbench/actions/runs/36907555600)
then passed all eight jobs and 1,340 tests per configuration again, including
minimum NumPy and Intel macOS. Clean wheel/sdist installations, the full offline
desktop/mobile/no-script browser scope and existing fault injections passed.

The [main cloud run](https://github.com/chocoemong17/chainbench/actions/runs/36907555063)
passed generation of 25 HTML pages, independent audits of 24 numerical records,
and the two-page PDF. It used the same complete-tour manifest as the PR:
`4336dc564fcc5e8e751c6db90a2cb885935d09b3efa21637653b800945662564`.
[Main verification](main-e385810-verification.json),
[final PR verification](pr76-fw-repair-verification.json),
[CG diagnosis](cg-reduction-diagnosis.json) and
[FW diagnosis](fw-segment-diagnosis.json) retain exact job/artifact identifiers
and actual outcomes. The earlier failed and cancelled runs remain separate.


The handoff priorities were checked against the integrated source:

| Requirement | Source or evidence | Scope |
| --- | --- | --- |
| Paper-specific reproduced result with source and differences | [docs/SHEWCHUK_REPRODUCTION.md](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/docs/SHEWCHUK_REPRODUCTION.md); [docs/FISTA_DEBLURRING.md](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/docs/FISTA_DEBLURRING.md); [docs/HEAVY_BALL_COUNTEREXAMPLE.md](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/docs/HEAVY_BALL_COUNTEREXAMPLE.md) | Selected numerical examples/protocols, not entire papers. |
| Meaningful geometry coupled to actual iterates | [docs/SIMPLEX_GEOMETRY.md](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/docs/SIMPLEX_GEOMETRY.md); [docs/PROXIMAL_GEOMETRY.md](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/docs/PROXIMAL_GEOMETRY.md); [docs/ADMM_GEOMETRY.md](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/docs/ADMM_GEOMETRY.md); [docs/LANDSCAPE_CONTEXT.md](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/docs/LANDSCAPE_CONTEXT.md) | Controlled examples with explicit input and projection conventions. |
| Breadth including inconvenient cases | [docs/STRESS_SAMPLING.md](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/docs/STRESS_SAMPLING.md); [scripts/check_tour_browser.py](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/scripts/check_tour_browser.py); [tests/test_stress_cases.py](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/tests/test_stress_cases.py) | Eight topics and every seed 0–31; unresolved ratios retained, finite synthetic scope. |
| Connected bilingual explanations | [docs/LEARNING_WORKFLOWS.md](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/docs/LEARNING_WORKFLOWS.md); [src/chainbench/mechanisms.py](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/src/chainbench/mechanisms.py); [docs/REVIEW_GUIDE.md](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/docs/REVIEW_GUIDE.md) | Motivation, recurrence, assumptions, bounds, trade-offs and neighboring methods. |
| Auditable raw results and no unsupported rankings | [docs/SOURCE_MAP.md](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/docs/SOURCE_MAP.md); [scripts/smoke_workflows.py](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/scripts/smoke_workflows.py); [scripts/render_review_packet.py](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/scripts/render_review_packet.py) | 24 independent record audits; numerical agreement does not prove a theorem. |
| Readable offline desktop/mobile UI and PDF | [browser workflow](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/.github/workflows/tests.yml); [scripts/render_review_packet.py](https://github.com/chocoemong17/chainbench/blob/e3858108ea492df04121c14d5306ac2bab1454fa/scripts/render_review_packet.py); cloud/33b6243/browser-gallery | Full browser matrix plus selected actual visual inspection; PDF archive stable, Actions HTML retention7days. |
| GitHub implementation, PR and full CI | PR73; PR76; final main e3858108ea492df04121c14d5306ac2bab1454fa | Original PR fully passed; original main had seven passes plus an ARM64 allocation cancellation. Final PR76/main outcomes are recorded above. |
| Local folder below1GB | [storage record](storage-usage.json) | About89MB allocated; all full tests/builds/rendering on GitHub. |

The PDF above was generated from final main
`e3858108ea492df04121c14d5306ac2bab1454fa` by the linked cloud run. Both pages
were opened and visually inspected; the artifact digest and four output hashes
matched. Its complete-tour manifest is identical to the tested PR's manifest.
The five general geometry previews remain pinned to the earlier fully passing
`33b62430c98c94aa822fcf7101c03d458a7fb308`; the later PR73 head changed ten Markdown
files only. The older PDF snapshot also remains archived. PR76 additionally repairs CG scalar arithmetic and Frank–Wolfe stored-objective
retention, tests, documentation and the macOS runner label. FISTA's computation and the rendering source remain
unchanged; the original CG gallery is explicitly a historical computation snapshot.
The [two fresh CG desktop/mobile views](../b857694/cg-repair) identify the repaired
runtime revision, their actual successful browser job and the separate full-run
failure. Both PNGs were opened and visually inspected; their SHA-256 and source
tree are recorded with the gallery. The later test changes and Frank–Wolfe value-retention repair do not alter these CG views.
Both PDF pages and all five PNGs were visually inspected. Their
artifact and output hashes were verified; the archived blobs' hashes and sizes
were then verified remotely. These display samples supplement the complete input
grids in the reports. They do not constitute independent outside review.

The [main cloud run](https://github.com/chocoemong17/chainbench/actions/runs/36907555063)
provides the actual full HTML reading bundle. Download the reading-bundle artifact,
extract the entire folder and open `index.html`. Actions downloads require GitHub
sign-in and expire after seven days. The archived PDF, gallery and source remain
available; the workflow can regenerate the HTML.

## History and remaining scope

Stacked PRs #46, #48, #50, #52, #54, #56, #58, #60, #62, #64, #66, #68, #70 and #72
were closed as superseded by #73. Their original descriptions, branches and
validation histories were retained. Integration is attributed to #73.

The initial Windows run exposed 12 fixture-decoding failures (1,276 passed).
Explicit UTF-8 fixture reads fixed them while retaining native platform locale
and assertions. Two PDF runs exposed narrow font assumptions; the final renderer
checks actual Type 3 glyph programs as well as embedded font files. Failed and
superseded/cancelled runs remain documented in #73.

PR76 also preserves the real [Intel rerun failure](https://github.com/chocoemong17/chainbench/actions/runs/36886268728/job/110450689899)
and the first comparator's [NumPy/decoded-float mismatch](https://github.com/chocoemong17/chainbench/actions/runs/36890580767/job/110464886744)
(1,310 tests passed). Neither failed nor superseded run is counted as a final pass.
New Intel results do not establish new Apple Silicon coverage.

The handoff's selected-paper, geometry, breadth, explanation and review requirements
are implemented. Broad historical issues #39/#40 still include separate requests,
such as a browser-driven local studio and saved-record comparison, beyond this
integration. Future work should start from actual reader feedback and concrete
defects, while preserving the current source-to-recurrence contracts.
There is no universal algorithm ranking, theorem proof from finite tests,
production-solver claim, or outside-adoption claim.

The frozen v0.5.0 release remains at `43ba91a8e7fe8d4baf287e3faa154ab5a5819c31`.
Its tag/assets, package version and historical review kit were preserved.
This integration did not trigger release publication. Runtime dependencies remain
NumPy only. Paper PDFs and installed dependencies are absent from the source tree.

The user's entire local task folder occupies about 89 MB, below the 1 GB ceiling.
Builds, full tests and report generation ran on GitHub. Only a small source checkout,
migration receipts and budgeted inspection files are retained locally.
