# One offline reading path

Available in development source after v0.5.0:

```bash
python -m chainbench tour --lang ko --output tour
```

Open `tour/index.html` in a browser. The recipient needs no Python installation,
server, account, API key or network after someone generates the folder. Copy or
archive the **whole folder**, so relative page links remain intact. Public source
links are optional; embedded images, scripts and numerical records load locally.

## What is included

The command generates fourteen HTML files and one manifest, currently about 35 MB
uncompressed. It reuses existing computations with fixed, declared settings:

| Page | Settings | Evidence level |
| --- | --- | --- |
| `index.html` | Generated navigation and previews from the actual reports | Reading guide |
| `atlas.html` | All eight fixed topics and their existing canonical fixtures | Symbolic explanations + canonical observations |
| `shewchuk.html` | 12-update budget; published start and all nine added starts | Exact published setup + separate controlled variations |
| `simplex.html` | 18 updates; all 12 target/start combinations | Controlled geometry |
| `proximal.html` | 18 updates; both methods for all nine lambda/start combinations | Controlled geometry |
| `stress-<topic>.html` | Every topic; every seed 0–31; sampler v2 | Finite synthetic breadth |
| `tight-gd.html` | Horizon 20; h=L=R=1 | Public tight construction within its stated scope |

The index asks what to read next and distinguishes these evidence levels. The
previews are extracted from the actual generated SVGs. They are static: full
interactive controls, raw samples and limitations remain in the linked reports.
Every report has a return-to-tour link. Both Korean and English and native
no-JavaScript reading are supported.

The stress interval is fixed in advance, not selected by performance. Across
quadratics it contains two full cycles of the declared dimension/orientation/start
strata. All 256 sampled rows remain available, including unresolved ratios; seed
24 of ISTA/FISTA is one such unresolved row. This is finite synthetic coverage,
not representative real-world data, a performance ranking or a theorem proof.

## Files, settings and hashes

`manifest.json` records the package/NumPy/Python/OS environment, language, entry
page, each artifact's evidence level and reproduction command, applicable source
and case settings, exact UTF-8 byte length and SHA-256. Commands omit `--output`;
append it with a new filename to generate a separate standalone report. The tour
adds navigation, so its file hash intentionally differs from a standalone export.
The numeric record remains the same.

Hashes cover the listed HTML files. The manifest does not hash itself and is not
an author signature, independent review or proof. Generated timestamps and absolute
paths are omitted; environment or numerical-library changes can still alter bytes.

The parent directory must exist. The command stages calculations in a temporary
sibling folder, then creates a **new** destination exclusively. It has no overwrite
flag. Existing files, directories and symlinks are refused before computation.
If calculation fails, no destination is created; if destination writing fails,
files created by that attempt are removed. The manifest is written last.

## Validation

Tests and installed wheel/sdist smoke inspect every file hash, local path/anchor,
return link, all eight topics and all 32 seeds. Numerical validators check the
published example and both geometries; installed standalone commands must reproduce
selected tour records exactly, including the unresolved case. Missing or changed
artifacts and injected calculation/write failures are exercised.

Browser CI opens all thirteen reports from the index and returns from each at
1440px and 390px, verifies loaded previews and the preserved unresolved row, and
checks language, overflow, offline operation and a no-JavaScript reading path.
The release gate requires `offline_tour: matched` for both distribution formats.

No tour or release is hosted or published by this command. Generated results should
be reviewed before sharing; prior releases and the frozen v0.2.0 kit are unchanged.
