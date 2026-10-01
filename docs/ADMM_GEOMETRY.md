# ADMM: fit, shrink, agree

`geometry admm-lasso` is an offline explanation of variable splitting on 36
predeclared two-dimensional LASSO problems. It is a controlled geometric
illustration, separate from the fixed literature checks and from the existing
ISTA/FISTA illustrations. It does not reproduce a published performance figure.

```bash
python -m chainbench geometry admm-lasso --lang ko --output admm.html
python -m chainbench geometry admm-lasso --format json --output admm.json
```

The default is 60 updates; `--steps` accepts integer budgets 1 through 160.
Existing `geometry frank-wolfe` and `geometry ista-fista` defaults remain 18.
Every case runs the whole budget, including cases which pass the residual test
early and those which never pass it. There is no performance-based selection.

## Source and scope

Boyd, Parikh, Chu, Peleato and Eckstein (2011),
[*Distributed Optimization and Statistical Learning via the Alternating Direction
Method of Multipliers*](https://web.stanford.edu/~boyd/papers/pdf/admm_distr_stats.pdf):

| Implemented or explained item | Exact location |
| --- | --- |
| Half-squared LASSO and its x/z/u updates | §6.4, Eq. (6.2) and displayed updates, printed p.43 / PDF p.46 |
| The two scaled subproblems and previous dual memory | §3.1.1, Eqs. (3.5)–(3.7), printed p.15 / PDF p.18 |
| Primal and dual residuals | §3.3, printed p.18 / PDF p.21 |
| Both residual norms ≤ their tolerances | Eq. (3.12), printed p.19 / PDF p.22 |
| Original objective evaluated at z | §11.1.1 / Figure 11.2, printed p.89 / PDF p.92 |

The source is a review: ADMM's origin predates 2011 by decades. Its dense example
uses m=1500, n=5000, normalized random columns, sparse data and a different
regularization choice. Its optimum 17.4547, fifteen-update stop and timings are
not targets or claims for these new inputs. No source PDF or MATLAB code is
included in this repository.

The [author's MATLAB implementation](https://web.stanford.edu/~boyd/papers/admm/lasso/lasso.html)
explicitly records `f(x)+g(z)`, while the paper's Figure 11.2 evaluates `F(z)`.
Both are retained with different labels here. This implementation follows the
paper's non-strict `≤` residual test; the MATLAB example uses strict comparisons.
No over-relaxation, adaptive penalty, distributed execution or general-purpose
ADMM solver API is introduced.

## Inputs declared before inspecting outcomes

The original problem is `min_w F(w)=½||Aw−b||²+λ||w||₁` with `w∈R²`.

| Factor | All values |
| --- | --- |
| A | `diag(1,3)`; `[[2,1],[1,2]]` |
| b | `[1.4,−2.4]` |
| λ | `{0.1,0.6,1.1} × λ_max`, where `λ_max=||Aᵀb||∞` |
| z₀ | `[0,0]`; `[−1.8,1.2]` |
| u₀ | `[0,0]` |
| ρ | `0.1`, `1`, `10`, fixed within a run |
| absolute / relative tolerance | `10⁻⁴` / `0.01` |

Both smooth Hessians have spectrum `{1,9}`. Their coordinate coupling differs.
The 2×3×2×3 factorial retains all 36 cases and three support regimes: both
coordinates active, only the second active, neither active. A sorted compact
JSON hash binds each matrix, datum, start, penalty, tolerance and budget.
There is no random input or seed.

## One iteration

Split the objective as `f(x)+g(z)` subject to `x−z=0`, where
`f(x)=½||Ax−b||²` and `g(z)=λ||z||₁`. The constraint matrices are `I` and `−I`;
they are distinct from the feature matrix named `A` above. For k≥1:

1. Solve `(AᵀA+ρI)x_k=Aᵀb+ρ(z_(k−1)−u_(k−1))`.
2. Shrink `z_k=soft(x_k+u_(k−1),λ/ρ)` componentwise.
3. Accumulate `u_k=u_(k−1)+x_k−z_k`; retain `y_k=ρu_k`.

At k=0 only z, u and y are initialized. x, the residuals, the split objective
and the stopping test are undefined, recorded as JSON null and displayed as an
em dash. There is no invented initial linear solve. Soft thresholding is the
exact separable subproblem minimizer, not rounding small coordinates to zero.

## Inspect the two subproblems within a recorded step

For selected k≥1, keep the previous `z_old,u_old` distinct from the new
`x_new,z_new,u_new`. The source's scaled form gives

`a=z_old−u_old`, `Hx(w)=½||Aw−b||²+ρ/2||w−a||²`,

`v=x_new+u_old`, `Hz(w)=λ||w||₁+ρ/2||w−v||²`.

The recorded x solve minimizes Hx. In exact arithmetic its zero gradient yields
`Hx(w)−Hx(x_new)=½(w−x_new)ᵀ(AᵀA+ρI)(w−x_new)`.
The panel uses this centered identity for levels 0.1, 0.5, 2 and 10: 129 rays
per level, with distances determined by their quadratic curvature. The center
is the actual recorded solve, whose floating-point equation residual is already
exported. Separate 60-digit reevaluation of the original Hx expression checks
the identity and its roundoff on these finite cases. The grey point is `z_old`,
and its Hx gap is shown below the plot.

Hz is separable: `z_new=soft(v,τ)` with `τ=λ/ρ`. Two scalar number lines show
each actual v coordinate and its recorded z result. The interval `[-τ,τ]`
maps to zero; outside it the displacement magnitude is τ. The vertical offsets
separate input/output symbols, not data coordinates. Both coordinate lines use
one fixed linear range for all recorded steps of that case:
`B=1.15 max(τ, all |v_i|, all |z_i|)`, with endpoints `−B,B`.
The range can change with the case or available budget. The shaded threshold
interval is drawn at its actual linear width, even when narrow.

The x-model window is the same `[-2.5,2.5]²` window as the original primal
geometry; the shrinkage axes have their own explicitly labelled range. The
penalty target a is a numerical readout, not a silently clipped point: at the
160-step budget some targets and inputs have magnitude close to 60, while all
recorded x/z coordinates stay inside the primal window. Neither panel substitutes
the new dual memory for the previous one.

Hx and Hz change with k. Their values and model gaps are not original F gaps,
and are not joined across iterations as one convergence curve. At k=0 the
panels show that no subproblem update has been completed. Without scripts,
every case retains its first-step figures and a table of previous states and
shifted inputs at all native sample iterations. The exported numerical record,
input fingerprints, original 2D/3D plots and residual decisions are unchanged.
The iteration control remains visible while scrolling through these panels.

## Original gap, split value and residuals

`F(z)` is an original-primal objective. `f(x)+g(z)` is the objective of two
different points in the split formulation. If x≠z it can be below the original
optimum; neither `f(x)+g(z)−F*` nor its negative is a certified optimality gap.
The view shows both curves on the same linear scale, with a separately named
original optimum. The 3D height always uses the original F gap.

The original optimum w* is found by enumerating the nine 2D sign patterns and
checking active signs, inactive subgradient bounds and stationarity. The
positive-definite Hessian gives uniqueness. With the resulting L1 subgradient
s*, the cancellation-resistant expression is

`F(w)−F*=½||A(w−w*)||²+λ Σ_i(|w_i|−s*_i w_i)`.

This uses `Aᵀ(Aw*−b)+λs*=0` and `s*ᵀw*=||w*||₁`. The raw subtraction
`F(z)−F*` and its difference from the stable expression are retained too. The
floating-point KKT check is not symbolic certification of arbitrary problems.

The two stopping quantities are
`r_k=x_k−z_k` and `s_k=−ρ(z_k−z_(k−1))`.
Their tolerances are
`ε_r=√2·10⁻⁴+0.01 max(||x_k||₂,||z_k||₂)` and
`ε_s=√2·10⁻⁴+0.01||y_k||₂`.
Both norms must be ≤ their own tolerances. In exact arithmetic,
`∇f(x_k)+y_k=s_k`; the raw identity difference is retained. A tolerance pass is
a finite stopping diagnostic, not a theorem establishing a particular gap.

With λ/λ_max=1.1 and the zero start, z is already the original optimum. The
first x generally differs from z, so a zero original gap and zero dual residual
still do not pass the primal residual test. At the default budget, 22 of 36
cases pass both tests at the last row; at 160, 32 pass. The remaining cases are
kept. These are finite observations on the declared inputs, not a ranking of ρ.

## How to read the geometry

The 2D square has equal coordinate scales, shared across all primal paths and
optima in the chosen budget. Contours are actual original gap levels
0.1, 0.5, 2, 10 and 40, located by ray bisection from w*. A 21×21 wire grid
shows the piecewise quadratic gap surface. Its height range is shared across
starts and penalties for the same F. Changing λ changes F and can change the
height scale; every axis declares its range.

Blue and green paths contain all computed x and z states. Large markers select
one actual iteration; amber joins its x and z. The vector r points from z to x.
The segment is a spatial connection of endpoints, not continuous optimizer
motion along the surface. The browser selects stored values rather than solving
another problem.

The purple path uses `y=ρu` in **feature coordinates**. After a completed shrink
step (k≥1), exact z optimality gives
`y∈∂(λ||z||₁)`: nonzero coordinates lie on the box boundary; zero coordinates
allow interior values. Initial memory y₀ need not be a subgradient of g at z₀;
for example, u₀=0 at a nonzero opposite start does not satisfy active-coordinate
subgradient equality. Raw y and signed `|y|−λ` are retained, without clipping
floating-point excess. The black reference is `y*=λs*`. This is not the
measurement-space residual dual used in the other LASSO pages, and the box
diagram is not a certified dual lower bound.

Residual curves divide each norm by its own tolerance. Positive values use a
logarithmic axis; exact zeros occupy a separate row and break positive line
segments. No positive floor is substituted. k=0 is absent from these curves.
Both ratios must be ≤1. Tables expose their unnormalized numerators too.

All 36 cases have native first-step figures and selected iteration tables.
Small screens can scroll figures and numerical tables with touch or keyboard.
The complete JSON includes every iteration, solve residual, shrink input,
dual memory, tolerance, raw roundoff difference, settings and environment.

## Compare the full declared grid

The outcome overview contains four matrix/start groups, with regularization
fractions as rows and fixed penalties as columns. All 36 cells show the final
simultaneous residual decision, the two final norm/tolerance ratios, the first
simultaneous pass or its explicit absence within the budget, and the stable
original-objective gap `F(z)−F*`. The first and final decisions are separate.
Labels use the unrounded stored decision, rather than rounded displayed ratios.
The grid order is fixed by the declared inputs, not sorted by observed success.

Each link selects its exact case at the displayed final iteration and moves
keyboard focus to the case summary. Returning to the overview preserves access
to every result. Without JavaScript, the same link targets the final native
table row and the browser opens its enclosing details. Report navigation jumps
immediately so expanding long native tables does not compete with a smooth
scroll animation. Narrow tables scroll
with touch or the keyboard. Accessible link labels include the matrix family,
regularization fraction, start, penalty and iteration.

Compare both ratios with 1 and read the original gap separately. In particular,
zero-start strongly regularized cases can have a zero original gap while their
primal residual remains too large. Equal iteration budgets do not imply equal
work or runtime; this finite grid is not a general ranking or an optimality
certificate. All numerical records and iteration budgets are unchanged.

## Verification

`scripts/smoke_admm_geometry.py` uses standard-library 60-digit Decimal
arithmetic, a scalar 2×2 inverse and independent closed-form optima for these
six matrix/regularization combinations. It imports neither NumPy nor runtime
ChainBench code. All rows of all cases at budgets 1, 60 and 160 are checked,
including initial nulls, hashes, signs, residual decisions and raw differences.

`scripts/check_admm_browser.py` reads the actual DOM. It checks every mesh
vertex, contour level and projected coordinate; every primal, dual, objective
and residual sample; every selected marker, chord and readout; native tables,
language controls, keyboard navigation, JSON download and offline behavior.
The independent `admm_subproblem_audit.py` also checks the model contours,
translated centers, previous-state readouts, threshold bands, full-range axes,
shrinkage markers/arrows, visibility and native input tables. The actual-DOM
mutation runner rejects 48 named faults, with a fresh positive baseline for
each dynamic fault. This is finite named-fault coverage, not general mutation
coverage. The sticky iteration control and all three scrollable figure types
are exercised at desktop/mobile widths.
The separate `admm_overview_audit.py` compares all rendered cells, visible
verdicts, ratios, gaps, absent/recorded first passes, matrix/start captions,
grid positions and unique final-row targets to the independently audited
record. Thirteen of the named DOM faults target this overview. Browser checks
follow every case link at both widths, exercise keyboard navigation, and follow
all 36 native fragments with JavaScript disabled at budgets 1, 60 and 160.
Desktop/mobile checks use actual browser event listeners. The installed-package
workflow runs the same independent numerical audit and binds HTML to JSON;
the publication gate requires its `admm_geometry` evidence. A built archive or
local browser run alone is not a clean-install or remote-CI result.

The optional [extended tour](OFFLINE_TOUR.md) links this report to ISTA/FISTA,
with a notation table and two symbolic update flows. In that proximal report,
z names the gradient proposal; here it names a copy variable. FISTA's y is an
extrapolated point; here y=ρu is dual memory. Their thresholds, inputs, budgets
and work per iteration differ. The connection does not turn their existing
curves into a controlled head-to-head speed comparison. Its preview uses the
actual named coupled-case surface, with XML-valid empty data attributes so the
same SVG can also render as an independent image.
