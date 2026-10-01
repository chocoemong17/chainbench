# FISTA reading packet from the integrated main

Open [the two-page Korean PDF](ChainBench_FISTA_review.pdf), or the rendered
[first](page-1.png) and [second](page-2.png) pages. This packet is preserved on
GitHub independently of the temporary Actions artifact lifetime.

- Source: `e3858108ea492df04121c14d5306ac2bab1454fa`.
- Tree: `260bcb2433eb518b039130353c922494fe424126`.
- [Successful generation and numerical audit](https://github.com/chocoemong17/chainbench/actions/runs/36907555063).
- [Full main CI](https://github.com/chocoemong17/chainbench/actions/runs/36907555600),
  separate from the PDF-generation result.
- [Integration, actual failures and repairs](../integration-20261001).

The packet follows fixed-curvature FISTA and backtracking step selection using
the actual rejected candidate curve, two symbolic flows and seven comparison
rows from the generated tour. All 24 numerical records were audited before
rendering. The counts come from those records: 25 HTML pages, 36 backtracking
runs, 790 candidate trials and 18 accepted updates per run. Candidate acceptance
is distinguished from global majorization and from runtime comparisons.

Both PDF pages were opened and visually inspected. Korean headings, the curve,
formula labels and comparison table are legible within the page boundaries.
The cloud renderer also checked layout, image loading and embedded font files
or Type 3 glyph programs. The artifact ZIP's SHA-256 was
`7037123d7837d8d41de8986fee4314963debb5284fe59b24b95ae196fadee6d7`;
all four output sizes and hashes matched `evidence.json` after extraction.
The evidence binds the source, environment and full-tour manifest.

For the complete interactive pages, download `chainbench-reading-bundle-e3858108ea492df04121c14d5306ac2bab1454fa`
from the generation run, extract the entire folder and open `index.html`.
Actions downloads require sign-in and expire after seven days. This PDF, its
previews and the source remain accessible here. These are finite educational
examples and internal checks, not independent outside review.
