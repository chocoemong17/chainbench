# Work and read on GitHub

The repository and pull requests are the source of truth. Full tests, clean
package installation, browser checks and report generation run on GitHub Actions.
The local task folder has a strict 1 GB ceiling; generated copies are disposable.

The **tests** workflow calls the reusable **cloud reading bundle** workflow, which
generates the complete 25-page Korean/English
tour and independently audits every file, link and all 24 numerical records.
Open the workflow run's **Artifacts** section, download `chainbench-reading-bundle-<commit>`,
extract it and open `index.html`. The recipient needs no Python or server.
Artifacts expire after seven days; rerun the workflow to regenerate them.
Manual cloud generation is also available. For the versioned ZIP and PDF, use the
[release download guide](OFFLINE_DOWNLOAD.md); those assets are separate from
temporary Actions retention and appear only after the publication gate completes.

The same run also uploads `chainbench-review-packet-<commit>`, a small artifact
containing the Korean two-page FISTA comparison PDF, two previews rendered from
the PDF, its HTML and `evidence.json`. The renderer first independently audits all
24 tour records, then reuses the actual first rejected candidate SVG and the
index's two flows and seven comparison rows. It derives counts from the records,
checks layout boundaries, figure loading, PDF page count and embedded CJK fonts.
The evidence binds the source commit, tour manifest fingerprint and output hashes.
The PDF makes no claim about other CI jobs or independent review.

The job packages the exact audited tour and review packet into
`chainbench-<version>-reading.zip`, alongside a standalone copy of the same PDF and
`reading-verification.json`. A strict member manifest covers all 35 ZIP entries
(25 HTML pages, original tour manifest, seven review files, README and bundle
manifest). Source/version bindings, hashes, sizes, member types and PDF identity
are checked before extraction. The extracted ZIP then goes through the existing
offline Chromium tour checks at 1440px and 390px, including no-script reading.
The `chainbench-reading-release-<commit>` artifact contains these three assets;
`chainbench-extracted-browser-<commit>` retains the browser evidence.

GitHub requires sign-in to download Actions artifacts. Select a completed run
whose source revision matches the candidate you want to inspect. Pull-request
runs use GitHub's merge commit, so their artifact suffix may differ from the PR's
head SHA; the review packet's `source-commit.txt` and evidence identify the actual checkout.
The commit and its tree remain available after the artifact expires.

The original `chainbench-reading-bundle-<commit>` artifact retains exactly the
generated tour files so it can be audited again with `validate_tour`. The release
ZIP adds `README.txt`, `bundle-manifest.json` and `review/`; its verifier checks
those additions separately. To use the original strict tour validator after
extraction, supply only the files listed by the original `manifest.json`.

The rendering tools (pinned Playwright and PyMuPDF, Chromium, Noto CJK fonts) are
installed only on the ephemeral runner. They are not package runtime dependencies.
To reproduce this step in an environment that already has those tools, run it
after tour generation, keeping metadata outside the tour directory:

```bash
python scripts/render_review_packet.py --tour reading-bundle --output review-packet \
  --run-url https://github.com/chocoemong17/chainbench/actions/runs/ACTUAL_RUN_ID
```

Replace `ACTUAL_RUN_ID` with the real generation run. Existing output directories,
incomplete tours and missing evidence are rejected. A failed render leaves no
finished packet directory. The workflow stores outputs on GitHub; do not create
local copies of the full test/build/report matrix.

The tests workflow has nine jobs: six compatibility configurations, the complete
offline report browser suite, cloud reading generation, and clean wheel/sdist
installation. The installation job downloads the reading assets from the same
workflow run, binds them to the same commit and validates all eight release files.
A successful reading job does not substitute for the remaining CI jobs.

The main-only release workflow calls this full suite. Its publishing job downloads
the exact already-tested `distributions-<run-id>` artifact; it does not rebuild
packages or regenerate reports. The publisher rechecks all eight files, source
and internal ZIP bindings before a release write, then downloads uploaded assets
again and verifies their bytes before publication. Prior releases stay unchanged.
[Release protocol](../RELEASING.md).

The macOS Python 3.12 gate uses GitHub's standard `macos-26-intel` runner.
The earlier `macos-latest` ARM64 job was cancelled without acquiring a runner;
[GitHub recorded its capacity constraint](https://github.com/chocoemong17/chainbench/actions/runs/36882942713/job/110439029108).
The Intel runner keeps the complete test suite and the same macOS generation.
It is a free standard runner for this public repository, as listed in
[GitHub's runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
Current Intel passes establish that environment's result; earlier Apple Silicon
passes and the cancelled attempt remain separate evidence.

The first Intel run then exposed 12 tests that required exact equality across
independent floating-point computations (1,276 passed). [Issue #77](https://github.com/chocoemong17/chainbench/issues/77)
records the failure and the stricter distinction between numerical rerun comparison
and exact serialization/provenance. This result is separate from the earlier
ARM64 allocation failure; it is not counted as a passing validation.

A stricter follow-up passed 1,315 Intel tests and failed three CG comparisons.
Full-array diagnosis then found larger late trajectory drift; single-thread
execution did not resolve it. The scalar-accumulation repair preserves the
original comparison tolerance, matrix-vector products and stopping contract.
[Actual runs, controlled experiments and limits](CG_ARITHMETIC.md).

The 2026-10-01 migration uploads the accumulated implementation, including the
latest FISTA backtracking reading path. Previous local browser checks covered
25 pages and 1,580 backtracking trial states across desktop/mobile. The final
local full suite was interrupted after 1,122 completed tests; that interrupted
run is not a complete pass. Current remote CI provides the candidate's status.

The first consolidated remote run passed Linux/macOS, clean installation and
browser checks but failed 12 Windows tests because test fixtures were decoded
with cp1252. Explicit UTF-8 fixture reads repair this in the follow-up commit;
[issue #74](https://github.com/chocoemong17/chainbench/issues/74) preserves the failure.
See [PR #73](https://github.com/chocoemong17/chainbench/pull/73) for current results.
