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
- CLI overwrite protection and HTML/JSON agreement.
- Installed wheel **and** sdist workflows execute the command and independently
  validate its output; missing evidence blocks release publication.
- Optional `scripts/check_simplex_browser.py` checks all twelve players at 1440px
  and 390px, marker positions, keyboard, playback, language, exact downloaded JSON,
  offline operation and the no-JavaScript fallback; saves actual screenshots.
