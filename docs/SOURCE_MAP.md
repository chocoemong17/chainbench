# Source-to-experiment map

The Backpropagation, CNN and Dropout visual lessons retain their approved constructed
examples. Their sources, exact numbers, timing and limitations are documented in
[Learning foundations](FOUNDATIONS.md). These are not trained paper benchmarks.

The standalone `reproduce reddi-2018` implements Reddi–Kale–Kumar's
Theorem 1 / Appendix A period-three online linear-loss counterexample,
with Algorithm 1's no-debiasing analysis variant and Algorithm 2's max-memory
AMSGrad. All nine declared C/alpha choices remain visible, including slow
AMSGrad progress. Loss-before-update indexing, regret and the complete-block
lower reference are separate from fixed-objective gaps and the different
Figure 1 protocol. [Exact version, recurrence and validation](ADAM_COUNTEREXAMPLE.md).

The standalone `case-study cg-spectrum` extends Shewchuk §9.1 / Eq. (50) /
Figure 31 and §9.2 / Eqs. (51)–(52) to 18 declared 16-dimensional inputs with
the same interval and condition number. It distinguishes actual mode ratios,
energy weights, source comparison polynomials and rounded-matrix residuals.
These are controlled illustrations, not Figure 31(d)'s unspecified original
inputs. [Full design and validation](CG_SPECTRUM.md).

The development Frank–Wolfe geometry report adds the scalar minimization from
Jaggi (2013), Algorithm 3 / PDF page 3, evaluated along each existing Algorithm 1
oracle direction. Its quadratic curve and analytic segment minimum are a local
diagnostic; the scheduled trajectory is unchanged and no second algorithm run or
method ranking is claimed. [Exact derivation and numerical contract](SIMPLEX_GEOMETRY.md#choosing-the-distance-along-the-oracle-direction).

The separate `reproduce kaczmarz-sampling` follows Strohmer–Vershynin's
arXiv:math/0702226v1 §4.1 / Eq. (18) / Figure 1: 101 Fourier coefficients,
700 irregular samples, cyclic/uniform/weighted row selection and 15,000
projections. Exact source inputs are unavailable; all three declared new inputs
remain visible. The coefficient L2 metric and Theorem 4's conditional spectral
bound are distinguished from squared error, expectations and measured SVD values.
[Protocol, complex recurrence, source ambiguity and validation](NONUNIFORM_SAMPLING.md).
The added projection-response panels derive the normalized Dirichlet kernel
from Eq. (18)'s finite Fourier basis and Algorithm 1. Actual prior coefficients
and rounded changes are stored during execution; the kernel is an exact-arithmetic
comparison with explicit floating-point differences, not an original paper figure.

The separate development `case-study kaczmarz-expectation` instantiates
Strohmer–Vershynin's public expected-squared-error bound attainment. It keeps
all declared random trials and distinguishes a theorem in expectation from a
single trajectory or finite sample mean. [Exact version, notation caveat,
six inputs and validation](KACZMARZ_EXPECTATION.md).
The added conditional-projection panel follows Theorem 2's proof, preprint
pp.5–6 / Eqs. (8)–(9): actual orthogonal error vectors, all candidate row outcomes
and their probability-weighted next error. It preserves the sampled paths and
distinguishes hypothetical choices from completed updates and finite-trial means.

The separate five-method `landscape` illustration uses the existing quadratic
specializations below. Its source links identify each recurrence; the constructed
rotated 2D inputs are not source-paper data. [Exact settings and projections](LANDSCAPE_CONTEXT.md).

This document separates the historical source of a method, the particular recurrence implemented, and the finite numerical condition checked. Fixed-suite fixtures are constructed by ChainBench; separate published-example workflows identify their exact inputs and differences. None purports to reproduce an original paper's full dataset or experimental section.

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

The development implementation now uses compensated accumulation of rounded
float64 products for CG's scalar inner products. NumPy matrix-vector products
and the recomputed true-residual stopping rule remain unchanged. This fixes
observed repeated-run drift without enlarging comparison or theorem thresholds;
finite trajectories may differ from earlier builds.
[Arithmetic diagnosis and limits](CG_ARITHMETIC.md).

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

The separate landscape explanation links each actual exact quadratic update to
Rockafellar Eqs. (1.7)–(1.9), printed p.878 / PDF 2, and the residual operator
Eq. (1.16), printed p.880 / PDF 4. Its subproblem contours, gradient balance and
floating solve residuals preserve that restricted scope.
[Inputs and display semantics](LANDSCAPE_CONTEXT.md#development-inspect-the-actual-ppa-subproblem).

## FISTA and the LASSO fixture

The separate development `geometry fista-backtracking` follows the **unnumbered
backtracking panel** on printed p.194 / PDF 12, not the fixed-L recurrence below.
It retains every candidate in 36 declared runs, carries accepted L forward, and
checks Theorem 4.4 with alpha=eta=2. Its quadratic model-difference identity,
raw subtraction differences, local acceptance semantics and complete visual
record are documented in [FISTA_BACKTRACKING.md](FISTA_BACKTRACKING.md).
The extended tour compares these two FISTA variants on their shared diagonal
objectives. It preserves their separate alpha=1 versus alpha=eta=2 envelopes,
actual input grids and unequal candidate work; the symbolic guide adds no
algorithm, timing ranking or general majorization certificate.

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
The metric view applies Section 7.1 / Figure 22's explanation to the existing
trajectories with the explicit symmetric square root of A. Raw displacements,
their transformed counterparts and observed normalized inner products distinguish
Euclidean orthogonality from A-conjugacy. It is a display transformation, not a
preconditioner experiment or a reproduction of Figure 22's original vectors.

The spectral view links Section 9.1 / Eq. (50) / Figure 31(a–c) and Section 9.2 /
Figure 33 to those same CG iterates. Exact finite-spectrum and interval comparison
polynomials are distinguished from measured eigenmode coefficient ratios and
weighted energy. Null initial-mode ratios and finite-precision errors are retained.
See [source equations and validation](CG_SPECTRAL_EXPLANATION.md). Equation (52)
is on printed p.36 / PDF p.42; the earlier reproduction locator was off by one.

## Separate simplex geometry (development source after v0.5.0)

The development command `geometry frank-wolfe` links Jaggi (2013) Algorithm 1,
Eq. (2) and Theorem 1 to a three-coordinate probability simplex. Its twelve
target/start fixtures are controlled illustrations, not original-paper figures.
See [the exact recurrence, curvature, projection and scope](SIMPLEX_GEOMETRY.md).
The `4/(k+2)` curve bounds objective gap for k>=1, not pointwise dual gap.
The same exact oracle minimizes the affine model from Section 2 / Eq. (2).
Its three vertex values and `[f(x)-g_FW(x), f(x)]` bracket are shown for each actual
step. The known `f*=0` audits the bracket but is not used to compute its endpoints.
The lower affine value can be negative while the quadratic objective is nonnegative.

The separate `case-study fw-sparsity` computes Jaggi's Section 3 Lemmas 3–4 and
Appendix C construction: f=||x||² on the unit simplex, C_f=4, f*=1/n. Minimum
objective with support≤s is 1/s, attained by equal weights. The dual floor 2/s
requires s<n. Existing FW updates are compared with this sharp support minimum;
they are not asserted to attain an exact iteration worst case. The dimension
choices and views are added illustrations. [Exact source and checks](FW_SPARSITY.md).

## ADMM LASSO geometry (development source after v0.5.0)

`geometry admm-lasso` follows Boyd et al. (2011), §6.4 / Eq. (6.2) and the
displayed LASSO updates (printed p.43 / PDF p.46); residuals and the ≤ stopping
test follow §3.3 / Eq. (3.12), printed pp.18–19 / PDF pp.21–22. This source is
a review of a method originating in the 1970s. All 36 two-dimensional inputs
are declared additions, not the original dense experiment. Original `F(z)` and
the infeasible split value `f(x)+g(z)` are explicitly distinct, as are feature
coordinates `y=ρu` and the other pages' measurement-space dual variables.
[Inputs, original optimum, stable gaps, geometry and audit](ADMM_GEOMETRY.md).
The extended tour connects these updates to the existing ISTA/FISTA page using
symbolic flows and an explicit notation table. It keeps different input grids,
thresholds, intermediate-variable meanings and per-step work separate. Its actual
surface preview and 36-case metadata retain the same controlled scope; no
FISTA theorem envelope or measurement-space dual certificate is transferred.
The subproblem panels specialize the scaled form in §3.1.1, Eqs. (3.5)–(3.7)
(printed p.15 / PDF p.18), to these same LASSO inputs. Quadratic contours use
the exact-arithmetic stationary-point identity for `AᵀA+ρI`; shrinkage uses
the previous scaled dual state. These changing model objectives are distinct
from the original primal gap and from a convergence-rate claim.

## Proximal geometry (development source after v0.5.0)

`geometry ista-fista` adds nine controlled diagonal-LASSO illustrations using
Beck–Teboulle Eqs. (1.5), (2.5)–(2.6), (3.1), (4.1)–(4.3) and Theorems 3.1/4.4.
The exact source locations, half-squared-loss scaling, stage indexing, bisection
contours and validation are documented in [PROXIMAL_GEOMETRY.md](PROXIMAL_GEOMETRY.md).
These do not reproduce the paper's original image-deblurring experiment.
The added dual geometry applies Kim et al. (2007), §III-B / Eqs. (10), (12),
p.609, after explicit conversion to this half-squared loss. The existing
primal iterates supply feasible residual candidates; a separately known diagonal
dual solution explains the candidate deficit. It does not introduce a dual solver
or claim to reproduce the source experiments. [Coordinates and scaling](PROXIMAL_GEOMETRY.md#development-addition-the-same-iterates-in-dual-coordinates).
The upper-model slice additionally links Eq. (2.7) and Remark 3.1 to each actual
proximal update. It compares F and Q on the line through y and the next point,
retains every existing case, and distinguishes descent from y from descent from
the previous iterate. It is an added explanation of the same fixed-L recurrence.

## Inspectable stress (development source after v0.5.0)

Sampler v2 reuses the above recurrences and measurements with four dimensions and
declared initial-point/orientation strata. Radius-dependent bounds use each actual
`||x0-x*||`, CG normalizes energy error by its actual initial error, and the simplex
oracle always starts feasible. Missing denominators are recorded as unresolved,
not zero metrics or replacement seeds. See [exact formulas, floors and migration](STRESS_SAMPLING.md).

## Post-release validation notes (v0.1.1)

The quadratic constructor requires stationarity to relative floating precision, without an absolute tolerance floor; callers should build `b=Q@x_star` from their supplied symmetric matrix. `gap` is the energy error relative to that reference, and its interpretation as an optimality gap assumes a valid reference solution. This numeric reference check is not symbolic certification.

Every bound sample must be finite and nonnegative before reduction; an empty vector or invalid sample is not discarded. Observations require real finite values, and an empty suite is an error rather than a vacuous pass. Tests include hand-computed recurrences and the explicit v0.1.0 counterexamples. `scripts/check_mutations.py` checks a fixed set of named fault injections in temporary copies, not all possible defects. The saved-comparison, reading-bundle and stored-instance publication-gate injections join the four earlier cases.


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


## Noiseless image experiment (development source after v0.5.0)

`reproduce fista-deblurring` follows Beck–Teboulle Section 5.2 / Figure 5's noiseless
64×64 setup for the ISTA/FISTA subset. It uses the **full** squared residual with
L=2, lambda=0, known optimal value zero and 10,000 updates. At zero penalty,
orthonormal Haar coordinates and image coordinates yield equivalent iterates;
the implementation uses the latter. The source image version and all differences
are explicit in [FISTA_DEBLURRING.md](FISTA_DEBLURRING.md). Source-reported endpoint
magnitudes are not pass thresholds; MTWIST and the noisy experiment are omitted
from that command. The separate `reproduce fista-wavelet` follows the noisy
256×256, λ=10⁻⁴, three-stage Haar protocol from §5.2 / Figure 4 with a declared
new noise draw and 200 updates. It uses actual coefficient shrinkage, full squared
loss, L=2 and threshold 5×10⁻⁵. The optimum is unknown, so F is not a gap.
See [inputs, conventions, source differences and validation](FISTA_WAVELET.md).
An added snapshot diagnostic uses Kim et al. (2007), Section III-B, Eqs. (10)
and (12), printed p.609 / PDF p.4: a feasible dual value bounds the unknown
optimum from below. Its capped residual scaling and floating-point margin are
declared additions, not a transcription of Eq. (11) or their interior-point
algorithm. F−D bounds suboptimality; it is not the true unknown F−F* or RMSE.

## Heavy-ball's public nonquadratic counterexample

`reproduce lessard-2016` uses Lessard–Recht–Packard (2016), arXiv:1408.3595v7,
§4.6 Eq. (4.11), Figures 6–7 and Appendix B Eqs. (B.1)–(B.3). The existing
heavy-ball recurrence runs with mu=1, L=25, alpha=1/9, beta=4/9 and x[-1]=x[0]=3.3
on the published piecewise-gradient objective. Its exact rational three-cycle is
an analytical reference, not a fitted output. See [inputs, indexing, geometry and
scope](HEAVY_BALL_COUNTEREXAMPLE.md). Eight extra starts and GD at 1/L are labelled
additions. The IQC programs and parameter searches are outside scope; the fixed
quadratic check and its empirical tolerance remain unchanged.

## Stored numeric inputs (development source after v0.6.0)

The separate `instance` workflow reuses the configurable observation metrics and
solver recurrences above with explicit arrays and x0. It adds no mathematical
claim or literature-check threshold. PSD reference distance is not distance to
the set of minimizers. The supplied quadratic reference is checked numerically,
not symbolically certified. [Inputs, generator, hashes and replay contract](STORED_INPUTS.md).

The opt-in [experiment studio](STUDIO.md) exposes a narrower parameter range of
this same generator and the same recurrences. It computes new observations in
Python; the embedded report then inspects stored rows. It adds no algorithm,
theorem threshold or universal ranking. Its install/browser checks independently
bind each displayed/downloaded report to the actual numeric input and request.

## Adam single-paper film

The separate `/papers/adam/` visual lesson implements Kingma--Ba
[arXiv:1412.6980v9](https://arxiv.org/abs/1412.6980v9), Algorithm 1 (PDF p.2),
including both bias corrections and epsilon outside the square root. Its unequal-scale
quartic valley is an authored full-gradient illustration, not original paper
data or a general performance ranking. It differs from the existing no-debiasing
Reddi counterexample. [Inputs, recurrence, movie timing and tests](ADAM_FILM.md).

The separate [example-selection study](ADAM_EXAMPLE_STUDY.md) explores 27 authored
quartic/curved/Rosenbrock cases with explicitly searched learning rates and
Momentum coefficients. Its approved unequal-scale quartic illustrates Algorithm 1's
coordinate-wise normalization; target-entry counts are finite observations, not
source-paper results or a general ranking. The lesson now uses the approved fixture and settings; the archived study remains
unchanged. Rotated controls and all tried settings are retained.

## Attention and ResNet visual lessons

The approved four-scene explanations use Vaswani et al.
[arXiv:1706.03762v7](https://arxiv.org/html/1706.03762v7), §3.2.1 Eq.(1),
§§3.2.2–3.2.3. Assigned name/location basis vectors demonstrate scaled dot-product
attention. The sentence/head scene is schematic, not trained semantic attention.
ResNet follows He et al. [arXiv:1512.03385v1](https://arxiv.org/html/1512.03385v1),
§§3.1–3.2 Eq.(1) with post-add ReLU, and the direct backward path from
[Identity Mappings](https://arxiv.org/html/1603.05027v3), §2 Eqs.(3)–(5).
The latter assumes identity after addition; our scalar ReLU examples are locally
active, so the gate derivative is1. Cancellation and inactive-gate controls are
explicit. Separate feature-grid, scalar-block and depth toys are declared; no
ImageNet, trained-network performance or universally preserved gradient claim.
[Exact fixtures, assumptions, animation semantics and checks](VISUAL_PAPERS.md).
The owner approved revision3 on `study/method-concepts` before this refinement.
