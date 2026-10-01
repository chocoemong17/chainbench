# The noiseless FISTA image experiment

## Exact source and retained scope

Beck and Teboulle, *A Fast Iterative Shrinkage-Thresholding Algorithm for Linear
Inverse Problems*, SIAM Journal on Imaging Sciences 2(1), 183–202 (2009),
[author-hosted paper](https://www.tau.ac.il/~becka/FISTA.pdf), DOI
[10.1137/080716542](https://doi.org/10.1137/080716542).

Section 5.2 (printed p.199 / PDF page 17) specifies the noiseless 64×64 variant of
the simple-image experiment, lambda=0 and 10,000 iterations. Figure 5 is on printed
p.201 / PDF page 19. The blur and initial-image conventions are taken from Section
5.1: Gaussian size 9×9, sigma=4, reflexive boundary, start from the blurred image.

`reproduce fista-deblurring` recomputes the **ISTA/FISTA subset of this protocol**.
MTWIST is omitted. The source reports approximate endpoint magnitudes; its exact
arrays and machine output are not supplied. This implementation does not assert
pixel-identical images, identical endpoint values or a reproduction of every curve.
A smaller `--steps` is explicitly labelled a preview of the same setup.

```bash
python -m chainbench reproduce fista-deblurring --lang ko --output deblur.html
python -m chainbench reproduce fista-deblurring --format json --output deblur.json
python -m chainbench reproduce fista-deblurring --steps 200 --output preview.html
```

The generated `tour` includes this full 10,000-step report and links it to the
positive-lambda proximal geometry. The atlas supplies the standalone command too.
The old `reproduce shewchuk-1994` default remains 12 updates. This new default is
10,000, with a hard 1–10,000 limit and fixed 64×64 inputs. No noise seed, resampling,
parameter search or visual selection is involved. One source experiment is not
representative image-data breadth. The existing stress reports provide a separate
kind of evidence on their own explicitly synthetic problems.

## Public input, provenance and permission

The paper cites Hansen's 1994 Regularization Tools article and says that the simple
image comes from `blur.m`. We inspected the author-linked
[Netlib archive](https://www.netlib.org/numeralgo/na4-matlab7.tgz), version 4.1,
March 2008. Its `REGU/blur.m` image-generation subset creates overlapping ellipses,
a triangle and a cross. This small subset is ported with attribution and its
[full permission notice](licenses/REGUTOOLS.txt), also retained in the installed
module and generated HTML/JSON. The original toolbox blur operator is **not** used:
it has different boundary/kernel conventions from the FISTA experiment.

- Archive SHA-256: `07a8e8844a5593fc8ba739428b7637391342d8467be989bfb08681ee65f24b97`.
- `blur.m` SHA-256: `6ab03d347375aab26c847d924ff00cd1936d5324be53adcf4409a910f6890ac5`.
- Normalized 64×64 image SHA-256: `1f8f4514e4179f4ea31023abc1291d3f0bb15cbfae40f7d0a7d0df94d3587694`.

The image uses MATLAB's positive rounding and source index conventions, then divides
by its maximum 4. The paper does not give a toolbox version hash or a precise
64×64 downsampling rule; we generate `blur(64)`'s image directly. These unresolved
source details stay visible. The paper PDF and MATLAB toolbox are not distributed.

## Operator, loss and recurrence

Let w[d]=exp(-d²/32)/sum(exp(-j²/32)), for d,j=-4,…,4. Define the 64×64 matrix B by
summing these weights at reflected indices: -1 maps to 0, -2 to 1, 64 to 63, etc.
The two-dimensional blur is R(u)=B u Bᵀ. This edge-repeating symmetric convention
is explicit; it is not zero padding, periodic wrap or edge-excluding reflection.
B is symmetric and doubly stochastic, with nonnegative entries, so ||B||₂=1 and
||R||₂=1. The clean image u_ref gives b=R(u_ref), with no added noise. Optimize

    F(u) = ||R(u)-b||_F²
    gradient F(u) = 2 R(R(u)-b)
    L = 2, step = 1/2, F* = 0, u0 = b.

This is the paper's **full squared loss**, unlike ChainBench's half-squared-loss
LASSO illustrations. The clean image is a minimizer because its residual is zero;
the all-zero image is not the asserted optimizer. There is no pixel box constraint
and no iterate clipping. Uniqueness or stable image inversion is not assumed.

The source describes a three-level Haar representation u=W x. At lambda=0 and
orthonormal W, x - (1/L)∇F(Wx) maps exactly to the displayed image-coordinate
step. Extrapolation commutes with W too, and soft thresholding at zero is the
identity. We therefore run the same fixed-L ISTA/FISTA recurrence directly in
image coordinates. No wavelet coefficient trajectory or positive-lambda shrinkage
experiment is claimed. An independent three-level 2D Haar matrix test verifies
this coordinate equivalence for both methods, including momentum.

`methods._proximal_iterates` streams the existing recurrence. The public `ista`
and `fista` still collect the same full `Trace`; the bounded image experiment
retains only declared snapshots plus every scalar observation. Each yielded array
is a copy. The four existing fault injections remain required, with the FISTA
momentum mutation now targeting the shared iterator.

## Evidence and display contract

Every iteration, including k=0, retains F and image RMSE. Since F*=0, F itself is
objective error. RMSE compares with the clean image and answers a different
question: ill-conditioned blur can hide substantial image error behind a small
residual. There is no general method ranking or theorem threshold.

Snapshots are the sorted union of {0,1,final} with {10,100,200,1000,5000,10000}
within the budget. The complete float64 image, minimum/maximum and SHA-256 are
retained at each snapshot. All intermediate images can be recomputed from the
retained inputs and fixed recurrence; they are not all embedded. Hashes encode
row-major little-endian float64 bytes. JSON includes B, w, clean and observed
images, settings, source differences and environment.

All displayed images share grayscale [0,1], rounded to 8-bit pixels. Display-only
clipping does not change numerical arrays, F or RMSE. The offline selector changes
both methods to the same saved iteration; every saved image remains available in
a native details gallery without JavaScript. The two plots retain all samples,
with independent objective and image-error axes. No CDN/server is required.

## Validation and limits

Tests compare the port to an independent scalar 1-based source construction, blur
to a padded stencil and explicit Kronecker matrix, adjoint symmetry, gradient
finite differences, operator norm, Haar equivalence, recurrence indexing, hash
integrity, first updates, snapshot metrics and fixed-scale PNG bytes. The full
10,000-step CLI budget is exercised. Fault injections and old method tests still
run. Browser checks compare every display pixel against the raw arrays, inspect
both full curves, all snapshots, text bounds, keyboard, JSON, no-script and narrow
layouts. A standard-library validator recomputes the operator and snapshot metrics
in both clean installed distributions; release evidence requires this workflow.

This is a small public synthetic inverse problem. It does not reproduce the noisy
256×256 Figure 4 experiment or license the Cameraman image. Original noise draws
are unavailable. The separately scoped [noisy Haar workflow](FISTA_WAVELET.md)
now reruns the Figure 4 protocol with a declared new noise draw; it does not
assert an exact match to the original experiment. Cameraman remains outside scope.
