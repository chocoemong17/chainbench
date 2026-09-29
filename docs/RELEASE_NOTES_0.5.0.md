# ChainBench v0.5.0 - one plot for intuition, many cases for evidence

This experimental alpha release responds directly to external feedback that a single attractive loss curve can look cherry-picked and that numerical plots alone do not explain **where an optimizer is moving**.

## Four evidence layers

The learning atlas now distinguishes:

1. the public literature claim and assumptions,
2. one transparent canonical illustration,
3. reproducible seeded stress across many synthetic instances,
4. a tight/worst-case case study only when public literature provides the extremal construction.

A canonical plot is explicitly labelled as ChainBench-generated rather than implied to be a figure from the original paper.

## Many-case stress

```bash
python -m chainbench stress nesterov-1983 --trials 24 --seed 0 --lang ko --output stress.html
```

All eight bundled topics can be sampled. Seeds and instance parameters are preserved in JSON. Bound-based topics report how many sampled metrics stay under the selected envelope. Heavy-ball's 8% line remains an empirical regression tolerance, not a theorem. ISTA/FISTA remains descriptive and has no universal pass/fail threshold.

Finite sampling broadens numerical evidence but does not prove a theorem or certify a worst case.

## See the path in the objective landscape

```bash
python -m chainbench landscape --condition-number 20 --methods gd smooth-fista heavy-ball cg proximal-point --lang ko --output landscape.html
```

The same 2D quadratic run is shown as:

- a shared contour map,
- a projected 3D objective surface,
- separate method-specific contour panels,
- and the corresponding objective-gap curve.

This geometric problem is intentionally selected to make zig-zagging, momentum, conjugate directions and implicit steps visible. It is an illustration rather than representative performance evidence.

## Deeper paper context

Every learning topic now adds why the work mattered, its main strength, its trade-offs, the neighboring method to compare with, and the evidence type. A compact timeline connects CG, heavy-ball, proximal point, Nesterov acceleration, FISTA and Frank-Wolfe.

## Compatibility and boundaries

The existing `check`, `report`, `experiment`, `sweep`, `replay` and `case-study gd-tight` workflows remain available. NumPy is still the only runtime dependency. No private research, external datasets, telemetry, paid service, PyPI publication, theorem-by-screenshot claim or fabricated adoption evidence is added.
