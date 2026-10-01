# One quadratic, five methods, identifiable calculations

`landscape` is a deliberately constructed **2D geometric illustration**, not a
published experiment, representative sample, theorem test or method ranking.
The development revision repairs the existing page's interpretation: its colors
now identify the same methods in every view, contour coordinates have equal
scales, and settings and actual stopping states remain visible.

```bash
python -m chainbench landscape --lang ko --output landscape.html
python -m chainbench landscape --condition-number 10000 --angle 85 --steps 80 \
  --methods proximal-point cg smooth-fista --format json --output extreme.json
```

The original numerical interface remains: condition number in [1.01,10000],
rotation in [-85,85] degrees, 2–80 updates, and a nonempty unique method subset.
The default is condition number 20, rotation 32 degrees and 18 updates. The tour
includes that full five-method default as `landscape.html`.

## Inputs and methods

For a rotation matrix R, construct `Q=R*diag(1/kappa,1)*R^T`,
`x*=(1,-0.8)`, `b=Q*x*`, `x0=(-1.55,1.45)` and
`f(x)=0.5*x^T*Q*x-b^T*x`. There is no randomness or regularizer. Store actual
float64 Q and b, the dimension, f*, computed L/mu and condition number, requested
rotation/condition number, start, reference solution, environment and input hash.
Every gap is computed stably as `0.5*(x-x*)^T*Q*(x-x*)`.

| Method | Existing calculation used | Stopping |
| --- | --- | --- |
| GD | Step 1/L | Fixed budget |
| Smooth FISTA | Beck–Teboulle fixed-L recurrence, g=0, t0=1 and y0=x0 | Fixed budget |
| Heavy-ball | alpha=4/(sqrt(L)+sqrt(mu))², beta=((sqrt(L)-sqrt(mu))/(sqrt(L)+sqrt(mu)))², previous=x0 | Fixed budget |
| CG | Existing scaled correction system and true-residual checks | `||b-Qx|| <= 1e-12*||b-Qx0||`, or exhausted budget |
| Proximal point | c=1, exact solve `(I+cQ)*x_next=x+c*b` | Fixed budget |

Each report links the public source and states the particular specialization.
[Source mapping](SOURCE_MAP.md) distinguishes smooth FISTA from a literal 1983
Nesterov transcription and the quadratic resolvent from the general inexact PPA.
The existing solver implementations and `traces`/`gaps` values are unchanged.
Schema 1 gains additive context fields; it is not a saved-file import interface.

The input hash uses sorted names Q, b, x_star, x0; for each, append the ASCII name
and NUL, compact shape JSON and NUL, then little-endian float64 C-order bytes.
It identifies the numerical inputs; the budget and method settings are recorded
separately. It is not a signature or an external review record.

## Reading the figures

The contour plots pad the shorter coordinate span so one x1 unit and one x2 unit
have the same pixel length. Numerical ticks and stored contour levels expose the
projection. Every small method panel uses bounds from the same combined run.
The full-size and small panels can have different padded extents to retain equal
scales in their different aspect ratios; each embeds its actual projection.

The 3D wireframe uses separately normalized x1/x2 ranges and z divided by the
stated maximum grid height, followed by the displayed oblique projection. Its
numeric axis origin/endpoints and projection metadata identify those scales.
Angles in that oblique display are not Euclidean angles. The height is f−f*,
not f. Chords connect computed endpoints; their interiors need not lie on the
objective surface, and the transparent wireframe is not a depth-occluded surface.

All views use stable colors by method, including a reordered subset. The loss
chart's data and each marker come from the same actual trajectory. The shared
player reports coordinates, gap and recomputed residual at the actual method
index; after CG stops, it holds and labels the last computed point. It does not
invent later CG iterations. Full values remain in native tables and JSON when
JavaScript is disabled; inactive playback controls are hidden then.

`fixed_budget` is not a convergence certificate. Nor are iteration counts equal
work: PPA solves a linear system, CG uses products and residual checks, and the
other methods have distinct state and arithmetic. These figures do not report
timing, universal dominance or nonquadratic convergence. The tour links the
quadratic picture to the [published heavy-ball counterexample](HEAVY_BALL_COUNTEREXAMPLE.md).

## Development: inspect the actual PPA subproblem

When PPA is selected, the page also shows the problem minimized by each of its
existing steps. Rockafellar (1976), [author-hosted paper](https://sites.math.washington.edu/~rtr/papers/rtr066-MonoOpProxPoint.pdf),
Eqs. (1.7)–(1.9), printed p.878 / PDF 2, describes the resolvent and penalized
objective. The paper studies approximate updates; this view takes its exact
quadratic specialization with the existing c=1:

`phi_k(u)=f(u)+||u-x_k||²/(2c)`, with Hessian `H=Q+I/c`.

The existing next point solves `H*next=b+x_k/c`. The first-order equation is
`grad f(next)+(next-x_k)/c=0` in exact arithmetic, matching the residual operator
in Eq. (1.16), printed p.880 / PDF 4. Both gradients are evaluated at the recorded
next point. The displayed orange/blue arrows are `c*grad f(next)` and `next-x_k`,
with one coordinate scale; they are gradients, not a path of iterates or an inner
solver animation. This is distinct from linearizing the smooth term in proximal
gradient. The same original f remains inside the PPA subproblem.

The ring marks a separately computed floating-point solve of the shifted 2×2
system. Green is the next point from the unchanged solver. Contours show
`E(u)=0.5*(u-reference)^T*H*(u-reference)`, the subproblem gap in exact arithmetic.
Reference and actual-point residuals are stored without replacing them by zero.
The shifted system is well conditioned on these fixtures (H has eigenvalues
1+1/kappa and 2); this explanation does not change the underlying solver.

Axes are offsets from that reference. Each frame fits the actual point/arrow
extents with equal coordinate scales, reports coordinate units per pixel and
lists all four energy levels. Contours are clipped to the axes. The prior point's
energy sets the levels at 0.25, 0.5, 1 and 2 times that value. At an exactly zero
energy, a declared unit-radius fallback sets a visible contour range. If the
recorded iterate is unchanged, a unit radius prevents tiny gradient roundoff from
appearing as a large movement. Tiny nonzero displacements are retained, and local
zoom can make roundoff visible.

The shared slider at k>=1 selects the last completed solve, x[k-1]→x[k]. At k=0,
the panel explicitly says that none has been completed. With JavaScript disabled,
the last completed view and a native table of every stage remain. A method subset
without PPA has neither a subproblem record nor a panel.

The additive `proximal_subproblems` field stores H, c, the source/scope and all
rows: old/next/reference points, right-hand side, both gradients, their balance,
absolute norm, denominator, relative balance, objective/penalty values, reference
error energy and movement. A zero denominator gives null. Near roundoff, a small
nonzero denominator can give a large relative balance even at an unchanged point;
neither fixed-budget completion nor unchanged coordinates certify convergence.

Independent checks use a scalar 2×2 inverse, the implicit equation and raw
gradients; norms are checked against the saved floating components so machine-level
dot-product ordering differences do not fabricate a different relative residual.
Tests also cover rational unrotated data, contour energies, endpoints, absent PPA,
stationary/undefined-ratio cases and corrupt explanations. Browser checks inspect
each frame, k=0, stationary scaling, all controls and no-script tables. Existing
mathematical runs and metrics are preserved. New remote validation is pending.
Contour tests bound the energy error induced by rounding SVG positions to 0.001
pixels using the frame's coordinate scale and H eigenvalues; raw records are not
rounded to display precision.

## Verification

Independent scalar checks recompute the rotated fixture, input hash, every gap
and residual, method parameters, all five recurrences (the implicit equation for
PPA), and termination. Tests cover boundary conditions, reordered subsets, both
projections, equal contour scales, chart colors and deliberately corrupted records.
Both installed wheel and sdist exercise all five methods and compare the default
standalone record to the tour output. Existing publication gates remain required.

The browser check compares every path, marker and readout with raw numerical
evidence at 1440/390 px, including early stopping, all saved states and the maximum
condition number/budget. It exercises keyboard/playback, language and JSON download,
checks text bounds and overflow, and reads the no-JavaScript fallback offline.

```bash
python scripts/check_landscape_browser.py --html landscape.html --output browser-check
```
