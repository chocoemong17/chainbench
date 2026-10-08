# A short route for teaching with ChainBench

[한국어](TEACHING_GUIDE.ko.md) · [Open the six lessons](https://chocoemong17.github.io/chainbench/papers/)

Choose **one** paper for a 30-minute session. Watch its film (30–59 seconds), rehearse
the control sequence below, and read its misconception note before presenting.
You do not need to derive the equations; the original paper and mathematical
scope remain available for follow-up. English is the default; the language button
changes the localized films where available and the captions. Adam uses the
same visual film with localized page text and captions.

## Attention — change what you are looking for

[Open Attention](https://chocoemong17.github.io/chainbench/papers/attention/)

**Say:** A question changes which information we give more weight to; we then
combine the information using those weights.

**Try:** Open the folded activity above the graphs. With Mia selected, drag
match strength to 0: all three shares are equal. Increase it to 4, then choose
Ava and Ben in turn. The dominant location changes with the selected name.

**Notice:** Each name has an assigned location: Ava → Library, Ben → Garden,
Mia → Studio. At strength 4, the selected location contributes about 96.5%; the
other two still contribute about 1.8% each. At 0, each contributes one third.
Individually rounded labels need not add to exactly 100.

**Connect:** Looking up where a friend is starts by finding the relevant name,
then using that person's location. The toy assigns these links explicitly; real
Transformer representations and Q/K/V projections are learned.

**Avoid:** Calling the weights confidence that an answer is true, or saying that
Attention always chooses only one item. The sentence/head picture is schematic.

## ResNet — keep the input and add a correction

[Open ResNet](https://chocoemong17.github.io/chainbench/papers/resnet/)

**Say:** One path carries the original information; another adds a correction.
During learning, both paths can carry information about how error changes.

**Try:** In Forward, drag correction strength to 0, then 1. The displayed input
stays 2.0 while the output moves from 2.0 to 2.1. Switch to Backward and trace the
arrows returning through both paths. In the second graph, compare 0 and 8 blocks.

**Notice:** The target is 2.2, so a correction of 0.1 leaves an error. The first
control changes chosen parameters; it does not run training. The second graph is
a separate toy: its starting signal is 100; at 8 blocks the displayed magnitudes
are less than 1 and about 43. These are not accuracy percentages.

**Connect:** Revising a drawing can preserve useful parts and add a correction.
This analogy describes a residual; a network must still learn that correction.

**Avoid:** Saying gradients never vanish with shortcuts, or that backpropagation
itself updates the weights. Backpropagation computes gradients; an optimizer
uses them to update weights. This example assumes active ReLU gates.

## Adam — different coordinates can need different step sizes

[Open Adam](https://chocoemong17.github.io/chainbench/papers/adam/)

**Say:** Adam uses recent gradients and their squared sizes to adapt its updates
for different coordinates.

**Try:** Watch the steep valley, pause near the held target-entry moment, and
drag the existing timeline backward to compare the paths. Ask which direction
makes progress difficult before revealing the rest of the film.

**Notice:** Under this lesson's stated settings, Adam settles into the declared
target at update 66, Momentum at 611, and gradient descent does not within 1,200
updates. The camera cutaway makes the steep height and valley depth visible.

**Connect:** A landscape can be steep in one direction and gentle in another.
Using coordinate-wise history can help here; it is not knowledge of the destination.

**Avoid:** Claiming Adam always wins. This is a selected constructed example with
disclosed settings, not a reproduction of a full training benchmark.

## Backpropagation — calculate how each variable affects the error

[Open Backpropagation](https://chocoemong17.github.io/chainbench/papers/backprop/)

**Say:** Send values forward, trace the error backward, then use the resulting
sensitivities to change the variables toward a target.

**Try:** Watch the 59-second film. Set completed updates to 0 and switch between
Forward and Backward. Follow both branches of `AB + CDE`. Move the update slider
to 1, then slowly to 6; the second diagram follows the same selected update.

**Notice:** The target is 4. Output starts at 2, becomes about 3.4330 after the
first update and 3.9965 after the sixth. Gradients are recalculated each time and
all five variables change together; the chart is a computed trace.

**Connect:** When a recipe misses a target, knowing which ingredients affect the
result helps choose adjustments. This example makes those sensitivities explicit.

**Avoid:** Saying backpropagation alone changes the weights, splitting an
addition's incoming derivative in half, or promising every step size reduces
error. Backprop computes gradients; gradient descent with the chosen rate 0.02
produces these six updates. This five-variable fixture is not a trained network.

## CNN — reuse one filter across locations

[Open CNN](https://chocoemong17.github.io/chainbench/papers/cnn/)

**Say:** Slide the same small filter over an image, record a response at each
location, then combine response maps through later layers.

**Try:** Move the scan from the first to the last position. Compare the vertical
and horizontal filters; inspect the numbered input patch, multiplication and
output. Switch stride 1 to 2. In the second diagram, move layer depth from 0 to 2.

**Notice:** Stride 1 produces 35 positions per filter; stride 2 produces 12.
Two filters make two maps. The deeper illustration always uses stride 1 and
combines both channels. Nonzero cells show numbers; gray output cells are not
visited yet. Zero cells are blank.

**Connect:** The same small pattern can occur anywhere in an image. Reusing the
filter lets a network check for that pattern at many positions.

**Avoid:** Saying 18 shared weights and 4,410 independent dense weights have the
same accuracy. The comparison matches first-layer input/output shapes, excludes
bias and uses stride 1; stride 2 changes the dense count to 1,512. Filters here
are chosen for demonstration; scores are not trained class probabilities.

## Dropout — change which hidden units participate

[Open Dropout](https://chocoemong17.github.io/chainbench/papers/dropout/)

**Say:** During training, randomly omit some hidden units so the network cannot
always rely on the same combination. At prediction, use all units with the
chosen scaling convention.

**Try:** Move through all five training draws in the 3→5→5→2 network. Follow
crossed-out units and their inactive connections. Select Prediction and observe
all hidden units return; compare both displayed scores.

**Notice:** There are 50 connections and two hidden layers. Draw 3 happens to
omit the entire first hidden layer, so both scores are zero. The example keeps
this outcome. Prediction scales the outgoing weights of each hidden layer by
0.5, matching the original paper's convention.

**Connect:** Practising with changing teammates can illustrate why one fixed
combination should not be the only available route.

**Avoid:** Claiming these fixed-weight mask changes demonstrate improved accuracy,
permanently delete neurons, or equal the exact average of all nonlinear networks.
The original training/prediction convention differs from modern inverted dropout.

## A 30-minute student-led session

| Minutes | Activity |
| --- | --- |
| 0–3 | Introduce the everyday question and open one lesson. |
| 3–6 | Watch the film; replay a scene if needed. |
| 6–18 | Predict a change, operate the controls, then explain what moved. In pairs, switch the operator halfway through. |
| 18–25 | Share an observation and connect it to the everyday example. Revisit a confusing word or graph. |
| 25–30 | Complete the optional ten-choice survey and show the link for later use. |

If only a projector is available, describe the session as a demonstration. Let
students suggest settings; offer turns if feasible. Watching a peer's screen is
not recorded as personally operating it. The activity is exploratory, with no
score, sign-in, new installation or collection of student answers by the website.

The site's folded “What to notice” note lets students check their own observation.
Invite a guess before opening it; guesses are part of the activity, not an exam.

## Feedback and deeper reading

The [classroom-use record](CLASSROOM_PILOT.md) includes all ten survey questions
and response distributions. Participation is optional; report findings as
perceived understanding and interest. Prefer aggregate results for sharing.

Use [Attention/ResNet sources and exact scope](VISUAL_PAPERS.md),
[Adam's example](ADAM_FILM.md), [the three foundations](FOUNDATIONS.md),
and the original-paper links on each lesson when
preparing for a deeper question. Report an unclear explanation through the
repository's existing issue templates, including the lesson and language.
