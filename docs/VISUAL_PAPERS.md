# Attention and ResNet: from approved concept to interactive explanation

Each lesson keeps the accepted layout: a 48-second film, two interactive diagrams,
a short takeaway and the paper link. Four twelve-second chapters follow the
owner-approved revision3 of the review on branch `study/method-concepts` (74ce5f6).
The explanation level was approved as sufficient; equations stay folded. Adam,
the 25 numerical reports and all publication gates remain unchanged.

English is the default. Korean changes both the page and the actual film labels,
preserving playback time. Each language has MP4/WebM, poster and native captions.
Chapter buttons and the film slider pause/seek; the two exploration diagrams have
separate controls so readers can experiment without jumping around the movie.
No autoplay, audio, remote fonts, trackers, third-party videos or runtime packages.

## Attention: match first, then collect information

Vaswani et al., [Attention Is All You Need](https://arxiv.org/html/1706.03762v7),
§3.2.1 Eq.(1), §§3.2.2–3.2.3. We compute `softmax(Q K^T / sqrt(3)) V`.
Three keys are the basis vectors e0,e1,e2, labeled Ava, Ben, Mia. Values are the
same basis vectors with different labels: Library, Garden, Studio. For a selected
name j, Q = sqrt(3)*s*ej. The slider varies the selected scaled score s from0 to4,
not model training or a measured semantic similarity. At4 the exact selected
share is exp(4)/(exp(4)+2) ≈.964663, the others ≈.017668. Main display rounds to
[2,2,96]% for Mia; readouts give one decimal place. Independently rounded shares
need not always total exactly100. They are not answer-confidence probabilities.

Chapters: Q/K/V roles → softmax shares → weighted collection as Mia's query moves
to Ava's → self-attention/multiple heads in a sentence. In chapter3,
Q=sqrt(3)*4*[u,0,1-u], where u is a smooth interpolation from0 to1. Every displayed
weight and output is recomputed from that query. Movement along links indicates
information flow, not a measured runtime or magnitude; bar lengths encode weights.
Interactive name selection and match strength use the same computation/fixtures.

The cat/sofa/sleeps scene is an explicitly authored relationship diagram. It does
not report trained attention weights or assert fixed “who/where” head roles.
Actual Transformer Q/K/V are learned projections of representations. Full training,
masking, positional encoding and translation benchmark reproduction are outside
this illustration. Original diagrams only; no paper figures or video are copied.

## ResNet: preserve, correct, then send learning signals backward

He et al., [Deep Residual Learning](https://arxiv.org/html/1512.03385v1), §§3.1–3.2,
Eq.(1) and post-add ReLU; [Identity Mappings](https://arxiv.org/html/1603.05027v3),
§2 Eqs.(3)–(5). The2016 derivation assumes identity after addition. Our post-add
ReLU scalar examples are locally active (gate derivative1). Neither source makes
the blanket claim that shortcuts always preserve gradients.

The first film scene illustrates the residual learning target using an original
9×9 house grid. Two cells are added ([5,3],[5,5]) and one removed ([6,4]); the
correction interpolates from0 to this signed grid. This is a feature illustration,
not an image-restoration experiment. Zero residual preserves nonnegative inputs
through the final ReLU; negative inputs can still be clipped.

The next two scenes use x=2, F(x)=−.1 ReLU(x)+.3, y=ReLU(x+F(x)), target2.2,
L=.5(y−target)^2. Thus F=.1, y=2.1, loss=.005. Incoming gradient−.1 splits into
shortcut−.1 and branch+.01; the input receives−.09. The branch's output-weight
gradient is−.2. Qualitative reverse arrows explain how gradients guide changes;
backprop calculates derivatives, and an optimizer updates weights afterward.
The first interactive diagram lets the reader switch directions and scale both
branch weights/bias by a in[0,1]. It is a parameter sweep, not a training run.

The depth scene is a SEPARATE chosen local-derivative comparison. Plain maps:
ReLU(−.1x+1.1). Residual maps: ReLU(x−.1x+.1). Both keep x=1 at1; all gates active;
terminal loss .5*y² supplies gradient1. After n blocks the signed initial gradients
are (−.1)^n and .9^n. The bars show MAGNITUDES normalized to100 on a fixed linear
scale. At n=8: .000001 versus43.046721, displayed “<1” and “43”. The film progresses
from0 to8 blocks; the second diagram explores0–16. The two full mappings differ,
with independently chosen biases. This is not an equal-budget trained-network
benchmark, speed/accuracy result, or guarantee. A branch slope−1 cancels the direct
term; an inactive final ReLU also blocks the signal. Larger is not always better.

## Implementation and evidence

`src/chainbench/visual_papers.py` owns pure numerical fixtures and frame states.
The renderer creates1,152 frames at1280×720/24fps per language per paper. Actual
BT.709 conversion and metadata are retained. Each frame's dots move along the
declared paths; numeric bars/grids evolve according to the fixtures. Scene holds
leave reading time. All generated media are hashed in experiment.json and the
website manifest; binaries live in Actions/Pages, not the source tree.

Cloud tests independently check NumPy attention arithmetic, normalization and
permutation behavior, grid changes, forward values, finite-difference input and
weight gradients, signed deep-chain derivatives and cancellation/gate controls.
Chromium/WebKit ×1440/390 verify both languages: decoded numeric colors/boundaries,
within-scene motion, unobscured captions, all chapter controls, range keyboard and
pointer drags, numerical SVG widths/readouts, localization with playback-time
retention, collapsed MathML, gallery/no-script/error states and no external requests.
Selected cloud screenshots receive manual visual review before publication.
Full PR/main tests and gated exact-artifact Pages publication remain mandatory.

The additional Backpropagation, CNN and Dropout lessons have their own
[source and numerical contract](FOUNDATIONS.md).
