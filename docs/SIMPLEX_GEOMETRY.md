# Frank–Wolfe: a vertex, a feasible segment, and a certificate

Available in the development source after v0.5.0:

```bash
python -m chainbench geometry frank-wolfe --steps 18 --lang ko --output simplex.html
python -m chainbench geometry frank-wolfe --steps 18 --format json --output simplex.json
```

Open the HTML offline. The same computed samples drive the triangle, projected 3D
objective surface, update inspector, convergence chart and full numerical appendix.
Keyboard arrows move between updates; playback and Korean/English switching require
JavaScript. Without it, all paths, tables and native expandable cases remain readable.

## Exact source mapping

Martin Jaggi, *Revisiting Frank-Wolfe: Projection-Free Sparse Convex Optimization*,
ICML 2013, [author's paper at PMLR](https://proceedings.mlr.press/v28/jaggi13.pdf):

- Algorithm 1, PDF page 1: the exact linear oracle and scheduled step `gamma=2/(k+2)`.
- Algorithm 3, PDF page 3: the added local segment-minimization diagnostic.
- Equation (2), Section 2, PDF page 2: the Frank–Wolfe dual gap.
- Theorem 1, Section 3, PDF page 3: objective-gap bound, with exact oracle `delta=0`.

The historical method is Frank–Wolfe (1956); this command implements the explicit
schedule in Jaggi's Algorithm 1. It does not silently replace that schedule with
line search. These are **controlled geometric illustrations**, not reproductions of
the paper's numerical figures, approximate-oracle results or application datasets.
No paper PDF, third-party figure or third-party algorithm source is bundled.

## Declared case design

The problem is `min 0.5*||x-target||²` on the probability simplex in R³:
`x_i>=0`, `sum(x_i)=1`. Its affine dimension is two. All three targets are feasible,
so `x*=target`, `f*=0`, `L=mu=1`. The curvature constant is the squared simplex
diameter, `C_f=2`: the quadratic curvature expression reduces to `||s-x||²`.

| Target name | Coordinates | Purpose |
| --- | --- | --- |
| interior | (0.2, 0.3, 0.5) | A solution away from every face |
| edge | (0.7, 0.3, 0) | A solution on a boundary face |
| near-vertex | (0.84, 0.10, 0.06) | A solution close to one atom |

Every target is paired with **all four** starts: e1, e2, e3 and the barycenter.
All twelve cases are retained regardless of outcomes. There is no random seed or
regularizer. The default is 18 updates, bounded to integers 1–60, with no early
termination. A final oracle certificate is computed even though no further update
is taken. Each input hash is SHA-256 over little-endian float64 target then start.

## Read one update

1. Compute `gradient=x-target`. The linear oracle chooses the basis vertex at the
   smallest gradient coordinate, with first-index tie breaking.
2. Move to `(1-gamma)*x+gamma*s`. Since `0<=gamma<=1`, feasibility is preserved by
   convexity. In the triangle, amber shows the chosen vertex and green the next point.
3. Compare `gap=0.5*||x-target||²` with the computable certificate
   `g_FW=gradientᵀ(x-s)`. Convexity gives `gap<=g_FW`.

## See where the certificate comes from

Jaggi Section 2 / Eq. (2) uses the affine lower model
`ell_x(v)=f(x)+gradientᵀ(v-x)`. For every feasible v, convexity gives
`ell_x(v)<=f(v)`. On a simplex, an affine function attains its minimum at a vertex.
The existing oracle therefore gives the lower endpoint without knowing an optimizer:

```text
lower = min_i ell_x(e_i) = ell_x(s) = f(x) - g_FW(x)
lower <= f* <= f(x) = upper
upper - lower = g_FW(x)
```

The new diagrams show all three **affine** vertex values and the selected minimum,
then the optimal-value bracket, on the same objective-value scale. These values
are not the actual objective heights at the vertices. The existing step control
updates both diagrams and their numerical readouts. The scale is fixed across a
case's entire run; different cases may use different ranges.

For the interior target at e1, the three affine values are `(0.49,-0.61,-0.81)`.
The oracle selects e3 and certifies `-0.81 <= f* <= 0.49`, a width of 1.3. The
actual objective at e3 is 0.19, not -0.81. A negative lower model does not imply
a negative objective. The known `f*=0` is drawn only as an audit reference; neither
endpoint uses it. The interval is intentionally not tightened using the separately
known nonnegativity of this special objective.

All recorded rows, including the final one with no subsequent update, retain
`certificate.affine_vertices`, `certificate.lower` and `certificate.upper` in the
JSON and full table. These are additive fields in the development schema-1 format;
new validation requires them rather than substituting missing values. The player
selects transitions k to k+1; the final row's certificate remains available in the
table. Without JavaScript, the diagrams show k=0 and all rows remain readable.

This is the real-arithmetic convexity argument evaluated with NumPy float64, not
directed-rounding interval arithmetic. Small residual discrepancies are checked
with explicit tolerances. The example's known solution helps audit the implementation;
a finite run does not establish the general theorem.

Starting at e1 with the interior target, the first three new points are e3,
`(0,2/3,1/3)` and `(1/2,1/3,1/6)`. Starting at the barycenter instead, the first gap
**increases from 7/300 to 19/100**. The fixed schedule does not promise descent
every step; `gamma_0=1` discards the initial point and goes to a vertex.

Under the theorem's compact convex domain, convex differentiable objective, finite
curvature and exact-oracle assumptions, the chart's bound is `4/(k+2)` for `k>=1`.
It bounds the **objective gap**, not the dual gap at each iteration. An upper bound
on the best dual gap over an interval is a separate result, not plotted here.

A vertex start uses at most `k+1` atoms after k updates. A barycenter already uses
three atoms; the page does not call that a sparse start. On this tiny simplex, atom
counts are explanatory, not evidence of performance on large sparse problems.

## Geometry and limitations

### Choosing the distance along the oracle direction

The added segment panel retains the Algorithm 1 path and examines its actual
current point x and chosen vertex s. For this quadratic, with d=s-x and q=||d||²,

```text
phi(gamma) = f(x) + gamma*slope + 0.5*gamma²*q
slope = (x-target)ᵀd = -g_FW(x)
gamma_min = clip(-slope/q, 0, 1)          when q>0
```

This is the closed-form specialization of Algorithm 3's minimization on [0,1].
For q=0 the segment is constant, and the diagnostic chooses gamma_min=0. The
purple ring marks this **one segment's** minimum; green is the actual scheduled
next point. A second trajectory is not advanced from the ring. This comparison
therefore says nothing about the relative performance of two complete methods.

The scalar plot shows the directly evaluated objective and its affine prediction.
The purple 3D curve lies on the objective surface over the same feasible segment,
whereas the amber dashed chord still joins its endpoints in space. Both diagrams
and their readouts follow the existing stage selector. A shortcut selects the first
objective increase exceeding 1e-12, when one exists; this is an inspection shortcut,
not a filter on retained cases. All twelve cases and all stored stages remain.

For the barycenter with the interior target, gamma_min=1/4 yields (1/4,1/4,1/2)
and f=1/400. The scheduled gamma=1 instead yields f=19/100, up from 7/300.
For the near-vertex target starting at e1, gamma_min=0.13 yields f=0.0027;
the actual first step goes from f=0.0196 to 0.7596. A negative initial slope
does not ensure descent after a large step: the exact-arithmetic change is
gamma*slope+gamma²*q/2. For q>0 its second zero is -2*slope/q, which may lie
outside [0,1]. JSON retains this unconstrained value without presenting it as a
floating-point certificate.

Each transition stores 65 uniformly spaced gamma values together with the
scheduled gamma and analytic minimizer. The points use the same convex-combination
arithmetic as the original recurrence; the scheduled point and its objective equal
the actual next recorded iterate. The final row has `segment: null`, since no next
update was performed. The raw maximum difference between direct evaluation and
the quadratic expansion is retained. The value scale stays fixed across a case;
on a narrow screen the scalar diagram scrolls horizontally to keep labels readable.
Without JavaScript, the initial diagrams and a native table of every segment remain.

The additive `segment_geometry` metadata identifies this derived explanation and
its source. Legacy records without the extension still render and validate; partial
extensions fail validation, and newly installed workflows require the extension.
Independent 60-digit Decimal calculations check every sampled feasible point,
objective, tangent value, constrained minimizer and actual scheduled sample.

The equilateral embedding is `(u,v)=(x2+x3/2,sqrt(3)*x3/2)`. Here the objective gap
equals squared planar distance to the target. Contours use that identity and equal
axis scales. The 3D view projects `(u,v,f-f*)` onto the page. Its dashed segment is
the straight chord between the current and oracle points in space; it is not the
curved objective restricted to that segment. Every green point is at its actual
objective height. The full static paths connect actual samples with straight lines.

Twelve starts/targets in one low-dimensional family do not provide representative
sampling, prove the theorem, establish worst cases or rank algorithms by runtime.
An iteration count does not price a linear oracle or compare it with projection.

## Validation contract

- Independent scalar checks of every feasible iterate, oracle, convex combination,
  gap, certificate, bound and input hash; hand-computed first updates and the explicit
  nonmonotonic example; rejection of corrupt or nonfinite evidence.
- SVG-coordinate checks against raw samples in both projections.
- Affine model values, both bracket endpoints and width checked independently for
  every row. Feasible probe points verify the quadratic tangent defect
  `f(v)-ell_x(v)=0.5*||v-x||²`; corrupt/missing/nonfinite model evidence is rejected.
- CLI overwrite protection and HTML/JSON agreement.
- Installed wheel **and** sdist workflows execute the command and independently
  validate its output; missing evidence blocks release publication.
- Optional `scripts/check_simplex_browser.py` checks all twelve players at 1440px
  and 390px, marker positions, every displayed certificate coordinate/readout,
  unclipped certificate labels, keyboard, playback, language, exact downloaded JSON,
  offline operation and the no-JavaScript fallback; saves actual screenshots.
