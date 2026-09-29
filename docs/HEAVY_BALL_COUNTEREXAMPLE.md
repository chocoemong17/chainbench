# Heavy-ball can settle into a cycle

Available in development source after v0.5.0:

```bash
python -m chainbench reproduce lessard-2016 --lang ko --output cycle.html
python -m chainbench reproduce lessard-2016 --format json --output cycle.json
```

This independently recomputes the published one-dimensional counterexample in
Lessard, Recht and Packard, *Analysis and Design of Optimization Algorithms via
Integral Quadratic Constraints*, SIAM Journal on Optimization 26(1), 57–95 (2016),
[DOI](https://doi.org/10.1137/15M1009597).
The exact source used here is [arXiv:1408.3595v7](https://arxiv.org/pdf/1408.3595v7),
revised 28 October 2015:

| Source location | What is used |
| --- | --- |
| §4.6, Eq. (4.11), PDF p.23 | The three-piece gradient, mu=1 and L=25 |
| Figures 6–7, PDF p.24 | Initial x0=3.3, signed iterate history and objective geometry |
| Appendix B, Eq. (B.1), PDF p.39 | Heavy-ball recurrence and initialization x[-1]=x[0] |
| Appendix B, Eqs. (B.2)–(B.3), PDF p.39 | Phase convention and exact rational three-cycle |
| Appendix B, PDF p.40 | Source argument for attraction of the cycle |

The source PDF's SHA-256 is
`ef4cb55f27a707fc67f1bd19e340ed2a6899da48877c5e8df8bc36f5986860bc`.
The repository contains independently written code, source links and formulas;
it does not redistribute the paper PDF or copy the authors' figure pixels/code.

## Why this result matters

On a strongly convex quadratic, the classical heavy-ball tuning follows an
eigenvalue analysis. The same parameters do not guarantee global convergence on
every smooth strongly convex function. This example demonstrates that distinction
without changing the implemented update or introducing private data.

The paper's broader contribution studies optimization algorithms as dynamical
systems, uses integral quadratic constraints to describe their nonlinear feedback,
and bounds their behavior through semidefinite programs. This workflow reproduces
the concrete counterexample only. It does not implement those IQC programs, certify
stability regions, or reproduce the entire paper.

## Exact function, recurrence and indexing

```text
                 x < 1             1 <= x < 2               x >= 2
f'(x)            25x               x + 24                   25x - 24
f(x)             12.5x²            0.5x² + 24x - 12         12.5x² - 24x + 36

mu = 1, L = 25, condition number = 25, dimension = 1
x* = 0, f* = 0
alpha = 4/(sqrt(L)+sqrt(mu))² = 1/9
beta  = ((sqrt(L)-sqrt(mu))/(sqrt(L)+sqrt(mu)))² = 4/9
x[k+1] = x[k] - alpha*f'(x[k]) + beta*(x[k]-x[k-1])
x[-1] = x[0] = 3.3
```

The antiderivative is normalized by f(0)=0, matching the source objective graph.
Both f and f' are continuous at 1 and 2. The gradient slopes are between 1 and 25,
so the function is 1-strongly convex with a 25-Lipschitz gradient. It is C1, but not
twice differentiable at the joins. **This is not a nonconvex or nonsmooth-objective
counterexample.** “Smooth” here means a Lipschitz gradient, not C2 everywhere.

The default keeps k=0 through k=50: fifty actual updates and the initial point,
matching the plotted iteration range of Figure 6. `--steps` accepts integers 1–500;
a different budget is explicitly labelled. There is no early stopping or invented
extension after stopping. The existing `methods.heavy_ball` performs all updates.

The published limiting cycle is

```text
p =  792/1225 =  0.646530612...
q = -2208/1225 = -1.802448979...
r = 2592/1225 =  2.115918367...
x[3n] -> p, x[3n+1] -> q, x[3n+2] -> r  (published initialization)
```

These values are source references, not fitted to our finite trace. Their exact
rational values satisfy the three update equations with p,q<1 and r>2. Appendix B
also gives an attraction argument for the source initialization. Numerical
closeness after fifty steps is evidence about this run, not by itself a proof
about infinitely many steps.

## What the views show

- **Objective graph:** actual `(x[k], f(x[k]))` points on the same function.
- **State plane:** actual `(x[k-1], x[k])` pairs, with equal coordinate scales.
  Momentum needs both coordinates; the current point alone does not determine the
  next iterate. Dark squares mark the source cycle in the appropriate coordinates.
- **Signed history:** every x[k], including negative values; dashed lines mark
  the gradient-piece boundaries 1 and 2. The full history stays visible while
  the player highlights a selected point.
- **Objective and stationarity:** separate plots of f(x[k])-f* and |f'(x[k])|.
  Neither is a fitted convergence-rate estimate.
- **Update terms:** the selected heavy-ball point, gradient step, momentum step
  and actual next point. At the budget's final point, there is no next update.

Straight chords between samples show their order, not continuous-time trajectories
or paths constrained to the objective curve. All geometry uses a common domain
covering every retained case; the numeric readouts preserve small values. Without
JavaScript, complete static paths, curves, tables and all cases remain available.

## Controlled variations and the GD comparison

In addition to the published start 3.3, every start in the predetermined grid
`0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0` is retained. These are eight **controlled
additions**, not representative random sampling or extra original-paper experiments.
Some approach the source cycle and some approach zero; none is filtered or replaced.

GD with step 1/L uses the same function and start as a separately labelled comparison.
It uses the existing `gradient_descent` implementation. This does not reproduce a
GD curve from Figures 6–7 or establish a general speed ranking. No claim is made
that every heavy-ball parameter choice or every nonquadratic problem fails.

## Repetition is not stationarity

Each row keeps both the distance to the source cycle set and `|x[k]-x[k-3]|`.
The latter is undefined for k<3 and is stored as null. A fixed point also has zero
three-step difference: that quantity alone cannot identify a nontrivial cycle.
Read the gradient norm and distance to the optimizer separately. No Boolean
“converged to a cycle” label is inferred from one small diagnostic.

The raw record contains the piece coefficients, joins, constants, start and initial
memory, method parameters, every row, source references, environment and exact
cycle fractions. Input hashes cover the UTF-8 compact sorted-key JSON of the
input dictionary. The final row's update terms are null. Fingerprints identify
inputs; they do not certify the author or the theorem.

## Validation and limits

Independent tests integrate the gradient's pieces, check continuity and secant
bounds, compute initial updates with rational arithmetic, and verify the exact
cycle equations. A standard-library validator recomputes every row and metric
from scalar formulas, including the first missing period comparisons and final
missing update. Corrupt observations are rejected.

SVG/browser checks compare actual state coordinates, complete curves, readouts,
keyboard/playback, language, raw JSON and no-script views for all nine cases.
Both installed distribution formats must execute the full default workflow,
agree with HTML and the offline tour, and satisfy the independent validator.

The existing eight fixed checks and empirical heavy-ball tolerance are unchanged.
This separate source example explains a limitation of the quadratic setting. It
adds neither a new optimizer nor a universal failure theorem about momentum.
