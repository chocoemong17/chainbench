# Source-to-experiment map

This document separates the historical source of a method, the particular recurrence implemented, and the finite numerical condition checked. All bundled fixtures are constructed by ChainBench; none purports to reproduce an original paper's full dataset or experimental section.

Write R = ||x0-x*||_2 and k for the number of completed updates. Quadratics use f(x)=0.5*x^T Q x-b^T x, with Q symmetric positive semidefinite, and b=Q*x*. For strongly convex checks, mu and L are the smallest and largest eigenvalues of Q.

## Gradient descent

`gradient_descent` uses x[k+1] = x[k] - grad f(x[k])/L. The quantitative condition is f(x[k])-f* <= L*R^2/(2*k), k>=1. It is the smooth specialization of the standard ISTA bound discussed by Beck and Teboulle (2009). The default fixture has a zero eigenvalue; the chosen optimizer has zero in that null coordinate.

## Historical Nesterov CLI name

`nesterov-1983` is retained for compatibility with the initial development interface. The actual `accelerated_gradient` recurrence is the **smooth specialization g=0 of fixed-L FISTA** in Beck and Teboulle (2009): t[0]=1, t[k+1]=(1+sqrt(1+4*t[k]^2))/2 and the associated extrapolated gradient update. The checked inequality is f(x[k])-f* <= 2*L*R^2/(k+1)^2 for k>=1.

Nesterov (1983) is credited for the historical accelerated O(1/k^2) idea, not as a claim that this code transcribes that paper's exact indexing or algorithm. See the fixed-L FISTA algorithm in the 2009 paper for the implemented update.

## Polyak heavy-ball

Classical quadratic tuning is alpha=4/(sqrt(L)+sqrt(mu))^2 and beta=((sqrt(L)-sqrt(mu))/(sqrt(L)+sqrt(mu)))^2. In each eigenmode lambda, the error recurrence has characteristic polynomial z^2-(1-alpha*lambda+beta)*z+beta. The associated spectral-radius prediction is rho=(sqrt(L)-sqrt(mu))/(sqrt(L)+sqrt(mu)).

The reported metric is the relative difference between rho and the median of the last up to 20 consecutive Euclidean error ratios whose previous error exceeds 1e-10. **0.08 is a deliberately explicit empirical regression tolerance, not a constant in Polyak's theorem.** Spectral radius does not imply that every finite-step Euclidean ratio equals rho; transients, repeated roots, oscillations and floating-point floors matter. This check is a finite-tail demonstration on one quadratic, not a general heavy-ball guarantee.

## Conjugate gradient

The historical algorithm source is Hestenes and Stiefel (1952). The exact bound used here is also stated explicitly in Shewchuk (1994), Section 9.2, equation (52):

    ||e[k]||_Q <= 2 * ((sqrt(kappa)-1)/(sqrt(kappa)+1))^k * ||e[0]||_Q

where kappa=L/mu and ||e||_Q=sqrt(e^T Q e). Only positive iterations are summarized: k=0 would always contribute an uninformative ratio of 0.5. As of v0.1.1, CG solves a normalized correction equation `(Q/L) z = (b-Q*x0)/(L*s)`, with `s` chosen from the scaled initial residual, and recovers `x=x0+s*z`. This positive scaling does not change the exact-arithmetic iterates. Stopping uses the recomputed true residual `||b-Q*x|| <= max(atol, rtol*||b-Q*x0||)` rather than just the recurrence residual. The returned trace distinguishes convergence from exhausted iteration budgets. This follows the residual-rechecking caution in Shewchuk Section 11.2; it costs an additional matrix-vector product per update. The initial-residual reference differs from libraries that use `||b||` for relative tolerance. This floating-point test is not a claim of exact finite termination in dimension n.

## Frank-Wolfe

Frank and Wolfe (1956), *An algorithm for quadratic programming*, is the historical
method source. The learning timeline distinguishes that origin from the specific
2013 analysis used here; neither its relationship links nor symbolic process maps
claim a direct historical derivation. See [REFERENCES.md](../REFERENCES.md).

The implementation follows Jaggi (2013), Algorithm 1 with an exact linear minimization oracle and gamma[k]=2/(k+2). Theorem 1, with approximation parameter delta=0, gives f(x[k])-f* <= 2*C_f/(k+2) for k>=1.

Here f(x)=0.5*||x-target||^2 on the probability simplex. The target is feasible, so x*=target and f*=0. The Hessian is I and the squared Euclidean diameter is 2, giving C_f=2. The oracle chooses a basis vector attaining the minimum gradient coordinate. The theorem is not extrapolated to arbitrary infeasible starts or to k=0.

## Proximal point

Rockafellar (1976) is the foundational algorithm reference. The actual experiment is the elementary **exact quadratic specialization**, not a reproduction of the paper's general inexact monotone-operator analysis:

    x[k+1] = solve(I+c*Q, x[k]+c*b)
    e[k+1] = (I+c*Q)^(-1) e[k]
    ||e[k+1]||_2 <= ||e[k]||_2 / (1+c*mu)

This follows directly from the spectrum of the displayed resolvent. Ratios whose previous error is at or below 1e-12 are excluded rather than divided by an arbitrary tiny denominator.

## FISTA and the LASSO fixture

The implemented recurrence is Beck and Teboulle's fixed-L FISTA. The objective is F(x)=0.5*||diag(a)*x-b||^2+lambda*||x||_1, with all a[i] nonzero and lambda>=0. Its exact minimizer is soft(a*b,lambda)/a^2 and L=max(a^2). The checked inequality is F(x[k])-F* <= 2*L*R^2/(k+1)^2, k>=1.

This is a transparent diagonal-design demonstration, not an image-deblurring reproduction or a realistic sparse-regression benchmark. The stable gap evaluates a quadratic error plus the l1 Bregman term using an optimal subgradient, avoiding cancellation in F(x)-F*.

## ISTA vs FISTA: informational only

`ista-vs-fista` reports the ratio of final gaps at a common budget. It has **no pass/fail threshold**. A better rate bound does not assert that FISTA's objective is smaller at every iteration on every instance. A denominator already below the comparison floor is rejected instead of turning 0/0 into a successful result.

## Numerical contract and limitations

The source code is independently implemented from public algorithms. Default experiments are deterministic and small. Broader tests also use fixed Householder rotations, dimensions, condition numbers and regularizers. Passing these tests is evidence about these implementations and fixtures, not a mathematical proof or a certificate over all functions.

Quantitative bound checks allow 1e-10 in the normalized ratio. The checked-in report uses seven significant digits, with regression tolerance rtol=1e-6 and atol=1e-12 for numeric cells and exact checks for labels/statuses. NaN and infinity are rejected. Very ill-scaled problems can still overflow or lose accuracy; this package is not an arbitrary-precision solver. Constructors reject matrices with numerically negative eigenvalues rather than silently treating them as positive semidefinite.

Full bibliographic links are in [REFERENCES.md](../REFERENCES.md).

## Separate published-example reproduction (after v0.5.0)

`reproduce shewchuk-1994` independently recomputes the particular numerical setup in
Shewchuk Eq. (4), with steepest descent Eqs. (10)–(12)/Figure 8 and CG
Eqs. (45)–(49)/Figure 30. This is distinct from the fixed-suite synthetic CG fixture
above. Exact line-search steepest descent is not fixed-step `gradient_descent`.
The envelope is Eq. (52). See [source locations, mathematical inputs, differences,
license scope and validation](SHEWCHUK_REPRODUCTION.md). The nine additional starts,
3D view and energy chart are ChainBench additions, not original-paper figures.

## Separate simplex geometry (development source after v0.5.0)

The development command `geometry frank-wolfe` links Jaggi (2013) Algorithm 1,
Eq. (2) and Theorem 1 to a three-coordinate probability simplex. Its twelve
target/start fixtures are controlled illustrations, not original-paper figures.
See [the exact recurrence, curvature, projection and scope](SIMPLEX_GEOMETRY.md).
The `4/(k+2)` curve bounds objective gap for k>=1, not pointwise dual gap.

## Proximal geometry (development source after v0.5.0)

`geometry ista-fista` adds nine controlled diagonal-LASSO illustrations using
Beck–Teboulle Eqs. (1.5), (2.5)–(2.6), (3.1), (4.1)–(4.3) and Theorems 3.1/4.4.
The exact source locations, half-squared-loss scaling, stage indexing, bisection
contours and validation are documented in [PROXIMAL_GEOMETRY.md](PROXIMAL_GEOMETRY.md).
These do not reproduce the paper's original image-deblurring experiment.

## Inspectable stress (development source after v0.5.0)

Sampler v2 reuses the above recurrences and measurements with four dimensions and
declared initial-point/orientation strata. Radius-dependent bounds use each actual
`||x0-x*||`, CG normalizes energy error by its actual initial error, and the simplex
oracle always starts feasible. Missing denominators are recorded as unresolved,
not zero metrics or replacement seeds. See [exact formulas, floors and migration](STRESS_SAMPLING.md).

## Post-release validation notes (v0.1.1)

The quadratic constructor requires stationarity to relative floating precision, without an absolute tolerance floor; callers should build `b=Q@x_star` from their supplied symmetric matrix. `gap` is the energy error relative to that reference, and its interpretation as an optimality gap assumes a valid reference solution. This numeric reference check is not symbolic certification.

Every bound sample must be finite and nonnegative before reduction; an empty vector or invalid sample is not discarded. Observations require real finite values, and an empty suite is an error rather than a vacuous pass. Tests include hand-computed recurrences and the explicit v0.1.0 counterexamples. `scripts/check_mutations.py` checks only four named fault injections in temporary copies, not all possible defects.


## Configurable observations (v0.2.0)

The `experiment` command reuses the same public-method implementations, but does not
apply a fixed literature-check threshold to every configuration. It reports objective
gaps, distance to the fixture reference and one explicitly named stationarity quantity.
For quadratics it is `||Qx-b||_2`. For diagonal LASSO it is the norm of
`L * (x - prox_l1(x - smooth_grad(x)/L, 1/L))`. For simplex it is the Frank–Wolfe gap
`grad(x)^T (x - linear_minimizer(grad(x)))`. The latter two are not smooth gradient
norms. Fixture formulas and output semantics are specified in [EXPERIMENTS.md](EXPERIMENTS.md).
No new mathematical theorem, original dataset reproduction or general performance
ranking is introduced by this interface.

## Learning and the separate tight-GD case (v0.4.0)

The `learn` pages explain selected existing results rather than expanding the eight fixed checks. The new `case-study gd-tight` is separately sourced to Drori--Teboulle preprint Theorems 3.1 and 3.2. See [GD_TIGHT_CASE.md](GD_TIGHT_CASE.md): a horizon-dependent Huber function attains LR²/(4Nh+2) for GD step h/L, restricted to 0<h<=1. The theorem supplies extremality; a floating-point match does not prove it.
