# Propose one clear explanation

Start with an inexpensive concept sketch. Maintainer review of the mechanism,
example and difficulty comes before polished film production. A polished render
alone is not evidence that beginners understand the method.

Copy this outline into a [paper proposal](https://github.com/chocoemong17/chainbench/issues/new?template=paper_check.yml)
or a draft PR. Rough SVGs, a numbered scene list or a small computed table suffice.
There is no fixed four-scene limit.

1. **Audience and one sentence:** who is reading, and what should they notice?
2. **Public source:** original paper, section/equation, and the exact mechanism.
3. **Concrete example:** inputs, parameters, reference values and the reason this
   example reveals the mechanism. Identify constructed versus paper-supplied data.
4. **Scene sequence:** what moves, what stays fixed, and what the viewer should
   compare at each step. Show failure or limitations when needed for the claim.
5. **Two interactions:** what each control changes and the expected observation.
6. **Boundaries:** what this example cannot establish; language and accessibility
   needs; whether another numerical convention would change the explanation.
7. **Verification:** an independent calculation, source-to-record mapping and
   intended browser checks. Do not copy the implementation as its own oracle.

## Filled example: the existing backpropagation lesson

- **Audience:** a beginner comfortable with multiplication and addition.
- **Sentence:** send values forward, compute sensitivities backward, then use
  those sensitivities to update the variables toward a target.
- **Source:** Rumelhart, Hinton & Williams (1986), pp. 533–534. The branched
  expression `y = AB + CDE` is a constructed chain-rule illustration.
- **Fixture:** `[A,B,C,D,E] = [2,3,2,-1,2]`, target 4, half-squared loss;
  all five variables update simultaneously using learning rate 0.02.
- **Scenes:** detailed first forward/backward pass, first updated output, five
  more forward/backward/update cycles, then a held convergence chart. Keep the
  repeated updates visible instead of spending the entire film on one gradient.
- **Interactions:** scrub completed updates; switch the graph's flow direction.
  The selected graph and output chart must describe the same numerical row.
- **Observation:** output goes from 2 to about 3.4330 after one update and about
  3.9965 after six. Backprop computes gradients; gradient descent applies updates.
- **Boundary:** this is not a trained neural network or a proof that every
  learning rate improves loss. The separate rate-0.5 example increases loss.
- **Checks:** independent central differences for every initial gradient and
  full-precision saved trajectories; keyboard, pointer and language checks.

[Actual implementation, sources and timing](FOUNDATIONS.md). This is a reusable
proposal example, not a request to redo the already approved lesson.
