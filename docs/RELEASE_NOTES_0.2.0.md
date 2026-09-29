# ChainBench v0.2.0 — configurable, reproducible experiments

This additive experimental alpha release makes the existing algorithms usable from
an installed wheel, without editing Python or cloning the source repository.

## New user workflow

```bash
python -m chainbench experiment --preset quadratic --format markdown --output experiment.md
python -m chainbench preset diagonal-lasso --output config.json
python -m chainbench experiment --config config.json --output result.json
```

Three preset families (quadratic, diagonal-LASSO, simplex) expose dimensions,
iteration budgets, compatible method selections and supported numerical parameters.
Versioned JSON is strictly parsed; unknown/duplicate fields, invalid combinations
and oversized work requests fail rather than being silently ignored. Coordinate
vectors are optional. Existing check/report commands and method APIs remain available.

## What a result contains

Every format retains the normalized config, configuration/input SHA-256 fingerprints,
minimal software environment and trajectories. Stationarity metrics are named for
each problem family. CG's convergence is checked against its true residual; other
methods report only completion of the requested budget. Equal iteration counts do
not imply equal work. These observations are not theorem certificates or a universal
algorithm ranking. Hashes identify settings/bytes, not independent proof of execution.

## Release validation

The validation workflow retains the numerical regression suite and four targeted
fault injections. It runs the new config/CLI/serialization tests and clean-installs
both wheel and sdist outside the source checkout. Each installed distribution must
execute all three presets, rerun saved configs and match its JSON/CSV/Markdown
exports. Publication checks the corresponding evidence before uploading and verifies
the downloaded assets. See attached verification.json, SHA256SUMS and environment
record for the actual build, installation and provenance evidence.

## Scope

See docs/EXPERIMENTS.md, docs/SOURCE_MAP.md and docs/REVIEWER_GUIDE.md. The fixtures
remain small and synthetic. Floating-point portability is not bitwise identity;
minimal environment metadata is not a full lockfile. No private research, real-name
maintainer metadata, API use, telemetry, paid service or PyPI publication is added.
Existing v0.1.0 and v0.1.1 artifacts are not overwritten.
