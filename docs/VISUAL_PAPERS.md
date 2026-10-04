# Attention and ResNet: one core operation, one film

The public collection at `/papers/` contains Adam, Attention and ResNet. Each
lesson keeps the accepted video-first layout: one 48-second film, two draggable
plots, a brief explanation, and a direct paper link. English is the default;
Korean copy and native captions are optional. The existing 25 reports remain
available. The homepage links prominently to the film collection.

## Attention: exact operation and authored inputs

Vaswani et al., *Attention Is All You Need*, NeurIPS 2017,
[arXiv:1706.03762v7](https://arxiv.org/html/1706.03762v7), §3.2.1, Eq. (1):
`softmax(Q K^T / sqrt(d_k)) V`.

The lesson implements a single query with `d_k=2`. Its length is 4 and its angle
sweeps from 0 to 180 degrees in one-degree samples. The four keys are `(1,0)`,
`(0,1)`, `(-1,0)`, `(0,-1)`. RGB values, independently chosen from the keys, are
`(.88,.25,.20)`, `(.22,.68,.47)`, `(.23,.45,.85)`, `(.89,.65,.22)`.
A max-shifted softmax computes the weights and the actual weighted output.
The diagram's query direction, percentages, connection widths and output color
all use those computed values. The two plots show all four weights and all
three output channels as the angle varies. Both plots seek the same film state.
The scale division is retained; the range slider changes the query angle, not
softmax temperature or a training iteration.

These are constructed color vectors. Colors do not claim learned language
semantics or attention explanations of a real language model. This is the
scaled dot-product core, not an implementation of the complete Transformer,
learned Q/K/V projections, multiple heads, masking, positional encoding or
paper translation experiments. No figures or video footage are copied.

## ResNet: identity shortcut and a chosen residual branch

He et al., *Deep Residual Learning for Image Recognition*, CVPR 2016,
[arXiv:1512.03385v1](https://arxiv.org/html/1512.03385v1), §3.2, Eq. (1) and the
post-addition ReLU described immediately below it. The branch uses two hidden
ReLU units, with W1=[[1],[0]], b1=[0,1], W2=a[.8,-.4], b2=0.
For each input pixel x, `F(x)=a(.8 ReLU(x)-.4 ReLU(1))`, and output is
`ReLU(x+F(x))`. Biases are explicit additions to the simplified source notation.

The original 32×32 binary ring/diagonal pattern generates low-contrast inputs
`.25 + .5 pattern` and a declared contrast target `.05 + .9 pattern`.
The same branch is applied independently to every pixel. Parameter a sweeps
from 0 to 1 in increments .01; these weights are authored, not fitted.
At a=0 the nonnegative input passes unchanged; at a=1 the output matches this
target up to rounding. Final ReLU remains present. Zero F does not preserve
negative input through that ReLU, and the code/tests explicitly retain this
limitation. This is one small residual block, not a trained convolutional ResNet,
ImageNet reproduction or comparison with independently trained plain networks.

Input and output are grayscale; the residual uses a signed colormap with teal
for positive changes, orange for negative changes, and neutral gray at zero.
Its scale is fixed ±.2 throughout the film. The first graph inspects row 16
(zero-based) of input, residual and output. Dragging that spatial graph selects
a pixel, not a time. The second graph shows actual full-image RMSE against the
declared target, with a as its horizontal axis. Dragging it or the slider seeks
the film. Neither axis is labeled as training time or a neural-network benchmark.

## Shared motion, accessibility and verification

Both films use 1280×720 pixels, 24 fps, and 1,152 frames. The shared timing knots
are (0,0), (4,0), (22,half), (25,half), (41,last), (48,last). Each frame selects
an actual computed parameter sample; every sample appears, with holds at the
start, middle and end. The recorded mapping drives all browser seeking.
Native captions occupy the reserved top header and are tested against the
same paused film with captions hidden; no caption pixels may cover the diagram.
No audio or autoplay. A visible poster/play control, native media controls,
keyboard-operable range, reduced-motion behavior, data-failure notice and
no-JavaScript MP4 access are preserved. Formulae in the folded details use
native MathML, not raw LaTeX.

Tests compare attention with independent NumPy matrix arithmetic, check
normalization, permutation behavior, zero query and stable softmax, and reject
invalid inputs. Residual checks independently evaluate the two-layer network,
all 101 full-image outputs and RMSEs, zero-branch behavior and final activation.
The film build verifies decoded frame counts/dimensions/duration with FFprobe.
Chromium and WebKit each check both lessons at 1440 and 390 pixels: actual
playback/decoded colors, every graph path coordinate, numerical readouts,
pointer/keyboard seeking, spatial pixel selection, English/Korean, caption
occlusion, gallery navigation, offline assets, no-script and data-failure paths.

All numerical execution, movie rendering and browser tests run on GitHub
Actions. Full PR/main validation and the existing gated Pages workflow remain
required. The exact browser-tested site artifact is hashed before publication.
Source records, media and website manifests are publicly inspectable. Existing
releases and immutable Adam selection evidence remain unchanged.
