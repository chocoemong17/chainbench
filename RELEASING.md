# Releasing ChainBench

## Release gate

Version metadata lives in `pyproject.toml`, `src/chainbench/__init__.py` and `release-manifest.json`; keep all three aligned and update `CITATION.cff` to the same release version. Add matching notes in `docs/RELEASE_NOTES_<version>.md` and update the changelog. Review changes through a pull request and merge only after CI passes.

A change to `release-manifest.json` on `main` triggers the release workflow. Manual dispatch from main is also available. The workflow first reuses all nine validation jobs: six compatibility configurations, offline report-browser checks, audited reading generation and clean package installation. The installation job builds wheel and sdist and installs each in a fresh virtual environment outside the checkout. It runs `pip check`, the installed CLI, all numerical conditions and every export format. It also runs each installed experiment preset, saves/reloads its configuration and checks JSON/CSV/Markdown equivalence. Each distribution must record this evidence before publication.

Reading generation audits all 25 HTML pages and 24 numerical records, renders the two-page PDF, and packages the original bytes with a member manifest. It extracts the resulting ZIP and checks its reports in offline desktop/mobile Chromium. The package job downloads these reading assets from the same workflow run, attaches them to its verified distributions and validates all eight release files. A separate main-only publishing job downloads that exact tested artifact. It does not rebuild distributions or regenerate reports under write permissions.

The gate binds `verification.json` to the tested commit and rechecks the recorded artifact hashes, recognized successful statuses, unique check names, all nine saved-comparison scenarios, export evidence and checksum manifest. It refuses unexpected files or symlinks. Reading verification additionally checks source/version/renderer bindings, strict ZIP member names and types, internal hashes, numerical/PDF audit fields, bounded expansion and equality of the standalone and embedded PDF. Rehashing an altered ZIP's outer manifest is insufficient to bypass its inner checks. Exact tag matching and annotated-tag resolution prevent an existing wrong-target tag from being reused; API failures stop the job.

Only after these checks does it create a **draft GitHub prerelease** at the exact tested commit. The eight assets are the wheel, sdist, reading ZIP, PDF, `verification.json`, `reading-verification.json`, `build-environment.txt` and `SHA256SUMS`. Uploaded files are downloaded again, compared by SHA-256 and passed through the full file verifier before the draft is published. Existing releases at a different commit are not overwritten; bump the version instead. An existing partial draft causes a stop for inspection rather than an automatic destructive retry.

No PyPI publishing, payment, PAT, account-wide secret or third-party service is configured. Only the main publishing job gets `contents: write`; validation is read-only, and external actions are pinned to verified commit SHAs. All runners are standard GitHub-hosted runners.

## Validation commands

For this repository's managed task, full validation and generation run on GitHub
Actions to keep the local task folder below 1 GB. These commands document the
source checks for other development environments; package installation alone
does not generate or validate the reading assets.

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

Stored-input evidence is mandatory for both installed distributions:
ten named generated/imported cases, exact input/manifest fingerprints, independent
scalar audits, retained HTML samples and actual replay agreement. Missing,
misordered or malformed cases fail publication; the seventh fault injection
checks this boundary. [Workflow contract](docs/STORED_INPUTS.md).

Studio evidence is also mandatory: both installed commands must
serve six independently audited live cases, reject all eight declared invalid
requests, shut down and leave no server-created files or session material in
outputs. Missing or mistyped evidence fails publication. An eighth targeted
fault injection checks this gate. [Studio contract](docs/STUDIO.md).
