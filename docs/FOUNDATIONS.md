# Backpropagation, CNN and Dropout — visual lessons

Three approved examples join the existing Adam, Attention and ResNet collection.
Each has a localized film, two draggable diagrams, a short optional activity and
an original-paper link. English is the initial language; Korean is selectable.
The original v3 concepts and their review history remain on
[the review branch](https://github.com/chocoemong17/chainbench/tree/study/learning-foundations/docs/reviews/learning-foundations).
The owner approved refinement on 2026-10-08. This approval concerns the explanation
and difficulty; it is not a measured learner outcome.

## Sources and exact examples

**Backpropagation.** Rumelhart, Hinton & Williams (1986),
[Learning representations by back-propagating errors](https://doi.org/10.1038/323533a0),
pp. 533–534, forward values and backward derivatives. The expression y = AB + CDE
is our constructed chain-rule example, not the paper's sigmoid experiment or a
claim of historical priority for reverse differentiation. Initial A…E are
[2, 3, 2, −1, 2], target is 4, and L = (y−4)²/2. Initial gradients are
[−6, −4, +4, −8, +4]. Six simultaneous gradient-descent steps use rate 0.02,
recomputing gradients from the current state each time. Outputs are
2, 3.433024, 3.802286, 3.928439, 3.973801, 3.990370, 3.996455 (rounded).
Backprop supplies gradients; the optimizer changes values. Addition passes the
incoming derivative to each branch, without dividing it by two. Multiplication
uses the other factor. A rate 0.5 control increases loss, so monotonic improvement
is claimed only for the six displayed updates, not arbitrary rates or functions.

The film lasts **59 seconds**: ten four-second chapters, thirteen seconds for
updates 2–6, then six seconds on the convergence chart. Forward/backward/update
states last approximately 0.7/0.7/1.2 seconds at 25 fps; boundaries round to the
nearest frame. Values never interpolate between numerical states. The chart and
both interactive diagrams select the same complete update from the seven-row trace.

**CNN.** LeCun, Bottou, Bengio & Haffner (1998),
[Gradient-Based Learning Applied to Document Recognition](https://bottou.org/papers/lecun-98h),
§II: local receptive fields, weight sharing, maps and successive layers. Chosen
filters and modern ReLU are teaching choices; this is not trained LeNet-5.
A binary 7×9×1 input, two 3×3 kernels (vertical: each row [−1,2,−1]; horizontal:
its transpose), valid cross-correlation, no bias or padding, followed by ReLU,
produce 5×7×2 at stride 1 or 3×4×2 at stride 2. Every scan position is shown.
Readable nonzero cells have numbers; zero cells are blank, while unvisited cells
are gray. Current input window, multiply-add and written output agree exactly.

The deeper illustrated network always uses **stride 1** and is labeled as such
independently of the first diagram's stride control. Two 3×3×2 filters combine
both incoming channels. Output filter 0 uses channel coefficients 1/9 and 1/18;
filter 1 reverses them. The resulting 3×5×2 maps are averaged, then multiplied by
[[1,−0.5],[−0.5,1]] to obtain two scores, not probabilities. The film lasts 44.72s.

First-layer parameter counts exclude bias. Two shared 3×3 filters have 18 weights.
A freely learned 63→70 Dense map has 4,410; at stride 2 the matching 63→24 map has
1,512. This compares input/output shapes, not accuracy. The 70×63 matrix equivalent
to the stride-one convolution has 630 nonzero entries tied to those 18 filter
coefficients; writing convolution as a matrix does not make its entries independent.

**Dropout.** Srivastava et al. (2014),
[Dropout: A Simple Way to Prevent Neural Networks from Overfitting](https://jmlr.org/papers/v15/srivastava14a.html),
§§2,4–5 and Figure 2. The 3→5→5→2 network has 50 connections, two ReLU hidden
layers, fixed signed weights and zero biases. Five independent Bernoulli(0.5)
hidden masks use seed 23. Inputs and outputs are retained. Node labels identify
positions, not activations. A cross marks omission, which differs from a zero
activation at a participating node. Draw 3 omits the entire first hidden layer,
so both scores are zero in this fixture; this draw is retained and explained.

Use the original paper's unscaled training / prediction-time weight scaling
convention throughout: W1 stays unchanged; W2 and W3 are each multiplied by 0.5
at prediction, with every node restored. No inverted-dropout convention is mixed
in. Nonlinear ensemble equality, trained accuracy and generalization improvement
are not claimed. The 30s film and interactive scores use the same masks and weights.

## Implementation and verification

- `src/chainbench/foundations.py`: pure fixtures, full-precision records and timelines.
- `scripts/foundation_board.py`, `foundation_scenes.py`, `render_foundations.py`:
  restrained film palette, direction pulses, checked glyphs and text bounds,
  MP4/WebM, English/Korean posters and WebVTT captions. Motion illustrates flow;
  numerical states change only at declared boundaries.
- `web/papers/{backprop,cnn,dropout}/`: films first, diagrams second, details folded.
  `web/papers/foundations/`: shared behavior and styles, no third-party runtime.
- `tests/test_foundations.py`: independent central differences, tensor convolution,
  tied matrix equivalence, second-layer sums, dropout matrix products, controls,
  contiguous frames and the under-one-minute backprop timing contract.
- `scripts/check_foundations_browser.py`: Chromium/WebKit, 1440/390px, both languages,
  all numeric selections, SVG quantities, real pointer and keyboard controls,
  every film chapter decoded, playback and language changes, no horizontal overflow,
  no-script access and missing/invalid-record failure. The complete existing
  website and numerical checks remain in the required `tests` workflow.

Production uses the existing gated Pages workflow: all jobs must succeed for the
current main source, then exactly that website artifact is verified and deployed.
Review images live on a separate branch and do not publish the production website.
The 150-response classroom evidence describes the previously shown material;
these newly refined lessons have no new survey or learning-effect claim.
