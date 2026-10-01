# Work and read on GitHub

The repository and pull requests are the source of truth. Full tests, clean
package installation, browser checks and report generation run on GitHub Actions.
The local task folder has a strict 1 GB ceiling; generated copies are disposable.

The **cloud reading bundle** workflow generates the complete 25-page Korean/English
tour and independently audits every file, link and all 24 numerical records.
Open the workflow run's **Artifacts** section, download `chainbench-reading-bundle-<commit>`,
extract it and open `index.html`. The recipient needs no Python or server.
Artifacts expire after seven days; rerun the workflow to regenerate them.
The artifact is a development reading bundle, separate from gated releases.

The tests workflow retains the full cross-platform suite, wheel/sdist clean
installation and offline browser checks. A successful reading-bundle job does
not substitute for the remaining CI jobs. Existing releases stay unchanged.

The 2026-10-01 migration uploads the accumulated implementation, including the
latest FISTA backtracking reading path. Previous local browser checks covered
25 pages and 1,580 backtracking trial states across desktop/mobile. The final
local full suite was interrupted after 1,122 completed tests; that interrupted
run is not a complete pass. Current remote CI provides the candidate's status.
