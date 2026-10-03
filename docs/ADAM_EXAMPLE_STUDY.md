# Adam: choose the example before remaking the film

The published layout stays in place. This branch studies the numerical example;
it does not change the lesson or generate a new movie.

## Question and protocol declared before results

Adam's coordinate-wise moment normalization is described in Kingma–Ba,
[Algorithm 1 and §2.1, arXiv:1412.6980v9](https://arxiv.org/pdf/1412.6980v9).
Can a deliberately unequal-scale nonlinear landscape make that mechanism visible?
These are authored deterministic illustrations, not original paper experiments
or a claim about general training speed.

Seventeen cases compare separable quartic bowls (scale ratios 1, 100, 10000;
orientations 0°, 15°, 45°), curved quartic valleys (ratios 100 and 10000;
bends 0.01, 0.1, 0.3) and Rosenbrock (0°, 30°). Rotations change the function
in optimizer coordinates, not just the camera. The existing film's rotated
Rosenbrock is retained as a control.

Every run uses 1200 full gradients from an identical start. A candidate reaches
the declared target when BOTH distance/initial-distance ≤ 0.01 and
objective/initial-objective ≤ 0.0001, and remains there through the last step.
Select the earliest such step; break ties by final relative distance, then loss.
Runs that never reach the target rank by final distance then loss. Divergence is
recorded explicitly, never substituted with a successful trace.

Each case gets a broad, separately tuned learning-rate grid: GD 61 values;
classical Momentum the same 61 × six beta values (0.5, 0.9, 0.95, 0.99, 0.995,
0.999); Adam 37 values from 0.001 to 1 with beta1=0.9, beta2=0.999, epsilon=1e-8
and both bias corrections. GD/Momentum alpha spans 0.0001–8 times a declared
case scale (not a claimed global Lipschitz bound). Momentum receives more
tuning opportunities. Every tried setting and failure stays in the JSON.

This is finite-grid example selection on known synthetic inputs, not a proof of
optimal tuning. A candidate needs further nearby-setting/start checks and readable
path/early-step views before being proposed for the lesson. All execution and
plotting take place in GitHub Actions. No new video is made in this study.
