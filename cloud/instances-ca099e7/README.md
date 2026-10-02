# Stored inputs: inspect the numbers and rerun them

Start with the [two-page Korean review PDF](ChainBench_stored_inputs_review.pdf).
Download [the complete review ZIP](reading-review.zip), extract it and open
`imported-quadratic.html`, `imported-psd.html` or `replay.html`.
The ZIP retains all ten generated/imported input cases, eleven offline HTML
reports, actual JSON inputs/results, browser downloads, previews and verification.
No Python or server is needed to read the reports. New computation needs the
current development Python source; this workflow is not in frozen v0.6.0 assets.

The supplied nonzero start matters. The off-diagonal quadratic shows the actual
first steps of five existing methods. The PSD example reaches zero gap while
remaining distance 4 from the selected reference: reference distance is not
distance to the solution set. The HTML includes all actual rows, settings,
reference/input arrays, language switching and a keyboard-operable row inspector.

Source head: `ca099e718803a07c96c73ecda736f66c6d124e16`.
These exact reports were generated from tested PR merge
`2eeeb0825b63ee3c9a01cb2c08f849bf37f719e5`, whose tree
`1abac02dd4b7d2845e4ae50abf758d3bef8ef9af` is identical to merged main
`9fa4a6ec3e63f7ff815ad9165377e518325c79a1`.
[PR 86](https://github.com/chocoemong17/chainbench/pull/86) passed
[all nine CI jobs](https://github.com/chocoemong17/chainbench/actions/runs/36941657065)
on attempt 1: 1,576 tests in each of six environments, seven fault injections,
both clean distribution installations, strict publication evidence and all
existing/new browser and reading checks. [Verification and history](pr86-verification.json).
The separate [main push run](https://github.com/chocoemong17/chainbench/actions/runs/36944034726)
was still running when this PR review was archived; its outcome is tracked separately.

[The browser proof](browser-verification.json) records ten independent scalar
and input-byte audits, eleven reports at 1440px/390px, exact keyboard-selected
rows/downloads, no-script reading, no external requests or JavaScript errors,
and two complete PDF pages. Both PDF pages were visually inspected; the final
reference-distance panel uses a readable linear axis from zero. Every one of
71 ZIP members was checked against its recorded hash and length before archiving.

The PDF is 210,328 bytes, SHA-256
`7f9b2f36c978e9483f9da27bcb7031bea070f7dcef9b99220b7b7f7857244529`.
The ZIP is 989,213 bytes, SHA-256
`03bbdb25bd68b923ad3b4ca03bc635efbdfb0598a157780089f80728c6adbb1b`.
The three loose HTML copies exactly match their ZIP members. The ZIP is the
actual Actions artifact, not a local regeneration.

These are constructed public teaching inputs. Hashes bind internal contents;
MATCH reports agreement with a rerun within explicit tolerances. Neither proves
author identity, generation history, a theorem, paper-figure replication or
outside adoption. [Full schema, methods and limits](https://github.com/chocoemong17/chainbench/blob/9fa4a6ec3e63f7ff815ad9165377e518325c79a1/docs/STORED_INPUTS.md).
