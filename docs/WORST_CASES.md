# Difficult instances, random instances and certified worst cases

Several outside users asked whether ChainBench can choose a different "space", make
one randomly, or construct a worst-case space. These are different requests.

## What users can already change

The configurable quadratic preset exposes dimension, condition number, smoothness
scale, rotation choice, iteration budget and compatible methods. LASSO exposes its
dimension and regularization level; simplex exposes dimension. Saving the JSON config
makes those choices explicit and reproducible.

These controls create **different deterministic instances**. They do not certify that
an instance is worst-case.

## Random is not worst-case

A seeded random instance can be useful for robustness testing, but "hard among the
samples we tried" is not the same as a mathematical worst case. Adding randomness
also requires the generator, seed and generated inputs to be recorded so another
machine can reconstruct what was tested.

ChainBench therefore does not label a sampled or user-chosen instance "worst case"
without a public theorem that identifies the class, algorithm, performance measure
and extremal construction.

## What a certified worst-case feature would require

A future worst-case demonstration should name, from public literature:

- the function/problem class,
- the algorithm and allowed information model,
- the iteration horizon,
- the performance criterion,
- the theorem or construction establishing extremality,
- the exact mapping from that construction to executable data.

Private or unpublished derivations are outside this repository. A literature-motivated
hard example may be added without being called worst-case if it is useful and honestly
labeled.

## Implemented in v0.4.0: one explicit tight GD construction

The new `case-study gd-tight` command illustrates Drori--Teboulle's public construction for constant-step GD with 0<h<=1. It is not a general search facility. The matching theorem, function, horizon and limitations are specified in [GD_TIGHT_CASE.md](GD_TIGHT_CASE.md).


## v0.5.0: sampled breadth without abusing the word worst-case

`chainbench stress` now generates many reproducible synthetic instances for every bundled topic. This is useful evidence against cherry-picking, but it remains finite sampling. The command deliberately calls its output *stress evidence*, not worst-case evidence. `chainbench landscape` is an even narrower geometric illustration. Only a public extremal construction such as the GD case above is labelled tight.
