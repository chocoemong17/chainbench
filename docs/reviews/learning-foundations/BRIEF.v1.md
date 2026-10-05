# Filled concept brief: learning foundations, revision 1

**Status: waiting for owner review.** Existing Adam, Attention and ResNet remain
the only completed visual lessons. No final film, production route or new
classroom observation is included in this round.

Audience: first-time learners, around the owner-approved Attention/ResNet
explanation depth (owner described that level as about 5). Basic multiplication
is enough for the front-facing story; exact contracts stay here.

## 1. Backpropagation — priority one

Takeaway: reuse forward calculations to work out how each weight affects the
loss; an optimizer then uses these derivatives to change the weights.
Connects to Adam's update rule and ResNet's backward path.

Source: Rumelhart, Hinton & Williams (1986),
[Learning representations by back-propagating errors](https://doi.org/10.1038/323533a0),
pp. 533–534, error derivatives propagated backward through layers.
[Author-hosted paper](https://www.cs.toronto.edu/~hinton/absps/naturebp.pdf).
This is a representative landmark, not a claim that reverse differentiation
was first invented in this paper.

| Scene | Visible change | Fixed reference |
| --- | --- | --- |
| Prediction | Input 2 passes through weights 1 and 0.5, yielding 1 | Target 2 |
| Backward signal | Arrows reverse; gradients −1 and −2 appear at their weights | Original forward values reused |
| Update | Weights become 1.1 and 0.7; output becomes 1.54 | Same input and target |
| Roles | Backprop and optimizer roles separated | Two operations in the same learning loop |

Constructed linear chain: h=w1*x, y=w2*h, L=(y−2)^2/2. No biases/activation.
At x=2,w1=1,w2=.5: h=2,y=1,L=.5; dL/dw1=−1,dL/dw2=−2.
One simultaneous gradient-descent update at rate .1 gives L=.1058.
This illustrates the chain rule but does not reproduce the paper's sigmoid
network, representation-learning experiment or training-speed results.
Check both derivatives with central finite differences at four different weight
pairs, including zero weights. Rate 0 changes nothing; rate 2 increases loss.
No statement that every update helps or backprop itself chooses the step.

After approval: step forward/backward/update separately; drag learning rate and
observe an oversized-step failure. Keep derivatives folded until requested.

## 2. CNN — priority two

Takeaway: a learned local detector is reused across positions; different detectors
make different response maps. Connects to the feature maps used by ResNet.

Source: LeCun, Bottou, Bengio & Haffner (1998),
[Gradient-Based Learning Applied to Document Recognition](https://bottou.org/papers/lecun-98h),
§II, local receptive fields, shared weights and feature maps.
We explain this mechanism, not all of LeNet-5 or a full digit recognizer.

| Scene | Visible change | Fixed reference |
| --- | --- | --- |
| Local detector | A selected 3×3 patch gives response 6 | Our own 7×9 binary-bar image |
| Move the image | One-cell input shift moves its response | Same filter |
| Two detectors | Vertical versus horizontal response maps | Same input |
| Sharing | 18 shared weights versus 630 position-specific weights | Two 3×3 filters, 35 positions each; bias excluded |

Vertical kernel: three rows of [−1,2,−1]; horizontal kernel is its transpose.
Valid stride-one cross-correlation followed by ReLU, no padding/bias. This modern
teaching operator is not claimed to be the original LeNet activation/pooling.
Output is 5×7. Window row2/col1 yields vertical6/horizontal0; row3/col5 yields
horizontal6/vertical0 (zero-based indices). Verify by direct dot products and a
one-cell translation in the common valid interior. No claim of full translation
invariance, superiority to all dense networks or measured accuracy. Filters are
hand-set here; a real CNN learns them.

After approval: drag the window, move the input and switch filters; then a second
small comparison for shared parameters. Avoid adding a whole classifier now.

## 3. Dropout — priority three

Takeaway: temporarily vary which units participate during training, reducing
reliance on a fixed combination; use all units with appropriate scaling at test.
Connects to generalization after learning and feature extraction.

Source: Srivastava et al. (2014),
[Dropout: A Simple Way to Prevent Neural Networks from Overfitting](https://jmlr.org/papers/v15/srivastava14a.html),
§§2,4–5 and Figure2. Use the paper's unscaled training / test-time weight scaling
convention. Do not mix it with inverted dropout's train-time scaling.

| Scene | Visible change | Fixed reference |
| --- | --- | --- |
| Full network | Four features feed one sum, output10 | Features [1,2,3,4], unit weights |
| One training mask | Gates [1,1,0,0], output3 | Same features and weights |
| Another mask | Gates [0,0,1,1], output7 | Same features and weights |
| Test mode | All return, outgoing weights ×.5, output5 | Retention probability p=.5 |

These are two chosen masks, not a simulation claiming exactly half always stay.
Every gate is independent Bernoulli(p); all16 combinations are possible. Enumerate
all16 and their probabilities: expected linear sum=10p; at p=.5 it is5.
Test scaling matches this linear expectation. It does not exactly average an
arbitrary nonlinear network: mean ReLU(sum−6) is nonzero while ReLU(mean(sum)−6)=0.
No weights are trained here; the masks do not demonstrate an accuracy gain.
Units are not permanently pruned and the changing output is not measured uncertainty.

After approval: inspect masks and retention probability, then switch to prediction
mode. Keep the purpose of reducing co-adaptation visible without inventing a
before/after accuracy chart.

## Common review gate

Ask the owner about **mechanism visibility, amount of explanation and difficulty**
for each topic. A response may approve one and request changes to another.
Maintain separate statuses. Only approved concepts advance to polished videos.
Cloud arithmetic, text bounds/glyph coverage and image decoding are technical
checks; the owner has not yet approved these scenes or their difficulty.
