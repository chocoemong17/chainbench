# Contributing

ChainBench explains public machine-learning papers and reproduces scoped
optimization results. Contributions can improve an explanation, translation,
control or numerical example; adding another algorithm is not required.

## Start with a small contribution

- Report a [confusing lesson step](https://github.com/chocoemong17/chainbench/issues/new?template=lesson_feedback.yml),
  including the topic, language and video time or control. No learner identities.
- Correct a translation or inaccessible label with the old wording, proposed
  wording and the page where it appears. Keep mathematical meaning unchanged.
- Propose a new explanation using the [outline and filled example](docs/LESSON_PROPOSAL.md).
  Submit a rough scene sequence first. Wait for mechanism/difficulty review before
  polishing media; accepted numerical results alone do not approve a teaching design.

Existing lesson HTML lives in `web/papers/`; pure computed fixtures live in
`src/chainbench/visual_papers.py` and `src/chainbench/foundations.py`. The latter
three lessons share `web/papers/foundations/lesson.js`. Source and convention notes
are in [VISUAL_PAPERS](docs/VISUAL_PAPERS.md), [FOUNDATIONS](docs/FOUNDATIONS.md),
and [SOURCE_MAP](docs/SOURCE_MAP.md).

Keep videos under one minute, preserve pause/seek/caption access and keyboard
alternatives to dragging, and supply English plus Korean wording where practical.
Use original or appropriately licensed assets; link papers instead of copying PDFs.

## Numerical changes

A good contribution includes:
1. a public paper or textbook reference,
2. a compact implementation,
3. a deterministic problem with an exact or independently verifiable reference quantity,
4. a clearly stated numerical consistency check, and
5. tests.

Please do not add unpublished/private research or claim that a finite experiment proves a theorem.

Development:

```bash
python -m pip install -e '.[dev]'
pytest
ruff check .
chainbench check all
```

Independent reruns compare computed floating values with the canonical trajectory
tolerance (`rtol=1e-12`, `atol=1e-14`), not bitwise equality. The test helper in
`tests/_numeric_records.py` keeps JSON numeric types, shape, inputs/config, hashes, strings,
counts, booleans and missing values exact, and rejects nonfinite values. It is
only for independent recomputation: serialization, embedded previews and views
of the same computed record still require exact equality. The scientific bounds,
independent validators and file-integrity checks retain their own unchanged contracts.
HTML retention tests capture the actual chart passed to the renderer and compare
the entire embedded chart record exactly, without recomputing a reference chart.
NumPy `float64` and its decoded JSON float share the floating-number contract;
neither can substitute for an integer count or boolean flag.

Do not raise this tolerance to hide larger trajectory drift. The Intel CG failure
required a scalar-accumulation repair, with the comparison gate retained.
[Controlled diagnosis and arithmetic contract](docs/CG_ARITHMETIC.md).

Interactive reports also have optional offline Playwright checks in `scripts/check_*_browser.py`.
For example, with Playwright and Chromium available:

```bash
python -m chainbench geometry ista-fista --output proximal.html
python scripts/check_proximal_browser.py --html proximal.html --output browser-check/proximal
```

The proximal checker visits every stored stage of both methods in all nine cases at desktop
and mobile widths. It dispatches the report's synchronous slider handler and collects one
DOM snapshot per stage; Python independently calculates the expected model curves and dual
plane/surface coordinates. Missing or duplicate elements, non-finite coordinates, truncated
paths and incorrect readouts fail the check. Keyboard, playback, download and JavaScript-free
fallback checks still use browser interactions. The output JSON counts compared frames and
points; batching DOM reads does not sample or skip stages. The pure checker tests use a
hand-calculated fixture and corrupted coordinates without requiring Playwright.
