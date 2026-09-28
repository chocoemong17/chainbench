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
