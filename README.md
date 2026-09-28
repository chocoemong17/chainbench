# ChainBench

[![tests](https://github.com/chocoemong17/chainbench/actions/workflows/tests.yml/badge.svg)](https://github.com/chocoemong17/chainbench/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

**ChainBench** is a small, transparent reproducibility project for classic results in optimization and iterative numerical methods.

Instead of introducing new theory, it implements well-known algorithms from the literature and runs deterministic numerical **consistency checks** on problems with exact solutions. The goal is to make it easy to answer questions such as:

- Does a standard accelerated-gradient implementation respect the familiar `O(1/k^2)` bound on a concrete smooth convex problem?
- Does Polyak's heavy-ball method exhibit the contraction predicted by its quadratic spectral analysis?
- Does conjugate gradient respect its classical condition-number convergence envelope?
- Does FISTA satisfy its standard objective-gap bound on a LASSO instance whose exact optimum is known?

ChainBench deliberately uses the word **check**, not *proof*. A finite numerical experiment can catch implementation mistakes and reproduce a published phenomenon, but it cannot establish a theorem.

## Bundled literature checks

| Command | Literature result | What is checked |
|---|---|---|
| `nesterov-1983` | Nesterov acceleration | Standard `O(1/k^2)` smooth-convex gap bound on a deterministic quadratic |
| `polyak-1964` | Polyak heavy-ball | Tail contraction versus the quadratic spectral-radius prediction |
| `hestenes-stiefel-1952` | Conjugate gradient | Classical A-norm error envelope on a deterministic SPD quadratic |
| `beck-teboulle-2009` | FISTA | Standard `O(1/k^2)` composite-objective gap bound on diagonal LASSO |
| `ista-vs-fista` | ISTA/FISTA | Same-budget empirical comparison on the bundled LASSO instance |
| `gd-baseline` | Gradient descent | Standard `O(1/k)` smooth-convex gap bound |

See [REFERENCES.md](REFERENCES.md) for bibliographic details and links to the original sources.

## Install

```bash
python -m pip install -e .
```

For development:

```bash
python -m pip install -e '.[dev]'
pytest
```

## Quick start

List the available checks:

```bash
chainbench list
```

Run one literature check:

```bash
chainbench check nesterov-1983
```

Run everything:

```bash
chainbench check all
```

Machine-readable output:

```bash
chainbench check all --json
```

The command exits with a non-zero status if a bundled quantitative consistency condition fails, so it can also be used in CI.

## Why exact-solvable instances?

A numerical reproduction is much easier to interpret if the reference optimum is not itself estimated numerically. ChainBench therefore starts with:

- diagonal smooth convex quadratics with a known optimizer, and
- diagonal-design LASSO problems whose minimizer is available coordinatewise by soft thresholding.

This keeps the checks deterministic, dependency-light, and auditable.

## Example output

```text
[CONSISTENT] FISTA
Reference : A. Beck and M. Teboulle (2009), A Fast Iterative Shrinkage-Thresholding Algorithm for Linear Inverse Problems
Check     : On a diagonal LASSO instance with an exact optimizer, FISTA stays below the standard O(1/k^2) objective-gap bound.
Metric    : max_k gap_k / bound_k
Observed  : ...
Threshold : 1
```

## Scope

ChainBench contains **implementations and reproducibility experiments for published methods only**. It does not contain unpublished optimization results, private derivations, or claims of new optimality/uniqueness results.

The initial release focuses on three widely cited algorithmic ideas. Future contributions can add another paper when the check is:

1. tied to a clear public reference,
2. reproducible from a deterministic instance,
3. tested against a concrete published formula or qualitative prediction, and
4. careful not to turn a finite experiment into a theorem claim.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md). A good contribution adds one public reference, one small implementation or experiment, and tests that make the reproduction auditable.

## License

MIT. See [LICENSE](LICENSE).
