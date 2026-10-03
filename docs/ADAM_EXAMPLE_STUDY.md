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

## Second pass: broaden tuning and test the candidate's limits

The initial run ([37139450987](https://github.com/chocoemong17/chainbench/actions/runs/37139450987),
source `c343b83`) passed 22 implementation tests. The aligned quartic with ratio
10000 was a promising illustration (Adam 82 / Momentum 880 / GD not within
1200 updates). Rotated and curved examples frequently favored Momentum.
These exploratory observations motivate the next pass, not a universal ranking.

The second pass retains all original rates and adds 101 GD/Momentum rates across
0.0001–64 times the scale; 15 Momentum betas including 0, 0.975–0.9999;
65 Adam rates over 0.001–4 and the round settings 0.2, 0.25, 0.3. Union grids
remove duplicates. No candidate from the original search is discarded.
It adds quartic ratios 1000/100000, rotations 0.5°/1°/2°/5°, and starts
(-2.4,1.6), (-3.6,2.4), (-3,1), (-2,3), for 27 cases total. Each is retuned;
frozen central settings will also be checked before recommending a final example.
The target and 1200-update budget are unchanged. All explored families, including
ones where Adam loses, remain available.

## Final proposal protocol

Before plotting, refine the central aligned ratio-10000 baselines once more:
GD adds 101 rates over 1e-5–1e-4; Momentum adds 65 rates over 1e-6–1e-4 ×
81 betas over 0.96–0.9999. Keep the entire previous grid. Adam uses the declared
round rate **0.14** for the proposed illustration, even if another searched rate
is faster. Baselines use their best found rates. The four nearby starts also run
with these central settings frozen, alongside the earlier per-start retuning.

Every point with a nonfinite coordinate or absolute coordinate ≥1e10 terminates
that candidate's usable trace. It is recorded as failed, not silently clipped
into the plotting window. All selected paths remain finite and unmodified.
Plots show the first 100 actual updates and the first 60 steep-coordinate values;
the progress chart uses a logarithmic distance axis and explicitly shows its range.
The known unique minimum is (0,0): each nonnegative quartic term vanishes only there.

The fixture's normalization illustrates the original paper's per-coordinate
moment mechanism. It does not reproduce an original training experiment, and
diagonal scale cancellation is only exact when epsilon is zero. The implemented
epsilon remains 1e-8. No universal advantage under rotations is claimed.
