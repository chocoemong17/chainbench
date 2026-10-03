# Choose conditions, compute, then keep the actual inputs

Open [the two-page studio PDF](ChainBench_studio_review.pdf), or download
[the complete small review ZIP](reading-review.zip). The ZIP retains actual
browser-downloaded input/result JSON, standalone reports, desktop/mobile images,
the PDF and the source-bound browser verification. Extract it to read offline.

Three selected reports are also available directly: [quadratic](quadratic-0-1440.html),
[diagonal LASSO](diagonal-lasso-0-1440.html) and [simplex](simplex-0-1440.html).
The complete packet retains both seeds and both viewport sizes; these three
copies are reading examples rather than a selection of favorable outcomes.

The source is tested PR merge `a23d54a72d52516399fa17a668fb1ca336f87579`, for
[PR #88](https://github.com/chocoemong17/chainbench/pull/88) head
`8673fc1ebbddffa293fa04b06035381365adb0bc`. Their Git tree is identical:
`760a8ccec0b46802593d94597ef94c7e90caab79`.
[All nine PR CI jobs passed](https://github.com/chocoemong17/chainbench/actions/runs/36947994005).
Completed source-checked logs record 1,680 passed tests in all six compatibility
configurations, including Intel macOS (1,593.76 seconds). Both clean installations,
eight targeted fault injections, full browser and audited reading checks passed.
PR #88 is merged as main `617f6230d2ad97f6b4ae8a141c471c64e7a1d04b`; its tree
is identical to the tested source. The [separate main CI](https://github.com/chocoemong17/chainbench/actions/runs/37102622981)
is in progress. A new release is not yet claimed.

The browser checks include twelve live cases, two selected-method runs, exact
JSON/HTML downloads, keyboard-selected rows, shutdown and 28 offline reads with
and without scripts. No external requests or JavaScript errors were observed.
The PDF is two pages; both were visually reviewed. All 51 review artifact members
were checked against their byte sizes and hashes. The artifact ZIP is 1,036,151
bytes with SHA-256 `288c49151535ce051575c65c244571004cd7c0790ca47f0ac49c1c251d6860db`.

[Browser evidence](browser-verification.json) binds actual files and source.
[PR validation and failure history](pr88-verification.json) records the genuine
outcomes and superseded attempts. Passing finite checks is not a theorem proof,
whole-paper replication or independent outside adoption. Package/runtime tests,
report generation and rendering run on GitHub; the user's local folder stays
below 1 GB. The existing v0.6.0 release remains unchanged.
