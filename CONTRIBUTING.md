# Contributing

ChainBench reproduces public, published optimization results.

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
