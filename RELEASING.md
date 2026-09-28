# Releasing ChainBench

ChainBench uses semantic versioning while the project is experimental.

## Before a release

1. Ensure `main` is green on every supported Python version.
2. Run `ruff check .`, `pytest`, and `chainbench check all`.
3. Update `CHANGELOG.md` with user-visible changes.
4. Confirm that every paper-specific check has a public citation in `REFERENCES.md`.
5. Confirm that the packaging job builds both wheel and sdist.
6. Create a tag such as `v0.1.0` from the intended `main` commit.

Pushing a `v*` tag triggers `.github/workflows/release.yml`. The workflow
re-runs linting, tests, all numerical checks, builds the distributions, and
creates a GitHub release with those artifacts attached.

The release workflow does **not** publish to PyPI or any paid/external registry.

A release should not claim adoption, downloads, or external validation that the
repository cannot substantiate.
