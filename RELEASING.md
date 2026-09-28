# Releasing ChainBench

ChainBench uses semantic versioning while the project is experimental.

## Before a release

1. Ensure `main` is green on every supported Python version.
2. Run `ruff check .`, `pytest`, and `chainbench check all`.
3. Update `CHANGELOG.md` with user-visible changes.
4. Confirm that every paper-specific check has a public citation in `REFERENCES.md`.
5. Build the package locally and inspect the wheel/sdist contents.
6. Create an annotated version tag and a GitHub release from that tag.

A release should not claim adoption, downloads, or external validation that the
repository cannot substantiate.
