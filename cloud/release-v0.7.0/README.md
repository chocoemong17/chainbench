# v0.7.0 release and verification

[Open the two-page Korean FISTA PDF](https://github.com/chocoemong17/chainbench/releases/download/v0.7.0/chainbench-0.7.0-review.pdf)
or download the [25-page reading ZIP](https://github.com/chocoemong17/chainbench/releases/download/v0.7.0/chainbench-0.7.0-reading.zip).
Extract the whole ZIP and open `index.html`. The reports retain numerical records, all declared cases and bilingual/offline controls.
The PDF explains fixed versus backtracking steps; it is a focused reading guide, not a summary of every new feature.

For the new choose-compute-download workflow, read the
[studio PDF from the tested development snapshot](../studio-8673fc1/ChainBench_studio_review.pdf)
and [v0.7.0 studio guide](https://github.com/chocoemong17/chainbench/blob/v0.7.0/docs/STUDIO.md).
Choose conditions in a loopback-only Python studio, download the actual arrays and result,
and replay those exact inputs. The precomputed reading ZIP does not start the studio.

## Source and separate checks

The [published experimental alpha](https://github.com/chocoemong17/chainbench/releases/tag/v0.7.0)
uses main `fccd654e85cd544fc1a33d7467df93babd4edd2a`,
tree `25511845e2a974ef15dd7249edadf3ab2e1bc3ab`.
That is the same tree as PR #89 head `816cdc8` and tested merge `317a53e`.

- [PR #89](https://github.com/chocoemong17/chainbench/pull/89): [nine-job CI](https://github.com/chocoemong17/chainbench/actions/runs/37103050217) and [verification](pr89-verification.json).
- Separate main push: [nine-job CI](https://github.com/chocoemong17/chainbench/actions/runs/37104389006) and [verification](main-verification.json).
- Main-only release: [nine validation jobs plus publication](https://github.com/chocoemong17/chainbench/actions/runs/37104389180) and [verification](release-workflow-verification.json).
- [Unauthenticated public byte verification](public-download-verification.json) streams all eight assets, checks GitHub digests and all seven checksum payloads, reads actual public install/reading JSON, and checks source and package bindings.
- [Handoff completion audit](completion-audit.json) records the implemented scope and its remaining limits.

Each of the six compatibility configurations passed 1,680 tests. The gates include
eight detected injected faults, both clean wheel/sdist installations, actual studio runs,
exact-input replay, the full offline browser suite and source-bound reading generation.
The publisher used the distributions and reading assets from its own successful run.
The separate main run has distinct generated-output bytes and is not substituted for release evidence.

The final 286,163-byte PDF has SHA-256
`d3dba073f103866c958dc9455d77fd63704eb3ed2ceda8fbdbc8520224cf676a`.
Its cloud-rendered page previews were visually inspected; both pages are readable without clipped plots, tables or source footers.
The 44,961,065-byte reading ZIP has SHA-256
`f21ac82500773b532b5e5d61c1e276d563a800d12021a5137eab5904a2ccb901`.
The public files are linked instead of duplicating the large ZIP in Git.

All eight older tag targets, eight releases and 43 named assets are preserved.
The frozen v0.2.0 review source is unchanged.
PR #89's earlier candidate was cancelled after finding stale citation metadata; that history
remains in its record. The studio's genuine earlier failing candidates remain in its own archive.

Finite synthetic observations and implementation checks do not prove theorems, establish
whole-paper reproduction or supply independent outside adoption. No OSS application was submitted.
Full execution and rendering occurred on GitHub Actions; only small source/metadata and necessary review previews were kept locally.
