# Cloud-generated FISTA reading packet

Open [the two-page PDF](ChainBench_FISTA_review.pdf), or the rendered [first](page-1.png)
and [second](page-2.png) pages. This small packet is archived here so its availability
is not tied to the seven-day Actions artifact retention. It was generated on GitHub,
not by a local report build.

- Source PR head: `33b62430c98c94aa822fcf7101c03d458a7fb308`.
- Actual Actions checkout: `543c2065c9a01afe0919787f5b1535bcfd329d31`.
- Both have tree `16416d9a13fa17092de4931f2455fa64a5862bf8`.
- [Successful generation and record audit](https://github.com/chocoemong17/chainbench/actions/runs/36878546599).
- [Full CI for this candidate](https://github.com/chocoemong17/chainbench/actions/runs/36878546485): inspect the actual run status; the PDF job does not certify it.
- [Development PR and preserved failures](https://github.com/chocoemong17/chainbench/pull/73).

The guide uses the actual rejected FISTA candidate plot, two symbolic flows and
seven comparison rows from the extended tour. All24 numerical records were audited
before rendering. Counts come from the records:25 HTML pages,36 backtracking runs,
790 candidate trials,18 accepted updates per run. The report distinguishes local
candidate acceptance from a global majorization claim and does not rank runtime.

Both PDF pages were visually inspected after download. Font validation checks
actual Korean headings plus embedded font files or Type3 glyph programs; layout
and image checks passed. `evidence.json` contains source, environment, manifest and
output fingerprints. The exact artifact SHA256 is
`7621e98c7a38b86607accb3de9c744f62da1c59d7947b5701898103ca07c94ca`.
The downloaded archive and all four recorded output hashes matched.
This is maintainer validation, not independent outside review.
