# ChainBench v0.2.1 — exact-reference input usability

This maintenance alpha release responds to a concrete input-usability issue found
while evaluating v0.2.0. It does **not** widen the project's research claims.

## Float32 reference construction

The strict three-argument `QuadraticProblem(Q, b, x_star)` constructor intentionally
requires the declared reference to satisfy `Q @ x_star = b` at float64-relative
precision. A right-hand side first computed in float32 can differ after promotion,
which previously produced a correct but poorly explained rejection.

When `b` is conceptually *defined by* a reference point, use:

```python
problem = QuadraticProblem.from_reference(Q, x_star)
```

The factory promotes the inputs to float64 first and then computes the stored
right-hand side, so the stored reference is stationary for the stored problem.
The original strict constructor is not relaxed and an independently supplied
inconsistent `b` is never silently rewritten.

## Concrete workflows

New documentation gives copyable examples for:

- checking an implementation change against the fixed public-source suite,
- changing a deterministic quadratic's condition number without editing Python,
- inspecting small trajectories for teaching/debugging,
- comparing frozen-release observations across machines,
- constructing an exact-reference quadratic from lower-precision source arrays.

These examples explain plausible uses of the existing small synthetic fixtures.
They are not claims that outside researchers have adopted the project.

## Scope

ChainBench remains experimental alpha software with NumPy as its only runtime
dependency. No private research, real-name maintainer metadata, telemetry, paid
service, API integration, external registry publication, or theorem-certification
claim is added.
