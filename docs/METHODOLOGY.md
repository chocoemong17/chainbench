# Reproducibility methodology

ChainBench is a numerical reproduction project. Its checks are designed to make
published optimization results easy to inspect, rerun, and regression-test.

## What a successful check means

A successful check means that one deterministic finite experiment is consistent
with a stated public result. It does not prove the theorem, establish worst-case
optimality, or validate behavior outside the tested instance.

The repository therefore avoids wording such as "proves the theorem" or
"verifies the result in general."

## Design principles

### 1. Public source first

Every paper-specific check must point to a public paper, publisher page, DOI,
or stable bibliographic page. The numerical statement implemented in code
should be recognizable from that source or a standard treatment of the result.

### 2. Independently verifiable reference quantity

Prefer problems where at least one of the following is available without
running a second optimizer:

- an exact optimizer,
- an exact optimal objective value,
- a closed-form residual or contraction factor,
- an exact spectral quantity for the constructed matrix, or
- a deterministic upper bound stated by the public result.

This prevents one numerical method from silently becoming the ground truth for
another.

### 3. Deterministic fixtures

Bundled checks should be deterministic across runs. If randomness is ever
necessary, the seed and distribution must be explicit and the test should not
depend on a fragile single random draw.

### 4. Numerically meaningful tolerances

Floating-point comparisons need tolerances tied to the scale and purpose of the
check. A tolerance should be loose enough to avoid platform-specific noise but
tight enough to catch a real implementation regression.

### 5. Small, auditable implementations

The core algorithms intentionally depend only on NumPy. A literature check is
more useful when a reader can inspect the implementation without traversing a
large framework.

## Review questions

Before merging a new check, ask:

1. Is the referenced result public and clearly identified?
2. Does the implementation match the algorithm being cited?
3. Is the benchmark instance deterministic?
4. Can the reference solution or bound be checked independently?
5. Does the test fail if the implementation is meaningfully perturbed?
6. Is the README wording careful about the difference between reproduction and proof?
7. Does the change avoid private or unpublished research?

## Scope boundary

ChainBench only contains public, published material and original glue code
needed to reproduce it. Private notes, unpublished derivations, confidential
benchmarks, and new theorem claims do not belong in this repository.
