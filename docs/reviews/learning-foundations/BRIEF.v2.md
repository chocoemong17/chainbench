# Learning foundations — revised concept contract, revision 2

**Owner review pending.** Revision 1 was reviewed as too sparse. On 2026-10-05 the
owner requested branching over five variables, moving CNN windows, stacked feature
volumes, a matrix-based parameter comparison, and dropout in several hidden layers.
The four-scene restriction is removed. No finished lessons or production pages are
added. [Previous contract](BRIEF.v1.md) and `v1/` assets remain available.

## Backpropagation: AB + CDE, ten stages

Source: Rumelhart, Hinton & Williams (1986),
[Learning representations by back-propagating errors](https://doi.org/10.1038/323533a0),
pp. 533–534, forward values and backward error derivatives.
[Author-hosted paper](https://www.cs.toronto.edu/~hinton/absps/naturebp.pdf).
This constructed expression illustrates the chain rule, not the paper's sigmoid
experiment, historical priority for reverse differentiation, or measured speed.

Inputs/adjustable variables: A=2, B=3, C=2, D=−1, E=2. Target 4.
Intermediate values u=AB=6, v=CD=−2, w=vE=−4, y=u+w=2.
Loss L=(y−4)^2/2=2. Seed g_y=−2. Addition passes g_u=g_w=−2.
Product u=AB gives g_A=g_u*B=−6 and g_B=g_u*A=−4.
Product w=vE gives g_v=g_w*E=−4 and g_E=g_w*v=+4.
Product v=CD gives g_C=g_v*D=+4 and g_D=g_v*C=−8.

| Stage | What changes |
| --- | --- |
| 1 | Five inputs and the branching graph; uncomputed nodes show question marks |
| 2 | AB and CD are computed independently |
| 3 | CDE, the sum, and loss are computed |
| 4 | Backward signal starts at output from the loss |
| 5 | Addition sends the same signal down both branches |
| 6 | AB sends two differently scaled signals to A and B |
| 7 | CDE sends signals to CD and E |
| 8 | CD sends signals to C and D |
| 9 | All five derivatives are visible together |
| 10 | One simultaneous gradient-descent update uses them |

Rate 0.02 gives [2.12,3.08,1.92,−0.84,1.92], y=3.433024 and
L≈0.160730. Three-significant-digit graph readouts are rounded; the verification
record retains computed values. A rate 0.5 control increases the loss. All 20
components at four distinct input sets are checked with central finite differences.
Addition distributes a derivative to its input branches; it does not split it in
half. Reusing one variable on multiple paths would instead require accumulating
its incoming derivatives; this particular graph has five distinct input leaves.

## CNN: nine chapters with 35/35/12 scan positions

Source: LeCun, Bottou, Bengio & Haffner (1998),
[Gradient-Based Learning Applied to Document Recognition](https://bottou.org/papers/lecun-98h),
§II: receptive fields, shared weights, feature maps and multiple layers.
Hand-set filters and modern ReLU are teaching choices, not a trained LeNet-5.

Our own 7×9 one-channel binary bars enter two 3×3 filters. Vertical filter: three
rows [−1,2,−1]; horizontal filter: its transpose. Valid cross-correlation followed
by ReLU, stride 1, no bias, produces 5×7×2 (height×width×channels).
Each scan shows the selected patch, coefficient-wise multiplication summarized
by three row sums, raw sum, ReLU output, and the corresponding newly filled cell.
The window visits all 35 positions in row-major order for each filter. The stride 2
comparison visits 12 positions and produces 3×4 per filter. Unknown cells are gray;
computed zeros are white. A dark cell is a larger response, not probability.

The next layer has two 3×3×2 filters, stride 1/no padding/no bias. Output filter 0
uses 1/9 for each coefficient in channel 0 and 1/18 in channel 1; filter 1 reverses
those channel coefficients. Sum all 18 contributions, then ReLU, yielding 3×5×2.
Each output map is averaged over its 15 positions. A final chosen 2×2 matrix
[[1,−0.5],[−0.5,1]] combines the means into two illustrative scores. They are not
class probabilities or evidence of correct recognition. Isometric stacks encode
actual channel counts and shapes; no fabricated learned feature labels.

| Chapter | Visible mechanism |
| --- | --- |
| 1 | One 3×3 patch with its actual multiply-and-add |
| 2 | Vertical filter moves; first output map fills, all 35 positions |
| 3 | Horizontal filter moves; second map fills, all 35 positions |
| 4 | Stride 2 moves two cells; a smaller map fills at 12 positions |
| 5 | 3D schematic: input → two maps → deeper two maps |
| 6 | A 3×3×2 filter combines both input-channel patches |
| 7 | Pool deeper maps and mix them into two computed scores |
| 8 | The first convolution unrolled as a 70×63 matrix |
| 9 | Large side-by-side counts and a fully free Dense matrix schematic |

**Parameter comparison is only for the FIRST layer, bias excluded.** A general
63→70 Dense layer has 4410 independent weights. Two 3×3 convolution filters have 18.
The exact unrolled convolution matrix has 630 nonzero entries; repeated entries
are tied to those 18 filter coefficients. Writing a CNN as a matrix does NOT turn
these copies into 4410 trainable parameters. A locally connected unshared variant
would have 630. Chapter 8 shows actual tied matrix entries and computed outputs;
chapter 9 shows empty Dense parameter slots and dimensions, not made-up weights
or outputs. Dense/CNN have the same input/output dimensions, not a claimed
equal accuracy. The tied matrix and convolution output agree numerically on
three complete inputs, including zero and signed data, after the same ReLU.
Two-layer shapes, constant-channel sums and stride 2/stride 1 subsampling are checked.

## Dropout: 5 → 10 → 5 → 2, eight chapters

Source: Srivastava et al. (2014),
[Dropout: A Simple Way to Prevent Neural Networks from Overfitting](https://jmlr.org/papers/v15/srivastava14a.html),
§§2,4–5 and Figure 2. Use the original paper's unscaled training/test-time weight
scaling convention throughout, not inverted dropout.

Five fixed inputs [1,.5,1.5,.75,1.25] pass through two ReLU hidden layers (10 and 5
units) and two linear outputs. Deterministic signed weights, zero biases, exact
formulas in `review/learning_foundations_v2.py`. Inputs and outputs are not dropped.
Hidden gates are independent Bernoulli(.5), generated by Random(23), five masks.
The actual number retained varies; exactly half is not enforced. The final
seeded draw drops all five units of the second hidden layer; its zero outputs
are explicitly explained on screen rather than presented as a typical half mask.

| Chapter | Visible mechanism |
| --- | --- |
| 1 | All four layers, 110 connections, and two calculated scores |
| 2 | Some first-hidden-layer nodes and their incident paths are omitted |
| 3 | Second-hidden-layer nodes are also omitted |
| 4 | Pulses follow participating paths through the layers |
| 5 | Two subsequent mask combinations change the participating network |
| 6 | Two more combinations change both hidden layers again |
| 7 | Prediction restores all nodes; both hidden outgoing matrices are scaled |
| 8 | The objective: reduce reliance on a fixed team of units |

Node numbers identify positions, not activations. X marks dropout, not a zero
ReLU value. Line thickness does not encode the learned weight. Pulses indicate
flow only; scores are computed from the full deterministic network. Gray paths
are inactive in the shown mask. Weights remain fixed to isolate gating; this is
not an actual learning run or measured generalization improvement.
At prediction, W1 stays unchanged; W2 and W3 are each multiplied by 0.5. No claim
that this nonlinear network exactly equals an ensemble average. All-dropped
hidden-layer controls give zero scores, and independent path sums verify outputs.
In this zero-bias positively homogeneous example, test scores happen to be 0.25
times the unmasked score; that is not a general identity for arbitrary networks.

## Review and delivery

Ten/nine/eight chapters are intentional; count follows the explanation, not a
fixed template. Scan frames run quickly; explanatory stages hold longer. Every
chapter has a full-size static image for reading at one's own pace. EN and KO
have equivalent scope. GIF duration, decoded frame count, and every decoded frame's pixels are verified in CI.
The review bundle has a 12 MB cap and is generated only in GitHub Actions.

Review these revised explanations and their difficulty before any polished video
or production interaction. The current live collection remains three lessons.
