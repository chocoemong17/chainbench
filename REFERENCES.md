# Public references

These sources are credited for published algorithms and analysis. Implementations are independent; papers and third-party source code are not bundled. The precise relationship of each source to the implemented recurrence and checked inequality is in [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md).

## Acceleration and proximal gradient

Yu. E. Nesterov (1983). A method of solving a convex programming problem with convergence rate O(1/k^2). Doklady Akademii Nauk SSSR, 269(3), 543-547. Historical acceleration reference; not the literal recurrence implemented here.
https://www.mathnet.ru/eng/dan46009

A. Beck and M. Teboulle (2009). A Fast Iterative Shrinkage-Thresholding Algorithm for Linear Inverse Problems. SIAM Journal on Imaging Sciences, 2(1), 183-202. Source for fixed-L FISTA, its smooth g=0 specialization and the associated objective-gap bounds.
https://doi.org/10.1137/080716542

## Heavy-ball

B. T. Polyak (1964). Some methods of speeding up the convergence of iteration methods. USSR Computational Mathematics and Mathematical Physics, 4(5), 1-17.
https://doi.org/10.1016/0041-5553(64)90137-5

## Conjugate gradient

M. R. Hestenes and E. Stiefel (1952). Methods of Conjugate Gradients for Solving Linear Systems. Journal of Research of the National Bureau of Standards, 49(6), 409-436. Historical algorithm source.
https://nvlpubs.nist.gov/nistpubs/jres/049/jresv49n6p409_A1b.pdf

J. R. Shewchuk (1994). An Introduction to the Conjugate Gradient Method Without the Agonizing Pain. Carnegie Mellon University, technical report CMU-CS-94-125. Section 9.2, equation (52), explicitly states the A-norm condition-number bound used by this project.
https://www.cs.cmu.edu/~quake-papers/painless-conjugate-gradient.pdf

## Frank-Wolfe

M. Jaggi (2013). Revisiting Frank-Wolfe: Projection-Free Sparse Convex Optimization. Proceedings of ICML, PMLR 28(1), 427-435. Algorithm 1 and Theorem 1 with delta=0 and k>=1.
https://proceedings.mlr.press/v28/jaggi13.html

## Proximal point

R. T. Rockafellar (1976). Monotone Operators and the Proximal Point Algorithm. SIAM Journal on Control and Optimization, 14(5), 877-898. Foundational PPA source; the experiment uses the directly derived quadratic resolvent specialization documented in SOURCE_MAP.
https://doi.org/10.1137/0314056

## Tight GD case study

Drori, Y. and Teboulle, M. (2014), *Performance of first-order methods for smooth convex minimization: a novel approach*, Mathematical Programming 145, 451–482. DOI: https://doi.org/10.1007/s10107-013-0653-0

Implemented source: public preprint https://arxiv.org/pdf/1206.3209, Theorems 3.1/3.2, restricted to 0<h<=1. See docs/GD_TIGHT_CASE.md for the horizon-dependent 1D specialization.
