# ChainBench v0.6.0 — a complete offline paper-reading tour

This experimental alpha brings the post-v0.5.0 explanations into one versioned
package and downloadable reading bundle. Read 25 Korean/English HTML pages
without installing Python, or install the wheel to generate and inspect your own
declared examples. NumPy remains the only runtime dependency.

## Begin with the actual reports

Download `chainbench-0.6.0-reading.zip`, extract the whole archive and open
`index.html`. The separate `chainbench-0.6.0-review.pdf` is a two-page FISTA guide
using an actual rejected step, symbolic update flows and a comparison table.
The same PDF and its layout/font audit are inside the ZIP.
[Download instructions and reading route](https://github.com/chocoemong17/chainbench/blob/v0.6.0/docs/OFFLINE_DOWNLOAD.md).

- Follow published examples from Shewchuk's CG exposition, Beck–Teboulle image
  experiments and Strohmer–Vershynin sampling. Each report names the implemented
  protocol, new or changed inputs, and omitted scope; it does not claim to match
  every figure or endpoint in the paper.
- Inspect actual 2D contours and projected 3D paths for quadratic methods,
  simplex oracle steps, proximal shrinkage, ADMM's solve/shrink/dual stages and
  all 36 FISTA backtracking cases. Review rejected proposals and local models.
- Compare several seeds, starts and dimensions; inspect 18 CG spectral examples,
  expectation calculations, sharp constructions and heavy-ball/Adam failure
  examples. Finite samples, illustrations and literature guarantees are labelled
  separately. [Exact source map](https://github.com/chocoemong17/chainbench/blob/v0.6.0/docs/SOURCE_MAP.md).
- Use the bilingual eight-topic atlas, symbolic update flows, method comparisons,
  local report links, keyboard controls and no-script text/figures/tables.
- Compare two to four saved experiment records with `chainbench compare`.
  The report retains original samples and provenance, lists setup differences,
  and overlays methods only when the complete recorded problem agrees.
  [Comparison contract](https://github.com/chocoemong17/chainbench/blob/v0.6.0/docs/SAVED_COMPARISON.md).

## Install or verify

```bash
python -m pip install https://github.com/chocoemong17/chainbench/releases/download/v0.6.0/chainbench-0.6.0-py3-none-any.whl
python -m chainbench --version
python -m chainbench tour --extended --lang ko --output tour
```

Eight named assets include the wheel, source distribution, HTML ZIP, PDF,
`verification.json`, `reading-verification.json`, `build-environment.txt` and
`SHA256SUMS`. Download all eight into one directory and run
`sha256sum -c SHA256SUMS` to check the recorded bytes.

The release workflow requires six compatibility configurations, clean wheel and
sdist installation, the complete offline browser suite, and cloud generation
with 24 independent numerical-record audits. It reads the extracted ZIP in
offline desktop/mobile Chromium before handing the exact tested bytes to the
main-only publisher. Six targeted fault injections include missing comparison
evidence and a changed ZIP with recomputed outer hashes. Internal member hashes,
source bindings and the standalone PDF's identity must still match. Uploaded
assets are downloaded and rechecked before the draft becomes a prerelease.

## Numerical migration and limits

CG now accumulates its scalar inner products with float64 products and compensated
summation. Paths can differ from older builds; matrix-vector products, true
residual stopping and the mathematical gates remain unchanged.
[Diagnosis and migration](https://github.com/chocoemong17/chainbench/blob/v0.6.0/docs/CG_ARITHMETIC.md). Frank–Wolfe segment displays retain
the recorded next objective after independent direct-evaluation validation.
Independent numerical reruns use the documented tolerance; serialization and
same-record provenance remain exact.

Stress sampler v2 changes how some seeded inputs are drawn. Old sampler-v1 JSON
is not silently relabelled as v2. Record the source commit, package version and
sampler contract when comparing saved results. [Sampler migration](https://github.com/chocoemong17/chainbench/blob/v0.6.0/docs/STRESS_SAMPLING.md).

The frozen v0.5.0 tag and assets stay unchanged. Earlier development builds also
reported 0.5.0, so their commit is necessary to identify them. This alpha is an
educational numerical toolkit; the checks do not establish production readiness,
universal algorithm rankings or independent adoption. No API key or paid service
is required. All source material is public and the existing image-generator
permission notice is retained.
