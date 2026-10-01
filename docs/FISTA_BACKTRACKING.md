# FISTA: inspect every backtracking trial

The separate development command follows Beck and Teboulle's **unnumbered
FISTA with backtracking panel**, printed p.194 / PDF page 12 of the
[author PDF](https://www.tau.ac.il/~becka/FISTA.pdf), SIAM Journal on Imaging
Sciences 2(1), 183–202 (2009), DOI 10.1137/080716542. It is not “Algorithm 2.”
The model is Eqs. (2.5)–(2.6), printed p.189 / PDF 7. The source bound is
Theorem 4.4 / Eq. (4.4), printed p.195 / PDF 13.

```bash
python -m chainbench geometry fista-backtracking --lang ko --output backtracking.html
python -m chainbench geometry fista-backtracking --steps 60 --format json --output backtracking.json
```

This is a development addition after the frozen v0.5.0 and pinned review snapshot;
it requires a checkout containing the command. Authenticated remote PR/CI remains
pending. Existing fixed-L ISTA/FISTA and image workflows are unchanged. This
report is also available as the eighth extension of the offline tour.

## Inputs and recurrence

The objective is `F(x)=0.5||diag(1,3)x−(1.4,−2.4)||²+λ||x||₁`.
The source's Eq. (1.3) uses an unhalved squared loss; the fixture deliberately
uses the same half-squared scaling as the existing proximal geometry. The smooth
curvatures are 1 and 9, and the closed solution is `soft(a*b,λ)/a²`.

All 36 runs remain in fixed input order:

| Factor | Values |
| --- | --- |
| λ | 0.1, 0.8, 1.8 |
| x₀ | opposite (−1.8,1.2), zero (0,0), near (2,−1.4), low-mode (−3,−0.8) |
| initial L₀ | 0.25, 1, 4 |
| η | 2 |
| accepted updates | default 18; integer 1–60; no early stop |

These are **12 objective/start inputs, each with three initial curvature guesses**,
not 36 distinct optimization problems. The first three starts match the earlier
proximal illustration. The added low-mode start has its second coordinate at
the *smooth* minimizer; it is not generally at the composite optimum. No run is
chosen or discarded based on performance. Inputs are fingerprinted using SHA-256
of sorted compact finite JSON, including the budget and recurrence settings.

Start with `y₁=x₀,t₁=1`. At update k, try `L=η^j L_{k−1}`, starting at j=0:

1. `z=y_k−∇f(y_k)/L`.
2. `q=soft(z,λ/L)`, the minimizer of `Q_L(·,y_k)`.
3. Accept the first trial satisfying `F(q)≤Q_L(q,y_k)`.
4. Set `L_k=L,x_k=q`, then `t_next=(1+sqrt(1+4t²))/2` and
   `y_next=x_k+((t−1)/t_next)(x_k−x_{k−1})`.

The accepted L is carried forward. There is no per-step reset, decrease,
monotone-FISTA restart or adaptive η. Because this grid reaches L=16≥9 in at
most seven trials, failure to accept within that budget raises an error.

The gate concerns a candidate at the **extrapolated y**, not descent relative
to the previous x. A trial may pass with L<9: that local test does not certify
a global upper model. FISTA can increase its original objective between accepted
iterates. A shortcut exposes the first recorded increase exceeding 1e−12; this
display threshold is never an acceptance tolerance.

## Stable gate and retained arithmetic differences

For this quadratic, exact algebra gives

`F(q)−Q_L(q,y) = 0.5 sum((a_i²−L)(q_i−y_i)²)`.

The specialized float64 implementation uses this identity with the actual
rounded displacement and accepts when its value is ≤0, without added tolerance.
It separately retains the directly evaluated F and Q, their raw subtraction,
and the decision that raw subtraction would produce. Near zero, subtracting two
large nearly equal values can disagree with the stable identity. Such cases are
retained; no raw value is replaced with a mathematical zero. This is a transparent
quadratic specialization, not a generic black-box line-search solver.

Stable objective gaps use quadratic error plus the l1 Bregman term around the
known optimum. Raw `F−F*` is also retained. The envelope for k≥1 is
`2ηL(f)R²/(k+1)²=36R²/(k+1)²`, where `R=||x₀−x*||`. All declared L₀≤L(f)=9.
No theorem value is invented at k=0. Trial counts are reported separately from
accepted updates; neither is a timing comparison or a universal method ranking.

## Reading the figures

The accepted x path has a 2D contour view and a projected 3D **original objective
gap** surface. Both use the fixed coordinate window [−3.5,3.5]²; all saved x and
y fit inside. Only contour curves are clipped to that window. The selected
accepted x and the current extrapolated y are marked separately. Chords join
saved points and do not assert continuous optimizer motion.

The proposal panel retains every attempted q at the chosen step. It uses equal
coordinate scales with symmetric radius `max(1,1.1 max|coordinate|)` over the
anchor and all candidates. Thus even large rejected trials remain visible.
Numbered proposals can overlap; the native table retains their distinct rows.
Dashed connectors show attempt order, not an optimization trajectory.

The model panel compares `F(u)−F*` and `Q_L(u,y)−F*` along
`u(s)=y+s(q−y)`, s∈[−0.25,1.25]. It includes 49 equally spaced base samples,
both endpoints s=0 and 1, and every coordinate zero crossing in the interval.
Saved endpoints are pinned to the actual y and q. Both heights share the same
shift F*, and the height range includes every sample and the previous objective;
negative rejected-model values are not clipped or floored. It refits per trial.
The grey reference is the previous objective value, not the previous point's
position on this line. A zero direction is retained as a degenerate slice.

All numeric trial rows and accepted path rows are native HTML. Without scripts,
every case's first trial figures remain visible with complete tables. With
scripts, the case, update and trial controls update all four figures and the
readouts together. The native-row link targets the exact chosen trial.

## Validation contract

`scripts/smoke_fista_backtracking.py` imports neither ChainBench nor NumPy. It
replays all recurrences with 60-digit Decimal arithmetic, reconstructs every
candidate and model slice, checks first-acceptance ordering and L carry, binds
raw subtractions to stored operands, and audits metadata, inputs and summaries.
For the tiny signed gate it audits the actual rounded displacement with a
relative **sum-of-absolute-terms** error limit of 2e−12, with no absolute floor.
Other recurrence/model comparisons allow rtol=3e−11 and atol=5e−13 for binary
floating arithmetic. The finite envelope check allows relative 1e−10.

Tests include a hand-computed λ=.8, x₀=0, L₀=1 step: L=1,2,4,8 are rejected
and L=16 yields q=(.0375,−.4). They reject missing cases/trials, wrong carry,
momentum, gradients, acceptance, model slices, bounds, summaries and nonfinite
evidence. Local browser and distribution checks are recorded separately from
remote CI; a built archive alone is not evidence of a clean installation.

`check_fista_backtracking_browser.py` selects every case, accepted update and
trial at desktop and mobile widths, then independently checks the actual SVG
paths, markers, signed model heights, proposal scales, labels, readouts and
native rows. It checks keyboard navigation, language controls, JSON download,
ordinary fragment clicks and all cases with scripts disabled. The companion
mutation command injects 18 real DOM faults and requires every one to fail the
same auditors before confirming that the restored page passes.


## Follow the fixed-L comparison in the tour

`tour --extended` includes `backtracking.html` with the same 18-update record and
all 36 runs. The index's step-selection section compares the FISTA subset of
`proximal.html` with this report. Both use the same half-squared diagonal LASSO
and share nine objective/start pairs; the backtracking grid adds a fourth start
and three initial curvature guesses. ISTA does not use the displayed extrapolation.

The two symbolic flows and seven comparison rows distinguish fixed L=9 from
candidate testing with carried L, their shrinkage thresholds, update/trial work
and the source envelopes 18R²/(k+1)² versus 36R²/(k+1)². Local acceptance is not
a global majorizer certificate or monotonicity relative to the previous iterate.
The actual preview is the first rejected model for λ=0.8, x₀=(0,0), L₀=1:
q=(0.6,−6.4), stable F(q)−Q₁(q,y)=163.84. Its horizontal variable is line position,
not iteration number. It is extracted unchanged from that report's SVG.
Reciprocal report links and the atlas reach the comparison guide; the base tour
and its existing question cards remain unchanged. See [tour contract](OFFLINE_TOUR.md).
