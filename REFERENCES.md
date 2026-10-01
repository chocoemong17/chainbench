# Public references

These sources are credited for published algorithms and analysis. Implementations are independent; papers and third-party source code are not bundled. The precise relationship of each source to the implemented recurrence and checked inequality is in [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md).

## Noisy-wavelet dual objective bound

S.-J. Kim, K. Koh, M. Lustig, S. Boyd and D. Gorinevsky (2007),
*An Interior-Point Method for Large-Scale l1-Regularized Least Squares*,
IEEE Journal on Selected Topics in Signal Processing 1(4), 606–617.
[Author page](https://stanford.edu/~boyd/papers/l1_ls.html),
[public PDF](https://web.stanford.edu/~boyd/papers/pdf/l1_ls.pdf),
[DOI](https://doi.org/10.1109/JSTSP.2007.910971).
Used for the full-squared-loss dual lower bound, §III-B / Eqs. (10), (12),
p.609; no interior-point solver or MRI reproduction is claimed.
[Implementation scope](docs/FISTA_WAVELET.md).
The same dual is explicitly rescaled to the half-squared loss in the controlled
[proximal dual geometry](docs/PROXIMAL_GEOMETRY.md#development-addition-the-same-iterates-in-dual-coordinates).

## Randomized Kaczmarz expectation attainment

T. Strohmer and R. Vershynin (2009). *A Randomized Kaczmarz Algorithm with
Exponential Convergence*. Journal of Fourier Analysis and Applications 15,
262–278. https://doi.org/10.1007/s00041-008-9030-4

Implemented locations use [arXiv:math/0702226v1 (2007)](https://arxiv.org/pdf/math/0702226v1),
Algorithm 1 / Eq. (4), Theorem 2 / Eq. (5), printed/PDF p.4, and Section 3.2,
printed/PDF p.9. The six added sizes/seeds instantiate that source's equality
construction. [Inputs and notation caveat](docs/KACZMARZ_EXPECTATION.md).

## Acceleration and proximal gradient

Yu. E. Nesterov (1983). A method of solving a convex programming problem with convergence rate O(1/k^2). Doklady Akademii Nauk SSSR, 269(3), 543-547. Historical acceleration reference; not the literal recurrence implemented here.
https://www.mathnet.ru/eng/dan46009

A. Beck and M. Teboulle (2009). A Fast Iterative Shrinkage-Thresholding Algorithm for Linear Inverse Problems. SIAM Journal on Imaging Sciences, 2(1), 183-202. Source for fixed-L FISTA, its smooth g=0 specialization and the associated objective-gap bounds.
https://doi.org/10.1137/080716542

## Heavy-ball

B. T. Polyak (1964). Some methods of speeding up the convergence of iteration methods. USSR Computational Mathematics and Mathematical Physics, 4(5), 1-17.
https://doi.org/10.1016/0041-5553(64)90137-5

L. Lessard, B. Recht and A. Packard (2016). Analysis and Design of Optimization
Algorithms via Integral Quadratic Constraints. SIAM Journal on Optimization,
26(1), 57–95. Source for the separate public heavy-ball counterexample, not an
implementation of the full IQC framework. [DOI](https://doi.org/10.1137/15M1009597);
exact implemented source: [arXiv:1408.3595v7](https://arxiv.org/pdf/1408.3595v7),
§4.6, Figures 6–7 and Appendix B.

## Adam counterexample and AMSGrad

S. J. Reddi, S. Kale and S. Kumar (2018). *On the Convergence of Adam and Beyond*.
ICLR 2018. Exact source: [arXiv:1904.09237v1](https://arxiv.org/pdf/1904.09237v1)
(uploaded 2019-04-19), Algorithm 1 / footnote 1 / Eq. (1), p.3;
Theorem 1, p.4; Appendix A, pp.10–11; Algorithm 2, p.5.
The separate workflow instantiates the period-three analysis variant without
debiasing, with beta1=0. It does not reproduce the distinct Figure 1 experiment.
[Protocol and limitations](docs/ADAM_COUNTEREXAMPLE.md).

## Conjugate gradient

M. R. Hestenes and E. Stiefel (1952). Methods of Conjugate Gradients for Solving Linear Systems. Journal of Research of the National Bureau of Standards, 49(6), 409-436. Historical algorithm source.
https://nvlpubs.nist.gov/nistpubs/jres/049/jresv49n6p409_A1b.pdf

J. R. Shewchuk (1994). An Introduction to the Conjugate Gradient Method Without the Agonizing Pain. Carnegie Mellon University, technical report CMU-CS-94-125. Section 9.2, equation (52), explicitly states the A-norm condition-number bound used by this project.
https://www.cs.cmu.edu/~quake-papers/painless-conjugate-gradient.pdf

## Frank-Wolfe

M. Frank and P. Wolfe (1956). An algorithm for quadratic programming. Naval Research Logistics Quarterly, 3(1–2), 95–110. Historical source of the method; the scheduled recurrence and bound implemented here follow Jaggi (2013).
https://doi.org/10.1002/nav.3800030109

M. Jaggi (2013). Revisiting Frank-Wolfe: Projection-Free Sparse Convex Optimization. Proceedings of ICML, PMLR 28(1), 427-435. Algorithm 1 and Theorem 1 with delta=0 and k>=1.
https://proceedings.mlr.press/v28/jaggi13.html

## ADMM variable splitting

S. Boyd, N. Parikh, E. Chu, B. Peleato and J. Eckstein (2011).
*Distributed Optimization and Statistical Learning via the Alternating Direction
Method of Multipliers*. Foundations and Trends in Machine Learning 3(1), 1–122.
[Author PDF](https://web.stanford.edu/~boyd/papers/pdf/admm_distr_stats.pdf),
§6.4 / Eq. (6.2) and the displayed LASSO updates, printed p.43 / PDF p.46;
§3.3, printed pp.18–19 / PDF pp.21–22; §11.1.1 / Figure 11.2, printed p.89 / PDF p.92.
This is a review of an algorithm originating in the 1970s. The added examples are
new controlled 2D inputs, not the source's dense experiment.
[Protocol and coordinate conventions](docs/ADMM_GEOMETRY.md).

## Proximal point

R. T. Rockafellar (1976). Monotone Operators and the Proximal Point Algorithm. SIAM Journal on Control and Optimization, 14(5), 877-898. Foundational PPA source; the experiment uses the directly derived quadratic resolvent specialization documented in SOURCE_MAP.
https://doi.org/10.1137/0314056

## Tight GD case study

Drori, Y. and Teboulle, M. (2014), *Performance of first-order methods for smooth convex minimization: a novel approach*, Mathematical Programming 145, 451–482. DOI: https://doi.org/10.1007/s10107-013-0653-0

Implemented source: public preprint https://arxiv.org/pdf/1206.3209, Theorems 3.1/3.2, restricted to 0<h<=1. See docs/GD_TIGHT_CASE.md for the horizon-dependent 1D specialization.
