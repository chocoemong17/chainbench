# Run and replay the numbers you saved

**Development source after v0.6.0.** These commands are in the current source and
its tested CI distributions; the frozen v0.6.0 downloads do not contain them.
The existing `experiment`, `replay`, `compare` and their schema-1 records remain
unchanged. Use `instance` for the separate exact-input workflow below.

기존 `replay`는 저장된 설정으로 예제 데이터를 다시 만듭니다. `instance replay`는
저장된 행렬·벡터·시작점 자체를 읽습니다. 시드는 실제 데이터를 처음 생성할 때만
사용하며, 다시 실행할 때는 난수 생성기를 호출하지 않습니다.

## Generate actual data, inspect it, rerun it

```bash
chainbench instance generate quadratic --seed 7 --dimension 4 --steps 20 \
  --include-iterates --output input.json
chainbench instance run input.json --output result.json
chainbench instance run input.json --format html --lang ko --output result.html
chainbench instance replay result.json --output replay.json
chainbench instance replay result.json --format html --lang ko --output replay.html
```

`generate` creates actual numeric arrays, including a nondefault start. Try
`diagonal-lasso` or `simplex` as well, with seeds 0 and 7, and inspect both sets
of inputs. A new seed changes numeric data, not just the preset configuration.
The same initial settings apply to all selected methods on that instance.

The self-contained HTML has three curves (gap, named stationarity quantity,
distance to the reference), method-specific settings/termination, the full input,
execution environment and downloadable JSON. Choose a method and a completed
update to inspect that exact stored row. A method that stops early has only its
computed rows; there is no fabricated continuation. Native input details, static
SVG plots, initial row and all evidence remain readable without JavaScript.
The browser never executes a numerical solver or requests a remote service.

JSON `run` and HTML `run` in this example are separate numerical executions.
Their input bytes are identical; floating outputs can differ within the documented
replay tolerance. An HTML download contains that HTML execution's own record.

## Import an explicit problem and starting point

Save this JSON as `raw.json`:

```json
{
  "schema_version": 1,
  "problem": {
    "kind": "quadratic",
    "Q": [[2, 1], [1, 2]],
    "b": [1, -1],
    "x_star": [1, -1]
  },
  "x0": [2, -1],
  "run": {
    "steps": 2,
    "methods": ["gd", "smooth-fista", "heavy-ball", "cg", "proximal-point"],
    "include_iterates": true,
    "method_options": {
      "cg": {"rtol": 1e-12, "atol": 0},
      "proximal-point": {"proximal_parameter": 1}
    }
  }
}
```

```bash
chainbench instance import raw.json --output input.json
chainbench instance run input.json --format html --lang ko --output imported.html
```

This off-diagonal problem has L=3, μ=1, initial gap 1 and initial gradient [2,1].
GD's first point is [4/3,−4/3]; exact quadratic PPA with c=1 gives [11/8,−9/8].
The report retains the actual rounded solver outputs, not these symbolic labels.
Four small [input files](../examples/instances) also include signed diagonal
LASSO, a nonvertex simplex start, and a PSD quadratic with multiple minimizers.
These are constructed teaching inputs, not data recovered from a paper.

| Problem kind | Required numeric fields | Methods and reference |
| --- | --- | --- |
| `quadratic` | `Q`, `b`, `x_star` | GD, smooth FISTA, quadratic PPA; CG and classical heavy-ball additionally require μ>0. Supplied reference must satisfy Qx*=b to the existing relative floating tolerance. |
| `diagonal-lasso` | `a`, `b`, `lam` | ISTA/FISTA on ½‖a⊙x−b‖²+λ‖x‖₁; λ≥0 and every abs(aᵢ)≥10⁻¹². Reference is the analytic soft-threshold solution. |
| `simplex` | `target` | Scheduled Frank–Wolfe on ½‖x−target‖². Target and supplied start must be nonnegative and sum to 1 within absolute 10⁻¹²; reference is target. |

Every imported problem requires an explicit `x0`. Quadratic symmetry must be
exact; the import boundary does not average asymmetric entries. PSD inputs with
L>0 are supported, but selecting CG or heavy-ball for μ=0 is an error. No method
is silently removed. A zero matrix is outside this workflow. General sparse
matrices, arbitrary loss functions, unknown-optimum inputs, callable code, URLs,
pickle and automatic repairs are outside this schema.

For Q=diag(0,2), b=[0,−2], reference [4,−1] and start [0,1], one GD update
reaches [0,−1]. Gap and stationarity are zero while distance to the supplied
reference is 4. **Reference distance is not distance to the solution set.**

To change sealed method settings, make a new raw input with the same `problem`
and `x0`, edit `run`, and import it again. This creates an explicitly imported
manifest. Editing a sealed file and retaining its old hashes is rejected.

## What is sealed, and what replay establishes

`chainbench.instance`, schema 1, contains normalized `problem`, `x0`, `run`,
declared `origin`, `input_sha256` and `manifest_sha256`. Imported integer array
values are converted to float64 only when exactly representable. Booleans and
numeric strings are rejected. Signed zeros are preserved and affect the input hash.

The input digest starts with ASCII `chainbench.numeric-input.v1`, NUL, family,
NUL. Each named array contributes a sorted, compact JSON `{name,shape}` header,
NUL, and C-order little-endian float64 bytes. Field order is Q,b,x_star,x0 for
quadratics; a,b,lam,x0 for LASSO; target,x0 for simplex. `lam` has scalar shape
`[]`. The manifest hash is SHA-256 of sorted compact ASCII JSON of the complete
manifest without `manifest_sha256`; it binds settings and declared origin too.

Generation declares `chainbench.pcg64-normal-qr.v1`: NumPy PCG64; quadratics use
a normal random matrix's QR factor, geometrically spaced eigenvalues, a uniform
[−1,1] reference and [−2,2] start. LASSO draws signed diagonal magnitudes in
[0.5,2], b and start in [−2,2]. Simplex draws target and start uniformly in
[0.1,1] and normalizes each. Quadratic generation permits L in [10⁻⁶,10⁶] and
condition number in [1,10⁶]; a one-dimensional quadratic has condition number 1.
LASSO generation permits λ in [0,1000]. Actual arrays are authoritative because
NumPy/QR/BLAS environments need not generate byte-identical arrays from a seed.

`chainbench.instance-experiment`, schema 1, stores the entire manifest, environment,
derived fixture constants/reference and actual method observations. Replay first
validates its complete structure, hashes, settings, start and provenance. Then
it runs those stored numbers through the existing solvers, with the supplied x0.
The seed is never executed. Missing/nonfinite values and invalid provenance are
errors (CLI exit 2), never successful or omitted observations.

`chainbench.instance-replay` reports `MATCH` (exit 0) or `MISMATCH` (exit 1).
For numeric observations it uses Python `math.isclose`: absolute error no greater
than max(atol, rtol·max(|saved|,|rerun|)), default rtol=10⁻⁷ and atol=10⁻¹².
Dimensions, indices, row counts, updates, names, declared method options and input
bytes are exact. Derived constants, parameters and every retained iterate are
compared. The first 20 differences, total count, original record hash and both
environments remain visible. Environment changes alone do not imply failure.

Hashes check internal consistency, not authorship or historical truth. Someone
can construct new arrays and recompute both hashes. A declared seed is not proof
that a generator produced those arrays; MATCH does not authenticate who executed
the original record, certify a theorem or establish independent replication.

## Limits and validation

Input transport is at most 256,000 UTF-8 bytes; saved result input is at most
8,000,000 bytes. Duplicate/unknown keys, NaN/Infinity, deep nesting (>16), ragged
arrays and mismatched dimensions fail. Dimension is 1–64 (simplex 2–64), seed is
0–2³²−1, steps 0–2000. The existing conservative work proxy is capped at 10⁸;
at most 100,000 recorded scalar slots are reserved before execution, counting
five row scalars plus d coordinates when requested. These are teaching-interface
resource bounds, not runtime promises. Unrepresentable intermediate arithmetic
fails; no numeric value is silently clipped. Outputs cannot alias their input,
even through hard links or `--force`.

The existing solver recurrences and [metric definitions](SOURCE_MAP.md) remain
unchanged. The interface adds no theorem thresholds or method leaderboard.
Directly imported arrays are not restricted to the seeded generator family.
The existing `compare` command still accepts only legacy `chainbench.experiment`
records; exact-input reports use this dedicated run/replay workflow.

GitHub CI checks hand-computed off-diagonal, PSD, signed-LASSO and simplex cases;
corrupt inputs/reports; a disabled generator during replay; strict publication
evidence and a seventh fault injection. A standard-library auditor independently
recomputes byte hashes and every row's four metrics for ten installed CLI cases
in both wheel and sdist. It audits each independently generated HTML's own record
and all SVG samples. Browser checks cover eleven reports at 1440px/390px, native
keyboard navigation, sample controls, exact downloads, offline/no-script reading
and the two-page PDF. The `stored-input-review-<commit>` artifact contains the
actual files and source-bound audit; it stays on GitHub and expires after seven
days. Test-fixture publication records are explicitly synthetic and are not
substitutes for that installed numerical evidence.
