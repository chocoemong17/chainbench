# A tight public example for gradient descent

## Public source and precise scope

Yoel Drori and Marc Teboulle, *Performance of first-order methods for smooth convex
minimization: a novel approach*, Mathematical Programming 145 (2014), 451–482.
DOI: https://doi.org/10.1007/s10107-013-0653-0

The implementation uses **Theorems 3.1 and 3.2 in the public preprint**:
https://arxiv.org/pdf/1206.3209 (PDF pages 12–13, preprint numbering).
Those pages were checked directly; do not silently use theorem numbering from a
different version of the publication.

Theorem 3.1 bounds the final objective error of GD with constant step h/L, 0<h<=1,
on convex continuously differentiable functions with L-Lipschitz gradient and an
optimizer x* within distance R of x0:

    f(x_N) - f* <= L R^2 / (4 N h + 2).

Theorem 3.2 supplies an attaining construction. For h<=1 the first construction
matches this upper bound. Our code does not implement the h>1 regime or present
a conjecture about that regime as an established theorem.

## Implemented one-dimensional specialization

Fix N and a=R/(2Nh+1), with x*=0, f*=0, x0=R. Set

    f(x) = L*x^2/2                       for |x| <= a
         = L*a*|x| - L*a^2/2             for |x| > a
    f'(x) = L * clip(x,-a,a).

Run actual floating-point GD updates `x <- x - (h/L)*f'(x)`. Over the first N
updates, the analytic expressions are

    x_k = R - k*h*a
    f(x_N) = L R^2 / (4 N h + 2).

Code records each computed x, gradient, gap, and the general upper bound at that
iteration. The equality ratio compares the **loop's final value** with the
independently evaluated target formula. The fixed function is used throughout
one run; changing N constructs a different function. Its gap need not equal the
upper bound at earlier k. This distinction is visible on the plot.

The function view marks the actual stored GD points in original units. A slider
selects a recorded point, shows its position/value/gradient, and reveals the
corresponding path prefix; playback does not run an optimizer in JavaScript.
The full path and every row remain accessible without JavaScript.

The sampling grid includes the exact joins ±a and at least 81 points inside the
quadratic centre. A uniform grid over the full R-scale can miss this narrow
centre when N is large. An adjacent view instead uses u=x/a and
φ(u)=f(a*u)/(L*a²). It is the same function with both axes rescaled:

    φ(u) = u²/2      for |u| <= 1
         = |u|-1/2  otherwise.

Its slopes agree at ±1. Affine tails have zero curvature, not zero gradient.
All stored iterates lie strictly beyond +a because

    x_N = (Nh+1)*a > a.

Thus their gradients are La, each step moves ha, and direct substitution gives
f(x_N)=La²(Nh+1/2)=LR²/(4Nh+2). This algebra explains attainment; Theorem 3.1
supplies the separate upper bound for the full class of admissible functions.

The JSON adds a `geometry` object with normalization scales, centre samples and
transition values/gradients. The existing function chart uses a transition-aware
grid; algorithm rows and bound/gap series are unchanged. The installed-package
validator independently evaluates the piecewise function, normalized samples and
stored recurrence at N=1 and N=500. Unit tests also cover extreme allowed L/R/h
scales. Browser CI checks every point, keyboard/playback, JSON, no-JavaScript
access and wide/narrow layouts for N=20 and N=500.

 No PDF, third-party code, confidential derivation or private research
is distributed. Only the public construction and independently written code are used.

## Meaning of the result

The worst-case assertion comes from the cited **mathematical upper bound plus
matching construction**, not the numerical graph or a random search. The local
floating-point check compares the final ratio with 1 at absolute tolerance 1e-9;
this is a reproducibility tolerance, not part of the theorem.

This does not prove optimality/uniqueness of any algorithm, classify all worst
cases, or claim worst-case behavior for FISTA, CG or a different performance
criterion. We do not optimize over algorithms or invoke a PEP solver.

UI limits: N integer 1–500, L,R in [1e-6,1e6], h in [1e-4,1]. The mathematical
statement allows 0<h<=1; the stricter implemented lower limit avoids excessively
small finite-precision steps. N=1,L=R=h=1 gives x1=2/3 and f(x1)=1/6, independently
checked in unit tests and the installed-package smoke test.
