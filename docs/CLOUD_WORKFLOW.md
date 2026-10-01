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

The same run also uploads `chainbench-review-packet-<commit>`, a small artifact
containing the Korean two-page FISTA comparison PDF, two previews rendered from
the PDF, its HTML and `evidence.json`. The renderer first independently audits all
24 tour records, then reuses the actual first rejected candidate SVG and the
index's two flows and seven comparison rows. It derives counts from the records,
checks layout boundaries, figure loading, PDF page count and embedded CJK fonts.
The evidence binds the source commit, tour manifest fingerprint and output hashes.
The PDF makes no claim about other CI jobs or independent review.

GitHub requires sign-in to download Actions artifacts. Select a completed run
whose source revision matches the candidate you want to inspect. Pull-request
runs use GitHub's merge commit, so their artifact suffix may differ from the PR's
head SHA; the review packet's `source-commit.txt` and evidence identify the actual checkout.
The commit and its tree remain available after the artifact expires.

The reading bundle retains exactly the generated tour files so it can be audited
again with `validate_tour`. Source/environment notes stay with the review packet,
outside the tour's strict manifest coverage.

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

The tests workflow retains the full cross-platform suite, wheel/sdist clean
installation and offline browser checks. A successful reading-bundle job does
not substitute for the remaining CI jobs. Existing releases stay unchanged.

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
