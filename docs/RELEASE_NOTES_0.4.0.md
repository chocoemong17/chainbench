# ChainBench v0.4.0 — learn, vary one thing, replay

This alpha release adds four completed workflows driven by the owner's request
and relayed outside reproduction feedback; it does not introduce a new optimizer.

1. **Learn**: Korean/English offline pages connecting the motivation, assumptions,
   implemented recurrence, selected result, actual plot, interpretation and limits.
   Search/filter topics, expand normalized bound ratios, and save the embedded JSON.
2. **Sweep**: vary a single supported configuration field across 2–8 values. Validate
   all points and the combined work budget before execution; preserve each result.
3. **Replay**: recompute a saved schema-1 experiment and compare complete observations,
   inputs and environments. Missing evidence is not a successful comparison.
4. **Public GD tight case**: reproduce the specific 1D construction in Drori--Teboulle,
   preprint Theorems 3.1/3.2, for GD step h/L with 0<h<=1. A changed horizon changes
   the function. It is not an arbitrary-method worst-case search engine.

```bash
python -m chainbench learn --lang ko --output learn.html
python -m chainbench sweep --preset quadratic --parameter condition_number --values 10 100 1000 --methods gd cg --output sweep.html
python -m chainbench experiment --preset quadratic --output saved.json
python -m chainbench replay saved.json --output replay.html
python -m chainbench case-study gd-tight --horizon 20 --output tight.html
```

Local browser controls never upload data or run a new optimizer. No server, API
key, paid service or extra runtime dependency is required. Python/NumPy computation
happens before HTML generation. In addition to existing gates, both wheel and sdist
must pass independent installed-CLI checks for all four workflows before publishing.

The original eight fixed checks, old reports, public Python APIs and the frozen
v0.2.0 review kit are retained. Existing releases are not replaced. `report` still
defaults to HTML and `experiment` still defaults to JSON.

Finite observations, internally run tests and example exports are not theorem
proofs, endorsements or new outside users. Public maintainer remains chocoemong17;
no private research or real-name metadata is added. All new features remain alpha.
