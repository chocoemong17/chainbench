# Read the complete tour without installing Python

The v0.6.0 alpha provides the full Korean/English reading tour and a short PDF
guide as named assets on the [GitHub release](https://github.com/chocoemong17/chainbench/releases/tag/v0.6.0).
During release preparation these links become available only after the main-branch
validation and publication gates finish; a version number in source is not a release.

1. Start with the [two-page FISTA PDF](https://github.com/chocoemong17/chainbench/releases/download/v0.6.0/chainbench-0.6.0-review.pdf).
   It introduces fixed and backtracking steps with an actual rejected proposal,
   two update flows and a comparison table.
2. Download [chainbench-0.6.0-reading.zip](https://github.com/chocoemong17/chainbench/releases/download/v0.6.0/chainbench-0.6.0-reading.zip).
   Extract the **whole archive**, then open `index.html` in a browser. Keep the
   files together so links between the 25 HTML pages continue to work.
3. Follow the [short reading route](REVIEW_GUIDE.md#a-short-reading-route): image
   reconstruction, step selection, motion in space, and several inputs. Switch
   between Korean and English inside each report. Native text, figures and tables
   remain available with JavaScript disabled; interactive controls require it.

The reading ZIP is the named asset above. GitHub's automatic **Source code (zip)**
download contains implementation files, not these generated reports. No Python,
server or account is needed after extraction. Reading and controls work offline;
opening an external paper link needs a connection. A mobile browser may require
its file manager to extract the archive before opening HTML.

The PDF summarizes one comparison. The full tour retains all declared cases and
24 numerical records across published protocols, changed inputs, illustrations,
stress samples, counterexamples and sharp constructions. Those categories remain
explicit: a computed example does not prove a theorem or a universal ranking.

## What the download records

`README.txt` names the version and source commit. `manifest.json` retains the
original tour inventory and file hashes. `bundle-manifest.json` additionally
covers the guide and `review/` files. `review/evidence.json` records the renderer,
source commit, actual numerical audit, PDF layout and embedded-font checks.
The standalone PDF has exactly the same bytes as the PDF inside `review/`.

The release also includes `reading-verification.json`, the wheel, source package,
clean-install `verification.json`, `build-environment.txt` and `SHA256SUMS`:
eight named assets in total. With all eight files in one directory, this checks
their recorded hashes on systems providing `sha256sum`:

```bash
sha256sum -c SHA256SUMS
```

Hashes establish byte consistency with the supplied manifest. They do not certify
independent scientific replication or authenticate an outside reviewer. The
[release gate](../RELEASING.md) also checks source bindings, the entire ZIP inventory
and internal hashes, both clean package installations, and the extracted ZIP in
offline desktop/mobile Chromium. Publication downloads the uploaded files again
and verifies them before exposing the prerelease.

## Inspect an unreleased change

A successful [tests run](https://github.com/chocoemong17/chainbench/actions/workflows/tests.yml)
provides `chainbench-reading-release-<commit>` containing the same three reading
assets. Actions downloads require GitHub sign-in and expire after seven days.
Release assets are separate from that temporary Actions retention. Select the
exact source commit you intend to review; PR artifacts use the tested merge
commit. [Cloud workflow details](CLOUD_WORKFLOW.md).

For a small, already published preview during release preparation, use the
[archived FISTA PDF](https://github.com/chocoemong17/chainbench/blob/archive/local-reviews-20261001/cloud/e385810/ChainBench_FISTA_review.pdf)
and [geometry views](https://github.com/chocoemong17/chainbench/tree/archive/local-reviews-20261001/cloud/33b6243/browser-gallery).
These are identified historical snapshots, with their own source and evidence.
