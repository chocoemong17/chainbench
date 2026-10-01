# What produced the canonical curve?

Development source after v0.5.0 adds instance context to the existing eight fixed
demonstrations. A new plot is not needed to expose missing context: the numerical
series, check metrics, source claims and default fixtures remain the same.

```bash
python -m chainbench learn --focus beck-teboulle-2009 --lang ko --output fista.html
python -m chainbench report --output report.html
python -m chainbench plot nesterov-1983 --output acceleration.svg
```

Learning and report pages place a concise setup before each detailed plot. Native
details reveal the exact inputs, reference optimizer, method parameters and input
fingerprint. The standalone SVG includes a visible caption, source URL and the
same instance object in its JSON metadata. It can therefore be shared separately
without losing the setup. HTML plots retain the metadata while using their
adjacent setup panel for presentation.

## The recorded instance

`charts[topic].instance` has `kind: canonical-fixed-instance` and retains:

- Problem family, objective, dimension, selected claim and primary source URL.
- L and applicable mu, conditioning, lambda or curvature; actual squared radius.
- `budget`, method parameters, completed updates, termination and true residual
  where the method exposes it. A budget is a limit, not a padded trajectory length.
- Actual input arrays: Q/b/reference for quadratics, a/b/lambda for diagonal LASSO,
  or target for simplex, plus the actual shared x0 from the returned traces.
- Reference optimizer and objective, plotted quantity and sample-index ranges.
- `seed: null`, explicitly labelled deterministic formulas with no random sampling.
- The input SHA-256 over sorted array names, shape and little-endian float64 bytes,
  using the same documented format as inspectable stress. The hash binds the input
  arrays, including x0; it does not authenticate an author or include run settings.

The smooth-convex quadratic contains a zero eigenvalue. Its mu is zero and its
condition number is **undefined**, stored as null, not a finite substitute or a
non-standard JSON infinity. Its zero-start squared radius is retained explicitly.
Frank–Wolfe starts at e1, not the infeasible zero vector. Method settings distinguish
fixed-L acceleration, quadratic heavy-ball tuning, CG residual tolerances, scheduled
Frank–Wolfe updates, and the exact quadratic PPA parameter.

The instance is captured from the same problem and trace objects used to construct
the chart, rather than a separate hand-written table of fixture defaults. The full
iterates are not duplicated in these records: retained inputs and options can rerun
the existing methods, while every plotted sample remains in the series. Use the
separate experiment, geometry or stress workflows when per-step vectors are needed.

## Validation and compatibility

Tests reconstruct problems from the retained arrays, rerun each method using the
recorded settings, and compare every observed sample, update count and termination.
Installed wheel and sdist smoke independently checks the byte fingerprint,
constants, first update and reference curves using Python's standard library.
Corrupted inputs, hash, L, step, sample, bound, budget or update count are rejected.
This validator intentionally covers the current fixed diagonal fixtures; it does
not certify arbitrary user-supplied matrices or saved reports.

Browser checks cover all eight report panels, a focused learning page and a
standalone SVG at 1440/390px. Full-input expansions must match embedded records;
caption text must fit inside the SVG viewBox. The pages remain readable offline
and without JavaScript. This is validation of presentation and finite computation,
not a proof of the literature result or representative empirical sampling.

The chart record adds optional `instance` metadata (`null` for unrelated generic
charts). Existing series and fixed `check`/JSON/CSV/Markdown report outputs retain
their numeric semantics. Standalone canonical SVGs grow vertically to fit their
captions; consumers should use the viewBox rather than assume a fixed height.
No previous release, frozen review kit, optimizer API or schema-1 experiment/replay
contract is changed.
