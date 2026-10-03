# ChainBench v0.7.0 — choose conditions, keep inputs, replay calculations

This experimental alpha connects the paper-reading toolkit to two new ways of
running teaching examples: an opt-in browser studio and a CLI that saves and
replays actual numeric inputs. Python 3.10+ and NumPy remain the runtime
requirements. The existing 25-page bilingual offline tour and two-page FISTA
PDF remain part of the eight named release assets.

The links below become available after the main-branch release gate publishes
the tested assets. Source version metadata alone does not establish publication.
The [frozen v0.6.0 release](https://github.com/chocoemong17/chainbench/releases/tag/v0.6.0)
remains available with its original files.

## Compute in the browser, then read offline

```bash
python -m pip install https://github.com/chocoemong17/chainbench/releases/download/v0.7.0/chainbench-0.7.0-py3-none-any.whl
python -m chainbench --version
chainbench studio --lang ko
```

Open the printed URL on the same computer. Choose a quadratic, diagonal LASSO
or simplex family, set conditions and select methods. **Run a new experiment**
performs bounded Python computation; the resulting report exposes the actual
arrays, starting point, method settings, metrics and every computed row.
Its controls inspect those rows rather than recomputing a solver.

Download input JSON, result JSON and standalone HTML. Stop with the page button,
Ctrl+C or idle expiry; the downloaded report remains readable offline. The
service binds only 127.0.0.1, checks Host/Origin and a fresh session key, bounds
requests/work/output and terminates timed-out worker processes. It does not
accept arbitrary code, URLs or file paths, and writes no report files itself.
The session is a local teaching interface, not a production server.
[Usage, worked questions and complete limits](https://github.com/chocoemong17/chainbench/blob/v0.7.0/docs/STUDIO.md).

## Replay the arrays rather than a generator

```bash
chainbench instance generate quadratic --seed 7 --dimension 4 --steps 20 --include-iterates --output input.json
chainbench instance run input.json --output result.json
chainbench instance replay result.json --format html --lang ko --output replay.html
```

`instance generate` saves real arrays and a starting point. `instance import`
accepts an explicit bounded problem; included examples cover an off-diagonal
quadratic, a PSD quadratic with multiple minimizers, signed diagonal LASSO and
a nonvertex simplex start. Input and manifest hashes bind the normalized arrays,
settings and declared origin. `instance replay` uses the saved inputs without
calling the generator, then reports agreement or actual differences with the
documented numerical tolerance.

JSON downloads preserve the original Python serialization, including signed zero
and float representations used by the sealed hashes. The browser does not
reserialize those bytes. Schema, indices, row counts and provenance checks remain
exact; hashes and numerical agreement do not establish authorship or a theorem.
[Input format, examples and replay contract](https://github.com/chocoemong17/chainbench/blob/v0.7.0/docs/STORED_INPUTS.md).

## Keep the paper-reading route

Download `chainbench-0.7.0-reading.zip`, extract the whole archive and open
`index.html`. Its 25 precomputed HTML pages connect published examples, 2D/3D
geometry, symbolic update flows, multiple inputs, counterexamples and scoped
sharp constructions. The separate `chainbench-0.7.0-review.pdf` remains the
two-page FISTA step-selection guide; it is also embedded in the reading ZIP.
[Download and verification guide](https://github.com/chocoemong17/chainbench/blob/v0.7.0/docs/OFFLINE_DOWNLOAD.md).

Opening the tour requires no Python or server. The ZIP does not start the studio
or include future user experiments. New computations require the installed
package; their downloaded reports are separate, self-contained files.
Korean/English controls, keyboard navigation and native no-script evidence
remain available throughout the reading workflow.

## Validation and migration

Publication requires all nine CI jobs: six compatibility configurations, the
complete live/offline browser suite, audited reading generation and clean wheel
and sdist installations. Each installed distribution must independently audit
ten generated/imported numeric cases and six live studio cases, validate their
input bytes and row metrics, reject malformed requests and shut down cleanly.
Eight targeted fault injections include removing the stored-input and studio
publication gates. Missing evidence prevents publication.

The reading gate audits all 24 numerical records, verifies ZIP members and the
two-page PDF, and reads the extracted ZIP offline at desktop/mobile sizes.
The main-only publisher uses those exact tested assets, downloads the uploaded
files and rechecks them before publishing. Download all eight named assets and
run `sha256sum -c SHA256SUMS` to check the recorded bytes.
[Full release contract](https://github.com/chocoemong17/chainbench/blob/v0.7.0/RELEASING.md).

Generated report source links select the v0.7.0 documentation.
Existing solver recurrences, legacy `experiment`/`replay`/`compare` behavior and
their schema-1 records remain unchanged from v0.6.0. The new exact-input records
have distinct kinds and use `instance run`/`instance replay`; legacy `compare`
does not accept them. These teaching workflows do not add general sparse-matrix
support, arbitrary objectives, an array editor in the studio or universal method
rankings. Equal update counts do not imply equal computational work. Prior tags
and release assets remain unchanged.
