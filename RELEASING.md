# Releasing ChainBench

## Release gate

Version metadata lives in `pyproject.toml`, `src/chainbench/__init__.py` and `release-manifest.json`; keep all three aligned. Add matching notes in `docs/RELEASE_NOTES_<version>.md` and update the changelog. Review changes through a pull request and merge only after CI passes.

A change to `release-manifest.json` on `main` triggers the release workflow. Manual dispatch from main is also available. The workflow first reuses the full cross-platform validation workflow. A separate main-only publishing job then builds wheel and sdist and installs each in a fresh virtual environment outside the checkout. It runs `pip check`, the installed CLI, all numerical conditions and every export format.

The gate binds `verification.json` to the tested commit and rechecks the recorded artifact hashes, recognized successful statuses, unique check names, export evidence and checksum manifest. It refuses unexpected files or symlinks. Exact tag matching and annotated-tag resolution prevent an existing wrong-target tag from being reused; API failures stop the job.

Only after these checks does it create a **draft GitHub prerelease** at the exact tested commit. Distribution files, the clean-install report, build environment and SHA256SUMS are uploaded. The uploaded files are downloaded again and compared by SHA-256 before the draft is published. Existing releases at a different commit are not overwritten; bump the version instead. An existing partial draft causes a stop for inspection rather than an automatic destructive retry.

No PyPI publishing, payment, PAT, account-wide secret or third-party service is configured. Only the main publishing job gets `contents: write`; validation is read-only, and external actions are pinned to verified commit SHAs. All runners are standard GitHub-hosted runners.

## Local checks

```bash
python -m pip install -e '.[dev]'
ruff check .
python -m pytest
python scripts/check_mutations.py
python -m build
python scripts/smoke_install.py
```

`dist/verification.json` records what was actually installed and executed. A successful build alone is not a successful clean installation. A generated release alone is not evidence of external adoption.

Technical reference for tag matching: [GitHub Git references REST API](https://docs.github.com/en/rest/git/refs). The endpoint is a prefix search; the publisher selects only the exact tag. Release enumeration uses [GitHub CLI pagination](https://cli.github.com/manual/gh_api), so a network error never implies an empty result.
