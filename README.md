# Preserved development reviews and verified cloud outputs

Start with the [two-page Korean FISTA PDF](cloud/e385810/ChainBench_FISTA_review.pdf),
[five geometry previews](cloud/33b6243/browser-gallery), or
[CG desktop/mobile views after the arithmetic repair](cloud/b857694/cg-repair).
Each review records its source revision and actual verification scope.

The [integration and validation record](cloud/integration-20261001) maps the
handoff requirements to the implemented source and retains the real CI history.
Current integrated source: [main commit e3858108ea492df04121c14d5306ac2bab1454fa](https://github.com/chocoemong17/chainbench/tree/e3858108ea492df04121c14d5306ac2bab1454fa).

For the complete interactive tour, download the reading-bundle artifact from the
[verified main cloud run](https://github.com/chocoemong17/chainbench/actions/runs/36907555063),
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
