# One paper, one film: Adam

The `/papers/adam/` lesson keeps one 48-second film, two synchronized draggable
graphs, a short takeaway and the original-paper link. English is the initial
language; Korean is optional. Its approved unequal-scale example is shown with
an open near wall so the valley floor and height differences remain visible.

## Source and scope

Kingma and Ba, *Adam: A Method for Stochastic Optimization*, ICLR 2015;
[arXiv:1412.6980v9](https://arxiv.org/abs/1412.6980v9), Algorithm 1 / PDF p.2.
The implementation uses first/second raw moment estimates, both bias corrections,
and epsilon **outside** the square root. It is separate from this repository's
Reddi et al. counterexample, which uses a different analysis variant.

This is an authored deterministic full-gradient illustration, not an original
neural-network experiment, a counterexample to Adam, or a general ranking.
No source-paper figures, training results or third-party video footage are copied.
The selected example and its controls are preserved in the
[27-case selection study](ADAM_EXAMPLE_STUDY.md) and its
[review record](reviews/adam-example/README.md).

## Approved experiment

`f(x,y) = phi(x) + 10000 phi(y)`, where `phi(z) = z²/2 + z⁴/4`.
The known unique minimum is zero at `(0,0)`; the start is `(-3,2)`.
Both terms are nonnegative and vanish only at zero. The coefficient ratio is
10000; it is not a constant global condition number of this nonquadratic function.
All methods receive 1200 full-gradient updates in the same coordinates.

- GD: `x_next = x - alpha grad f(x)`, `alpha=3.9810717055349695e-5`.
- Classical momentum: `b_next = beta b + grad f(x)`, `x_next = x - alpha b_next`,
  `b0=0`, `alpha=2.2067340690845897e-5`, `beta=.985935`.
- Adam: Algorithm 1, `alpha=.14`, `beta1=.9`, `beta2=.999`, `epsilon=1e-8`, zero moments.

The baselines use their best found central settings after the broad and refined
searches; Adam uses the declared round learning rate .14. This is finite-grid
selection, not globally optimal tuning. All 80,407 candidate records (including
repeated settings in refinement and failures) remain in the compressed ledger.
Rotated/curved controls where the ranking changes have not been removed.

The target requires **both** distance/initial-distance <= .01 and
objective/initial-objective <= .0001, maintained through update 1200. The first
such index is computed from the complete recorded trajectory: Adam 66,
Momentum 611, and GD not within 1200. This is a gradient-count observation,
not a wall-clock benchmark or a convergence theorem. No stochastic sampling,
clipped gradients or favorable replacement traces are used.

## Height and visibility

The fixed camera has elevation 27 degrees and azimuth -56 degrees. Height is
`log(1 + f)` for the surface, paths and height ticks alike. The near wall (`y<0`)
is drawn as a wireframe, with a narrow filled strip adjoining the valley floor;
the far wall stays filled. This is a visibility choice, not a changed objective,
coordinate transform, path distortion or optimizer preconditioner.

A nonuniform surface mesh resolves the narrow floor down to `|y|=.001`.
Height colors, profiles across the far wall, a zero-height ground grid, and
vertical dashed projections of the current points show the depth. Dashed lines
are display guides, not optimizer steps. The height guide is labeled with original
objective values at their logarithmic heights. The floor is highlighted and the
minimum has a light cross. Outlined paths and their markers are drawn above the
background for visibility. The camera, axes and visual height transform stay
fixed throughout the film; nothing auto-zooms to favor one method.

The right-side readout is remaining distance as a percentage of initial distance.
It shows a target-entry k only after that recorded index is reached. A displayed
0.0% is rounded, not a claim of an exactly attained floating-point minimum.
The build records camera/projection evidence and rejects clipped numerical paths
or an insufficiently separated height guide. Static frames and browser-decoded
frames are visually reviewed from Actions artifacts.

## Shared clock and graphs

The film has 24 fps and lasts 48 seconds:

| Time | Recorded updates |
|---|---|
| 0–4 s | Start hold |
| 4–22 s | 0–60, all early updates visible |
| 22–24 s | 60–66 |
| 24–27 s | Hold at Adam's target-entry update 66 |
| 27–31 s | 66–100 |
| 31–42 s | 100–1200 |
| 42–48 s | Final hold |

The JSON timing knots drive both Python rendering and JavaScript seeking.
`frame_iterations` records each actual displayed k; no optimizer states are
interpolated. Later frames skip some updates, while both graphs retain every row.
Native media clocks may round boundaries, so graph/range seeking selects the
middle of an encoded frame. Both methods of seeking remain draggable.

The graphs show actual objective and Euclidean distance on log axes; values below
1e-12 sit at the floor, while exact numbers remain in the readouts and JSON.
English/Korean captions explain the same sequence. No audio or autoplay.

## Build and checks

GitHub Actions performs all numeric execution, rendering and browser checks.
Matplotlib creates the fixed 3D background, Pillow draws recorded paths, and
FFmpeg encodes H.264 MP4/VP9 WebM. FFprobe checks resolution, duration and decoded
frame count. The site's manifest hashes all media, data, captions and web assets.

Tests compare every iterate with an independent NumPy recurrence and the
previously reviewed numerical artifact; check gradients by finite differences;
check the minimum, starting gradient, first Adam bias-corrected step, target
criteria, complete early-step coverage and the deliberate pause. Nonfinite or
divergent traces fail. Chromium/WebKit tests decode distinct movie frames,
exercise playback, pointer/keyboard/chart seeking, verify both numeric readouts,
clock inversion and the target-entry hold, and check English/Korean, mobile,
no-script reading, CSP and unavailable-data handling.

Deployment continues to require every job of the current main commit's full
`tests` workflow and the exact verified website artifact. No release is overwritten.
