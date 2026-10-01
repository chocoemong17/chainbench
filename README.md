# Preserved development reviews and verified cloud outputs

Current source: [main afa81a6](https://github.com/chocoemong17/chainbench/tree/afa81a6cf33c56d955ef60a5840d2a2cb94722e4).
[Separate main push CI](https://github.com/chocoemong17/chainbench/actions/runs/36926953569)
passed all eight jobs, with 1,437 tests in each of six environments, both clean
installs, the five-file publication gate, five fault injections and full browser checks.
[Main verification](cloud/main-afa81a6/verification.json) and
[PR 82 history](cloud/main-afa81a6/pr82-verification.json) retain actual completed-log
checks and distinct superseded candidates. This change tightens saved-comparison
publication evidence; the historical rendered review packets below keep their
original source identities.

Latest development review: [saved-experiment comparison PDF](cloud/comparison-c16e8a9/ChainBench_saved_comparison_review.pdf)
and [actual offline HTML, input records and verification](cloud/comparison-c16e8a9).
Compare two to four stored runs with explicit setup/input/environment differences.
Its full PR gate passed all eight jobs, including 1,394 tests per configuration.
The packet is pinned to the tested PR; its tree is identical to main f8fdc61.
Prior verified source: [main f8fdc61](https://github.com/chocoemong17/chainbench/tree/f8fdc61502426a0f60c99274e4960bf568812b45).
[Separate main push CI](https://github.com/chocoemong17/chainbench/actions/runs/36919253999)
passed all eight jobs: 1,394 tests in each of six environments, both clean
installations and the complete browser checks. [The completed main verification](cloud/main-f8fdc61/verification.json)
retains all job IDs, actual-log checks and separate cloud output hashes.

For the broader optimization toolkit, start with the [two-page Korean FISTA PDF](cloud/e385810/ChainBench_FISTA_review.pdf),
[five geometry previews](cloud/33b6243/browser-gallery), or
[CG desktop/mobile views after the arithmetic repair](cloud/b857694/cg-repair).
Each review records its source revision and actual verification scope.

The [integration and validation record](cloud/integration-20261001) maps the
handoff requirements to the implemented source and retains the real CI history.
Prior integrated source: [main commit e3858108ea492df04121c14d5306ac2bab1454fa](https://github.com/chocoemong17/chainbench/tree/e3858108ea492df04121c14d5306ac2bab1454fa).

For the complete interactive tour, download the reading-bundle artifact from the
[verified current-main cloud run](https://github.com/chocoemong17/chainbench/actions/runs/36926953557),
extract the folder and open `index.html`. The 25 HTML pages retain all 24 numerical
records for offline reading. Actions downloads require GitHub sign-in and expire
after seven days; the source workflow can regenerate them. The previews on this
branch remain directly accessible.

## Historical source and reviews

The original migration preserves 41 generated review PDFs and two source archives.
Their SHA-256 and Git blob identifiers are in [manifest.json](manifest.json).
Later cloud reviews have their own evidence files; the original migration manifest
does not describe those additions. Historical PDFs do not establish current CI
status or independent outside review.

`source/all-local-refs.bundle` preserves the development commits and branch names
captured on 2026-10-01. Inspect it with `git bundle list-heads`, or recover it with
`git clone source/all-local-refs.bundle recovered`.
`source/pre-migration-source.tar.gz` preserves the source before the cloud-workflow
change, including the then-uncommitted FISTA tour edits.

Full tests, package installation and report generation now run on GitHub Actions.
The source and review records are preserved here while disposable generated copies
are regenerated as needed. The frozen v0.5.0 release remains unchanged.
