# An external review you can actually reproduce

This is an invitation to inspect a small experimental project, not a claim that an
independent reviewer has already approved it. Maintainer-assisted tests, automated
PRs and release downloads by validation jobs are not external adoption evidence.

## One-file review helper

The [fixed-release review kit](../review/README.md) checks the published wheel,
records public synthetic observations and compares reports without executing their
contents. It also explains privacy, tolerances and inconclusive input-byte differences.
Share an actual attempt through [issue #28](https://github.com/chocoemong17/chainbench/issues/28).
No outside review has been inferred from this invitation or from CI activity.

## Start with the released package

For a new manual review, prefer the latest v0.3.0 GitHub prerelease. The standalone
`review/` helper is intentionally pinned to v0.2.0 so its historical cross-platform
baseline does not move underneath existing reports. Install the version you intend
to review in a new virtual environment, not over an editable source install, then run:

```bash
python -m chainbench --version
python -m chainbench check all --json
python -m chainbench preset quadratic --output review-config.json
python -m chainbench experiment --config review-config.json --output review-result.json
```

The JSON result retains the exact normalized config plus software versions. You
can compare the output from `--preset quadratic` with that saved-config run.
Review the seven quantitative conditions and the INFO observation separately;
`CONSISTENT` is a finite experiment result, not a theorem certification.

## Examine one mathematical connection

Read [SOURCE_MAP.md](SOURCE_MAP.md) and choose a single method. Check the update,
indexing, assumptions and measured formula rather than just whether the green
label appears. For a tiny case with coordinates, inspect the two-dimensional diagonal GD case in `tests/test_experiments.py`
or the hand-computed recurrence tests. A missing FISTA momentum term should not survive those tests.

## Inspect negative cases

A valid review can focus on malformed input, an exhausted CG budget, a mislabeled
metric, a missing measurement or unsafe publication evidence. The test suite and
four targeted fault injections demonstrate specific cases; they are not exhaustive.
To run them in a source checkout:

```bash
python -m pip install -e '.[dev]'
python -m pytest
python scripts/check_mutations.py
```

## Report an actual observation

Use the reproducibility feedback issue form for a successful or failed attempt.
Include the release/version, OS/Python/NumPy, command, a **public synthetic** config,
expected behavior, actual result and any reduced counterexample. Preserve meaningful
error text, but remove credentials, account paths and private datasets before posting.
A reproduction failure or unclear explanation is useful feedback; no star, positive
review or endorsement is requested or required.

Do not post unpublished derivations, another person's private work, API keys, or
sensitive input files. Contributors remain free to use their public pseudonyms.
No success claims should be added to the README until supported by a real report.
