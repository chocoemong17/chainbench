# ChainBench benchmark report

Deterministic numerical consistency checks for public, published results.

| Check | Status | Observed | Threshold | Metric |
|---|---|---:|---:|---|
| gd-baseline | CONSISTENT | 0.04231974 | 1 | max_k gap_k / bound_k |
| nesterov-1983 | CONSISTENT | 0.07520596 | 1 | max_k gap_k / bound_k |
| polyak-1964 | CONSISTENT | 0.01692285 | 0.08 | relative error: observed tail ratio vs predicted rho |
| hestenes-stiefel-1952 | CONSISTENT | 0.5 | 1 | max_k \|\|e_k\|\|_Q / (2 rho^k \|\|e_0\|\|_Q) |
| jaggi-2013 | CONSISTENT | 0.3675 | 1 | max_k gap_k / (2 C_f / (k+2)) |
| beck-teboulle-2009 | CONSISTENT | 0.1425624 | 1 | max_k gap_k / bound_k |
| ista-vs-fista | CONSISTENT | 0.009192292 | 1 | FISTA final gap / ISTA final gap |

A consistent row means the bundled finite experiment satisfies its stated
numerical condition. It is not a mathematical proof of the cited result.
