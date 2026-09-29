# ISTA/FISTA: extrapolate, step, shrink

Development source after v0.5.0:

```bash
python -m chainbench geometry ista-fista --steps 18 --lang ko --output proximal.html
python -m chainbench geometry ista-fista --steps 18 --format json --output proximal.json
```

The contour, projected 3D surface, stage inspector and convergence curves use the
same actual numerical runs. Choose ISTA or FISTA, then inspect `x → y → z → x_next`.
All nine combinations remain available with both methods, numerical tables and
raw JSON. The controls are local; no optimizer runs in the browser. Without JavaScript,
all full paths, stage tables and native expandable cases remain readable.

## Public source and conventions

Beck and Teboulle (2009), *A Fast Iterative Shrinkage-Thresholding Algorithm for
Linear Inverse Problems*, [author-hosted original](https://www.tau.ac.il/~becka/FISTA.pdf):

| Source location | What this view implements |
| --- | --- |
| Eq. (1.5), printed p.185 / PDF page 3 | Componentwise soft-thresholding |
| Eqs. (2.5)–(2.6), printed p.189 / PDF page 7 | Minimize the quadratic smooth surrogate plus the exact nonsmooth term |
| Eq. (3.1), printed p.191 / PDF page 9 | Fixed-L ISTA |
| Eqs. (4.1)–(4.3), printed p.193 / PDF page 11 | Fixed-L FISTA, with its t sequence and extrapolation |
| Theorem 3.1, printed p.192 / PDF page 10 | ISTA objective-gap envelope |
| Theorem 4.4, printed p.195 / PDF page 13 | FISTA objective-gap envelope |

The paper's Eq. (1.3) uses an **unhalved** squared loss. ChainBench uses
`f(x)=0.5||Ax-b||²`, hence `gradient=Aᵀ(Ax-b)` and `L=||AᵀA||`, without the factor
two in the initial paper example. The paper's general composite model covers this
convention. This is a specialization of that model, not its deblurring experiment.
Our stage index k=0 denotes the first update, which the paper labels step k=1.
No paper image, PDF, third-party source or image dataset is distributed in the package.

## Declared mathematical input

`F(x)=0.5||diag(1,3)x-(1.4,-2.4)||² + lambda*(|x1|+|x2|)` on R².
The smooth part has L=9, mu=1 and condition number 9; the complete objective has
L1 corners and is not globally smooth. The step is 1/9 and the threshold is lambda/9.

All lambda values **0.1, 0.8, 1.8** are paired with all starts:

- `opposite`: (-1.8, 1.2)
- `zero`: (0, 0)
- `near`: (2, -1.4)

Both methods run every case. Defaults are 18 updates; integers 2–60 are supported.
There is no seed, filtering or early stopping. Hashes cover little-endian float64
`a,b,lambda,x0` in that order. Every report retains these values, method records,
source indexing and the environment.

The known optimizer is `soft(a*b,lambda)/a²`, a coordinatewise formula valid for
this diagonal problem. For lambda=0.1, 0.8, 1.8, its first coordinate is 1.3, 0.6, 0,
respectively. Changing lambda changes the objective, so gaps across different
lambda cases should not be interpreted as a common-problem performance ranking.

## What happens inside an update?

For ISTA, y=x. For FISTA, y extrapolates two previous iterates using the published t
recurrence. Both compute `z=y-gradient(f,y)/L`, then
`x_next,i=sign(z_i)*max(|z_i|-lambda/L,0)`.

The latter is the exact minimizer of `lambda*||u||1 + (L/2)*||u-z||²`.
At a nonzero coordinate, optimality gives `L*(z_i-u_i)=lambda*sign(u_i)`.
At zero, it requires `|L*z_i|<=lambda`. Thus the zero interval is part of the
mathematical proximal operator, not an arbitrary rounding tolerance.

The existing `ista`/`fista` routines supply the actual iterate arrays. The view then
reconstructs y, z and the momentum coefficient from those arrays, and checks each
soft-thresholded result against the returned next iterate. A disagreement is an error.
The visualization is not driven by an unrelated animation or a separate trajectory.

For lambda=0.8 from the opposite start, the first z is `(-13/9,-4/5)` and the next
point is `(-61/45,-32/45)`. The first two updates of ISTA and FISTA coincide; the
third differs because extrapolation has become nonzero. Later FISTA gaps can rise,
which the plots preserve. With valid fixed L, ISTA is nonincreasing (Remark 3.1).

## Curves, contours and heights

The main curve shows actual composite objective gaps. A separate expandable plot
adds `L*R²/(2k)` for ISTA and `2*L*R²/(k+1)²` for FISTA, k>=1, where R is each
case's actual distance from the start to the known optimizer. These use convexity,
L-smooth f, convex g, an exact prox and the correct fixed L (alpha=1 in the theorems).
A better upper envelope does not order all iterates of the two methods.

Contours solve `F(x)-F*=level` on rays from the unique optimizer. Vectorized
bisection approximates each level curve, including L1 kinks. The viewport uses equal
coordinate scales on x1∈[-2.5,2.5], x2∈[-2,2]; all recorded stage points lie inside
this range over the supported budgets. Contours outside it are explicitly clipped
to the axes, while labels and trajectory points remain inside the frame.

The surface is an oblique projection of `(x1,x2,F-F*)`. It includes the L1 term,
not just the smooth quadratic. Stage segments are straight chords connecting
sampled points at their actual heights; they do not claim continuous motion along
the surface. Colors/patterns distinguish method paths from the purple y, amber z
and green next point. In ISTA, y and x coincide.

## Checks and limitations

Independent tests reconstruct objective values, exact reference solutions, hashes,
bound normalizations, scalar first updates and the proximal optimality conditions.
They verify every marker against raw coordinates, test contour-level residuals,
preserve FISTA objective increases and reject inconsistent annotations. Clean wheel
and sdist workflows exercise the command and independently reconstruct its stages;
missing evidence blocks publication. Offline browser checks cover both methods in
all nine cases, keyboard/playback, zero-coordinate readouts, exact JSON downloads,
desktop/mobile sizes and no-JavaScript viewing.

Nine controlled low-dimensional cases help explain the mechanism. They are not
representative data, the paper's image experiment, a proof, worst-case evidence or
a claim that one method always wins. Use the separate versioned `stress` workflow
for wider declared synthetic sampling.
