# One paper, one film: Adam

This is the single-paper format study at `/papers/adam/`. It consists of one
48-second film, two synchronized graphs, a short takeaway and the original-paper
link. English is the initial language; Korean is optional. Other papers and the
existing homepage are not converted to this format until the user reviews it.

## Source and scope

Kingma and Ba, *Adam: A Method for Stochastic Optimization*, ICLR 2015;
[arXiv:1412.6980v9](https://arxiv.org/abs/1412.6980v9), Algorithm 1 / PDF p.2.
The code implements first/second raw moment estimates, both bias corrections,
and epsilon **outside** the square root. It is separate from this repository's
Reddi et al. counterexample, which uses a different analysis variant.

The movie is an authored deterministic full-gradient illustration. It does not
reproduce the paper's neural-network experiments or claim its convergence result.
No paper figures, neural-network results or video footage are copied.

## Declared experiment

Let `(x,y) = R(30 degrees) (u,v)` and
`f(x,y) = (1-u)^2 + 100(v-u^2)^2`.
The known minimum is zero at `R(1,1)`; the start is `R(-1.2,1)`.
All three methods take 2,400 full-gradient updates in the same coordinates.

- GD: `x_next = x - .001 grad f(x)`.
- Classical momentum: `b_next = .9 b + grad f(x)`, `x_next = x - .001 b_next`, `b0=0`.
- Adam: Algorithm 1, `alpha=.02, beta1=.9, beta2=.999, epsilon=1e-8`, zero moments.

The learning rates are fixed teaching choices, not a tuned comparison or the
paper's recommended Adam learning rate (.001). There is no stochastic sampling.
Equal iterations here mean equal gradient calls, not equal wall time or work.
The example was declared before inspecting its endpoints; the cloud design study
is retained. It shows Momentum ahead at this budget, rather than selecting a
scene that requires Adam to win. Outcomes depend on settings and coordinates.

## Display contract

Video height is `log(1 + f)`. The fixed camera shows actual projected iterates;
connecting lines aid tracing but introduce no new numerical states. The marker
for the minimizer and all trajectories share this projection. The camera and
plot bounds remain fixed; the build rejects paths outside the declared view.
The right-side ledger displays the actual objective of the selected iterate.

Frames run at 24 fps for 48 seconds. Seconds 0–6 hold the start; 6–16 expose the
first 60 updates; 16–40 cover the remaining updates; 40–48 hold the endpoint.
`frame_iterations` records every displayed k. Seeking graphs or the range control
selects an encoded frame and its actual recorded iterate. Later frames skip some
updates; the graphs retain every numerical row. No intermediate states are invented.

The two plots show the original objective and Euclidean distance to the known
minimum on logarithmic axes; values below 1e-12 sit at the display floor. Exact
numbers remain in the readouts and JSON. English/Korean WebVTT captions carry the
explanation; the film has no audio or automatic playback.

## Build and checks

Only GitHub Actions renders the film. Matplotlib creates a fixed 3D background;
Pillow overlays recorded paths and numbers; FFmpeg encodes H.264 MP4 and VP9 WebM.
FFprobe checks resolution, duration and decoded frame count. The site's existing
manifest hashes the film, poster, data, captions, HTML, JS and CSS before deployment.

Numerical tests compare every iterate against an independent NumPy recurrence,
check the rotated analytic gradient by finite differences, inspect Adam's first
bias-corrected step and reject non-finite/divergent calculations. Chromium/WebKit
checks decode multiple different video frames, play/pause, actual pointer/keyboard
and graph seeking, numerical readouts, captions, language preference, mobile layout,
no-script reading and data-load failures. Screenshots are reviewed from CI artifacts.
